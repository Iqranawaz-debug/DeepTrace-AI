"""Regressions found in the Phase 3 audit: host policy, word boundaries, worker failure."""

import pytest
from test_collection_api import client, investigation, start, terminal  # noqa: F401

from deeptrace.collection.extractor import extract
from deeptrace.collection.policy import CollectionError, normalize_url
from deeptrace.storage.collection_repository import CollectionRepository


@pytest.mark.parametrize("url", ["https://bad.cafe/x", "https://dead.beef/", "https://face.bed/"])
def test_letter_only_hex_hostnames_are_ordinary_names(url):
    assert normalize_url(url) == url


@pytest.mark.parametrize(
    "url", ["https://example.123/", "https://0x7f.1/", "https://a.0x7f/", "https://1.2.3.4.5/"]
)
def test_numeric_final_labels_are_ambiguous_and_rejected(url):
    with pytest.raises(CollectionError):
        normalize_url(url)


def test_block_and_cell_boundaries_never_merge_words():
    body = (
        b"<html><head><title>Document title</title></head><body><main>"
        b"<svg><title>icon</title></svg>"
        b"<table><tr><th>alpha</th><td>beta</td></tr></table><h5>Five</h5>"
        b"<blockquote>Quoted</blockquote><dl><dt>term</dt><dd>definition</dd></dl>"
        b"<p>" + b"padding words " * 10 + b"</p></main></body></html>"
    )
    result = extract(body, "text/html")
    assert result.title == "Document title"
    for merged in ("alphabeta", "FiveQuoted", "termdefinition"):
        assert merged not in result.text
    assert "alpha beta" in result.text
    assert result.extraction_version.endswith("-v3")


def test_svg_title_is_not_a_declared_title():
    result = extract(b"<body><svg><title>icon</title></svg><main><p>" + b"w " * 60 + b"</p>"
                     b"</main></body>", "text/html")  # fmt: skip
    assert result.title is None


def test_worker_failure_marks_run_failed_and_keeps_serving(client, monkeypatch):  # noqa: F811
    inv = investigation(client)
    client.post("/api/web-consent", json={"accepted": True})
    original = CollectionRepository.save_source
    calls = {"n": 0}

    def explode_once(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated persistence fault")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CollectionRepository, "save_source", explode_once)
    failed = terminal(client, inv, start(client, inv).json()["id"])
    assert (failed["status"], failed["error_code"]) == ("failed", "worker_failure")
    # The worker survived and serves the next run; no orphaned running state remains.
    assert not client.app.state.collection_worker.stop_event.is_set()
    nxt = terminal(client, inv, start(client, inv).json()["id"])
    assert nxt["status"] == "completed"


def test_finish_never_rewrites_a_terminal_run(client):  # noqa: F811
    inv = investigation(client)
    client.post("/api/web-consent", json={"accepted": True})
    run = terminal(client, inv, start(client, inv).json()["id"])
    repo = CollectionRepository(client.app.state.database)
    events = len(client.get(f"/api/investigations/{inv}/events?run_id={run['id']}").json())
    repo.finish(run["id"], "failed", "late")
    after = repo.run(run["id"], inv)
    assert (after["status"], after["error_code"]) == ("completed", None)
    assert len(client.get(f"/api/investigations/{inv}/events?run_id={run['id']}").json()) == events
