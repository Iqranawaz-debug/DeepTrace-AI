"""SDK-independent extension points. No network implementation exists in Phase 1."""

from typing import Literal, Protocol

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    title: str
    url: str


class SearchProvider(Protocol):
    def search(self, request: SearchRequest) -> list[SearchResult]: ...


class LLMProvider(Protocol):
    def generate(self, task: Literal["plan", "synthesize"], question: str) -> str: ...


class OutboundDisabled(RuntimeError):
    pass


class ProviderBoundary:
    """Future provider allowlist; even allowlisted destinations remain disabled."""

    allowed_providers = frozenset({"gemini", "tavily"})

    def authorize(self, provider: str) -> None:
        if provider not in self.allowed_providers:
            raise OutboundDisabled("Provider is not allowlisted")
        raise OutboundDisabled("External operations are unavailable in Phase 1")
