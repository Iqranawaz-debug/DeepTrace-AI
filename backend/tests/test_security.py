import logging

import pytest
from test_investigations import client as workspace_client
from test_investigations import create

client = workspace_client


@pytest.mark.parametrize(
    "header,value,status",
    [
        ("Origin", "https://evil.example", 403),
        ("Origin", "null", 403),
        ("Origin", "", 403),
        ("X-DeepTrace-Token", "wrong", 403),
        ("Host", "localhost.evil", 400),
        ("Content-Type", "text/plain", 415),
    ],
)
def test_mutation_boundary(client, header, value, status):
    assert (
        client.post("/api/investigations", json={}, headers={header: value}).status_code == status
    )
    assert client.get("/api/investigations").json()["total"] == 0


def test_session_and_payload_security(client, caplog):
    response = client.get("/api/session")
    assert response.headers["cache-control"] == "no-store"
    token = response.json()["token"]
    with caplog.at_level(logging.INFO, logger="deeptrace"):
        assert create(client, question="private-marker-question").status_code == 201
    assert token not in caplog.text
    assert "private-marker-question" not in caplog.text
    assert (
        client.post(
            "/api/investigations",
            content=b"x" * 65537,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/investigations", content="{", headers={"Content-Type": "application/json"}
        ).status_code
        == 422
    )
    del client.headers["Origin"]
    assert client.post("/api/investigations", json={}).status_code == 403
    assert client.get("/api/health").status_code == 200


def test_mutation_preflight(client):
    response = client.options(
        "/api/investigations",
        headers={
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-deeptrace-token",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-credentials" not in response.headers


def test_duplicate_headers_missing_token_and_hostile_session(client):
    token = client.headers["X-DeepTrace-Token"]
    response = client.post(
        "/api/investigations",
        json={},
        headers=[("Origin", "http://127.0.0.1:5173"), ("Origin", "http://127.0.0.1:5173")],
    )
    assert response.status_code == 403
    response = client.post(
        "/api/investigations",
        json={},
        headers=[("X-DeepTrace-Token", token), ("X-DeepTrace-Token", token)],
    )
    assert response.status_code == 403
    assert client.get("/api/session", headers={"Origin": "https://evil.example"}).status_code == 403
    del client.headers["X-DeepTrace-Token"]
    assert client.post("/api/investigations", json={}).status_code == 403


def test_non_ascii_session_token_is_denied(client):
    response = client.post("/api/investigations", json={}, headers={b"X-DeepTrace-Token": b"\xff"})
    assert response.status_code == 403
