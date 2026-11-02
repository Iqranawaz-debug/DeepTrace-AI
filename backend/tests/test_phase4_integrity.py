"""Checklist gaps: limits, oversize rejection, evidence that changes or disappears."""

import json
from uuid import uuid4

import pytest
from test_collection_api import client, investigation, start, terminal  # noqa: F401
from test_synthesis_api import claim, collected, save

from deeptrace.collection.extractor import extract
from deeptrace.evidence import kernel


def test_mixed_collection_keeps_successes_and_reports_partial(client):  # noqa: F811
    inv = investigation(client)
    client.post("/api/web-consent", json={"accepted": True})
    urls = ["https://fixture.example/article", "https://fixture.example/failure"]
    run = terminal(client, inv, start(client, inv, urls).json()["id"])
    # Documented limitation: any failed URL labels the run failed/partial_collection.
    assert (run["status"], run["error_code"]) == ("failed", "partial_collection")
    statuses = sorted(s["status"] for s in run["sources"])
    assert statuses == ["failed", "fetched"]
    # The successful source and its passages remain available as evidence.
    assert client.get(f"/api/investigations/{inv}/passages").json()[0]["display_id"] == "P-0001"


def test_claim_and_citation_limits(client):  # noqa: F811
    inv, passage = collected(client)
    pid = passage["id"]
    many = [claim(pid) for _ in range(31)]
    assert save(client, inv, many).status_code == 422
    assert save(client, inv, many[:30]).status_code == 200
    eleven = claim(pid)
    eleven["citations"] = [{"passage_id": str(uuid4()), "relation": "context"}] * 11
    assert save(client, inv, [eleven], revision=1).status_code == 422
    duplicate = claim(pid)
    duplicate["citations"] *= 2
    assert save(client, inv, [duplicate], revision=1).status_code == 422
    assert client.get(f"/api/investigations/{inv}/answer").json()["revision_no"] == 1


def test_oversized_draft_is_rejected_not_truncated(client):  # noqa: F811
    inv, passage = collected(client)
    assert save(client, inv, [claim(passage["id"])], summary_text="Kept.").status_code == 200
    huge = [claim(passage["id"], text="x" * 2000) for _ in range(30)]
    body = json.dumps({"expected_revision": 1, "claims": huge, "summary_text": "Lost?"})
    assert len(body.encode()) > 65536
    response = client.put(
        f"/api/investigations/{inv}/answer",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    saved = client.get(f"/api/investigations/{inv}/answer").json()
    assert (saved["revision_no"], saved["summary_text"], len(saved["claims"])) == (1, "Kept.", 1)


def test_context_only_and_contradicting_only_claims_are_not_established(client):  # noqa: F811
    inv, passage = collected(client)
    pid = passage["id"]
    claims = [claim(pid, relation="context"), claim(pid, relation="contradicts")]
    body = save(client, inv, claims).json()
    assert [c["evidence_state"] for c in body["claims"]] == ["not_established"] * 2
    # The contradicting citation is still displayed, not hidden.
    assert body["claims"][1]["citations"][0]["relation"] == "contradicts"


def test_changed_passage_invalidates_citation_on_read_and_report(client):  # noqa: F811
    inv, passage = collected(client)
    save(client, inv, [claim(passage["id"], quote="SIMULATED EVIDENCE")])
    assert (
        client.get(f"/api/investigations/{inv}/answer").json()["claims"][0]["evidence_state"]
        == "cited"
    )
    # Simulate out-of-band tampering that bypasses the immutability trigger.
    with client.app.state.database.transaction() as con:
        con.execute("DROP TRIGGER immutable_passage")
        con.execute("UPDATE passages SET text='Different words entirely.' WHERE id=?",
                    (passage["id"],))  # fmt: skip
    answer = client.get(f"/api/investigations/{inv}/answer").json()
    cite = answer["claims"][0]["citations"][0]
    assert (cite["reference_valid"], cite["invalid_reason"]) == (False, "passage_changed")
    assert answer["claims"][0]["evidence_state"] == "not_established"
    report = client.post(f"/api/investigations/{inv}/reports", json={"expected_revision": 1})
    text = report.json()["markdown_text"]
    assert "REFERENCE INVALID (passage\\_changed)" in text
    assert "Not established" in text
    assert report.json()["validation_summary"]["claims_cited"] == 0


def test_removed_passage_is_never_valid():
    record = kernel.PassageRecord("p", "inv", "text", removed=True)
    assert kernel.check_citation("inv", record, None).reason == "passage_removed"
    assert kernel.check_citation("inv", record, "text").reference_valid is False


def test_foreign_and_invalid_report_requests(client):  # noqa: F811
    inv, passage = collected(client)
    other = investigation(client)
    save(client, inv, [claim(passage["id"])])
    client.post(f"/api/investigations/{inv}/reports", json={"expected_revision": 1})
    assert client.get(f"/api/investigations/{other}/reports/1/download").status_code == 404
    assert client.get(f"/api/investigations/{inv}/reports/0").status_code == 422
    assert client.get("/api/investigations/not-a-uuid/reports").status_code == 422
    bad_json = client.put(
        f"/api/investigations/{inv}/answer",
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert bad_json.status_code == 422


@pytest.mark.parametrize(
    ("body", "status", "fragment"),
    [
        (b"<main><p>Unclosed <b>bold <i>text" + b" words" * 20, "fetched", "Unclosed bold text"),
        (b"<body><noscript>Enable JavaScript</noscript><div id=root></div></body>", None, None),
        (b"<main><p>caf\xc3\xa9 \xe2\x80\x94 \xf0\x9f\xa7\xaa</p>" + b"<p>pad</p>" * 30
         + b"</main>", "fetched", "café — 🧪"),
    ],
    ids=["malformed", "javascript-only", "unicode"],
)  # fmt: skip
def test_extraction_fixtures(body, status, fragment):
    if status is None:
        # A script-dependent shell yields no readable text and is reported, not invented.
        with pytest.raises(Exception, match="empty_content"):
            extract(body, "text/html")
        return
    result = extract(body, "text/html")
    assert result.status == status and fragment in result.text
