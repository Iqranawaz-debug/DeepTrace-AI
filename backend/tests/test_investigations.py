from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from deeptrace.config import Settings
from deeptrace.main import create_app


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


def create(client, **changes):
    data = {
        "id": str(uuid4()),
        "title": "Synthetic study",
        "question": "What should we investigate?",
    }
    data.update(changes)
    return client.post("/api/investigations", json=data)


def test_create_retry_duplicate_title_list_edit_conflict(client):
    data = create(client).json()
    path = "/api/investigations/" + data["id"]
    assert client.get(path).json() == data
    payload = {k: data[k] for k in ("id", "title", "question", "description")}
    assert client.post("/api/investigations", json=payload).json() == data
    assert create(client).status_code == 201
    assert client.get("/api/investigations?limit=1").json()["total"] == 2
    assert len(client.get("/api/investigations?limit=1").json()["items"]) == 1
    patch = {
        "title": "Edited",
        "question": data["question"],
        "description": "Notes",
        "expected_updated_at": data["updated_at"],
    }
    saved = client.patch(path, json=patch)
    assert saved.status_code == 200
    assert saved.json()["updated_at"] > data["updated_at"]
    assert client.patch(path, json=patch).status_code == 409
    assert client.get(path).json() == saved.json()
    assert client.get("/api/investigations?q=edited").json()["total"] == 1
    assert client.get("/api/investigations?q=%27%20OR%201=1--").json()["total"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " "},
        {"title": "x" * 121},
        {"question": ""},
        {"question": "short"},
        {"question": "x" * 1001},
        {"description": "x" * 5001},
        {"id": "invalid"},
        {"unknown": True},
    ],
)
def test_validation(client, changes):
    assert create(client, **changes).status_code == 422
    assert client.get("/api/investigations").json()["total"] == 0


def test_missing_and_invalid(client):
    assert client.get("/api/investigations/invalid").status_code == 422
    assert client.get("/api/investigations/" + str(uuid4())).status_code == 404
    assert client.get("/api/investigations?limit=101").status_code == 422
    assert client.get("/api/investigations?offset=-1").status_code == 422
