"""M1 vertical slice: AC-01/02/03/06/09/11, ERR cases, lifecycle, deletion and secrets."""

import json
import logging
import re
import shutil
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_collection_api import investigation, terminal

from deeptrace.config import Settings
from deeptrace.evidence import kernel
from deeptrace.main import create_app
from deeptrace.research.contracts import (
    Budgets,
    LLMText,
    PlanOutput,
    ProviderError,
    SearchLead,
    parse_output,
)
from deeptrace.research.credentials import MemoryCredentialStore
from deeptrace.research.mock import MockLLM
from deeptrace.research.pipeline import rank_passages
from deeptrace.research.prompts import plan_prompt
from deeptrace.storage.database import MIGRATIONS, Database

SECRET = "tvly-SEEDED-SECRET-0123456789"


def connect(tmp_path, **kwargs):
    settings = kwargs.pop("settings", {})
    c = TestClient(
        create_app(Settings(data_dir=tmp_path, _env_file=None, **settings), **kwargs),
        base_url="http://127.0.0.1:8000",
    )
    c.__enter__()
    c.headers.update(
        {
            "Origin": "http://127.0.0.1:5173",
            "X-DeepTrace-Token": c.get("/api/session").json()["token"],
        }
    )
    return c


@pytest.fixture
def make(tmp_path):
    made = []

    def build(**kwargs):
        c = connect(tmp_path, **kwargs)
        made.append(c)
        c.post("/api/web-consent", json={"accepted": True})
        return c

    yield build
    for c in made:
        c.__exit__(None, None, None)


def plan_steps(c, inv, count=2):
    items = [
        {"id": str(uuid4()), "sub_question": f"Step {n}", "search_query": f"query {n}"}
        for n in range(count)
    ]
    r = c.put(f"/api/investigations/{inv}/plan", json={"expected_revision": 0, "items": items})
    assert r.status_code == 200, r.text
    return r.json()["revision_no"]


def research(c, inv, revision=1, **budgets):
    r = c.post(
        f"/api/investigations/{inv}/research",
        json={"expected_revision": revision, "budgets": budgets},
    )
    assert r.status_code == 202, r.text
    return terminal(c, inv, r.json()["id"])


class ScriptedSearch:
    id = "mock_search"

    def __init__(self, failures=(), urls=None):
        self.failures, self.calls = list(failures), []
        self.urls = urls or ["https://fixture.example/lead-1", "https://fixture.example/lead-2"]

    def search(self, query, limit, timeout):
        self.calls.append(query)
        if self.failures:
            raise ProviderError(self.failures.pop(0))
        return [SearchLead(u, None, i) for i, u in enumerate(self.urls[:limit], 1)]


class ScriptedLLM:
    id = "mock_llm"
    model = "scripted"

    def __init__(self, outputs):
        self.outputs, self.prompts = list(outputs), []

    def generate(self, prompt, max_tokens, timeout):
        self.prompts.append(prompt)
        item = self.outputs.pop(0)
        if isinstance(item, Exception):
            raise item
        return LLMText(item if isinstance(item, str) else json.dumps(item), 10, 5)


# AC-02 ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "What caused the 2008 financial crisis?",
        "How do vaccines train the immune system?",
        "Is remote work better for productivity?",
        "Why did the Roman Empire fall?",
        "What is the boiling point of water at altitude?",
        "How does photosynthesis convert light into energy?",
        "What are the risks of intermittent fasting?",
        "Define entropy?",
        "Compare SQLite and PostgreSQL for local apps",
        "اردو میں تحقیق کے طریقے کیا ہیں؟",
    ],
)
def test_plan_schema_is_valid_for_varied_questions(question):
    text = MockLLM().generate(plan_prompt(question), 100, 1).text
    plan = parse_output(text, PlanOutput)
    assert 1 <= len(plan.steps) <= 8
    if len(plan.steps) < 3:
        assert plan.narrow_reason


