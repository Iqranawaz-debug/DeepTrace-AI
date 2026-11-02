import hashlib
import sqlite3
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from deeptrace.config import Settings
from deeptrace.main import create_app
from deeptrace.storage.collection_repository import CollectionRepository


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(Settings(data_dir=tmp_path, _env_file=None)), base_url="http://127.0.0.1:8000"
    ) as client:
        client.headers.update(
            {
                "Origin": "http://127.0.0.1:5173",
                "X-DeepTrace-Token": client.get("/api/session").json()["token"],
            }
        )
        yield client


def investigation(client):
    result = client.post(
        "/api/investigations",
        json={
            "id": str(uuid4()),
            "title": "Synthetic evidence study",
            "question": "Fixture question?",
        },
    )
    assert result.status_code == 201, result.text
    return result.json()["id"]


def start(client, inv, urls=None, **extra):
    return client.post(
        f"/api/investigations/{inv}/runs",
        json={
            "id": str(uuid4()),
            "expected_revision": 0,
            "urls": urls or ["https://fixture.example/article"],
            **extra,
        },
    )


def terminal(client, inv, run):
    for _ in range(100):
        response = client.get(f"/api/runs/{run}?investigation_id={inv}")
        assert response.status_code == 200, response.text
        if response.json()["status"] not in {"queued", "running"}:
            return response.json()
        time.sleep(0.1)
    pytest.fail("Worker did not finish")


def test_collection_provenance_isolation_duplicate_and_immutability(client):
    inv, other = investigation(client), investigation(client)
    assert start(client, inv).status_code == 403
    assert client.post("/api/web-consent", json={"accepted": True}).status_code == 200
    created = start(client, inv)
    assert created.status_code == 202, created.text
    run = terminal(client, inv, created.json()["id"])
    assert run["status"] == "completed", run
    assert run["question_snapshot"] == "Fixture question?"
    assert run["plan_revision"] == 0
    source_id = run["sources"][0]["id"]
    source = client.get(f"/api/sources/{source_id}?investigation_id={inv}").json()
    assert source["origin"] == "mock"
    assert "SIMULATED EVIDENCE" in source["extracted_text"]
    assert source["text_sha256"] == hashlib.sha256(source["extracted_text"].encode()).hexdigest()
    assert source["author"] is None and source["published_at"] is None
    passages = client.get(f"/api/sources/{source_id}/passages?investigation_id={inv}").json()
    for passage in passages:
        assert (
            passage["text"]
            == source["extracted_text"][passage["start_offset"] : passage["end_offset"]]
        )
        assert passage["text_sha256"] == source["text_sha256"]
        assert (
            client.get(f"/api/passages/{passage['id']}?investigation_id={other}").status_code == 404
        )
    assert client.get(f"/api/sources/{source_id}?investigation_id={other}").status_code == 404
    assert client.get(f"/api/runs/{run['id']}?investigation_id={other}").status_code == 404
    assert (
        client.post(f"/api/runs/{run['id']}/cancel?investigation_id={other}", json={}).status_code
        == 404
    )
    duplicate = terminal(client, inv, start(client, inv).json()["id"])
    assert duplicate["sources"][0]["status"] == "duplicate"
    db = client.app.state.database
    with db.transaction() as con:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            con.execute("UPDATE sources SET title='changed' WHERE id=?", (source_id,))
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            con.execute("UPDATE passages SET text='changed'")
    events = client.get(f"/api/investigations/{inv}/events?run_id={run['id']}").json()
    assert [event["sequence_no"] for event in events] == list(range(1, len(events) + 1))


def test_failed_collection_preserves_history_and_safe_errors(client):
    inv = investigation(client)
    client.post("/api/web-consent", json={"accepted": True})
    run = terminal(
        client, inv, start(client, inv, ["https://fixture.example/failure"]).json()["id"]
    )
    assert run["status"] == "failed"
    assert run["sources"][0]["status"] == "failed"
    assert len(client.get(f"/api/investigations/{inv}/runs").json()) == 1
    assert start(client, inv, expected_revision=99).status_code == 409
    assert start(client, inv, ["http://localhost/"]).status_code == 422
    assert client.post("/api/web-consent/revoke", json={}).status_code == 200
    assert start(client, inv).status_code == 403


def test_offline_gate_ignores_consent(tmp_path):
    with TestClient(
        create_app(Settings(data_dir=tmp_path, mode="offline", _env_file=None)),
        base_url="http://127.0.0.1:8000",
    ) as client:
        client.headers.update(
            {
                "Origin": "http://127.0.0.1:5173",
                "X-DeepTrace-Token": client.get("/api/session").json()["token"],
            }
        )
        inv = investigation(client)
        assert client.get("/api/providers").json()["fixture_collection"] is False
        assert client.post("/api/web-consent", json={"accepted": True}).status_code == 403
        assert start(client, inv).status_code == 403


