"""Saved URLs, evidence review, drafts and report versions. Fully local; no outbound calls."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import Response

from deeptrace.evidence.models import (
    AnswerSave,
    AnswerView,
    EvidencePassageView,
    NoteSave,
    NoteView,
    ReportCreate,
    ReportSummary,
    ReportView,
    SavedUrlCreate,
    SavedUrlView,
)
from deeptrace.storage.synthesis_repository import SynthesisRepository

router = APIRouter(prefix="/api/investigations/{identifier}")


def repository(request: Request) -> SynthesisRepository:
    return SynthesisRepository(request.app.state.database)


Repo = Annotated[SynthesisRepository, Depends(repository)]
Offset = Annotated[int, Query(ge=0, le=1000000)]
Version = Annotated[int, Path(ge=1, le=1000000)]


@router.get("/saved-urls", response_model=list[SavedUrlView])
def saved_urls(identifier: UUID, repo: Repo, offset: Offset = 0) -> list[dict[str, Any]]:
    return repo.saved_urls(str(identifier), offset)


@router.post("/saved-urls", status_code=201, response_model=SavedUrlView)
def save_url(identifier: UUID, data: SavedUrlCreate, repo: Repo) -> dict[str, Any]:
    return repo.save_url(str(identifier), data)


@router.get("/passages", response_model=list[EvidencePassageView])
def passages(identifier: UUID, repo: Repo, offset: Offset = 0) -> list[dict[str, Any]]:
    return repo.investigation_passages(str(identifier), offset)


@router.get("/evidence-notes", response_model=list[NoteView])
def notes(identifier: UUID, repo: Repo) -> list[dict[str, Any]]:
    return repo.notes(str(identifier))


@router.put("/evidence-notes", response_model=NoteView)
def save_note(identifier: UUID, data: NoteSave, repo: Repo) -> dict[str, Any]:
    return repo.save_note(str(identifier), data)


@router.get("/answer", response_model=AnswerView)
def answer(identifier: UUID, repo: Repo) -> dict[str, Any]:
    return repo.answer(str(identifier))


@router.put("/answer", response_model=AnswerView)
def save_answer(identifier: UUID, data: AnswerSave, repo: Repo) -> dict[str, Any]:
    return repo.save_answer(str(identifier), data)


@router.get("/reports", response_model=list[ReportSummary])
def reports(identifier: UUID, repo: Repo) -> list[dict[str, Any]]:
    return repo.reports(str(identifier))


@router.post("/reports", status_code=201, response_model=ReportView)
def create_report(identifier: UUID, data: ReportCreate, repo: Repo) -> dict[str, Any]:
    return repo.create_report(str(identifier), data)


@router.get("/reports/{version}", response_model=ReportView)
def report(identifier: UUID, version: Version, repo: Repo) -> dict[str, Any]:
    return repo.report(str(identifier), version)


@router.get("/reports/{version}/download")
def download(identifier: UUID, version: Version, repo: Repo) -> Response:
    saved = repo.report(str(identifier), version)  # Verifies the stored checksum first.
    # Server-chosen ASCII name; no user text reaches the header or the filesystem.
    name = f"deeptrace-report-{str(identifier)[:8]}-v{version}.md"
    return Response(
        saved["markdown_text"].encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "X-Report-SHA256": saved["markdown_sha256"],
        },
    )