def test_generate_plan_is_saved_with_provenance_and_guarded(make):
    c = make()
    narrow = investigation(c)  # A two-word question: a shorter plan must explain itself.
    run = terminal(c, narrow, c.post(f"/api/investigations/{narrow}/plan/generate",
                                     json={"expected_revision": 0}).json()["id"])  # fmt: skip
    progress = c.get(f"/api/runs/{run['id']}/progress?investigation_id={narrow}").json()
    assert "narrow" in progress["narrow_reason"]
    assert len(c.get(f"/api/investigations/{narrow}/plan").json()["items"]) == 1
    inv = c.post(
        "/api/investigations",
        json={"title": "Broad study", "question": "How do vaccines train the immune system?"},
    ).json()["id"]
    url = f"/api/investigations/{inv}/plan/generate"
    run = terminal(c, inv, c.post(url, json={"expected_revision": 0}).json()["id"])
    assert run["status"] == "completed" and run["scope"] == "plan_generation"
    plan = c.get(f"/api/investigations/{inv}/plan").json()
    assert plan["revision_no"] == 1 and 3 <= len(plan["items"]) <= 8
    assert all(item["search_query"] for item in plan["items"])
    with c.app.state.database.connection() as con:
        assert con.execute(
            "SELECT provider_id,model_id,prompt_version FROM plans WHERE investigation_id=?", (inv,)
        ).fetchone() == (
            "mock_llm",
            "mock-deterministic-v1",
            "plan-v1",
        )
    # Existing work is never replaced without explicit confirmation.
    assert c.post(url, json={"expected_revision": 1}).json()["error"]["code"] == "plan_exists"
    assert c.post(url, json={"expected_revision": 0, "replace": True}).status_code == 409
    again = c.post(url, json={"expected_revision": 1, "replace": True})
    assert terminal(c, inv, again.json()["id"])["status"] == "completed"
    # A manual edit makes the plan user-authored again.
    latest = c.get(f"/api/investigations/{inv}/plan").json()
    c.put(f"/api/investigations/{inv}/plan",
          json={"expected_revision": latest["revision_no"], "items": latest["items"]})  # fmt: skip
    with c.app.state.database.connection() as con:
        assert (
            con.execute(
                "SELECT provider_id FROM plans WHERE investigation_id=?", (inv,)
            ).fetchone()[0]
            is None
        )


def test_malformed_plan_gets_bounded_retry_then_recoverable_failure(make):
    llm = ScriptedLLM(["not json", {"steps": []}, "never used"])
    c = make(llm_provider=llm)
    inv = investigation(c)
    r = c.post(f"/api/investigations/{inv}/plan/generate", json={"expected_revision": 0})
    run = terminal(c, inv, r.json()["id"])
    assert (run["status"], run["error_code"]) == ("failed", "malformed_response")
    assert len(llm.prompts) == 2  # FR-P3: bounded, not endless.
    assert c.get(f"/api/investigations/{inv}/plan").json()["items"] == []


# AC-03, AC-06 --------------------------------------------------------------------------


