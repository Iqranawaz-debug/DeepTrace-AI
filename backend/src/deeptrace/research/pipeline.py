"""Plain bounded staged orchestrator (ADR-A05): every stage checkpoints; every loop has a cap.

The language model never chooses a URL: only search-provider leads that pass the URL
policy are fetched, and model output is validated before anything is shown or stored.
"""

import contextlib
import json
import re
import threading
import time
from collections import Counter
from collections.abc import Callable
from functools import partial
from typing import Any

from deeptrace.collection.extractor import Extraction
from deeptrace.collection.fetcher import Fetcher, Transport
from deeptrace.collection.parser_process import parse
from deeptrace.collection.policy import CollectionError, normalize_url
from deeptrace.evidence import kernel
from deeptrace.research import prompts
from deeptrace.research.contracts import (
    Budgets,
    LLMText,
    PlanOutput,
    ProviderError,
    SynthOutput,
    parse_output,
)
from deeptrace.research.gateway import Gateway
from deeptrace.research.report import GENERATED_SCHEMA_VERSION, GeneratedInput, counts, render
from deeptrace.storage.collection_repository import CollectionRepository
from deeptrace.storage.research_repository import (
    ResearchRepository,
    ValidatedClaim,
    ValidCitation,
)

MAX_OUTPUT_TOKENS = 4096
MAX_ALLOWED_PASSAGES = 12
MODEL_ATTEMPTS = 2  # FR-P3: bounded retry for malformed model output.
PROVIDER_TIMEOUT = 45.0
NO_MODEL = "none"
LIMIT_NAMES = {
    "search_budget": "the search limit",
    "page_budget": "the page limit",
    "step_budget": "the step limit",
    "token_budget": "the token limit",
    "quota_exhausted": "the provider quota",
}
_WORD = re.compile(r"\w+", re.UNICODE)
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how in is it of on or that the this to "
    "was were what when where which who why will with".split()
)


class Halt(Exception):
    """Stop the run with an honest terminal state; saved evidence is always retained."""

    def __init__(self, status: str, code: str | None = None, omissions: list[str] | None = None):
        self.status, self.code = status, code
        self.omissions = omissions or []
        super().__init__(status)


