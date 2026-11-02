"""Research, provider setup and investigation lifecycle API."""

from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import Response
from pydantic import Field

from deeptrace.models import StrictModel
from deeptrace.research.contracts import Budgets
from deeptrace.research.credentials import ENV_NAMES, KEY, resolve_key
from deeptrace.research.gateway import DISCLOSURES, PROVIDERS, Gateway
from deeptrace.storage.collection_repository import CollectionRepository
from deeptrace.storage.repository import WorkspaceError
from deeptrace.storage.research_repository import ResearchRepository

router = APIRouter(prefix="/api")
Version = Annotated[int, Path(ge=1, le=1000000)]
ProviderId = Literal["tavily", "gemini", "public_web"]
KeyedProvider = Literal["tavily", "gemini"]


class RunRequest(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    expected_revision: int = Field(ge=0, strict=True)
    budgets: Budgets = Field(default_factory=Budgets)


class PlanRequest(RunRequest):
    replace: bool = Field(default=False, strict=True)


class Flag(StrictModel):
    value: bool = Field(strict=True)


class DeleteRequest(StrictModel):
    confirm_title: str = Field(min_length=1, max_length=120)


class CredentialRequest(StrictModel):
    value: str = Field(min_length=8, max_length=512)


class ConsentRequest(StrictModel):
    disclosure_version: str = Field(min_length=1, max_length=64)
    free_tier_confirmed: bool = Field(strict=True)


def repository(request: Request) -> ResearchRepository:
    return ResearchRepository(request.app.state.database)


def gateway(request: Request) -> Gateway:
    return request.app.state.gateway  # type: ignore[no-any-return]


Repo = Annotated[ResearchRepository, Depends(repository)]
Gate = Annotated[Gateway, Depends(gateway)]


@router.get("/providers")
def providers(request: Request, gate: Gate, repo: Repo) -> dict[str, Any]:
    collection: CollectionRepository = request.app.state.collection_repository
    live = gate.mode == "live_free"
    described = []
    for info in PROVIDERS:
        keyed = info.credential
        has_key = keyed and resolve_key(gate.credentials, info.id) is not None
        consent = repo.consented(info.id, DISCLOSURES[info.id])
        failure = gate.last_failure.get(info.id)
        state = "Not required"
        if keyed:
            state = "Saved" if has_key else "Not configured"
            if not gate.credentials.available and not has_key:
                state = "Unavailable"
            if failure == "auth_rejected":
                state = "Invalid"
            elif failure == "quota_exhausted":
                state = "Quota reached"
        described.append(
            {
                "id": info.id,
                "role": info.role,
                "data_sent": info.data_sent,
                "notice": info.notice,
                "needs_credential": keyed,
                "credential_state": state,
                "consent": consent,
                "disclosure_version": DISCLOSURES[info.id],
            }
        )
    return {
        "mode": gate.mode,
        "gemini": "enabled" if live else "disabled",
        "tavily": "enabled" if live else "disabled",
        "live_network": live,
        "fixture_collection": request.app.state.fixture_collection,
        "consent": collection.consent(),
        "disclosure_version": collection.disclosure_version,
        "providers": described,
        "llm_model": gate.llm_provider.model if gate.llm_configured else None,
        "budgets": Budgets().model_dump(),
        "budget_ceilings": {
            name: next(m.le for m in field.metadata if hasattr(m, "le"))
            for name, field in Budgets.model_fields.items()
        },
        "blockers": gate.blockers(),
    }


@router.put("/providers/{provider}/credential")
def put_credential(provider: KeyedProvider, data: CredentialRequest, gate: Gate) -> dict[str, str]:
    if not KEY.fullmatch(data.value):
        raise WorkspaceError(422, "invalid_credential", "That does not look like an API key.")
    try:
        gate.credentials.put(provider, data.value)
    except OSError:
        raise WorkspaceError(
            503, "credential_store_unavailable", "The key could not be saved securely."
        ) from None
    gate.last_failure.pop(provider, None)
    # Write-only: the stored value is never returned.
    return {"credential_state": "Saved"}


@router.delete("/providers/{provider}/credential")
def delete_credential(provider: KeyedProvider, gate: Gate) -> dict[str, str]:
    gate.credentials.delete(provider)
    gate.last_failure.pop(provider, None)
    env_set = resolve_key(gate.credentials, provider) is not None
    # A process-environment key is outside the app's control, so say so rather than hide it.
    return {
        "credential_state": "Saved" if env_set else "Not configured",
        "environment_variable": ENV_NAMES[provider] if env_set else "",
    }


@router.post("/providers/{provider}/consent")
def grant_consent(provider: ProviderId, data: ConsentRequest, repo: Repo) -> dict[str, bool]:
    if data.disclosure_version != DISCLOSURES[provider]:
        raise WorkspaceError(409, "disclosure_changed", "Review the current disclosure first.")
    if not data.free_tier_confirmed:
        raise WorkspaceError(422, "confirmation_required", "Confirm the disclosure to continue.")
    repo.set_consent(provider, data.disclosure_version, True)
    return {"consent": True}


@router.delete("/providers/{provider}/consent")
def revoke_consent(provider: ProviderId, repo: Repo) -> dict[str, bool]:
    repo.set_consent(provider, DISCLOSURES[provider], False)
    return {"consent": False}


def _admit(request: Request, gate: Gate, repo: Repo, investigation: str, model_first: bool) -> None:
    blockers = gate.blockers()
    if gate.mode == "offline":
        raise WorkspaceError(403, "offline", blockers[0])
    if gate.mode == "mock" and not request.app.state.collection_repository.consent():
        raise WorkspaceError(
            403, "consent_required", "Approve the synthetic fixture disclosure first."
        )
    if blockers:
        raise WorkspaceError(403, "setup_required", " ".join(blockers))
    if model_first and gate.mode != "mock" and repo.sensitive(investigation):
        raise WorkspaceError(
            409, "sensitive_blocked", "Sensitive investigations are never sent to a hosted model."
        )
    if request.app.state.collection_worker.stop_event.is_set():
        raise WorkspaceError(503, "worker_unavailable", "The research worker is unavailable.")


@router.post("/investigations/{identifier}/plan/generate", status_code=202)
def generate_plan(
    identifier: UUID, data: PlanRequest, request: Request, gate: Gate, repo: Repo
) -> dict[str, str]:
    _admit(request, gate, repo, str(identifier), True)
    repo.start(
        str(identifier),
        str(data.id),
        "plan_generation",
        "mock" if gate.mode == "mock" else "live_free",
        data.budgets,
        data.expected_revision,
        data.replace,
    )
    return {"id": str(data.id)}


@router.post("/investigations/{identifier}/research", status_code=202)
def start_research(
    identifier: UUID, data: RunRequest, request: Request, gate: Gate, repo: Repo
) -> dict[str, str]:
    _admit(request, gate, repo, str(identifier), False)
    repo.start(
        str(identifier),
        str(data.id),
        "research_pipeline",
        "mock" if gate.mode == "mock" else "live_free",
        data.budgets,
        data.expected_revision,
    )
    return {"id": str(data.id)}


@router.get("/runs/{identifier}/progress")
def progress(identifier: UUID, investigation_id: UUID, repo: Repo) -> dict[str, Any]:
    return repo.progress(str(identifier), str(investigation_id))


@router.get("/investigations/{identifier}/generated-answer")
def generated_answer(identifier: UUID, repo: Repo) -> dict[str, Any]:
    return {"answer": repo.latest_answer(str(identifier))}


@router.get("/investigations/{identifier}/generated-reports")
def generated_reports(identifier: UUID, repo: Repo) -> list[dict[str, Any]]:
    return repo.reports(str(identifier))


@router.get("/investigations/{identifier}/generated-reports/{version}")
def generated_report(identifier: UUID, version: Version, repo: Repo) -> dict[str, Any]:
    return repo.report(str(identifier), version)


@router.get("/investigations/{identifier}/generated-reports/{version}/download")
def download_generated(identifier: UUID, version: Version, repo: Repo) -> Response:
    saved = repo.report(str(identifier), version)
    name = f"deeptrace-research-{str(identifier)[:8]}-v{version}.md"
    return Response(
        saved["markdown_text"].encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "X-Report-SHA256": saved["markdown_sha256"],
        },
    )


@router.get("/investigations/{identifier}/storage")
def storage(identifier: UUID, request: Request, repo: Repo) -> dict[str, int | bool]:
    used = repo.storage_bytes(str(identifier))
    limit = request.app.state.storage_warning_bytes
    return {"bytes": used, "warning_bytes": limit, "over_warning": used >= limit}


@router.post("/investigations/{identifier}/sensitive")
def set_sensitive(identifier: UUID, data: Flag, repo: Repo) -> dict[str, bool]:
    repo.set_sensitive(str(identifier), data.value)
    return {"sensitive": data.value}


@router.post("/investigations/{identifier}/archive")
def set_archived(identifier: UUID, data: Flag, repo: Repo) -> dict[str, bool]:
    repo.set_archived(str(identifier), data.value)
    return {"archived": data.value}


@router.delete("/investigations/{identifier}")
def delete_investigation(identifier: UUID, data: DeleteRequest, repo: Repo) -> dict[str, Any]:
    removed = repo.delete_investigation(str(identifier), data.confirm_title)
    return {
        "deleted": True,
        "rows_removed": sum(removed.values()),
        "note": "Upgrade backups, prior downloads and OS backups are outside this deletion.",
    }
