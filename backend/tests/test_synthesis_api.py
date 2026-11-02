"""Phase 4: saved URLs, evidence review, citation integrity and immutable reports."""

import hashlib
import re
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_collection_api import client, investigation, start, terminal  # noqa: F401

from deeptrace.config import Settings
from deeptrace.evidence import kernel
from deeptrace.evidence.report import escape_block
from deeptrace.main import create_app

HOSTILE = "<script>alert(1)</script> [click](javascript:alert(1)) ![x](http://evil/x.png) # H"


def collected(client):  # noqa: F811
    """Investigation with one synthetic source; returns (investigation, passage)."""
    inv = investigation(client)
    client.post("/api/web-consent", json={"accepted": True})
    run = terminal(client, inv, start(client, inv).json()["id"])
    assert run["status"] == "completed", run
    passages = client.get(f"/api/investigations/{inv}/passages").json()
    assert passages and passages[0]["display_id"] == "P-0001"
    return inv, passages[0]


def claim(passage_id, relation="supports", quote=None, text="Fixture text exists.", kind="finding"):
    cite = {"passage_id": passage_id, "relation": relation}
    if quote is not None:
        cite["quoted_text"] = quote
    return {"id": str(uuid4()), "claim_type": kind, "claim_text": text, "citations": [cite]}


def save(client, inv, claims, revision=0, **fields):  # noqa: F811
    return client.put(
        f"/api/investigations/{inv}/answer",
        json={"expected_revision": revision, "claims": claims, **fields},
    )


def test_saved_url_is_a_lead_not_evidence(client):  # noqa: F811
    inv, other = investigation(client), investigation(client)
    body = {"id": str(uuid4()), "url": "https://Example.org/page", "note": "Read later"}
    saved = client.post(f"/api/investigations/{inv}/saved-urls", json=body)
    assert saved.status_code == 201, saved.text
    assert saved.json()["retrieved"] is False
    assert saved.json()["canonical_url"] == "https://example.org/page"
    # Idempotent retry; duplicate canonical URL is reported, not silently merged.
    assert client.post(f"/api/investigations/{inv}/saved-urls", json=body).status_code == 201
    dup = {"url": "https://example.org/page"}
    assert client.post(f"/api/investigations/{inv}/saved-urls", json=dup).status_code == 409
    for unsafe in ("http://127.0.0.1/", "file:///etc/passwd", "https://user:pw@example.org/"):
        r = client.post(f"/api/investigations/{inv}/saved-urls", json={"url": unsafe})
        assert r.status_code == 422
    # Saving never creates a source, run, passage or network request.
    assert client.get(f"/api/investigations/{inv}/sources").json() == []
    assert client.get(f"/api/investigations/{inv}/runs").json() == []
    assert client.get(f"/api/investigations/{other}/saved-urls").json() == []
    missing = f"/api/investigations/{uuid4()}/saved-urls"
    assert client.post(missing, json={"url": "https://example.org/"}).status_code == 404


def test_evidence_notes_revisions_targets_and_isolation(client):  # noqa: F811
    inv, passage = collected(client)
    other, other_passage = collected(client)
    step = str(uuid4())
    plan = client.put(
        f"/api/investigations/{inv}/plan",
        json={"expected_revision": 0, "items": [{"id": step, "sub_question": "Step one"}]},
    )
    assert plan.status_code == 200
    note = {"id": str(uuid4()), "passage_id": passage["id"], "target_key": step,
            "stance": "supports", "note": HOSTILE, "expected_revision": 0}  # fmt: skip
    url = f"/api/investigations/{inv}/evidence-notes"
    created = client.put(url, json=note)
    assert created.status_code == 200, created.text
    assert created.json()["target_label"] == "Step one" and created.json()["note"] == HOSTILE
    assert client.put(url, json=note).status_code == 409  # duplicate passage/target
    updated = client.put(url, json={**note, "stance": "contradicts", "expected_revision": 1})
    assert updated.json()["revision_no"] == 2
    stale = client.put(url, json={**note, "stance": "context", "expected_revision": 1})
    assert stale.status_code == 409
    unknown = {**note, "id": str(uuid4()), "target_key": str(uuid4())}
    assert client.put(url, json=unknown).status_code == 422
    foreign = {**note, "id": str(uuid4()), "passage_id": other_passage["id"]}
    assert client.put(url, json=foreign).status_code == 404
    # Removing the plan step keeps the label snapshot and flags it; never retargets.
    client.put(f"/api/investigations/{inv}/plan", json={"expected_revision": 1, "items": []})
    listed = client.get(url).json()
    assert (listed[0]["target_label"], listed[0]["target_current"]) == ("Step one", False)
    assert client.get(f"/api/investigations/{other}/evidence-notes").json() == []


