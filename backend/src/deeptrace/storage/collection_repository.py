"""Short transactions for immutable evidence and collection checkpoints."""

import json
import sqlite3
from typing import Any
from uuid import uuid4

from deeptrace.collection.extractor import Extraction
from deeptrace.collection.models import RunStart
from deeptrace.collection.passages import slices
from deeptrace.storage.database import Database
from deeptrace.storage.repository import Repository, WorkspaceError, lookup, stamp


class CollectionRepository:
    def __init__(self, database: Database, disclosure_version: str = "fixture-v1"):
        self.db = database
        # Consent is version-bound: fixture consent can never authorize live networking.
        self.disclosure_version = disclosure_version

    def consent(self) -> bool:
        with self.db.connection() as con:
            row = con.execute(
                "SELECT 1 FROM provider_consents WHERE provider_id='public_web' AND "
                "disclosure_version=? AND revoked_at IS NULL LIMIT 1",
                (self.disclosure_version,),
            ).fetchone()
            return row is not None

    def set_consent(self, accepted: bool) -> None:
        with self.db.transaction() as con:
            now = stamp()
            con.execute(
                "UPDATE provider_consents SET revoked_at=? WHERE provider_id='public_web' AND "
                "disclosure_version=? AND revoked_at IS NULL",
                (now, self.disclosure_version),
            )
            if accepted:
                con.execute(
                    "INSERT INTO provider_consents VALUES (?,'public_web','collection',?,?,NULL)",
                    (str(uuid4()), self.disclosure_version, now),
                )
            else:
                con.execute(
                    "UPDATE runs SET cancel_requested=1 WHERE status IN ('queued','running')"
                )

    @staticmethod
    def event(con: sqlite3.Connection, run: str, code: str) -> None:
        number = con.execute(
            "SELECT COALESCE(MAX(sequence_no),0)+1 FROM run_events WHERE run_id=?", (run,)
        ).fetchone()[0]
        con.execute(
            "INSERT INTO run_events VALUES (?,?,?, ?,NULL,?,?)",
            (str(uuid4()), run, number, code, code, stamp()),
        )

    def start(self, investigation: str, data: RunStart) -> dict[str, Any]:
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            if current.archived_at:
                raise WorkspaceError(409, "archived", "Unarchive this investigation first.")
            existing = con.execute("SELECT * FROM runs WHERE id=?", (str(data.id),)).fetchone()
            if existing:
                snapshot = json.loads(existing["config_snapshot_json"])
                if (
                    existing["investigation_id"] != investigation
                    or snapshot["urls"] != data.urls
                    or existing["plan_revision"] != data.expected_revision
                ):
                    raise WorkspaceError(
                        409, "conflict", "Run identifier already belongs to different work."
                    )
                return self.public_run(dict(existing))
            plan = Repository._plan(con, investigation)
            if plan.revision_no != data.expected_revision:
                raise WorkspaceError(409, "conflict", "Plan changed. Reload before collecting.")
            if con.execute("SELECT 1 FROM runs WHERE status IN ('queued','running')").fetchone():
                raise WorkspaceError(409, "run_active", "A collection is already active.")
            snapshot = json.dumps(
                {
                    "scope": "evidence_collection",
                    "urls": data.urls,
                    "plan": plan.model_dump(mode="json"),
                }
            )
            now = stamp()
            con.execute(
                "INSERT INTO "
                "runs(id,investigation_id,status,mode,plan_id,plan_revision,config_snapsh"
                "ot_json,question_snapshot,created_at) VALUES "
                "(?,?,'queued','mock',?,?,?,?,?)",
                (
                    str(data.id),
                    investigation,
                    str(plan.id) if plan.id else None,
                    plan.revision_no,
                    snapshot,
                    current.question,
                    now,
                ),
            )
            self.event(con, str(data.id), "queued")
        return self.run(str(data.id), investigation)

    @staticmethod
    def public_run(row: dict[str, Any]) -> dict[str, Any]:
        snapshot = json.loads(row.pop("config_snapshot_json"))
        row.pop("worker_claim_token", None)
        row["urls"] = snapshot["urls"]
        row["plan_snapshot"] = snapshot["plan"]
        row["scope"] = snapshot.get("scope", "evidence_collection")
        return row

    def run(self, run: str, investigation: str | None = None) -> dict[str, Any]:
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM runs WHERE id=?", (run,)).fetchone()
            if not row or (investigation is not None and row["investigation_id"] != investigation):
                raise WorkspaceError(404, "not_found", "Collection not found.")
            result = self.public_run(dict(row))
            result["sources"] = [
                dict(r) for r in con.execute("SELECT id,status FROM sources WHERE run_id=?", (run,))
            ]
            return result

    def list_rows(self, table: str, investigation: str, offset: int = 0) -> list[dict[str, Any]]:
        # Table names are internal constants, never request strings.
        if table not in {"runs", "sources"}:
            raise ValueError("Invalid table")
        with self.db.connection() as con:
            lookup(con, investigation)
            if table == "runs":
                rows = con.execute(
                    "SELECT * FROM runs WHERE investigation_id=? ORDER BY created_at "
                    "DESC,id LIMIT 25 OFFSET ?",
                    (investigation, offset),
                )
                return [self.public_run(dict(row)) for row in rows]
            rows = con.execute(
                "SELECT "
                "id,investigation_id,run_id,title,original_url,canonical_url,status,origi"
                "n,fetched_at,extracted_at,limitation,duplicate_of FROM sources WHERE "
                "investigation_id=? ORDER BY rowid DESC LIMIT 25 OFFSET ?",
                (investigation, offset),
            )
            return [dict(row) for row in rows]

    def source(self, identifier: str, investigation: str) -> dict[str, Any]:
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT * FROM sources WHERE id=? AND investigation_id=?",
                (identifier, investigation),
            ).fetchone()
            if not row:
                raise WorkspaceError(404, "not_found", "Source not found in this investigation.")
            return dict(row)

    def passages(self, source: str, investigation: str, offset: int = 0) -> list[dict[str, Any]]:
        self.source(source, investigation)
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in con.execute(
                    "SELECT * FROM passages WHERE source_id=? AND investigation_id=? "
                    "ORDER BY ordinal LIMIT 25 OFFSET ?",
                    (source, investigation, offset),
                )
            ]

    def passage(self, identifier: str, investigation: str) -> dict[str, Any]:
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT * FROM passages WHERE id=? AND investigation_id=?",
                (identifier, investigation),
            ).fetchone()
            if not row:
                raise WorkspaceError(404, "not_found", "Passage not found in this investigation.")
            return dict(row)

    def events(self, investigation: str, after: int, run: str) -> list[dict[str, Any]]:
        self.run(run, investigation)
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in con.execute(
                    "SELECT * FROM run_events WHERE run_id=? AND sequence_no>? ORDER BY "
                    "sequence_no LIMIT 100",
                    (run, after),
                )
            ]

    def cancel(self, run: str) -> None:
        self.run(run)
        with self.db.transaction() as con:
            con.execute(
                "UPDATE runs SET cancel_requested=1 WHERE id=? AND status IN ('queued','running')",
                (run,),
            )

    def recover(self) -> None:
        with self.db.transaction() as con:
            rows = con.execute(
                "SELECT id FROM runs WHERE status IN ('queued','running')"
            ).fetchall()
            for row in rows:
                con.execute(
                    "UPDATE runs SET "
                    "status='interrupted',finished_at=?,error_code='process_interrupted' "
                    "WHERE id=?",
                    (stamp(), row[0]),
                )
                self.event(con, row[0], "interrupted")

    def claim(self) -> dict[str, Any] | None:
        with self.db.transaction() as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM runs WHERE status='queued' LIMIT 1").fetchone()
            if not row:
                return None
            now = stamp()
            con.execute(
                "UPDATE runs SET "
                "status='running',started_at=?,last_heartbeat_at=?,worker_claim_token=? "
                "WHERE id=? AND status='queued'",
                (now, now, str(uuid4()), row["id"]),
            )
            self.event(con, row["id"], "running")
            return dict(row)

    def stopped(self, run: str) -> bool:
        with self.db.connection() as con:
            row = con.execute("SELECT cancel_requested FROM runs WHERE id=?", (run,)).fetchone()
            return not row or bool(row[0]) or not self.consent()

    def save_source(
        self,
        run: dict[str, Any],
        url: str,
        final: str,
        result: Extraction | None,
        failure: str | None,
        ordinal: int,
        origin: str = "mock",
    ) -> str | None:
        with self.db.transaction() as con:
            state = con.execute(
                "SELECT cancel_requested,status FROM runs WHERE id=?", (run["id"],)
            ).fetchone()
            if not state or state[0] or state[1] != "running" or not self.consent():
                return None
            existing = con.execute(
                "SELECT id FROM sources WHERE investigation_id=? AND "
                "text_sha256=? AND status IN ('fetched','partial') LIMIT 1",
                (run["investigation_id"], result.text_sha256 if result else None),
            ).fetchone()
            identifier, now = str(uuid4()), stamp()
            status = (
                "duplicate"
                if existing
                else result.status
                if result
                else (
                    "blocked"
                    if failure
                    in {"robots_blocked", "blocked_destination", "blocked", "consent_revoked"}
                    else "unsupported"
                    if failure == "unsupported"
                    else "failed"
                )
            )
            saved = result if not existing else None
            con.execute(
                "INSERT INTO "
                "sources(id,investigation_id,run_id,origin,original_url,canonical_url,tit"
                "le,status,extracted_text,text_sha256,extraction_version,normalization_ve"
                "rsion,fetched_at,extracted_at,limitation,duplicate_of,author,published_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    identifier,
                    run["investigation_id"],
                    run["id"],
                    origin,
                    url,
                    final,
                    result.title if result else None,
                    status,
                    saved.text if saved else None,
                    saved.text_sha256 if saved else None,
                    saved.extraction_version if saved else None,
                    saved.normalization_version if saved else None,
                    now if result else None,
                    now if saved else None,
                    result.limitation if result else failure,
                    existing[0] if existing else None,
                    result.author if result else None,
                    result.published_at if result else None,
                ),
            )
            if saved:
                count = con.execute(
                    "SELECT COUNT(*) FROM passages WHERE investigation_id=?",
                    (run["investigation_id"],),
                ).fetchone()[0]
                for number, (start, end, text) in enumerate(slices(saved.text), 1):
                    con.execute(
                        "INSERT INTO "
                        "passages(id,investigation_id,source_id,display_id,ordinal,text,s"
                        "tart_offset,end_offset,extraction_version,text_sha256,extracted_"
                        "at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            str(uuid4()),
                            run["investigation_id"],
                            identifier,
                            f"P-{count + number:04d}",
                            number,
                            text,
                            start,
                            end,
                            saved.extraction_version,
                            saved.text_sha256,
                            now,
                        ),
                    )
            con.execute(
                "INSERT INTO "
                "run_stages(id,run_id,stage_key,stage_revision,status,started_at,complete"
                "d_at,output_ref_json,error_code) VALUES (?,?,'extract',?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    run["id"],
                    ordinal,
                    "completed" if result else "failed",
                    now,
                    now,
                    json.dumps({"source_id": identifier}),
                    failure,
                ),
            )
            current = lookup(con, run["investigation_id"])
            con.execute(
                "UPDATE investigations SET updated_at=? WHERE id=?",
                (stamp(current.updated_at), run["investigation_id"]),
            )
            con.execute("UPDATE runs SET last_heartbeat_at=? WHERE id=?", (now, run["id"]))
            self.event(con, run["id"], "source_saved" if result else "source_failed")
            return identifier

    def finish(self, run: str, status: str, error: str | None = None) -> None:
        with self.db.transaction() as con:
            # Terminal states are final; a late call must not rewrite history.
            changed = con.execute(
                "UPDATE runs SET status=?,finished_at=?,error_code=? "
                "WHERE id=? AND status IN ('queued','running')",
                (status, stamp(), error, run),
            ).rowcount
            if changed:
                self.event(con, run, status)
