"""Requirements found missing after M1: partial reports, Retry-After, bounded logs, storage."""

import logging
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest
from test_collection_api import investigation
from test_m1_research import ScriptedLLM, ScriptedSearch, make, plan_steps, research  # noqa: F401

import deeptrace.main as app_module
from deeptrace.research.contracts import ProviderError, SearchLead
from deeptrace.research.gateway import MAX_RETRY_WAIT, Gateway
from deeptrace.research.live import TavilySearch, retry_after


class Distinct(ScriptedSearch):
    def search(self, query, limit, timeout):
        self.calls.append(query)
        return [SearchLead(f"https://fixture.example/lead-{len(self.calls)}", None, 1)]


def test_budget_stop_produces_a_labelled_partial_report_without_a_model(make):  # noqa: F811
    llm = ScriptedLLM([])
    c = make(search_provider=Distinct(), llm_provider=llm)
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 3), max_pages=1)
    assert (run["status"], run["error_code"]) == ("budget_reached", "page_budget")
    assert llm.prompts == []
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    assert answer["status"] == "partial" and answer["claims"] == []
    assert answer["provider_id"] == "none" and "the page limit" in answer["summary_text"]
    text = c.get(f"/api/investigations/{inv}/generated-reports/1").json()["markdown_text"]
    assert "PARTIAL REPORT" in text and "no language model was used" in text
    assert "not fetched" in text  # The omission is disclosed.
    assert "## References" in text and "lead-1" in text  # What was found is still there.
    # A partial report is never a normal completion.
    assert c.get(f"/api/investigations/{inv}").json()["lifecycle"] == "Budget reached"


@pytest.mark.parametrize(
    ("budgets", "code"),
    [({"max_searches": 1}, "search_budget"), ({"max_tokens": 1000}, "token_budget")],
)
def test_other_limits_also_keep_a_partial_report(make, budgets, code):  # noqa: F811
    c = make(search_provider=ScriptedSearch(), llm_provider=ScriptedLLM([]))
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 2), **budgets)
    assert run["error_code"] == code
    assert len(c.get(f"/api/investigations/{inv}/generated-reports").json()) == 1


def test_quota_stop_keeps_a_partial_report(make):  # noqa: F811
    c = make(search_provider=ScriptedSearch(failures=["quota_exhausted"]))
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    assert (run["status"], run["error_code"]) == ("budget_reached", "quota_exhausted")
    text = c.get(f"/api/investigations/{inv}/generated-reports/1").json()["markdown_text"]
    assert "the provider quota reached" in text


def test_failed_and_cancelled_runs_do_not_get_a_report(make, monkeypatch):  # noqa: F811
    monkeypatch.setattr(Gateway, "backoff", staticmethod(lambda attempt: 0.0))
    c = make(search_provider=ScriptedSearch(failures=["auth_rejected"]))
    inv = investigation(c)
    assert research(c, inv, plan_steps(c, inv, 1))["status"] == "failed"
    assert c.get(f"/api/investigations/{inv}/generated-reports").json() == []


def test_retry_after_header_parsing():
    assert retry_after({"retry-after": "8"}) == 8.0
    assert retry_after({}) is None
    assert retry_after({"retry-after": "soon"}) is None
    assert retry_after({"retry-after": "-5"}) == 0.0
    future = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
    assert 25 <= retry_after({"retry-after": future}) <= 30
    past = format_datetime(datetime.now(UTC) - timedelta(seconds=30), usegmt=True)
    assert retry_after({"retry-after": past}) == 0.0


def test_provider_error_carries_retry_after():
    poster = lambda *a: (429, b"{}", {"retry-after": "7"})  # noqa: E731
    with pytest.raises(ProviderError) as caught:
        TavilySearch(lambda: "k", poster).search("q", 1, 1)
    assert (caught.value.category, caught.value.retry_after) == ("rate_limited", 7.0)


class RateLimited(ScriptedSearch):
    def __init__(self, wait, times=1):
        super().__init__()
        self.wait, self.times = wait, times

    def search(self, query, limit, timeout):
        self.calls.append(query)
        if self.times:
            self.times -= 1
            raise ProviderError("rate_limited", self.wait)
        return [SearchLead("https://fixture.example/lead-1", None, 1)]


def test_gateway_waits_at_least_as_long_as_retry_after(make, monkeypatch):  # noqa: F811
    c = make(search_provider=RateLimited(7.0))
    waits = []
    gate = c.app.state.gateway
    real_wait = gate.stop.wait

    def record(timeout=None):
        if timeout and timeout > 1:  # Worker polling uses its own, shorter event.
            waits.append(timeout)
            return False
        return real_wait(timeout)

    monkeypatch.setattr(gate.stop, "wait", record)
    inv = investigation(c)
    assert research(c, inv, plan_steps(c, inv, 1))["status"] == "completed"
    assert waits == [7.0]


def test_excessive_retry_after_stops_instead_of_holding_the_worker(make):  # noqa: F811
    search = RateLimited(MAX_RETRY_WAIT + 1, times=9)
    c = make(search_provider=search)
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    assert (run["status"], run["error_code"]) == ("failed", "rate_limited")
    assert len(search.calls) == 1