def test_full_mock_journey_produces_a_traceable_report(make):
    c = make()
    inv = investigation(c)
    generated = c.post(f"/api/investigations/{inv}/plan/generate", json={"expected_revision": 0})
    terminal(c, inv, generated.json()["id"])
    run = research(c, inv)
    assert run["status"] == "completed" and run["mode"] == "mock", run
    statuses = {s["status"] for s in run["sources"]}
    assert "fetched" in statuses
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    assert answer["provider_id"] == "mock_llm" and answer["prompt_version"] == "synthesize-v2"
    states = {claim["evidence_state"] for claim in answer["claims"]}
    assert states == {"cited", "not_established"}
    # Every displayed citation resolves to a stored, same-investigation passage.
    for claim in answer["claims"]:
        for cite in claim["citations"]:
            stored = c.get(f"/api/passages/{cite['passage_id']}?investigation_id={inv}")
            assert stored.status_code == 200 and stored.json()["text"] == cite["passage_text"]
            assert cite["reference_valid"] is True and cite["quote_valid"] is True
            assert kernel.quote_matches(cite["quoted_text"], stored.json()["text"])
    reports = c.get(f"/api/investigations/{inv}/generated-reports").json()
    assert [r["version_no"] for r in reports] == [1]
    report = c.get(f"/api/investigations/{inv}/generated-reports/1").json()
    text = report["markdown_text"]
    for section in ("Question", "Summary", "Findings", "Supporting Evidence",
                    "Conflicting or Missing Evidence", "Limitations", "Methodology",
                    "References"):  # fmt: skip
        assert f"## {section}" in text, section
    for required in ("AI-generated research aid. Verify important findings using original sources.",
                     "SIMULATED RESEARCH", "synthesize-v2", "mock-deterministic-v1", "mock_llm",
                     "Search queries:", "Not established", "Retrieved (UTC)"):  # fmt: skip
        assert required in text, required
    assert kernel.sha256(text) == report["markdown_sha256"]
    cited_ids = set(re.findall(r"P-\d{4}", text))
    stored = {p["display_id"] for p in c.get(f"/api/investigations/{inv}/passages").json()}
    # The hostile fixture's fake P-9999 may appear only as escaped source-derived text, never cited.
    assert "P-9999" not in cited_ids or "P-9999" not in stored
    download = c.get(f"/api/investigations/{inv}/generated-reports/1/download")
    assert download.content == text.encode()
    assert download.headers["content-disposition"] == (
        f'attachment; filename="deeptrace-research-{inv[:8]}-v1.md"'
    )
    assert download.headers["x-report-sha256"] == report["markdown_sha256"]
    progress = c.get(f"/api/runs/{run['id']}/progress?investigation_id={inv}").json()
    keys = {stage["stage_key"] for stage in progress["stages"]}
    assert {"discover", "fetch", "rank", "synthesize", "validate", "report"} <= keys
    assert progress["usage"]["search_attempts"] >= 1 and progress["usage"]["estimated_tokens"] > 0
    with c.app.state.database.transaction() as con, pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE generated_reports SET markdown_text='changed'")


def test_fabricated_and_misquoted_citations_are_suppressed(make):
    outputs = [
        {
            "summary": "S",
            "claims": [
                {"text": "Fabricated", "citations": [{"passage_id": "P-9999"}]},
                {"text": "Misquoted", "citations": [{"passage_id": "P-0001", "quote": "never"}]},
                {"text": "Valid", "citations": [{"passage_id": "P-0001", "quote": "SIMULATED"}]},
                {"text": "Mixed", "citations": [{"passage_id": "P-0001"}, {"passage_id": "X"}]},
            ],
        }
    ]
    c = make(llm_provider=ScriptedLLM(outputs), search_provider=ScriptedSearch())
    inv = investigation(c)
    assert research(c, inv, plan_steps(c, inv, 1))["status"] == "completed"
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    states = [claim["evidence_state"] for claim in answer["claims"]]
    assert states == ["not_established", "not_established", "cited", "cited"]
    assert answer["suppressed_citations"] == 3 and answer["status"] == "partial"
    assert (
        answer["claims"][0]["citations"] == []
        and "suppressed" in answer["claims"][0]["explanation"]
    )
    assert [x["display_id"] for x in answer["claims"][3]["citations"]] == ["P-0001"]
    text = c.get(f"/api/investigations/{inv}/generated-reports/1").json()["markdown_text"]
    assert (
        "P-9999" not in text and "never" not in text.split("## Limitations")[0].split("Findings")[1]
    )


