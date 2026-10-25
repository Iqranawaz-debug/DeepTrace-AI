import logging
import socket

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from deeptrace.config import Settings
from deeptrace.main import create_app
from deeptrace.providers import OutboundDisabled, ProviderBoundary


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, _env_file=None))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        yield client


def test_health_readiness_capabilities(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/ready").json()["status"] == "ready"
    assert client.get("/api/capabilities").json() == {
        "phase": 2,
        "mode": "mock",
        "research": False,
        "outbound": False,
        "investigations": True,
    }
    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://localhost.evil:5173"])
def test_hostile_origins(client, origin):
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


def test_cors_and_host(client):
    response = client.options(
        "/api/health",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.post("/api/settings").status_code == 405


@pytest.mark.parametrize("host", ["evil@localhost", "localhost:bad", "[broken", "localhost:9999"])
def test_malformed_hosts(client, host):
    assert client.get("/api/health", headers={"Host": host}).status_code == 400


def test_readiness_reports_database_failure(client):
    with client.app.state.database.transaction() as connection:
        connection.execute("DROP TABLE schema_meta")
    assert client.get("/api/health").status_code == 200
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_ready"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "live_free"},
        {"allow_paid_apis": True},
        {"host": "0.0.0.0"},
        {"origins": ["*"]},
        {"origins": ["http://127.0.0.1:5173/"]},
        {"origins": ["http://user@localhost:5173"]},
        {"data_dir": "relative"},
    ],
)
def test_unsafe_configuration(kwargs):
    with pytest.raises(ValidationError):
        Settings(**kwargs, _env_file=None)


def test_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPTRACE_MODE", "offline")
    assert Settings(data_dir=tmp_path, _env_file=None).mode == "offline"


def test_errors_and_logging_do_not_echo_input(client, caplog):
    marker = "test-private-content-123"
    with caplog.at_level(logging.INFO, logger="deeptrace"):
        response = client.get(f"/api/missing?key={marker}")
    assert response.status_code == 404
    assert marker not in response.text
    assert marker not in " ".join(r.message for r in caplog.records if r.name == "deeptrace")
    assert set(response.json()["error"]) == {
        "code",
        "message",
        "what_failed",
        "what_saved",
        "next_step",
    }


def test_internal_error_redacted(tmp_path, caplog):
    app = create_app(Settings(data_dir=tmp_path, _env_file=None))

    @app.get("/api/broken")
    def broken():
        raise RuntimeError("test-private-content-123")

    with TestClient(app, base_url="http://localhost:8000") as client:
        response = client.get("/api/broken")
    assert response.status_code == 500
    assert "test-private-content" not in response.text + caplog.text


@pytest.mark.parametrize("provider", ["gemini", "tavily", "unknown"])
def test_provider_boundary_always_denies(provider):
    with pytest.raises(OutboundDisabled):
        ProviderBoundary().authorize(provider)


def test_network_guard_blocks_real_connections():
    with pytest.raises(AssertionError, match="Network is disabled"):
        socket.create_connection(("example.invalid", 443))
    with socket.socket() as connection:
        with pytest.raises(AssertionError, match="Network is disabled"):
            connection.connect_ex(("203.0.113.1", 443))


def test_offline_mode_has_no_provider_execution(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, mode="offline", _env_file=None))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        assert client.get("/api/capabilities").json()["outbound"] is False
        assert client.get("/api/capabilities").json()["mode"] == "offline"
        assert client.post("/api/investigations").status_code == 403
