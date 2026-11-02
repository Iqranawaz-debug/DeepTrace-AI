"""Atomic local writes; no provider operations."""

import sqlite3
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from deeptrace.models import (
    Investigation,
    InvestigationCreate,
    InvestigationEdit,
    InvestigationList,
    Plan,
    PlanItem,
    PlanSave,
)
from deeptrace.storage.database import Database


class WorkspaceError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def stamp(previous: str | None = None) -> str:
    now = datetime.now(UTC)
    if previous:
        now = max(now, datetime.fromisoformat(previous) + timedelta(microseconds=1))
    return now.isoformat()


# Status is derived from persisted run state: migration 001 fixes the column to 'draft'.
SELECT_INVESTIGATION = (
    "SELECT i.id,i.title,i.question,i.description,i.status,i.created_at,i.updated_at,i.sensitive,"
    "(SELECT a.archived_at FROM investigation_archives a WHERE a.investigation_id=i.id) "
    "AS archived_at,"
    "(SELECT COUNT(*) FROM sources s WHERE s.investigation_id=i.id) AS source_count,"
    "(SELECT r.status FROM runs r WHERE r.investigation_id=i.id "
    "ORDER BY r.created_at DESC,r.rowid DESC LIMIT 1) AS run_status,"
    "(SELECT json_extract(r.config_snapshot_json,'$.scope') FROM runs r "
    "WHERE r.investigation_id=i.id ORDER BY r.created_at DESC,r.rowid DESC LIMIT 1) AS run_scope "
    "FROM investigations i "
)
LIFECYCLE = {
    "queued": "Running",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
    "cancelled": "Cancelled",
    "budget_reached": "Budget reached",
    "interrupted": "Interrupted",
}


def to_investigation(row: sqlite3.Row) -> Investigation:
    values = dict(row)
    status, scope = values.pop("run_status"), values.pop("run_scope")
    if values["archived_at"]:
        lifecycle = "Archived"
    elif status is None:
        lifecycle = "Draft"
    elif scope == "plan_generation":
        # Generating a plan is not research: only active planning changes the label.
        lifecycle = "Planning" if status in {"queued", "running"} else "Draft"
    else:
        lifecycle = LIFECYCLE[status]
    return Investigation.model_validate({**values, "lifecycle": lifecycle})


def lookup(connection: sqlite3.Connection, identifier: str) -> Investigation:
    connection.row_factory = sqlite3.Row
    row = connection.execute(SELECT_INVESTIGATION + "WHERE i.id=?", (identifier,)).fetchone()
    if row is None:
        raise WorkspaceError(404, "not_found", "Investigation not found.")
    return to_investigation(row)


