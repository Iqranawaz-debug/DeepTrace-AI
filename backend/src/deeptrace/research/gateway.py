"""Outbound policy choke point (ADR-A08): mode, allowlist, credential, consent, bounded retry."""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from deeptrace.research.contracts import RETRYABLE, LLMProvider, ProviderError, SearchProvider
from deeptrace.research.credentials import ENV_NAMES, CredentialStore, resolve_key
from deeptrace.storage.research_repository import ResearchRepository

T = TypeVar("T")
MAX_ATTEMPTS = 3
MAX_RETRY_WAIT = 60.0  # A longer Retry-After stops the run rather than holding the worker.
# Bumping a version invalidates earlier consent: a stored key or old consent is not enough.
DISCLOSURES = {"tavily": "tavily-live-v1", "gemini": "gemini-live-v1", "public_web": "web-live-v1"}


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    role: str
    data_sent: str
    notice: str
    credential: bool


PROVIDERS = (
    ProviderInfo(
        "tavily",
        "Web search",
        "Your search queries.",
        "Queries leave this computer. Stay within your verified free plan; DeepTrace never "
        "buys credits or falls back to a paid service.",
        True,
    ),
    ProviderInfo(
        "gemini",
        "Language model",
        "Your question and the selected saved passages.",
        "Gemini free-tier content may be used by Google to improve products under applicable "
        "terms. Send only synthetic, public or deliberately approved non-sensitive material. "
        "Confirm your account and region really have a free tier: DeepTrace cannot verify "
        "billing and cannot override provider-side charges.",
        True,
    ),
    ProviderInfo(
        "public_web",
        "Website retrieval",
        "Requests for the pages found by search, plus their robots.txt.",
        "Sites see your IP address. DeepTrace honours robots.txt, does not bypass access "
        "controls and refuses private or local addresses.",
        False,
    ),
)


class Gateway:
    def __init__(
        self,
        mode: str,
        repository: ResearchRepository,
        credentials: CredentialStore,
        search: SearchProvider,
        llm: LLMProvider,
        llm_configured: bool = True,
    ):
        self.mode, self.repo, self.credentials = mode, repository, credentials
        self.search_provider, self.llm_provider = search, llm
        self.llm_configured = llm_configured
        self.last_failure: dict[str, str] = {}
        self.stop = threading.Event()

    def blockers(self) -> list[str]:
        """Fixed reasons a new run cannot start. Empty means every gate is open."""
        if self.mode == "offline":
            return ["Offline mode: saved work can be read, but new research is disabled."]
        if self.mode == "mock":
            return []
        problems = []
        for info in PROVIDERS:
            if not self.repo.consented(info.id, DISCLOSURES[info.id]):
                problems.append(f"Review and accept the {info.role} disclosure.")
            if info.credential and not resolve_key(self.credentials, info.id):
                problems.append(f"Add a {info.role} API key.")
        if not self.llm_configured:
            problems.append("Set DEEPTRACE_LLM_MODEL to your verified free-tier model ID.")
        return problems

    def admit(self, provider: str) -> None:
        if self.mode == "offline":
            raise ProviderError("offline")
        if self.mode == "mock":
            if not provider.startswith("mock_"):
                raise ProviderError("not_configured")
            return
        if provider not in DISCLOSURES:
            raise ProviderError("not_configured")
        if not self.repo.consented(provider, DISCLOSURES[provider]):
            raise ProviderError("consent_required")
        if provider in ENV_NAMES and not resolve_key(self.credentials, provider):
            raise ProviderError("not_configured")

    def call(self, run: str, provider: str, operation: str, action: Callable[[], T]) -> T:
        """Admit before every attempt, record every attempt, retry only safe failures."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self.admit(provider)
            usage = self.repo.usage_begin(run, provider, operation, attempt)
            try:
                result = action()
            except ProviderError as exc:
                self.repo.usage_end(usage, exc.category)
                self.last_failure[provider] = exc.category
                if exc.category not in RETRYABLE or attempt == MAX_ATTEMPTS:
                    raise
                wait = max(self.backoff(attempt), exc.retry_after or 0.0)
                if wait > MAX_RETRY_WAIT or self.stop.wait(wait):
                    raise
                continue
            self.repo.usage_end(usage, "ok")
            self.last_failure.pop(provider, None)
            return result
        raise ProviderError("unavailable")

    @staticmethod
    def backoff(attempt: int) -> float:
        return float(2 ** (attempt - 1))
