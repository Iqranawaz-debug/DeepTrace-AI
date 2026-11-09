"""Evidence review, synthesis and report contracts. All text here is user-authored."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field, StringConstraints, field_validator, model_validator

from deeptrace.collection.policy import CollectionError, normalize_url
from deeptrace.models import StrictModel

Text1000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Text2000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Text5000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
Text10000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]
ClaimText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


Stance = Literal["unreviewed", "supports", "contradicts", "context", "insufficient"]
Relation = Literal["supports", "contradicts", "context"]
ClaimType = Literal["finding", "interpretation", "conflict", "hypothesis", "gap", "conclusion"]

MAX_CLAIMS = 30
MAX_CITATIONS = 10
MAX_SAVED_URLS = 200


class SavedUrlCreate(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    url: str = Field(min_length=1, max_length=2048)
    note: Text1000 | None = None

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        try:
            normalize_url(value.strip())
        except CollectionError:
            raise ValueError("Unsupported or unsafe URL") from None
        return value.strip()


class SavedUrlView(StrictModel):
    id: str
    investigation_id: str
    original_url: str
    canonical_url: str
    note: str | None
    created_at: str
    retrieved: Literal[False] = False


class EvidencePassageView(StrictModel):
    id: str
    display_id: str
    source_id: str
    source_title: str | None
    source_status: str
    source_origin: str
    original_url: str
    ordinal: int
    start_offset: int
    end_offset: int
    text: str
    extraction_version: str


class NoteSave(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    passage_id: UUID
    target_key: str = Field(min_length=1, max_length=64)
    stance: Stance
    note: Text5000 | None = None
    expected_revision: int = Field(ge=0, strict=True)

    @field_validator("target_key")
    @classmethod
    def valid_target(cls, value: str) -> str:
        if value != "question":
            UUID(value)
        return value


class NoteView(StrictModel):
    id: str
    passage_id: str
    display_id: str
    source_id: str
    source_title: str | None
    target_key: str
    target_label: str
    target_current: bool
    stance: Stance
    note: str | None
    revision_no: int
    created_at: str
    updated_at: str


class CitationSave(StrictModel):
    passage_id: UUID
    relation: Relation
    quoted_text: Text2000 | None = None

    @field_validator("quoted_text")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        return value or None


class ClaimSave(StrictModel):
    id: UUID
    claim_type: ClaimType
    claim_text: ClaimText
    citations: list[CitationSave] = Field(default_factory=list, max_length=MAX_CITATIONS)

    @model_validator(mode="after")
    def unique_passages(self) -> ClaimSave:
        if len({c.passage_id for c in self.citations}) != len(self.citations):
            raise ValueError("A passage can be cited once per claim")
        return self


class AnswerSave(StrictModel):
    expected_revision: int = Field(ge=0, strict=True)
    scope_text: Text5000 | None = None
    methodology_text: Text5000 | None = None
    summary_text: Text10000 | None = None
    limitations_text: Text5000 | None = None
    next_steps_text: Text5000 | None = None
    claims: list[ClaimSave] = Field(default_factory=list, max_length=MAX_CLAIMS)

    @model_validator(mode="after")
    def unique_claims(self) -> AnswerSave:
        if len({claim.id for claim in self.claims}) != len(self.claims):
            raise ValueError("Claim identifiers must be unique")
        return self


class CitationView(StrictModel):
    id: str
    passage_id: str
    display_id: str
    source_id: str
    source_title: str | None
    relation: Relation
    quoted_text: str | None
    reference_valid: bool
    quote_valid: bool | None
    invalid_reason: str | None
    start_offset: int
    end_offset: int
    passage_text: str


class ClaimView(StrictModel):
    id: str
    ordinal: int
    claim_type: ClaimType
    claim_text: str
    evidence_state: Literal["cited", "not_established"]
    citations: list[CitationView]


class AnswerView(StrictModel):
    id: str | None
    revision_no: int
    authorship: Literal["user"] = "user"
    mode: str
    scope_text: str | None
    methodology_text: str | None
    summary_text: str | None
    limitations_text: str | None
    next_steps_text: str | None
    updated_at: str | None
    claims: list[ClaimView]


class ReportCreate(StrictModel):
    expected_revision: int = Field(ge=1, strict=True)


class ReportSummary(StrictModel):
    version_no: int
    created_at: str
    answer_revision: int
    markdown_sha256: str
    mode: str
    report_schema_version: str
    validation_summary: dict[str, int]


class ReportView(ReportSummary):
    markdown_text: str
    current_warnings: list[str]