def test_passage_outside_the_run_allowlist_cannot_be_cited(make):
    # Passages from an earlier run exist in the investigation but were not selected here.
    c = make(search_provider=ScriptedSearch(urls=["https://fixture.example/lead-1"]))
    inv = investigation(c)
    revision = plan_steps(c, inv, 1)
    assert research(c, inv, revision)["status"] == "completed"
    llm = c.app.state.gateway
    llm.search_provider = ScriptedSearch(urls=["https://fixture.example/lead-2"])
    llm.llm_provider = ScriptedLLM(
        [{"summary": "S", "claims": [{"text": "Old", "citations": [{"passage_id": "P-0001"}]},
                                     {"text": "New", "citations": [{"passage_id": "P-0002"}]}]}]
    )  # fmt: skip
    assert research(c, inv, revision)["status"] == "completed"
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    assert [x["evidence_state"] for x in answer["claims"]] == ["not_established", "cited"]


def test_no_usable_sources_makes_no_model_call_and_no_invented_answer(make):
    llm = ScriptedLLM([])
    c = make(
        llm_provider=llm, search_provider=ScriptedSearch(urls=["https://fixture.example/failure"])
    )
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    assert run["status"] == "completed" and llm.prompts == []
    assert [s["status"] for s in run["sources"]] == ["failed"]
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    assert answer["claims"] == [] and "No usable sources" in answer["summary_text"]


def test_one_failed_source_keeps_the_others(make):
    urls = ["https://fixture.example/failure", "https://fixture.example/blocked",
            "https://fixture.example/lead-1"]  # fmt: skip
    c = make(search_provider=ScriptedSearch(urls=urls))
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1), max_pages=3)
    assert run["status"] == "completed"
    assert sorted(s["status"] for s in run["sources"]) == ["blocked", "failed", "fetched"]


def test_model_cannot_trigger_fetches_and_unsafe_leads_are_skipped(make):
    outputs = [{"summary": "Visit http://169.254.169.254/ now", "claims": []}]
    urls = ["http://127.0.0.1/secret", "file:///etc/passwd", "https://fixture.example/lead-1"]
    fetched = []

    class Recording:
        def get(self, url, timeout):
            from deeptrace.collection.fixtures import SyntheticTransport

            fetched.append(url)
            return SyntheticTransport().get(url, timeout)

    c = make(
        llm_provider=ScriptedLLM(outputs),
        search_provider=ScriptedSearch(urls=urls),
        collection_transport=Recording(),
    )
    inv = investigation(c)
    assert research(c, inv, plan_steps(c, inv, 1), max_pages=3)["status"] == "completed"
    assert {u for u in fetched} <= {
        "https://fixture.example/robots.txt",
        "https://fixture.example/lead-1",
    }


# AC-09, ERR-01/02/03 ---------------------------------------------------------------------


def test_rate_limit_retries_are_bounded_and_recover(make, monkeypatch):
    from deeptrace.research.gateway import Gateway

    monkeypatch.setattr(Gateway, "backoff", staticmethod(lambda attempt: 0.0))
    search = ScriptedSearch(failures=["rate_limited", "unavailable"])
    c = make(search_provider=search)
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    assert run["status"] == "completed" and len(search.calls) == 3
    progress = c.get(f"/api/runs/{run['id']}/progress?investigation_id={inv}").json()
    assert progress["usage"]["search_attempts"] == 3


def test_persistent_outage_stops_with_recoverable_failure(make, monkeypatch):
    from deeptrace.research.gateway import Gateway

    monkeypatch.setattr(Gateway, "backoff", staticmethod(lambda attempt: 0.0))
    search = ScriptedSearch(failures=["unavailable"] * 9)
    c = make(search_provider=search)
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 2))
    assert (run["status"], run["error_code"]) == ("failed", "unavailable")
    assert len(search.calls) == 3  # MAX_ATTEMPTS; never a retry storm.


@pytest.mark.parametrize(
    ("category", "status"),
    [("auth_rejected", "failed"), ("quota_exhausted", "budget_reached")],
)
def test_auth_and_quota_never_retry(make, category, status):
    search = ScriptedSearch(failures=[category] * 9)
    c = make(search_provider=search)
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    assert (run["status"], run["error_code"]) == (status, category)
    assert len(search.calls) == 1