def test_citations_validated_before_save(client):  # noqa: F811
    inv, passage = collected(client)
    other, other_passage = collected(client)
    fabricated = save(client, inv, [claim(str(uuid4()))])
    assert fabricated.status_code == 422
    assert "passage_not_found" in fabricated.json()["error"]["message"]
    cross = save(client, inv, [claim(other_passage["id"])])
    assert cross.status_code == 422  # Never reveals the other investigation's passage.
    wrong_quote = save(client, inv, [claim(passage["id"], quote="words never in the passage")])
    assert wrong_quote.status_code == 422 and "quote_mismatch" in wrong_quote.text
    # Nothing was persisted by the rejected saves.
    assert client.get(f"/api/investigations/{inv}/answer").json()["revision_no"] == 0
    with client.app.state.database.connection() as con:
        assert con.execute("SELECT COUNT(*) FROM citations").fetchone()[0] == 0


def test_cited_contradicting_and_insufficient_states(client):  # noqa: F811
    inv, passage = collected(client)
    pid = passage["id"]
    # Whitespace and NFC-normalized, case-sensitive quote matching (ADR-A14).
    quote = "SIMULATED   EVIDENCE: This paragraph"
    claims = [
        claim(pid, quote=quote),
        claim(pid, relation="contradicts", text="A disputed statement.", kind="conflict"),
        {"id": str(uuid4()), "claim_type": "gap", "claim_text": "Nothing found yet.",
         "citations": []},
        claim(pid, quote="simulated evidence", text="Case differs."),
    ]  # fmt: skip
    assert save(client, inv, claims).status_code == 422  # lower-case quote rejected
    saved = save(client, inv, claims[:3], summary_text=HOSTILE)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    states = [c["evidence_state"] for c in body["claims"]]
    assert states == ["cited", "not_established", "not_established"]
    first = body["claims"][0]["citations"][0]
    assert first["quote_valid"] is True and first["display_id"] == "P-0001"
    assert first["passage_text"] == passage["text"]
    assert body["summary_text"] == HOSTILE  # stored verbatim; escaped only on render
    assert save(client, inv, claims[:1], revision=0).status_code == 409  # stale draft


def test_report_versions_are_immutable_escaped_and_survive_restart(tmp_path):
    settings = Settings(data_dir=tmp_path, _env_file=None)

    def connect():
        c = TestClient(create_app(settings), base_url="http://127.0.0.1:8000")
        c.__enter__()
        c.headers.update({"Origin": "http://127.0.0.1:5173",
                          "X-DeepTrace-Token": c.get("/api/session").json()["token"]})  # fmt: skip
        return c

    c = connect()
    inv, passage = collected(c)
    url = f"/api/investigations/{inv}/reports"
    assert c.post(url, json={"expected_revision": 1}).status_code == 409  # no draft yet
    claims = [claim(passage["id"], quote="SIMULATED EVIDENCE", text=HOSTILE)]
    assert save(c, inv, claims, limitations_text="Fixture only.").status_code == 200
    assert c.post(url, json={"expected_revision": 2}).status_code == 409
    v1 = c.post(url, json={"expected_revision": 1})
    assert v1.status_code == 201, v1.text
    report = v1.json()
    text = report["markdown_text"]
    assert report["version_no"] == 1
    assert report["markdown_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    for required in ("SIMULATED EVIDENCE.", "`` P-0001 ``"[1:-1], "quotation matches",
                     "Research aid, not verified research", "no language model was used",
                     "Author and publication date: unknown"):  # fmt: skip
        assert required in text, required
    assert "P-0001" in text
    # Hostile user text cannot form HTML, links or images in the Markdown.
    # No unescaped HTML opener and no unescaped link/image bracket anywhere in the file.
    assert not re.search(r"(?<!\\)<", text)
    assert not re.search(r"(?<!\\)\]\(", text)
    assert "\\<script\\>" in text and "\\[click\\]" in text
    assert report["validation_summary"]["claims_cited"] == 1
    download = c.get(f"{url}/1/download")
    assert download.status_code == 200
    assert download.content == text.encode("utf-8")
    assert download.headers["content-disposition"] == (
        f'attachment; filename="deeptrace-report-{inv[:8]}-v1.md"'
    )
    assert download.headers["x-content-type-options"] == "nosniff"
    with c.app.state.database.transaction() as con, pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE report_versions SET markdown_text='changed'")
    # A new draft revision produces version 2; version 1 bytes never change.
    save(c, inv, claims, revision=1, summary_text="Revised.")
    assert c.post(url, json={"expected_revision": 2}).json()["version_no"] == 2
    old = c.get(f"{url}/1").json()
    assert old["markdown_text"] == text
    assert "You are viewing an older version." in old["current_warnings"]
    assert "The draft has changed since this version was created." in old["current_warnings"]
    c.__exit__(None, None, None)
    # Restart: drafts, citations and reports persist across processes.
    c = connect()
    assert [r["version_no"] for r in c.get(url).json()] == [2, 1]
    assert c.get(f"{url}/1").json()["markdown_text"] == text
    restored = c.get(f"/api/investigations/{inv}/answer").json()
    assert restored["claims"][0]["citations"][0]["passage_id"] == passage["id"]
    assert c.get(f"{url}/9").status_code == 404
    c.__exit__(None, None, None)