def rank_passages(terms_from: list[str], passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic lexical ranking (ADR-A10): term hits, then stable passage order."""
    terms = {
        word for text in terms_from for word in _WORD.findall(text.lower()) if word not in STOPWORDS
    }

    def score(passage: dict[str, Any]) -> int:
        found = Counter(_WORD.findall(passage["text"].lower()))
        return sum(found[term] for term in terms)

    return sorted(passages, key=lambda p: (-score(p), p["display_id"]))[:MAX_ALLOWED_PASSAGES]


def validate_claims(
    output: SynthOutput, allowed: list[dict[str, Any]], investigation: str
) -> list[ValidatedClaim]:
    """Fabricated, disallowed or misquoted citations are suppressed, never displayed."""
    by_display = {p["display_id"]: p for p in allowed}
    claims = []
    for claim in output.claims:
        valid, suppressed = {}, 0
        for cite in claim.citations:
            passage = by_display.get(cite.passage_id)
            check = kernel.check_citation(
                investigation,
                None
                if passage is None
                else kernel.PassageRecord(passage["id"], investigation, passage["text"]),
                cite.quote,
            )
            if passage is None or not check.reference_valid or check.quote_valid is False:
                suppressed += 1
                continue
            valid[passage["id"]] = ValidCitation(
                passage["id"],
                passage["display_id"],
                passage["source_id"],
                cite.quote,
                kernel.sha256(passage["text"]),
            )
        claims.append(ValidatedClaim(claim.text, list(valid.values()), suppressed))
    return claims


class Pipeline:
    def __init__(
        self,
        collection: CollectionRepository,
        research: ResearchRepository,
        gateway: Gateway,
        transport: Transport,
        allowed: Callable[[], bool],
    ):
        self.collection, self.research = collection, research
        self.gateway, self.transport, self.allowed = gateway, transport, allowed

    def execute(self, run: dict[str, Any], stop: threading.Event) -> None:
        snapshot = json.loads(run["config_snapshot_json"])
        try:
            if snapshot["scope"] == "plan_generation":
                self._plan(run, snapshot, stop)
            else:
                self._research(run, snapshot, stop)
        except Halt as halt:
            self._stop(run, snapshot, halt.status, halt.code, halt.omissions)
        except ProviderError as exc:
            # Quota exhaustion is a budget stop; everything else is a recoverable failure.
            quota = exc.category == "quota_exhausted"
            self._stop(run, snapshot, "budget_reached" if quota else "failed", exc.category, [])

    def _stop(
        self,
        run: dict[str, Any],
        snapshot: dict[str, Any],
        status: str,
        code: str | None,
        omissions: list[str],
    ) -> None:
        if status == "budget_reached" and snapshot["scope"] == "research_pipeline":
            # DESIGN §9.6: a budget stop still offers a partial report of what was found.
            with contextlib.suppress(Exception):
                self._partial_report(run, code, omissions)
        self.collection.finish(run["id"], status, code)

    def _partial_report(self, run: dict[str, Any], code: str | None, omissions: list[str]) -> None:
        limit = LIMIT_NAMES.get(code or "", "a run limit")
        output = SynthOutput(
            summary=f"Stopped: {limit} reached before an answer was drafted. "
            "Partial results are shown and may be incomplete.",
            limitations="No answer was generated, so nothing here is a finding.",
        )
        self._save(run, output, [], omissions, NO_MODEL, NO_MODEL, NO_MODEL, limit)

    def _check(self, run: str, stop: threading.Event) -> None:
        if stop.is_set():
            raise Halt("interrupted", "process_interrupted")
        if self.collection.stopped(run):
            raise Halt("cancelled")

    def _guard_model(self, investigation: str) -> None:
        # Sensitive material never goes to a hosted model; mock adapters stay on this computer.
        if self.gateway.mode != "mock" and self.research.sensitive(investigation):
            raise ProviderError("sensitive_blocked")

    def _model[Output: (PlanOutput, SynthOutput)](
        self,
        run: str,
        operation: str,
        prompt: str,
        schema: type[Output],
        spent: list[int],
        limit: int,
    ) -> Output:
        llm = self.gateway.llm_provider
        for attempt in range(1, MODEL_ATTEMPTS + 1):
            estimate = len(prompt) // 4 + MAX_OUTPUT_TOKENS
            if spent[0] + estimate > limit:
                raise Halt("budget_reached", "token_budget")

            def request() -> LLMText:
                return llm.generate(prompt, MAX_OUTPUT_TOKENS, PROVIDER_TIMEOUT)

            result = self.gateway.call(run, llm.id, operation, request)
            used = len(prompt) // 4 + len(result.text) // 4
            spent[0] += used
            self.research.record_tokens(
                run, llm.id, used, {"input": result.input_tokens, "output": result.output_tokens}
            )
            try:
                return parse_output(result.text, schema)
            except ProviderError:
                if attempt == MODEL_ATTEMPTS:
                    raise
        raise ProviderError("malformed_response")

    # Plan generation ---------------------------------------------------------------

    def _plan(self, run: dict[str, Any], snapshot: dict[str, Any], stop: threading.Event) -> None:
        self._check(run["id"], stop)
        self._guard_model(run["investigation_id"])
        budgets = Budgets(**snapshot["budgets"])
        output = self._model(
            run["id"],
            "plan",
            prompts.plan_prompt(run["question_snapshot"]),
            PlanOutput,
            [0],
            budgets.max_tokens,
        )
        self._check(run["id"], stop)
        llm = self.gateway.llm_provider
        self.research.apply_plan(run, output, llm.id, llm.model, prompts.PLAN_VERSION)
        self.collection.finish(run["id"], "completed")

    # Research ----------------------------------------------------------------------

    def _research(
        self, run: dict[str, Any], snapshot: dict[str, Any], stop: threading.Event
    ) -> None:
        identifier, investigation = run["id"], run["investigation_id"]
        budgets = Budgets(**snapshot["budgets"])
        deadline = time.monotonic() + budgets.max_minutes * 60
        items = snapshot["plan"]["items"]
        steps = 0
        budget_stop: str | None = None
        omissions: list[str] = []

        def over_time() -> bool:
            return time.monotonic() >= deadline

        # Discover: ceilings are split deterministically before any call is made.
        per_query = min(3, max(1, budgets.max_pages // max(1, len(items))))
        leads: dict[str, str] = {}
        search = self.gateway.search_provider
        searches = 0
        for item in items:
            self._check(identifier, stop)
            if searches >= budgets.max_searches or steps >= budgets.max_steps or over_time():
                budget_stop = "search_budget"
                omissions.append("Some plan steps were not searched: a budget limit was reached.")
                break
            query = (item.get("search_query") or item["sub_question"])[:500]

            def request(text: str = query) -> Any:
                return search.search(text, per_query, PROVIDER_TIMEOUT)

            try:
                found = self.gateway.call(identifier, search.id, "search", request)
            except ProviderError as exc:
                self.research.add_query(
                    identifier, investigation, query, search.id, exc.category, 0
                )
                raise
            searches += 1
            steps += 1
            self.research.add_query(
                identifier, investigation, query, search.id, "completed", len(found)
            )
            for lead in found:
                try:
                    canonical = normalize_url(lead.url)
                except CollectionError:
                    omissions.append("A search result with an unsafe or invalid URL was skipped.")
                    continue
                leads.setdefault(canonical, lead.url)
        self.research.stage(
            identifier, "discover", "completed", {"searches": searches, "leads": len(leads)}
        )

        # Fetch and extract: one failed source never discards the others (FR-W10).
        fetcher = Fetcher(self.transport, partial(self._may_fetch, identifier, stop))
        pages = 0
        for number, (canonical, url) in enumerate(leads.items(), 1):
            self._check(identifier, stop)
            if pages >= budgets.max_pages or steps >= budgets.max_steps or over_time():
                budget_stop = budget_stop or "page_budget"
                omissions.append(f"{len(leads) - number + 1} found page(s) were not fetched.")
                break
            result: Extraction | None = None
            final, failure = canonical, None
            try:
                final, body, mime = fetcher.fetch(url)
                result = parse(body, mime)
            except CollectionError as exc:
                failure = exc.code
            except Exception:
                failure = "collection_failed"
            self._check(identifier, stop)
            self.collection.save_source(
                run, url, final, result, failure, number, origin=self._origin(search.id)
            )
            pages += 1
            steps += 1
        self.research.stage(identifier, "fetch", "completed", {"attempted": pages})
        if budget_stop:
            raise Halt("budget_reached", budget_stop, omissions)

        # Rank a bounded allowlist; only these passages may be sent or cited.
        allowed = rank_passages(
            [run["question_snapshot"], *[i["sub_question"] for i in items]],
            self.research.allowed_passages(identifier, investigation),
        )
        self.research.stage(identifier, "rank", "completed", {"allowed": len(allowed)})
        self._check(identifier, stop)
        self._guard_model(investigation)
        llm = self.gateway.llm_provider
        spent = [0]
        if allowed:
            if steps >= budgets.max_steps or over_time():
                raise Halt("budget_reached", "step_budget", omissions)
            output = self._model(
                identifier,
                "synthesize",
                prompts.synthesize_prompt(
                    run["question_snapshot"],
                    [
                        (p["display_id"], p["source_title"] or "Untitled", p["text"])
                        for p in allowed
                    ],
                ),
                SynthOutput,
                spent,
                budgets.max_tokens,
            )
            self.research.stage(
                identifier, "synthesize", "completed", {"claims": len(output.claims)}
            )
        else:
            # ERR-07: no readable evidence means no model call and no invented answer.
            output = SynthOutput(
                summary="No usable sources were retrieved, so no answer can be given.",
                limitations="No passages were available to the model.",
                needed_evidence="Readable sources relevant to this question.",
            )
            omissions.append("No model call was made because no passages were available.")
        self._check(identifier, stop)
        claims = validate_claims(output, allowed, investigation)
        self._save(run, output, claims, omissions, llm.id, llm.model, prompts.SYNTHESIZE_VERSION)
        self.collection.finish(identifier, "completed")

    def _save(
        self,
        run: dict[str, Any],
        output: SynthOutput,
        claims: list[ValidatedClaim],
        omissions: list[str],
        provider: str,
        model: str,
        prompt_version: str,
        stopped: str | None = None,
    ) -> None:
        identifier, investigation = run["id"], run["investigation_id"]
        sources = self.research.run_sources(identifier, investigation)
        queries = self.research.queries(identifier)
        search_id = self.gateway.search_provider.id

        def build(version: int, created: str) -> tuple[str, str, dict[str, int]]:
            data = GeneratedInput(
                title=self._title(investigation),
                question=run["question_snapshot"],
                summary=output.summary,
                limitations=output.limitations,
                needed=output.needed_evidence,
                claims=claims,
                sources=sources,
                queries=queries,
                omissions=omissions,
                provider=provider,
                model=model,
                prompt_version=prompt_version,
                search_provider=search_id,
                mode=run["mode"],
                version_no=version,
                created_at=created,
                stopped=stopped,
            )
            return render(data), GENERATED_SCHEMA_VERSION, counts(data)

        self.research.save_outcome(
            run,
            output.summary,
            output.limitations,
            output.needed_evidence,
            claims,
            provider,
            model,
            prompt_version,
            build,
            partial=stopped is not None,
        )

    def _title(self, investigation: str) -> str:
        with self.research.db.connection() as con:
            row = con.execute(
                "SELECT title FROM investigations WHERE id=?", (investigation,)
            ).fetchone()
            return str(row[0])

    @staticmethod
    def _origin(search_id: str) -> str:
        return "tavily" if search_id == "tavily" else "mock"

    def _may_fetch(self, run: str, stop: threading.Event) -> bool:
        return self.allowed() and not stop.is_set() and not self.collection.stopped(run)