def test_model_outage_preserves_collected_evidence(make, monkeypatch):
    from deeptrace.research.gateway import Gateway

    monkeypatch.setattr(Gateway, "backoff", staticmethod(lambda attempt: 0.0))
    c = make(
        llm_provider=ScriptedLLM([ProviderError("timeout")] * 3),
        search_provider=ScriptedSearch(),
    )
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    assert (run["status"], run["error_code"]) == ("failed", "timeout")
    assert c.get(f"/api/investigations/{inv}/passages").json()
    assert c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"] is None
    assert c.get(f"/api/investigations/{inv}").json()["lifecycle"] == "Failed"


# AC-11 --------------------------------------------------------------------------------


def test_search_budget_stops_exactly_and_keeps_partial_sources(make):
    search = ScriptedSearch()
    llm = ScriptedLLM([])
    c = make(search_provider=search, llm_provider=llm)
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 4), max_searches=2)
    assert (run["status"], run["error_code"]) == ("budget_reached", "search_budget")
    assert len(search.calls) == 2 and llm.prompts == []
    assert run["sources"], "Partial evidence must be retained"
    assert c.get(f"/api/investigations/{inv}").json()["lifecycle"] == "Budget reached"


def test_page_budget_stops_exactly(make):
    class Distinct(ScriptedSearch):
        def search(self, query, limit, timeout):
            self.calls.append(query)
            url = f"https://fixture.example/lead-{len(self.calls)}"
            return [SearchLead(url, None, 1)]

    llm = ScriptedLLM([])
    c = make(search_provider=Distinct(), llm_provider=llm)
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 3), max_pages=1)
    assert (run["status"], run["error_code"]) == ("budget_reached", "page_budget")
    assert len(run["sources"]) == 1 and llm.prompts == []


def test_token_budget_stops_before_the_call(make):
    llm = ScriptedLLM([])
    c = make(llm_provider=llm, search_provider=ScriptedSearch())
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1), max_tokens=1000)
    assert (run["status"], run["error_code"]) == ("budget_reached", "token_budget")
    assert llm.prompts == []


@pytest.mark.parametrize(
    "budgets",
    [
        {"max_searches": 21},
        {"max_pages": 16},
        {"max_steps": 26},
        {"max_tokens": 400_001},
        {"max_minutes": 21},
        {"max_pages": 0},
    ],  # fmt: skip
)
def test_hard_ceilings_cannot_be_raised(make, budgets):
    c = make()
    inv = investigation(c)
    revision = plan_steps(c, inv, 1)
    r = c.post(f"/api/investigations/{inv}/research",
               json={"expected_revision": revision, "budgets": budgets})  # fmt: skip
    assert r.status_code == 422


def test_budget_defaults_sit_at_or_below_prd_ceilings():
    b = Budgets()
    assert b.max_steps <= 25 and b.max_searches <= 20 and b.max_pages <= 15
    assert b.max_tokens <= 400_000 and b.max_minutes <= 20


# Admission, cancellation, restart (AC-01) ---------------------------------------------------


def test_admission_rules(make):
    c = make()
    inv = investigation(c)
    url = f"/api/investigations/{inv}/research"
    assert c.post(url, json={"expected_revision": 0}).json()["error"]["code"] == "no_plan"
    revision = plan_steps(c, inv, 1)
    assert c.post(url, json={"expected_revision": 99}).status_code == 409
    assert c.post(f"/api/investigations/{uuid4()}/research",
                  json={"expected_revision": 0}).status_code == 404  # fmt: skip
    c.post("/api/web-consent/revoke", json={})
    assert c.post(url, json={"expected_revision": revision}).status_code == 403