def test_recovery_idempotency_and_concurrency(client):
    # Stop the worker to deterministically exercise admission, cancellation and recovery.
    client.app.state.collection_worker.close()
    repo = CollectionRepository(client.app.state.database)
    from deeptrace.collection.models import RunStart

    inv = investigation(client)
    data = RunStart(expected_revision=0, urls=["https://fixture.example/article"])
    first = repo.start(inv, data)
    assert repo.start(inv, data)["id"] == first["id"]
    from deeptrace.storage.repository import WorkspaceError

    with pytest.raises(WorkspaceError):
        repo.start(inv, RunStart(expected_revision=0, urls=["https://fixture.example/second"]))
    repo.cancel(first["id"])
    assert repo.stopped(first["id"])
    repo.recover()
    assert repo.run(first["id"], inv)["status"] == "interrupted"
    assert repo.claim() is None


@pytest.mark.parametrize("path", ["/api/web-consent", "/api/web-consent/revoke"])
def test_new_mutations_require_origin_and_token(client, path):
    client.headers.pop("X-DeepTrace-Token")
    assert client.post(path, json={"accepted": True}).status_code == 403


@pytest.mark.parametrize("revocation", [False, True])
def test_cancellation_during_retrieval_does_not_persist_content(tmp_path, revocation):
    import threading

    from deeptrace.collection.fixtures import SyntheticTransport

    entered, release = threading.Event(), threading.Event()

    class PausedTransport:
        def get(self, url, timeout):
            if url.endswith("/article"):
                entered.set()
                assert release.wait(5)
            return SyntheticTransport().get(url, timeout)

    app = create_app(
        Settings(data_dir=tmp_path, _env_file=None), collection_transport=PausedTransport()
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        client.headers.update(
            {
                "Origin": "http://127.0.0.1:5173",
                "X-DeepTrace-Token": client.get("/api/session").json()["token"],
            }
        )
        inv = investigation(client)
        client.post("/api/web-consent", json={"accepted": True})
        run = start(client, inv).json()["id"]
        try:
            assert entered.wait(3)
            if revocation:
                assert client.post("/api/web-consent/revoke", json={}).status_code == 200
            else:
                assert (
                    client.post(
                        f"/api/runs/{run}/cancel?investigation_id={inv}", json={}
                    ).status_code
                    == 200
                )
        finally:
            release.set()
        result = terminal(client, inv, run)
        assert result["status"] == "cancelled"
        assert result["sources"] == []


def test_worker_lock_excludes_second_process_owner(client):
    from deeptrace.collection.fetcher import Fetcher
    from deeptrace.collection.transport import DisabledTransport
    from deeptrace.collection.worker import Worker

    other = Worker(CollectionRepository(client.app.state.database), Fetcher(DisabledTransport()))
    with pytest.raises((RuntimeError, OSError)):
        other.start()


def test_persistence_atomicity_and_database_ownership(client, monkeypatch):
    import deeptrace.storage.collection_repository as module
    from deeptrace.collection.extractor import extract
    from deeptrace.collection.models import RunStart

    client.app.state.collection_worker.close()
    inv, other = investigation(client), investigation(client)
    repo = CollectionRepository(client.app.state.database)
    repo.set_consent(True)
    repo.start(inv, RunStart(expected_revision=0, urls=["https://fixture.example/article"]))
    run = repo.claim()
    result = extract(b"<main>Synthetic checkpoint evidence.</main>", "text/html")
    original = module.slices

    def failed_slices(_):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(module, "slices", failed_slices)
    with pytest.raises(OSError):
        repo.save_source(run, run["id"], "https://fixture.example/article", result, None, 1)
    with repo.db.connection() as con:
        assert con.execute("SELECT count(*) FROM sources").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM run_stages").fetchone()[0] == 0
    monkeypatch.setattr(module, "slices", original)
    repo.save_source(
        run, "https://fixture.example/article", "https://fixture.example/article", result, None, 1
    )
    changed = extract(b"<main>Changed synthetic evidence at the same URL.</main>", "text/html")
    repo.save_source(
        run, "https://fixture.example/article", "https://fixture.example/article", changed, None, 2
    )
    assert len(repo.list_rows("sources", inv)) == 2
    assert all(row["status"] == "partial" for row in repo.list_rows("sources", inv))
    with repo.db.transaction() as con:
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(
                "INSERT INTO sources(id,investigation_id,run_id,origin,"
                "original_url,canonical_url,status) "
                "VALUES ('cross',?,?,'mock','https://fixture.example/a',"
                "'https://fixture.example/a','failed')",
                (other, run["id"]),
            )


def test_tavily_contract_is_mock_only():
    from deeptrace.collection.tavily import MockTavily, Tavily
    from deeptrace.providers import OutboundDisabled, SearchRequest

    request = SearchRequest(query="Synthetic query", limit=1)
    assert MockTavily().search(request)[0].title.startswith("SIMULATED")
    with pytest.raises(OutboundDisabled):
        Tavily().search(request)
