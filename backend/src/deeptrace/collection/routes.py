"""Evidence API. Production collection admission is unconditionally disabled."""

from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from deeptrace.collection.models import (
    Consent,
    EventView,
    PassageView,
    RunStart,
    RunView,
    SourceSummary,
    SourceView,
)
from deeptrace.storage.collection_repository import CollectionRepository
from deeptrace.storage.repository import WorkspaceError

router = APIRouter(prefix="/api")


def repository(request: Request) -> CollectionRepository:
    return request.app.state.collection_repository  # type: ignore[no-any-return]


Repo = Annotated[CollectionRepository, Depends(repository)]


@router.post("/web-consent")
def consent(data: Consent, request: Request, repo: Repo) -> dict[str, bool]:
    if not request.app.state.fixture_collection:
        raise WorkspaceError(403, "live_network_disabled", "Live networking is not authorized.")
    repo.set_consent(data.accepted)
    return {"accepted": data.accepted}


@router.post("/web-consent/revoke")
def revoke(repo: Repo) -> dict[str, bool]:
    repo.set_consent(False)
    return {"accepted": False}


@router.post("/investigations/{identifier}/runs", status_code=202, response_model=RunView)
@router.post("/investigations/{identifier}/sources", status_code=202, response_model=RunView)
def start(identifier: UUID, data: RunStart, request: Request, repo: Repo) -> dict[str, Any]:
    if not request.app.state.fixture_collection:
        raise WorkspaceError(
            403, "live_network_disabled", "Live collection is disabled. No website was contacted."
        )
    if not repo.consent():
        raise WorkspaceError(
            403, "consent_required", "Approve the synthetic fixture disclosure first."
        )
    if any(urlsplit(url).hostname != "fixture.example" or urlsplit(url).query for url in data.urls):
        raise WorkspaceError(
            422,
            "fixture_only",
            "Only synthetic fixture.example URLs without queries are supported.",
        )
    if request.app.state.collection_worker.stop_event.is_set():
        raise WorkspaceError(
            503, "worker_unavailable", "Collection worker unavailable; saved evidence is retained."
        )
    return repo.start(str(identifier), data)


@router.get("/investigations/{identifier}/runs", response_model=list[RunView])
def runs(
    identifier: UUID, repo: Repo, offset: int = Query(0, ge=0, le=1000000)
) -> list[dict[str, Any]]:
    return repo.list_rows("runs", str(identifier), offset)


@router.get("/runs/{identifier}", response_model=RunView)
def run(identifier: UUID, repo: Repo, investigation_id: UUID) -> dict[str, Any]:
    return repo.run(str(identifier), str(investigation_id))


@router.post("/runs/{identifier}/cancel")
def cancel(identifier: UUID, repo: Repo, investigation_id: UUID) -> dict[str, bool]:
    repo.run(str(identifier), str(investigation_id))
    repo.cancel(str(identifier))
    return {"cancel_requested": True}


@router.get("/investigations/{identifier}/events", response_model=list[EventView])
def events(
    identifier: UUID, repo: Repo, run_id: UUID, after: int = Query(0, ge=0)
) -> list[dict[str, Any]]:
    return repo.events(str(identifier), after, str(run_id))


@router.get("/investigations/{identifier}/sources", response_model=list[SourceSummary])
def sources(
    identifier: UUID, repo: Repo, offset: int = Query(0, ge=0, le=1000000)
) -> list[dict[str, Any]]:
    return repo.list_rows("sources", str(identifier), offset)


@router.get("/sources/{identifier}", response_model=SourceView)
def source(identifier: UUID, repo: Repo, investigation_id: UUID) -> dict[str, Any]:
    return repo.source(str(identifier), str(investigation_id))


@router.get("/sources/{identifier}/passages", response_model=list[PassageView])
def passages(
    identifier: UUID, repo: Repo, investigation_id: UUID, offset: int = Query(0, ge=0, le=1000000)
) -> list[dict[str, Any]]:
    return repo.passages(str(identifier), str(investigation_id), offset)


@router.get("/passages/{identifier}", response_model=PassageView)
def passage(identifier: UUID, repo: Repo, investigation_id: UUID) -> dict[str, Any]:
    return repo.passage(str(identifier), str(investigation_id))