def test_offline_mode_blocks_research_but_keeps_reads(tmp_path):
    c = connect(tmp_path, settings={"mode": "offline"})
    try:
        inv = investigation(c)
        for path in ("research", "plan/generate"):
            r = c.post(f"/api/investigations/{inv}/{path}", json={"expected_revision": 0})
            assert (r.status_code, r.json()["error"]["code"]) == (403, "offline")
        assert c.get("/api/capabilities").json()["research"] is False
        assert c.get(f"/api/investigations/{inv}/generated-reports").json() == []
    finally:
        c.__exit__(None, None, None)


def test_cancellation_stops_between_stages(make):
    c = make()
    inv = investigation(c)
    revision = plan_steps(c, inv, 1)
    c.app.state.collection_worker.close()  # Hold the run queued, then drive it directly.
    from deeptrace.storage.research_repository import ResearchRepository

    repo = ResearchRepository(c.app.state.database)
    run_id = str(uuid4())
    repo.start(inv, run_id, "research_pipeline", "mock", Budgets(), revision)
    assert c.post(f"/api/runs/{run_id}/cancel?investigation_id={inv}", json={}).status_code == 200
    claimed = c.app.state.collection_repository.claim()
    import threading

    c.app.state.collection_worker.research.execute(claimed, threading.Event())
    run = c.get(f"/api/runs/{run_id}?investigation_id={inv}").json()
    assert run["status"] == "cancelled" and run["sources"] == []


def test_restart_restores_everything_and_interrupts_stale_runs(tmp_path):
    c = connect(tmp_path)
    c.post("/api/web-consent", json={"accepted": True})
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    text = c.get(f"/api/investigations/{inv}/generated-reports/1").json()["markdown_text"]
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()
    with c.app.state.database.transaction() as con:
        con.execute(
            "INSERT INTO runs(id,investigation_id,status,mode,plan_revision,config_snapshot_json,"
            "question_snapshot,created_at) VALUES ('stale',?,'running','mock',1,?,'q','9999')",
            (inv, json.dumps({"scope": "research_pipeline", "urls": [], "plan": {}})),
        )
    c.__exit__(None, None, None)
    c = connect(tmp_path)
    try:
        assert (
            c.get(f"/api/investigations/{inv}/generated-reports/1").json()["markdown_text"] == text
        )
        assert c.get(f"/api/investigations/{inv}/generated-answer").json() == answer
        assert (
            c.get(f"/api/runs/{run['id']}?investigation_id={inv}").json()["status"] == "completed"
        )
        assert c.get(f"/api/runs/stale?investigation_id={inv}").status_code == 422  # Not a UUID.
        with c.app.state.database.connection() as con:
            assert (
                con.execute("SELECT status FROM runs WHERE id='stale'").fetchone()[0]
                == "interrupted"
            )
        assert c.get(f"/api/investigations/{inv}").json()["lifecycle"] == "Interrupted"
    finally:
        c.__exit__(None, None, None)


# Isolation, lifecycle, deletion (FR-01.3/4, FR-08.1) ------------------------------------------


def test_cross_investigation_isolation(make):
    c = make(search_provider=ScriptedSearch())
    inv, other = investigation(c), investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    assert c.get(f"/api/runs/{run['id']}/progress?investigation_id={other}").status_code == 404
    assert c.get(f"/api/investigations/{other}/generated-answer").json()["answer"] is None
    assert c.get(f"/api/investigations/{other}/generated-reports/1").status_code == 404
    assert c.get(f"/api/investigations/{other}/generated-reports/1/download").status_code == 404


def test_tampered_generated_report_is_refused(make):
    c = make(search_provider=ScriptedSearch())
    inv = investigation(c)
    research(c, inv, plan_steps(c, inv, 1))
    with c.app.state.database.transaction() as con:
        con.execute("DROP TRIGGER immutable_generated_report")
        con.execute("UPDATE generated_reports SET markdown_text='tampered'")
    assert c.get(f"/api/investigations/{inv}/generated-reports/1").status_code == 500
    assert c.get(f"/api/investigations/{inv}/generated-reports/1/download").status_code == 500


