"""Vendor-independent provider contracts, typed failures and validated model output."""

import json
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Category = Literal[
    "not_configured",
    "consent_required",
    "offline",
    "auth_rejected",
    "rate_limited",
    "quota_exhausted",
    "unavailable",
    "timeout",
    "malformed_response",
    "sensitive_blocked",
]
RETRYABLE = frozenset({"rate_limited", "unavailable", "timeout"})


class ProviderError(Exception):
    """Carries a fixed category only: never provider bodies, keys or research text."""

    def __init__(self, category: Category, retry_after: float | None = None):
        self.category: Category = category
        self.retry_after = retry_after
        super().__init__(category)


@dataclass(frozen=True)
class SearchLead:
    """A discovery lead. Never evidence until fetched and extracted."""

    url: str
    title: str | None
    rank: int


@dataclass(frozen=True)
class LLMText:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class SearchProvider(Protocol):
    id: str

    def search(self, query: str, limit: int, timeout: float) -> list[SearchLead]: ...


class LLMProvider(Protocol):
    id: str
    model: str

    def generate(self, prompt: str, max_tokens: int, timeout: float) -> LLMText: ...


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PlanStep(Strict):
    sub_question: Annotated[str, Field(min_length=1, max_length=1000)]
    search_query: Annotated[str, Field(min_length=1, max_length=500)]


class PlanOutput(Strict):
    steps: list[PlanStep] = Field(min_length=1, max_length=8)
    narrow_reason: Annotated[str, Field(max_length=500)] | None = None

    @model_validator(mode="after")
    def narrow_needs_reason(self) -> PlanOutput:
        if len(self.steps) < 3 and not self.narrow_reason:
            raise ValueError("A plan under three steps must explain why")
        return self


class ClaimCitation(Strict):
    passage_id: Annotated[str, Field(max_length=64)]
    quote: Annotated[str, Field(max_length=2000)] | None = None


class SynthClaim(Strict):
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    citations: list[ClaimCitation] = Field(default_factory=list, max_length=5)


class SynthOutput(Strict):
    summary: Annotated[str, Field(max_length=5000)]
    claims: list[SynthClaim] = Field(default_factory=list, max_length=20)
    limitations: Annotated[str, Field(max_length=5000)] | None = None
    needed_evidence: Annotated[str, Field(max_length=5000)] | None = None


def parse_output[Output: (PlanOutput, SynthOutput)](text: str, schema: type[Output]) -> Output:
    """Model text is untrusted: anything off-schema is a typed recoverable failure."""
    try:
        return schema.model_validate(json.loads(text))
    except ValidationError, ValueError, TypeError:
        raise ProviderError("malformed_response") from None


class Budgets(Strict):
    """PRD FR-11.1 hard ceilings; defaults sit below them because they are not targets."""

    max_steps: int = Field(default=25, ge=1, le=25, strict=True)
    max_searches: int = Field(default=8, ge=1, le=20, strict=True)
    max_pages: int = Field(default=10, ge=1, le=15, strict=True)
    max_tokens: int = Field(default=100_000, ge=1000, le=400_000, strict=True)
    max_minutes: int = Field(default=10, ge=1, le=20, strict=True)