def test_tampered_report_is_refused(client):  # noqa: F811
    inv, passage = collected(client)
    save(client, inv, [claim(passage["id"])])
    client.post(f"/api/investigations/{inv}/reports", json={"expected_revision": 1})
    with client.app.state.database.transaction() as con:
        con.execute("DROP TRIGGER immutable_report_version")
        con.execute("UPDATE report_versions SET markdown_text='tampered'")
    assert client.get(f"/api/investigations/{inv}/reports/1").status_code == 500
    assert client.get(f"/api/investigations/{inv}/reports/1/download").status_code == 500


def test_cross_investigation_reports_are_isolated(client):  # noqa: F811
    inv, passage = collected(client)
    other = investigation(client)
    save(client, inv, [claim(passage["id"])])
    client.post(f"/api/investigations/{inv}/reports", json={"expected_revision": 1})
    assert client.get(f"/api/investigations/{other}/reports/1").status_code == 404
    assert client.get(f"/api/investigations/{other}/reports").json() == []
    assert client.get(f"/api/investigations/{other}/answer").json()["claims"] == []


def test_database_rejects_cross_investigation_citation(client):  # noqa: F811
    inv, passage = collected(client)
    other, _ = collected(client)
    save(client, other, [])
    with client.app.state.database.transaction() as con:
        answer = con.execute("SELECT id FROM answers WHERE investigation_id=?", (other,)).fetchone()
        con.execute(
            "INSERT INTO claims VALUES ('c1',?,?,1,'finding','x','not_established',NULL)",
            (answer[0], other),
        )
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(
                "INSERT INTO citations VALUES ('x','c1',?,?,1,'supports','manual',NULL,?,1,NULL,"
                "'v','now',1,NULL)",
                (other, passage["id"], "0" * 64),
            )


@pytest.mark.parametrize(
    ("method", "path"),
    [("put", "answer"), ("post", "reports"), ("put", "evidence-notes"), ("post", "saved-urls")],
)
def test_new_mutations_require_token_and_origin(client, method, path):  # noqa: F811
    inv = investigation(client)
    url = f"/api/investigations/{inv}/{path}"
    no_token = getattr(client, method)(url, json={}, headers={"X-DeepTrace-Token": "wrong"})
    assert no_token.status_code == 403
    hostile = getattr(client, method)(url, json={}, headers={"Origin": "https://evil.example"})
    assert hostile.status_code == 403


def test_kernel_and_escaping_units():
    assert kernel.quote_matches("café  au lait", "Un café au lait chaud")
    assert not kernel.quote_matches("Cafe", "cafe")
    assert not kernel.quote_matches("   ", "anything")
    check = kernel.check_citation("a", kernel.PassageRecord("p", "b", "text"), None)
    assert (check.reference_valid, check.reason) == (False, "passage_not_found")
    changed = kernel.check_citation("a", kernel.PassageRecord("p", "a", "t"), None, "0" * 64)
    assert changed.reason == "passage_changed"
    lines = escape_block("# Heading\n\n- item\n\n1. one\n\n---\n\n> quote\n\n<b>x</b> `c` *e*")
    assert lines[0] == "\\# Heading" and lines[2] == "\\- item" and lines[4] == "1\\. one"
    assert lines[6] == "\\---" and lines[8] == "\\> quote"
    assert lines[10] == "\\<b\\>x\\</b\\> \\`c\\` \\*e\\*"