def test_changed_passage_is_not_presented_as_cited(make):
    c = make(search_provider=ScriptedSearch())
    inv = investigation(c)
    research(c, inv, plan_steps(c, inv, 1))
    with c.app.state.database.transaction() as con:
        con.execute("DROP TRIGGER immutable_passage")
        con.execute("UPDATE passages SET text='Different words entirely.'")
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    assert all(claim["evidence_state"] == "not_established" for claim in answer["claims"])


def test_dashboard_fields_archive_and_sensitive(make):
    c = make(search_provider=ScriptedSearch())
    inv = investigation(c)
    base = f"/api/investigations/{inv}"
    assert c.get(base).json()["lifecycle"] == "Draft"
    revision = plan_steps(c, inv, 1)
    research(c, inv, revision)
    listed = c.get("/api/investigations").json()["items"][0]
    assert listed["lifecycle"] == "Completed" and listed["source_count"] >= 1
    assert c.post(f"{base}/sensitive", json={"value": True}).json() == {"sensitive": True}
    assert c.get(base).json()["sensitive"] is True
    assert c.post(f"{base}/archive", json={"value": True}).status_code == 200
    assert c.get(base).json()["lifecycle"] == "Archived"
    blocked = c.post(f"{base}/research", json={"expected_revision": revision})
    assert blocked.json()["error"]["code"] == "archived"
    assert c.post(f"{base}/archive", json={"value": False}).status_code == 200
    assert c.get(base).json()["lifecycle"] == "Completed"


def test_delete_requires_exact_title_and_removes_every_row(make):
    c = make(search_provider=ScriptedSearch())
    inv, keep = investigation(c), investigation(c)
    revision = plan_steps(c, inv, 1)
    research(c, inv, revision)
    c.post(f"/api/investigations/{inv}/saved-urls", json={"url": "https://example.org/x"})
    c.post(f"/api/investigations/{inv}/archive", json={"value": True})
    url = f"/api/investigations/{inv}"
    wrong = c.request("DELETE", url, json={"confirm_title": "wrong"})
    assert wrong.status_code == 422 and c.get(url).status_code == 200
    done = c.request("DELETE", url, json={"confirm_title": "Synthetic evidence study"})
    assert done.status_code == 200 and "outside this deletion" in done.json()["note"]
    assert c.get(url).status_code == 404 and c.get(f"/api/investigations/{keep}").status_code == 200
    with c.app.state.database.connection() as con:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            columns = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
            if "investigation_id" in columns:
                count = con.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE investigation_id=?", (inv,)
                ).fetchone()[0]
                assert count == 0, table
        for table in ("provider_usage", "run_events", "run_stages", "plan_items"):
            assert con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []


def test_new_mutations_need_token_and_origin(make):
    c = make()
    inv = investigation(c)
    for method, path, body in (
        ("POST", f"/api/investigations/{inv}/research", {"expected_revision": 0}),
        ("POST", f"/api/investigations/{inv}/plan/generate", {"expected_revision": 0}),
        ("POST", f"/api/investigations/{inv}/archive", {"value": True}),
        ("POST", f"/api/investigations/{inv}/sensitive", {"value": True}),
        ("DELETE", f"/api/investigations/{inv}", {"confirm_title": "x"}),
        ("PUT", "/api/providers/tavily/credential", {"value": SECRET}),
        ("DELETE", "/api/providers/tavily/credential", {}),
        ("POST", "/api/providers/tavily/consent", {}),
        ("DELETE", "/api/providers/tavily/consent", {}),
    ):
        bad = c.request(method, path, json=body, headers={"X-DeepTrace-Token": "wrong"})
        assert bad.status_code == 403, path
        evil = c.request(method, path, json=body, headers={"Origin": "https://evil.example"})
        assert evil.status_code == 403, path
    assert c.request("DELETE", "/api/health").status_code == 405
    assert c.request("DELETE", f"/api/investigations/{inv}/plan", json={}).status_code == 405


