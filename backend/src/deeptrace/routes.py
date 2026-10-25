"""Local workspace routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from deeptrace.models import (
    Investigation,
    InvestigationCreate,
    InvestigationEdit,
    InvestigationList,
    Plan,
    PlanSave,
)
from deeptrace.storage.repository import Repository

router = APIRouter(prefix="/api/investigations")


def repository(request: Request) -> Repository:
    return Repository(request.app.state.database)


Repo = Annotated[Repository, Depends(repository)]


@router.get("")
def list_investigations(
    repo: Repo,
    q: str = Query(default="", max_length=1000),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1000000),
) -> InvestigationList:
    return repo.list(q, limit, offset)


@router.post("", status_code=201)
def create_investigation(data: InvestigationCreate, repo: Repo) -> Investigation:
    return repo.create(data)


@router.get("/{identifier}")
def get_investigation(identifier: UUID, repo: Repo) -> Investigation:
    return repo.get(str(identifier))


@router.patch("/{identifier}")
def edit_investigation(identifier: UUID, data: InvestigationEdit, repo: Repo) -> Investigation:
    return repo.edit(str(identifier), data)


@router.get("/{identifier}/plan")
def get_plan(identifier: UUID, repo: Repo) -> Plan:
    return repo.plan(str(identifier))


@router.put("/{identifier}/plan")
def save_plan(identifier: UUID, data: PlanSave, repo: Repo) -> Plan:
    return repo.save_plan(str(identifier), data)