class Repository:
    def __init__(self, database: Database):
        self.database = database

    def get(self, identifier: str) -> Investigation:
        with self.database.connection() as connection:
            return lookup(connection, identifier)

    def create(self, data: InvestigationCreate) -> Investigation:
        with self.database.transaction() as connection:
            identifier = str(data.id)
            if connection.execute(
                "SELECT 1 FROM investigations WHERE id=?", (identifier,)
            ).fetchone():
                existing = lookup(connection, identifier)
                if (existing.title, existing.question, existing.description) == (
                    data.title,
                    data.question,
                    data.description,
                ):
                    return existing
                raise WorkspaceError(409, "conflict", "Identifier already belongs to saved work.")
            now = stamp()
            connection.execute(
                "INSERT INTO investigations(id,title,question,description,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (identifier, data.title, data.question, data.description, now, now),
            )
            return lookup(connection, identifier)

    def edit(self, identifier: str, data: InvestigationEdit) -> Investigation:
        with self.database.transaction() as connection:
            current = lookup(connection, identifier)
            if connection.execute(
                "SELECT 1 FROM runs WHERE investigation_id=? AND status IN ('queued','running')",
                (identifier,),
            ).fetchone():
                raise WorkspaceError(
                    409, "run_active", "Wait for collection to finish before editing."
                )
            if current.updated_at != data.expected_updated_at:
                raise WorkspaceError(409, "conflict", "Newer changes exist. Reload before saving.")
            connection.execute(
                "UPDATE investigations SET title=?,question=?,description=?,updated_at=? "
                "WHERE id=?",
                (
                    data.title,
                    data.question,
                    data.description,
                    stamp(current.updated_at),
                    identifier,
                ),
            )
            return lookup(connection, identifier)

    def list(self, query: str, limit: int, offset: int) -> InvestigationList:
        with self.database.connection() as connection:
            connection.execute("BEGIN")
            connection.row_factory = sqlite3.Row
            where = " WHERE instr(lower(title),lower(?))>0 OR instr(lower(question),lower(?))>0"
            args = (query, query)
            total = connection.execute(
                "SELECT count(*) FROM investigations" + where, args
            ).fetchone()[0]
            rows = connection.execute(
                SELECT_INVESTIGATION + where + " ORDER BY i.updated_at DESC,i.id LIMIT ? OFFSET ?",
                (*args, limit, offset),
            ).fetchall()
            return InvestigationList(items=[to_investigation(r) for r in rows], total=total)

    def plan(self, identifier: str) -> Plan:
        with self.database.connection() as connection:
            connection.execute("BEGIN")
            lookup(connection, identifier)
            return self._plan(connection, identifier)

    @staticmethod
    def _plan(connection: sqlite3.Connection, identifier: str) -> Plan:
        row = connection.execute(
            "SELECT id,revision_no FROM plans WHERE investigation_id=?",
            (identifier,),
        ).fetchone()
        if row is None:
            return Plan(id=None, revision_no=0, items=[])
        items = connection.execute(
            "SELECT id,sub_question,search_query FROM plan_items WHERE plan_id=? ORDER BY ordinal",
            (row[0],),
        ).fetchall()
        return Plan(
            id=row[0], revision_no=row[1], items=[PlanItem.model_validate(dict(r)) for r in items]
        )

    def save_plan(self, identifier: str, data: PlanSave) -> Plan:
        with self.database.transaction() as connection:
            investigation = lookup(connection, identifier)
            if connection.execute(
                "SELECT 1 FROM runs WHERE investigation_id=? AND status IN ('queued','running')",
                (identifier,),
            ).fetchone():
                raise WorkspaceError(
                    409, "run_active", "Wait for collection to finish before editing."
                )
            current = self._plan(connection, identifier)
            if current.revision_no != data.expected_revision:
                raise WorkspaceError(
                    409, "conflict", "Newer plan changes exist. Reload before saving."
                )
            plan_id = str(current.id or uuid4())
            for item in data.items:
                owner = connection.execute(
                    "SELECT plan_id FROM plan_items WHERE id=?", (str(item.id),)
                ).fetchone()
                if owner and owner[0] != plan_id:
                    raise WorkspaceError(409, "ownership_conflict", "Step belongs to another plan.")
            if current.id is None:
                connection.execute(
                    "INSERT INTO plans(id,investigation_id,revision_no,created_at) "
                    "VALUES (?,?,1,?)",
                    (plan_id, identifier, stamp()),
                )
            else:
                # A manual edit makes the plan user-authored; drop any generation provenance.
                connection.execute(
                    "UPDATE plans SET revision_no=revision_no+1,prompt_version=NULL,"
                    "provider_id=NULL,model_id=NULL WHERE id=?",
                    (plan_id,),
                )
            connection.execute("DELETE FROM plan_items WHERE plan_id=?", (plan_id,))
            connection.executemany(
                "INSERT INTO plan_items(id,plan_id,ordinal,sub_question,search_query) "
                "VALUES (?,?,?,?,?)",
                [
                    (str(item.id), plan_id, order, item.sub_question, item.search_query)
                    for order, item in enumerate(data.items, 1)
                ],
            )
            connection.execute(
                "UPDATE investigations SET updated_at=? WHERE id=?",
                (stamp(investigation.updated_at), identifier),
            )
            return self._plan(connection, identifier)