# AC-15: seeded secrets ----------------------------------------------------------------------


def test_seeded_secret_never_appears_anywhere(make, caplog, tmp_path):
    store = MemoryCredentialStore()
    c = make(credentials=store, search_provider=ScriptedSearch())
    caplog.set_level(logging.DEBUG)
    put = c.put("/api/providers/tavily/credential", json={"value": SECRET})
    assert put.json() == {"credential_state": "Saved"} and store.values["tavily"] == SECRET
    bodies = [c.get("/api/providers").text, put.text]
    inv = investigation(c)
    research(c, inv, plan_steps(c, inv, 1))
    bodies += [
        c.get(f"/api/investigations/{inv}/generated-reports/1").text,
        c.get(f"/api/investigations/{inv}/generated-answer").text,
    ]
    assert not any(SECRET in body for body in bodies)
    assert SECRET not in caplog.text
    for path in tmp_path.rglob("*"):
        # collection.lock is empty and OS-locked while the app runs.
        if path.is_file() and path.name != "collection.lock":
            assert SECRET.encode() not in path.read_bytes(), path.name
    assert (
        c.put("/api/providers/tavily/credential", json={"value": "has space in it"}).status_code
        == 422
    )
    assert c.put("/api/providers/nope/credential", json={"value": SECRET}).status_code == 422
    removed = c.request("DELETE", "/api/providers/tavily/credential", json={}).json()
    assert removed["credential_state"] == "Not configured"
    assert store.values == {}


# Migration ----------------------------------------------------------------------------------


@pytest.mark.parametrize("fail", [False, True])
def test_populated_upgrade_to_006_and_rollback(tmp_path, fail):
    sql = tmp_path / "sql"
    sql.mkdir()
    for file in sorted(MIGRATIONS.glob("00[1-5]_*.sql")):
        shutil.copyfile(file, sql / file.name)
    db = Database(tmp_path / "data")
    db.migrate(sql)
    with db.transaction() as con:
        con.execute(
            "INSERT INTO investigations(id,title,question,created_at,updated_at) "
            "VALUES ('inv','Synthetic','Synthetic question','2026','2026')"
        )
        con.execute(
            "INSERT INTO runs(id,investigation_id,status,mode,plan_revision,config_snapshot_json,"
            "question_snapshot,created_at) "
            "VALUES ('run','inv','completed','mock',0,'{}','q','2026')"
        )
        con.execute(
            "INSERT INTO run_stages VALUES ('st','run','extract',1,'completed',NULL,NULL,NULL,NULL)"
        )
    body = (MIGRATIONS / "006_research_pipeline.sql").read_bytes()
    (sql / "006_research_pipeline.sql").write_bytes(body + (b"\nINVALID SQL;\n" if fail else b""))
    if fail:
        with pytest.raises(sqlite3.Error):
            db.migrate(sql)
    else:
        db.migrate(sql)
        assert db.ready()
    with db.connection() as con:
        assert con.execute("SELECT stage_key FROM run_stages").fetchone()[0] == "extract"
        assert con.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0] == (
            5 if fail else 6
        )
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert ("generated_reports" in names) is not fail
        assert "run_stages_new" not in names
        if not fail:
            con.execute("BEGIN")
            con.execute(
                "INSERT INTO run_stages VALUES "
                "('s2','run','plan',1,'completed',NULL,NULL,NULL,NULL)"
            )
            con.rollback()
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert len(list((db.path.parent / "backups").glob("before-6-*.sqlite3"))) == 1


def test_lexical_ranking_is_deterministic_and_bounded():
    passages = [
        {"display_id": f"P-{n:04d}", "text": "cats " * (n % 3), "id": str(n)} for n in range(30)
    ]
    first = rank_passages(["cats"], passages)
    assert first == rank_passages(["cats"], list(reversed(passages))) and len(first) == 12
    assert first[0]["text"].count("cats") == 2
