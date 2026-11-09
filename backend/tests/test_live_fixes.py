"""Fixes from the first live run: honest failure reasons, RFC 9309 robots, DNS retry, diversity."""

import pytest
from test_collection_api import investigation
from test_m1_live_boundary import live_client, open_all_gates
from test_m1_research import ScriptedLLM, ScriptedSearch, plan_steps, research

from deeptrace.collection import live_transport
from deeptrace.collection.fetcher import Fetcher
from deeptrace.collection.fixtures import SyntheticTransport
from deeptrace.collection.policy import CollectionError
from deeptrace.collection.transport import Reply
from deeptrace.research.pipeline import MAX_PASSAGES_PER_SOURCE, rank_passages

PAGE = "https://site.example/article"
HTML = Reply(200, {"content-type": "text/html"}, [b"<main><p>" + b"words " * 30 + b"</p></main>"])


class Scripted:
    def __init__(self, robots):
        self.robots, self.calls = robots, []

    def get(self, url, timeout):
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            if isinstance(self.robots, Exception):
                raise self.robots
            return self.robots
        return HTML


@pytest.mark.parametrize(
    ("robots", "fetches"),
    [
        (Reply(404, {}, []), True),  # RFC 9309: missing means no restrictions.
        (Reply(410, {}, []), True),
        (Reply(200, {"content-type": "text/plain"}, [b""]), True),  # Empty file: no rules.
        (Reply(200, {"content-type": "text/plain"}, [b"User-agent: *\nAllow: /\n"]), True),
    ],
    ids=["404", "410", "empty", "allow"],
)
def test_missing_or_permissive_robots_allows_the_page(robots, fetches):
    transport = Scripted(robots)
    final, body, mime = Fetcher(transport, lambda: True).fetch(PAGE)
    assert mime == "text/html" and transport.calls == ["https://site.example/robots.txt", PAGE]


@pytest.mark.parametrize(
    ("robots", "code"),
    [
        (
            Reply(200, {"content-type": "text/plain"}, [b"User-agent: *\nDisallow: /\n"]),
            "robots_blocked",
        ),
        (Reply(403, {}, []), "blocked"),  # The site refuses: reported as a refusal.
        (Reply(500, {}, []), "robots_unavailable"),  # Unknown permission still fails closed.
        (Reply(200, {"content-type": "text/plain"}, [b"\xff\xfe"]), "robots_unavailable"),
        (CollectionError("dns_failed"), "dns_failed"),  # Not a robots refusal.
        (TimeoutError(), "timeout"),
    ],
    ids=["disallow", "403", "500", "undecodable", "dns", "timeout"],
)
def test_robots_failures_keep_their_real_reason_and_never_fetch_the_page(robots, code):
    transport = Scripted(robots)
    with pytest.raises(CollectionError) as caught:
        Fetcher(transport, lambda: True).fetch(PAGE)
    assert caught.value.code == code
    assert PAGE not in transport.calls


def test_dns_lookup_is_retried_once(monkeypatch):
    calls = []

    def flaky(host):
        calls.append(host)
        if len(calls) == 1:
            raise OSError("temporary failure")
        return ["93.184.216.34"]

    monkeypatch.setattr(live_transport, "resolve", flaky)
    monkeypatch.setattr(live_transport.time, "sleep", lambda seconds: None)
    assert live_transport.bounded_resolve("example.org") == ["93.184.216.34"]
    assert len(calls) == 2
    calls.clear()
    monkeypatch.setattr(live_transport, "resolve", lambda host: calls.append(host) or [])
    with pytest.raises(CollectionError, match="dns_failed"):
        live_transport.bounded_resolve("example.org")
    assert len(calls) == 2  # Bounded: exactly one retry.


def test_passage_ranking_caps_each_source():
    long_source = [
        {"display_id": f"P-{n:04d}", "source_id": "long", "text": "admissions " * 5}
        for n in range(20)
    ]
    others = [
        {"display_id": f"P-{n:04d}", "source_id": f"s{n}", "text": "admissions"}
        for n in range(20, 26)
    ]
    chosen = rank_passages(["admissions"], long_source + others)
    assert sum(p["source_id"] == "long" for p in chosen) == MAX_PASSAGES_PER_SOURCE
    assert len({p["source_id"] for p in chosen}) == 1 + 6


def test_dns_failure_is_reported_as_failed_not_blocked(tmp_path):
    class Transport:
        def get(self, url, timeout):
            raise CollectionError("dns_failed")

    class LiveSearch(ScriptedSearch):
        id = "tavily"

    class LiveLLM(ScriptedLLM):
        id = "gemini"
        model = "synthetic"

    llm = LiveLLM([])
    c, _ = live_client(
        tmp_path, search_provider=LiveSearch(), llm_provider=llm, collection_transport=Transport()
    )
    try:
        open_all_gates(c)
        inv = investigation(c)
        run = research(c, inv, plan_steps(c, inv, 1))
        statuses = {s["status"] for s in run["sources"]}
        assert statuses == {"failed"}, statuses
        sources = c.get(f"/api/investigations/{inv}/sources").json()
        assert {s["limitation"] for s in sources} == {"dns_failed"}
    finally:
        c.__exit__(None, None, None)
    assert llm.prompts == []


def test_live_runs_read_one_page_per_website(tmp_path):
    class LiveSearch(ScriptedSearch):
        id = "tavily"

    class LiveLLM(ScriptedLLM):
        id = "gemini"
        model = "synthetic"

    urls = ["https://fixture.example/lead-1", "https://fixture.example/lead-2"]
    c, _ = live_client(
        tmp_path,
        search_provider=LiveSearch(urls=urls),
        llm_provider=LiveLLM([{"summary": "S", "claims": []}]),
        collection_transport=SyntheticTransport(),
    )
    try:
        open_all_gates(c)
        inv = investigation(c)
        run = research(c, inv, plan_steps(c, inv, 1), max_pages=2)
        assert len(run["sources"]) == 1  # The second page from the same site was skipped.
        text = c.get(f"/api/investigations/{inv}/generated-reports/1").json()["markdown_text"]
        assert "1 result(s) from an already-used website were skipped." in text
    finally:
        c.__exit__(None, None, None)


def test_mock_runs_still_read_several_fixture_pages(tmp_path):
    from test_m1_research import connect

    urls = ["https://fixture.example/lead-1", "https://fixture.example/lead-2"]
    c = connect(tmp_path, search_provider=ScriptedSearch(urls=urls))
    try:
        c.post("/api/web-consent", json={"accepted": True})
        inv = investigation(c)
        assert len(research(c, inv, plan_steps(c, inv, 1), max_pages=2)["sources"]) == 2
    finally:
        c.__exit__(None, None, None)
