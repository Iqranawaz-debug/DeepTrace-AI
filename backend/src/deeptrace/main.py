"""Local API with safe, fixed-shape diagnostics."""

import json
import logging
import logging.handlers
import secrets
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from deeptrace.collection.fetcher import Fetcher, Transport
from deeptrace.collection.fixtures import SyntheticTransport
from deeptrace.collection.live_transport import LiveTransport
from deeptrace.collection.routes import router as collection_router
from deeptrace.collection.transport import DisabledTransport
from deeptrace.collection.worker import Worker
from deeptrace.config import Settings
from deeptrace.evidence.routes import router as evidence_router
from deeptrace.providers import ProviderBoundary
from deeptrace.research.contracts import LLMProvider, SearchProvider
from deeptrace.research.credentials import (
    CredentialStore,
    WindowsCredentialStore,
    resolve_key,
)
from deeptrace.research.gateway import DISCLOSURES, Gateway
from deeptrace.research.live import GeminiLLM, TavilySearch
from deeptrace.research.mock import MockLLM, MockSearch
from deeptrace.research.pipeline import Pipeline
from deeptrace.research.routes import router as research_router
from deeptrace.routes import router
from deeptrace.security import MAX_BODY, mutation_failure
from deeptrace.storage.collection_repository import CollectionRepository
from deeptrace.storage.database import Database
from deeptrace.storage.repository import WorkspaceError
from deeptrace.storage.research_repository import ResearchRepository

logger = logging.getLogger("deeptrace")
LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 3


def rotating_log(directory: Path) -> logging.Handler | None:
    """NFR-O1: bounded local log. Every message is a fixed event, never research or secrets."""
    try:
        (directory / "logs").mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            directory / "logs" / "deeptrace.log",
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUPS,
            encoding="utf-8",
        )
    except OSError:
        return None  # Logging must never stop the application.
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return handler


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "what_failed": message,
                "what_saved": "Existing data has not been deleted.",
                "next_step": "Check the local server configuration and try again.",
            }
        },
    )


class Health(BaseModel):
    status: str
    version: str = "0.1.0"


class Capabilities(BaseModel):
    phase: int = 5
    mode: str
    research: bool = False
    outbound: bool = False
    investigations: bool = True


def get_database(request: Request) -> Database:
    return request.app.state.database  # type: ignore[no-any-return]


def get_providers(request: Request) -> ProviderBoundary:
    return request.app.state.providers  # type: ignore[no-any-return]


def create_app(
    settings: Settings | None = None,
    *,
    collection_transport: Transport | None = None,
    credentials: CredentialStore | None = None,
    search_provider: SearchProvider | None = None,
    llm_provider: LLMProvider | None = None,
) -> FastAPI:
    config = settings or Settings()
    database = Database(config.data_dir)
    fixtures = config.mode == "mock"
    live = config.mode == "live_free"
    store: CredentialStore = credentials or WindowsCredentialStore()

    collection_repository = CollectionRepository(
        database, DISCLOSURES["public_web"] if live else "fixture-v1"
    )
    research_repository = ResearchRepository(database)
    transport: Transport
    if fixtures:
        transport = collection_transport or SyntheticTransport()
    elif live:
        transport = collection_transport or LiveTransport()
    else:
        transport = DisabledTransport()
    fetcher = Fetcher(
        transport, lambda: config.mode != "offline" and collection_repository.consent()
    )
    # Live adapters exist only in live_free mode; mock and offline cannot reach a provider.
    search: SearchProvider = search_provider or (
        TavilySearch(lambda: resolve_key(store, "tavily")) if live else MockSearch()
    )
    llm: LLMProvider = llm_provider or (
        GeminiLLM(config.llm_model or "", lambda: resolve_key(store, "gemini"))
        if live
        else MockLLM()
    )
    gateway = Gateway(
        config.mode,
        research_repository,
        store,
        search,
        llm,
        not live or bool(config.llm_model) or llm_provider is not None,
    )
    worker = Worker(
        collection_repository,
        fetcher,
        Pipeline(collection_repository, research_repository, gateway, transport, fetcher.allowed),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            database.migrate()
        except Exception:
            logger.error('{"event":"startup_failed"}')
            raise RuntimeError("Database initialization failed; inspect migration setup.") from None
        log_file = rotating_log(config.data_dir)
        worker.start()
        try:
            yield
        finally:
            gateway.stop.set()
            worker.close()
            if log_file:
                logger.removeHandler(log_file)
                log_file.close()

    app = FastAPI(
        title="DeepTrace AI",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.database = database
    app.state.providers = ProviderBoundary()
    session_token = secrets.token_urlsafe(32)
    app.include_router(router)
    app.include_router(collection_router)
    app.include_router(evidence_router)
    app.include_router(research_router)
    app.state.fixture_collection = fixtures
    app.state.collection_repository = collection_repository
    app.state.gateway = gateway
    app.state.storage_warning_bytes = config.storage_warning_mb * 1_000_000
    app.state.collection_worker = worker
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-DeepTrace-Token"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def local_boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = request.headers.get("host", "").lower()
        origin = request.headers.get("origin")
        if len(request.headers.getlist("host")) != 1 or host not in {
            "localhost",
            "127.0.0.1",
            f"localhost:{config.port}",
            f"127.0.0.1:{config.port}",
        }:
            return error(400, "invalid_host", "Host is not allowed.")
        if len(request.headers.getlist("origin")) > 1 or (
            origin is not None and origin not in config.origins
        ):
            return error(403, "invalid_origin", "Origin is not allowed.")
        failure = mutation_failure(request, config.origins, session_token)
        if failure:
            return error(*failure)
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY:
                    return error(413, "request_too_large", "Request exceeds the local size limit.")
                body.extend(chunk)
            request._body = bytes(body)

        try:
            response = await call_next(request)
        except Exception:
            response = error(500, "internal_error", "The local operation failed.")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        # Never log paths, queries, headers, exception strings or response content.
        logger.info(json.dumps({"event": "request", "status": response.status_code}))
        return response

    @app.exception_handler(WorkspaceError)
    async def workspace_error(request: Request, exc: WorkspaceError) -> JSONResponse:
        return error(exc.status, exc.code, exc.message)

    @app.get("/api/session")
    def session() -> dict[str, str]:
        return {"token": session_token}

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error(exc.status_code, "http_error", "The requested operation is unavailable.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        response = error(
            422, "validation_error", "Check field lengths, required fields and identifiers."
        )
        return response

    @app.get("/api/health")
    def health() -> Health:
        return Health(status="ok")

    @app.get("/api/ready", response_model=Health)
    def ready(db: Annotated[Database, Depends(get_database)]) -> Health | JSONResponse:
        try:
            if db.ready():
                return Health(status="ready")
        except sqlite3.Error:
            pass
        return error(503, "not_ready", "The local database is not ready.")

    @app.get("/api/capabilities")
    def capabilities() -> Capabilities:
        return Capabilities(mode=config.mode, research=config.mode != "offline", outbound=live)

    return app