def test_log_file_is_bounded_and_holds_only_fixed_events(make, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setattr(app_module, "LOG_MAX_BYTES", 2000)
    c = make()
    inv = investigation(c)
    c.get(f"/api/investigations/{inv}")
    logger = logging.getLogger("deeptrace")
    for _ in range(2000):
        logger.info('{"event":"request","status":200}')
    files = sorted((tmp_path / "logs").glob("deeptrace.log*"))
    assert len(files) == 4  # One active plus exactly three backups.
    assert all(path.stat().st_size <= 2000 for path in files)
    assert "Synthetic evidence study" not in "".join(p.read_text() for p in files)


def test_log_handler_is_removed_at_shutdown(tmp_path):
    from test_m1_research import connect

    logger = logging.getLogger("deeptrace")
    before = len(logger.handlers)
    c = connect(tmp_path)
    assert len(logger.handlers) == before + 1
    c.__exit__(None, None, None)
    assert len(logger.handlers) == before


def test_storage_warning_threshold(make):  # noqa: F811
    c = make(settings={"storage_warning_mb": 1}, search_provider=ScriptedSearch())
    inv, other = investigation(c), investigation(c)
    url = f"/api/investigations/{inv}/storage"
    assert c.get(url).json() == {"bytes": 0, "warning_bytes": 1_000_000, "over_warning": False}
    research(c, inv, plan_steps(c, inv, 1))
    used = c.get(url).json()["bytes"]
    assert used > 0
    assert c.get(f"/api/investigations/{other}/storage").json()["bytes"] == 0
    c.app.state.storage_warning_bytes = used
    assert c.get(url).json()["over_warning"] is True


def test_progress_reports_live_counts_and_queries(make):  # noqa: F811
    c = make(search_provider=ScriptedSearch())
    inv = investigation(c)
    run = research(c, inv, plan_steps(c, inv, 1))
    progress = c.get(f"/api/runs/{run['id']}/progress?investigation_id={inv}").json()
    assert progress["usage"]["pages_attempted"] >= progress["usage"]["pages_retrieved"] >= 1
    assert progress["queries"][0]["query_text"] == "query 0"
    assert progress["queries"][0]["status"] == "completed"
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    cited = [cite for claim in answer["claims"] for cite in claim["citations"]]
    assert cited and all(cite["source_status"] == "fetched" for cite in cited)


def test_model_timeout_is_not_retried_but_rate_limits_are(make, monkeypatch):  # noqa: F811
    from deeptrace.research import pipeline

    monkeypatch.setattr(Gateway, "backoff", staticmethod(lambda attempt: 0.0))
    assert pipeline.MODEL_TIMEOUT >= 120 and "timeout" not in pipeline.MODEL_RETRYABLE
    slow = ScriptedLLM([ProviderError("timeout")] * 3)
    c = make(llm_provider=slow)
    inv = investigation(c)
    url = f"/api/investigations/{inv}/plan/generate"
    from test_collection_api import terminal

    run = terminal(c, inv, c.post(url, json={"expected_revision": 0}).json()["id"])
    assert (run["status"], run["error_code"]) == ("failed", "timeout")
    assert len(slow.prompts) == 1  # One long wait, not three.
    busy = ScriptedLLM(
        [
            ProviderError("rate_limited"),
            '{"steps":[{"sub_question":"a","search_query":"b"}],"narrow_reason":"narrow"}',
        ]
    )
    c.app.state.gateway.llm_provider = busy
    run = terminal(c, inv, c.post(url, json={"expected_revision": 0}).json()["id"])
    assert run["status"] == "completed" and len(busy.prompts) == 2


def test_overview_reports_real_counts_and_activity(make):  # noqa: F811
    c = make(search_provider=ScriptedSearch())
    empty = c.get("/api/overview").json()
    assert empty["totals"] == {"investigations": 0, "sources": 0, "sources_read": 0,
                               "passages": 0, "cited_findings": 0, "reports": 0}  # fmt: skip
    assert empty["recent"] == [] and empty["activity"] == []
    inv, archived = investigation(c), investigation(c)
    research(c, inv, plan_steps(c, inv, 1))
    c.post(f"/api/investigations/{archived}/archive", json={"value": True})
    data = c.get("/api/overview").json()
    answer = c.get(f"/api/investigations/{inv}/generated-answer").json()["answer"]
    cited = sum(claim["evidence_state"] == "cited" for claim in answer["claims"])
    assert data["totals"]["investigations"] == 2
    assert data["totals"]["cited_findings"] == cited > 0
    assert data["totals"]["reports"] == 1 and data["totals"]["sources_read"] >= 1
    assert [r["id"] for r in data["recent"]] == [inv]  # Archived work is not "continue" work.
    card = data["recent"][0]
    assert (card["lifecycle"], card["plan_steps"], card["report_version"]) == ("Completed", 1, 1)
    assert card["cited_findings"] == cited
    assert data["activity"][0]["event_type"] == "completed"
    assert all(item["investigation_id"] == inv for item in data["activity"])
