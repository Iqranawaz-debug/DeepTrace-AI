import sqlite3
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from test_investigations import client as workspace_client
from test_investigations import create

from deeptrace.models import PlanSave
from deeptrace.storage.repository import Repository, WorkspaceError

client = workspace_client


def step(text="Investigate the local context"):
    return {"id": str(uuid4()), "sub_question": text, "search_query": None}


def test_plan_reorder_edit_remove_and_conflict(client):
    inv = create(client).json()
    path = f"/api/investigations/{inv['id']}/plan"
    assert client.get(path).json() == {"id": None, "revision_no": 0, "items": []}
    items = [step(), step("Second question")]
    first = client.put(path, json={"expected_revision": 0, "items": items})
    assert first.status_code == 200
    assert first.json()["items"] == items
    reordered = [items[1], {**items[0], "sub_question": "Edited question"}]
    second = client.put(path, json={"expected_revision": 1, "items": reordered}).json()
    assert second["items"] == reordered
    assert second["id"] == first.json()["id"]
    assert client.put(path, json={"expected_revision": 1, "items": []}).status_code == 409
    assert client.get(path).json() == second
    assert client.put(path, json={"expected_revision": 2, "items": []}).json()["items"] == []
    assert client.get(f"/api/investigations/{inv['id']}").json()["updated_at"] > inv["updated_at"]


def test_limits_ownership_and_failed_write_preserve_data(client):
    inv = create(client).json()
    path = f"/api/investigations/{inv['id']}/plan"
    item = step()
    for items in ([step() for _ in range(9)], [item, item], [step("")]):
        assert client.put(path, json={"expected_revision": 0, "items": items}).status_code == 422
    saved = client.put(path, json={"expected_revision": 0, "items": [item]}).json()
    other = create(client).json()
    other_path = f"/api/investigations/{other['id']}/plan"
    assert client.put(other_path, json={"expected_revision": 0, "items": [item]}).status_code == 409
    assert client.get(other_path).json()["revision_no"] == 0
    assert client.get(path).json() == saved
    db = client.app.state.database
    before = client.get(f"/api/investigations/{inv['id']}").json()
    with db.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER fail_step BEFORE INSERT ON plan_items "
            "BEGIN SELECT RAISE(ABORT, 'synthetic private failure'); END"
        )
    response = client.put(path, json={"expected_revision": 1, "items": [step()]})
    assert response.status_code == 500
    assert "synthetic private" not in response.text
    assert client.get(path).json() == saved
    assert client.get(f"/api/investigations/{inv['id']}").json() == before


def test_concurrent_plan_writers_and_foreign_keys(client):
    inv = create(client).json()
    repo = Repository(client.app.state.database)

    def save(_):
        try:
            return repo.save_plan(inv["id"], PlanSave(expected_revision=0, items=[])).revision_no
        except WorkspaceError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, range(2))) == [1, 409]
    assert Repository(client.app.state.database).plan(inv["id"]).revision_no == 1
    with (
        pytest.raises(sqlite3.IntegrityError),
        client.app.state.database.transaction() as connection,
    ):
        connection.execute(
            "INSERT INTO plans(id,investigation_id,revision_no,created_at) "
            "VALUES ('orphan','missing',1,'now')"
        )
