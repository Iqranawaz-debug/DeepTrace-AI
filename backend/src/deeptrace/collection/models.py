"""Collection request schemas; no secrets or arbitrary execution options."""

from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from deeptrace.collection.policy import CollectionError, normalize_url
from deeptrace.models import StrictModel


class RunStart(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    expected_revision: int = Field(ge=0, strict=True)
    urls: list[Annotated[str, Field(max_length=2048)]] = Field(min_length=1, max_length=15)

    @field_validator("urls")
    @classmethod
    def valid_urls(cls, values: list[str]) -> list[str]:
        try:
            for value in values:
                normalize_url(value)
        except CollectionError:
            raise ValueError("Unsupported or unsafe URL") from None
        return list(dict.fromkeys(values))


class Consent(StrictModel):
    accepted: bool = Field(strict=True)


# Explicit response contracts prevent accidental internal-field exposure.
class RunSource(StrictModel):
    id: str
    status: str


class RunView(StrictModel):
    id: str
    investigation_id: str
    kind: str
    status: str
    mode: str
    plan_id: str | None
    plan_revision: int
    question_snapshot: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    cancel_requested: int
    last_heartbeat_at: str | None
    error_code: str | None
    urls: list[str]
    plan_snapshot: dict[str, object]
    scope: str = "evidence_collection"
    sources: list[RunSource] = Field(default_factory=list)


class SourceSummary(StrictModel):
    id: str
    investigation_id: str
    run_id: str
    title: str | None
    original_url: str
    canonical_url: str
    status: str
    origin: str
    fetched_at: str | None
    extracted_at: str | None
    limitation: str | None
    duplicate_of: str | None


class SourceView(SourceSummary):
    source_type: str
    author: str | None
    published_at: str | None
    extracted_text: str | None
    text_sha256: str | None
    extraction_version: str | None
    normalization_version: str | None


class PassageView(StrictModel):
    id: str
    investigation_id: str
    source_id: str
    display_id: str
    ordinal: int
    text: str
    start_offset: int
    end_offset: int
    extraction_version: str
    text_sha256: str
    extracted_at: str
    page_index: None
    removed_at: None


class EventView(StrictModel):
    id: str
    run_id: str
    sequence_no: int
    event_type: str
    stage_key: str | None
    safe_message: str
    created_at: str
