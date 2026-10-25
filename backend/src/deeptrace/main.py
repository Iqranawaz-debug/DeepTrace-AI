"""Read-only local API with safe, fixed-shape diagnostics."""

import json
import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from deeptrace.config import Settings
from deeptrace.providers import ProviderBoundary
from deeptrace.storage.database import Database

logger = logging.getLogger("deeptrace")


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
    phase: int = 1
    mode: str
    research: bool = False
    outbound: bool = False
    investigations: bool = False


def get_database(request: Request) -> Database:
    return request.app.state.database  # type: ignore[no-any-return]


def get_providers(request: Request) -> ProviderBoundary:
    return request.app.state.providers  # type: ignore[no-any-return]


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    database = Database(config.data_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            database.migrate()
        except Exception:
            logger.error('{"event":"startup_failed"}')
            raise RuntimeError("Database initialization failed; inspect migration setup.") from None
        yield

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def local_boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = request.headers.get("host", "").lower()
        origin = request.headers.get("origin")
        if host not in {
            "localhost",
            "127.0.0.1",
            f"localhost:{config.port}",
            f"127.0.0.1:{config.port}",
        }:
            return error(400, "invalid_host", "Host is not allowed.")
        if origin is not None and origin not in config.origins:
            return error(403, "invalid_origin", "Origin is not allowed.")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            return error(405, "read_only", "Phase 1 API is read-only.")
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

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error(exc.status_code, "http_error", "The requested operation is unavailable.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(422, "validation_error", "The request is invalid.")

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
        return Capabilities(mode=config.mode)

    return app
