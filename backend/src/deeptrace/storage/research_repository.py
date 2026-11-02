"""Pipeline persistence, provider bookkeeping, archive and verified deletion.

Every write is a short transaction; provider and network work always happens outside.
"""

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from deeptrace.evidence import kernel
from deeptrace.research.contracts import Budgets, PlanOutput
from deeptrace.storage.collection_repository import CollectionRepository
from deeptrace.storage.database import Database
from deeptrace.storage.repository import Repository, WorkspaceError, lookup, stamp


@dataclass(frozen=True)
class ValidCitation:
    passage_id: str
    display_id: str
    source_id: str
    quote: str | None
    passage_sha256: str


@dataclass(frozen=True)
class ValidatedClaim:
    text: str
    citations: list[ValidCitation] = field(default_factory=list)
    suppressed: int = 0

    @property
    def state(self) -> str:
        return "cited" if self.citations else "not_established"

    @property
    def explanation(self) -> str | None:
        if not self.suppressed:
            return None
        return f"{self.suppressed} citation(s) failed validation and were suppressed."


class ResearchRepository:
    def __init__(self, database: Database):
        self.db = database

    # Consent ---------------------------------------------------------------------

    def consented(self, provider: str, version: str) -> bool:
        with self.db.connection() as con:
            row = con.execute(
                "SELECT 1 FROM provider_consents WHERE provider_id=? AND disclosure_version=? "
                "AND revoked_at IS NULL LIMIT 1",
                (provider, version),
            ).fetchone()
            return row is not None

    def set_consent(self, provider: str, version: str, accepted: bool) -> None:
        with self.db.transaction() as con:
            now = stamp()
            con.execute(
                "UPDATE provider_consents SET revoked_at=? WHERE provider_id=? AND "
                "disclosure_version=? AND revoked_at IS NULL",
                (now, provider, version),
            )
            if accepted:
                con.execute(
                    "INSERT INTO provider_consents VALUES (?,?,'research',?,?,NULL)",
                    (str(uuid4()), provider, version, now),
                )
            else:
                # Revocation blocks new calls and stops active work; it cannot recall old ones.
                con.execute(
                    "UPDATE runs SET cancel_requested=1 WHERE status IN ('queued','running')"
                )

    # Run admission ---------------------------------------------------------------

    def start(
        self,
        investigation: str,
        identifier: str,
        scope: str,
        mode: str,
        budgets: Budgets,
        expected_revision: int,
        replace: bool = False,
    ) -> None:
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            existing = con.execute(
                "SELECT investigation_id,config_snapshot_json FROM runs WHERE id=?", (identifier,)
            ).fetchone()
            if existing:
                if (
                    existing["investigation_id"] != investigation
                    or json.loads(existing["config_snapshot_json"]).get("scope") != scope
                ):
                    raise WorkspaceError(409, "conflict", "Run identifier belongs to other work.")
                return
            if current.archived_at:
                raise WorkspaceError(409, "archived", "Unarchive this investigation first.")
            plan = Repository._plan(con, investigation)
            if plan.revision_no != expected_revision:
                raise WorkspaceError(409, "conflict", "The plan changed. Reload before starting.")
            if scope == "research_pipeline" and not plan.items:
                raise WorkspaceError(409, "no_plan", "Add or generate at least one plan step.")
            if scope == "plan_generation" and plan.items and not replace:
                raise WorkspaceError(409, "plan_exists", "Confirm replacing your existing plan.")
            if con.execute("SELECT 1 FROM runs WHERE status IN ('queued','running')").fetchone():
                raise WorkspaceError(409, "run_active", "Another run is already active.")
            snapshot = {
                "scope": scope,
                "urls": [],
                "plan": plan.model_dump(mode="json"),
                "budgets": budgets.model_dump(),
            }
            con.execute(
                "INSERT INTO runs(id,investigation_id,status,mode,plan_id,plan_revision,"
                "config_snapshot_json,question_snapshot,created_at) VALUES "
                "(?,?,'queued',?,?,?,?,?,?)",
                (
                    identifier,
                    investigation,
                    mode,
                    str(plan.id) if plan.id else None,
                    plan.revision_no,
                    json.dumps(snapshot),
                    current.question,
                    stamp(),
                ),
            )
            CollectionRepository.event(con, identifier, "queued")

    # Bookkeeping -----------------------------------------------------------------

    def usage_begin(self, run: str, provider: str, operation: str, attempt: int) -> str:
        identifier = str(uuid4())
        with self.db.transaction() as con:
            con.execute(
                "INSERT INTO provider_usage(id,run_id,provider_id,operation,attempt_no,"
                "requested_at,status,is_estimate) VALUES (?,?,?,?,?,?,'requested',1)",
                (identifier, run, provider, operation, attempt, stamp()),
            )
        return identifier

    def usage_end(self, identifier: str, status: str) -> None:
        with self.db.transaction() as con:
            con.execute(
                "UPDATE provider_usage SET status=?,finished_at=? WHERE id=?",
                (status, stamp(), identifier),
            )

    def record_tokens(
        self, run: str, provider: str, estimated: int, reported: dict[str, int | None]
    ) -> None:
        """Estimates and provider-reported counts stay distinguishable; neither is billing."""
        with self.db.transaction() as con:
            row = con.execute(
                "SELECT id FROM provider_usage WHERE run_id=? AND provider_id=? "
                "ORDER BY requested_at DESC,rowid DESC LIMIT 1",
                (run, provider),
            ).fetchone()
            if row:
                known = any(value is not None for value in reported.values())
                con.execute(
                    "UPDATE provider_usage SET estimated_units_json=?,reported_units_json=?,"
                    "is_estimate=? WHERE id=?",
                    (
                        json.dumps({"tokens": estimated}),
                        json.dumps(reported) if known else None,
                        0 if known else 1,
                        row[0],
                    ),
                )

    def add_query(
        self, run: str, investigation: str, text: str, provider: str, status: str, results: int
    ) -> None:
        with self.db.transaction() as con:
            con.execute(
                "INSERT INTO search_queries(id,run_id,investigation_id,query_text,provider_id,"
                "status,searched_at,results_count) VALUES (?,?,?,?,?,?,?,?)",
                (str(uuid4()), run, investigation, text, provider, status, stamp(), results),
            )

    def stage(
        self,
        run: str,
        key: str,
        status: str,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self.db.transaction() as con:
            self._stage(con, run, key, status, output, error)

    @staticmethod
    def _stage(
        con: sqlite3.Connection,
        run: str,
        key: str,
        status: str,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        revision = con.execute(
            "SELECT COALESCE(MAX(stage_revision),0)+1 FROM run_stages WHERE run_id=? AND "
            "stage_key=?",
            (run, key),
        ).fetchone()[0]
        now = stamp()
        con.execute(
            "INSERT INTO run_stages VALUES (?,?,?,?,?,?,?,?,?)",
            (
                str(uuid4()),
                run,
                key,
                revision,
                status,
                now,
                now,
                json.dumps(output) if output is not None else None,
                error,
            ),
        )
        con.execute("UPDATE runs SET last_heartbeat_at=? WHERE id=?", (now, run))
        CollectionRepository.event(con, run, f"{key}_{status}")

    def sensitive(self, investigation: str) -> bool:
        with self.db.connection() as con:
            return lookup(con, investigation).sensitive

    # Plan application ------------------------------------------------------------

    def apply_plan(
        self,
        run: dict[str, Any],
        output: PlanOutput,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> None:
        """Replace the plan and checkpoint the stage atomically."""
        investigation = run["investigation_id"]
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            plan = Repository._plan(con, investigation)
            if plan.revision_no != run["plan_revision"]:
                raise WorkspaceError(409, "conflict", "The plan changed during generation.")
            plan_id = str(plan.id or uuid4())
            if plan.id is None:
                con.execute(
                    "INSERT INTO plans(id,investigation_id,revision_no,prompt_version,provider_id,"
                    "model_id,created_at) VALUES (?,?,1,?,?,?,?)",
                    (plan_id, investigation, prompt_version, provider, model, stamp()),
                )
            else:
                con.execute(
                    "UPDATE plans SET revision_no=revision_no+1,prompt_version=?,provider_id=?,"
                    "model_id=? WHERE id=?",
                    (prompt_version, provider, model, plan_id),
                )
            con.execute("DELETE FROM plan_items WHERE plan_id=?", (plan_id,))
            con.executemany(
                "INSERT INTO plan_items(id,plan_id,ordinal,sub_question,search_query) "
                "VALUES (?,?,?,?,?)",
                [
                    (str(uuid4()), plan_id, order, step.sub_question, step.search_query)
                    for order, step in enumerate(output.steps, 1)
                ],
            )
            con.execute(
                "UPDATE investigations SET updated_at=? WHERE id=?",
                (stamp(current.updated_at), investigation),
            )
            self._stage(
                con,
                run["id"],
                "plan",
                "completed",
                {"steps": len(output.steps), "narrow_reason": output.narrow_reason},
            )

    # Evidence selection and generated answers -------------------------------------

    def allowed_passages(self, run: str, investigation: str) -> list[dict[str, Any]]:
        """This run's evidence allowlist: its sources plus originals of its duplicates."""
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT p.id,p.display_id,p.source_id,p.text,s.title AS source_title "
                "FROM passages p JOIN sources s ON s.id=p.source_id AND "
                "s.investigation_id=p.investigation_id WHERE p.investigation_id=? "
                "AND p.removed_at IS NULL AND p.source_id IN (SELECT id FROM sources WHERE "
                "run_id=? UNION SELECT duplicate_of FROM sources WHERE run_id=? AND "
                "duplicate_of IS NOT NULL) ORDER BY p.display_id",
                (investigation, run, run),
            ).fetchall()
            return [dict(row) for row in rows]

    def run_sources(self, run: str, investigation: str) -> list[dict[str, Any]]:
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT id,title,author,published_at,original_url,canonical_url,status,origin,"
                "fetched_at,extracted_at,extraction_version,text_sha256,limitation,duplicate_of "
                "FROM sources WHERE run_id=? AND investigation_id=? ORDER BY rowid",
                (run, investigation),
            ).fetchall()
            return [dict(row) for row in rows]

    def queries(self, run: str) -> list[dict[str, Any]]:
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT query_text,provider_id,status,searched_at,results_count "
                "FROM search_queries WHERE run_id=? ORDER BY searched_at,rowid",
                (run,),
            ).fetchall()
            return [dict(row) for row in rows]

    def save_outcome(
        self,
        run: dict[str, Any],
        summary: str,
        limitations: str | None,
        needed: str | None,
        claims: list[ValidatedClaim],
        provider: str,
        model: str,
        prompt_version: str,
        render: Callable[[int, str], tuple[str, str, dict[str, int]]],
        partial: bool = False,
    ) -> int:
        """Answer, claims, citations, report and checkpoints commit together or not at all."""
        investigation = run["investigation_id"]
        suppressed = sum(claim.suppressed for claim in claims)
        answer_id, now = str(uuid4()), stamp()
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            con.execute(
                "INSERT INTO generated_answers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    answer_id,
                    investigation,
                    run["id"],
                    prompt_version,
                    provider,
                    model,
                    now,
                    "partial" if suppressed or partial else "validated",
                    run["mode"],
                    summary,
                    limitations,
                    needed,
                    suppressed,
                ),
            )
            for ordinal, claim in enumerate(claims, 1):
                claim_id = str(uuid4())
                con.execute(
                    "INSERT INTO generated_claims VALUES (?,?,?,?,?,?,?)",
                    (
                        claim_id,
                        answer_id,
                        investigation,
                        ordinal,
                        claim.text,
                        claim.state,
                        claim.explanation,
                    ),
                )
                for number, cite in enumerate(claim.citations, 1):
                    con.execute(
                        "INSERT INTO generated_citations VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            str(uuid4()),
                            claim_id,
                            investigation,
                            cite.passage_id,
                            number,
                            cite.quote,
                            cite.passage_sha256,
                            kernel.VALIDATION_VERSION,
                            now,
                        ),
                    )
            self._stage(con, run["id"], "validate", "completed",
                        {"claims": len(claims), "suppressed": suppressed})  # fmt: skip
            version = con.execute(
                "SELECT COALESCE(MAX(version_no),0)+1 FROM generated_reports WHERE "
                "investigation_id=?",
                (investigation,),
            ).fetchone()[0]
            markdown, schema, counts = render(version, now)
            con.execute(
                "INSERT INTO generated_reports VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    investigation,
                    answer_id,
                    run["id"],
                    version,
                    markdown,
                    kernel.sha256(markdown),
                    now,
                    prompt_version,
                    run["mode"],
                    json.dumps(counts, sort_keys=True),
                    schema,
                ),
            )
            self._stage(con, run["id"], "report", "completed", {"version_no": version})
            con.execute(
                "UPDATE investigations SET updated_at=? WHERE id=?",
                (stamp(current.updated_at), investigation),
            )
            return int(version)

    # Reads -----------------------------------------------------------------------

    def progress(self, run: str, investigation: str) -> dict[str, Any]:
        with self.db.connection() as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT status,error_code,cancel_requested,config_snapshot_json,mode FROM runs "
                "WHERE id=? AND investigation_id=?",
                (run, investigation),
            ).fetchone()
            if row is None:
                raise WorkspaceError(404, "not_found", "Run not found in this investigation.")
            stages = con.execute(
                "SELECT stage_key,stage_revision,status,completed_at,output_ref_json,error_code "
                "FROM run_stages WHERE run_id=? ORDER BY rowid",
                (run,),
            ).fetchall()
            usage = con.execute(
                "SELECT provider_id,operation,status,estimated_units_json,reported_units_json "
                "FROM provider_usage WHERE run_id=?",
                (run,),
            ).fetchall()
            pages = con.execute(
                "SELECT COUNT(*) FROM sources WHERE run_id=? AND fetched_at IS NOT NULL", (run,)
            ).fetchone()[0]
            attempted = con.execute(
                "SELECT COUNT(*) FROM sources WHERE run_id=?", (run,)
            ).fetchone()[0]
            queries = con.execute(
                "SELECT query_text,status,searched_at,results_count FROM search_queries "
                "WHERE run_id=? ORDER BY searched_at,rowid LIMIT 40",
                (run,),
            ).fetchall()
            snapshot = json.loads(row["config_snapshot_json"])
            tokens = sum(
                json.loads(u["estimated_units_json"]).get("tokens", 0)
                for u in usage
                if u["estimated_units_json"]
            )
            narrow = next(
                (
                    json.loads(s["output_ref_json"]).get("narrow_reason")
                    for s in stages
                    if s["stage_key"] == "plan" and s["output_ref_json"]
                ),
                None,
            )
            return {
                "status": row["status"],
                "error_code": row["error_code"],
                "cancel_requested": bool(row["cancel_requested"]),
                "mode": row["mode"],
                "scope": snapshot.get("scope", "evidence_collection"),
                "budgets": snapshot.get("budgets"),
                "narrow_reason": narrow,
                "queries": [dict(query) for query in queries],
                "stages": [
                    {
                        "stage_key": s["stage_key"],
                        "stage_revision": s["stage_revision"],
                        "status": s["status"],
                        "completed_at": s["completed_at"],
                        "error_code": s["error_code"],
                    }
                    for s in stages
                ],
                "usage": {
                    "search_attempts": sum(u["operation"] == "search" for u in usage),
                    "model_attempts": sum(u["operation"] in {"plan", "synthesize"} for u in usage),
                    "pages_retrieved": pages,
                    "pages_attempted": attempted,
                    "estimated_tokens": tokens,
                },
            }

    def latest_answer(self, investigation: str) -> dict[str, Any] | None:
        with self.db.connection() as con:
            lookup(con, investigation)
            answer = con.execute(
                "SELECT a.* FROM generated_answers a WHERE a.investigation_id=? "
                "ORDER BY a.generated_at DESC,a.rowid DESC LIMIT 1",
                (investigation,),
            ).fetchone()
            if answer is None:
                return None
            claims = []
            for claim in con.execute(
                "SELECT * FROM generated_claims WHERE answer_id=? ORDER BY ordinal", (answer["id"],)
            ).fetchall():
                citations = []
                for cite in con.execute(
                    "SELECT c.quoted_text,c.passage_sha256,p.id,p.display_id,p.text,p.removed_at,"
                    "p.start_offset,p.end_offset,p.source_id,s.title,s.original_url,s.fetched_at,"
                    "s.status AS source_status "
                    "FROM generated_citations c JOIN passages p ON p.id=c.passage_id AND "
                    "p.investigation_id=c.investigation_id JOIN sources s ON s.id=p.source_id AND "
                    "s.investigation_id=p.investigation_id WHERE c.claim_id=? ORDER BY c.ordinal",
                    (claim["id"],),
                ).fetchall():
                    # Re-checked on every read so a stored label cannot outlive its evidence.
                    check = kernel.check_citation(
                        investigation,
                        kernel.PassageRecord(
                            cite["id"], investigation, cite["text"], cite["removed_at"] is not None
                        ),
                        cite["quoted_text"],
                        cite["passage_sha256"],
                    )
                    citations.append(
                        {
                            "passage_id": cite["id"],
                            "display_id": cite["display_id"],
                            "source_id": cite["source_id"],
                            "source_title": cite["title"],
                            "source_status": cite["source_status"],
                            "original_url": cite["original_url"],
                            "fetched_at": cite["fetched_at"],
                            "quoted_text": cite["quoted_text"],
                            "start_offset": cite["start_offset"],
                            "end_offset": cite["end_offset"],
                            "passage_text": cite["text"],
                            "reference_valid": check.reference_valid,
                            "quote_valid": check.quote_valid,
                            "invalid_reason": check.reason,
                        }
                    )
                valid = [
                    c for c in citations if c["reference_valid"] and c["quote_valid"] is not False
                ]
                claims.append(
                    {
                        "ordinal": claim["ordinal"],
                        "claim_text": claim["claim_text"],
                        "evidence_state": "cited" if valid else "not_established",
                        "explanation": claim["explanation"],
                        "citations": citations,
                    }
                )
            return {
                "run_id": answer["run_id"],
                "provider_id": answer["provider_id"],
                "model_id": answer["model_id"],
                "prompt_version": answer["prompt_version"],
                "generated_at": answer["generated_at"],
                "mode": answer["mode"],
                "status": answer["status"],
                "summary_text": answer["summary_text"],
                "limitations_text": answer["limitations_text"],
                "needed_evidence_text": answer["needed_evidence_text"],
                "suppressed_citations": answer["suppressed_citations"],
                "claims": claims,
            }

    @staticmethod
    def _report_summary(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "version_no": row["version_no"],
            "run_id": row["run_id"],
            "created_at": row["created_at"],
            "markdown_sha256": row["markdown_sha256"],
            "mode": row["mode"],
            "prompt_version": row["prompt_version"],
            "report_schema_version": row["report_schema_version"],
            "validation_summary": json.loads(row["validation_summary_json"]),
        }

    def reports(self, investigation: str) -> list[dict[str, Any]]:
        with self.db.connection() as con:
            lookup(con, investigation)
            rows = con.execute(
                "SELECT * FROM generated_reports WHERE investigation_id=? "
                "ORDER BY version_no DESC LIMIT 100",
                (investigation,),
            ).fetchall()
            return [self._report_summary(row) for row in rows]

    def report(self, investigation: str, version: int) -> dict[str, Any]:
        with self.db.connection() as con:
            lookup(con, investigation)
            row = con.execute(
                "SELECT * FROM generated_reports WHERE investigation_id=? AND version_no=?",
                (investigation, version),
            ).fetchone()
            if row is None:
                raise WorkspaceError(404, "not_found", "Report version not found.")
            if kernel.sha256(row["markdown_text"]) != row["markdown_sha256"]:
                raise WorkspaceError(500, "report_integrity", "Saved report failed its checksum.")
            newest = con.execute(
                "SELECT MAX(version_no) FROM generated_reports WHERE investigation_id=?",
                (investigation,),
            ).fetchone()[0]
            warnings = ["You are viewing an older version."] if newest != version else []
            return {
                **self._report_summary(row),
                "markdown_text": row["markdown_text"],
                "current_warnings": warnings,
            }

    # Investigation lifecycle -----------------------------------------------------

    def storage_bytes(self, investigation: str) -> int:
        """Text this investigation keeps in SQLite (UTF-8 bytes), excluding index overhead."""
        with self.db.connection() as con:
            lookup(con, investigation)
            total = 0
            for table, column in (
                ("sources", "extracted_text"),
                ("passages", "text"),
                ("generated_reports", "markdown_text"),
                ("report_versions", "markdown_text"),
            ):
                # Table and column names are internal constants, never request strings.
                total += con.execute(
                    f"SELECT COALESCE(SUM(length(CAST({column} AS BLOB))),0) "  # noqa: S608
                    f"FROM {table} WHERE investigation_id=?",
                    (investigation,),
                ).fetchone()[0]
            return int(total)

    def set_sensitive(self, investigation: str, sensitive: bool) -> None:
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            con.execute(
                "UPDATE investigations SET sensitive=?,updated_at=? WHERE id=?",
                (int(sensitive), stamp(current.updated_at), investigation),
            )

    def set_archived(self, investigation: str, archived: bool) -> None:
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            if con.execute(
                "SELECT 1 FROM runs WHERE investigation_id=? AND status IN ('queued','running')",
                (investigation,),
            ).fetchone():
                raise WorkspaceError(409, "run_active", "Wait for the active run to finish.")
            if archived:
                con.execute(
                    "INSERT OR IGNORE INTO investigation_archives VALUES (?,?)",
                    (investigation, stamp()),
                )
            else:
                con.execute(
                    "DELETE FROM investigation_archives WHERE investigation_id=?", (investigation,)
                )
            con.execute(
                "UPDATE investigations SET updated_at=? WHERE id=?",
                (stamp(current.updated_at), investigation),
            )

    def delete_investigation(self, investigation: str, confirm_title: str) -> dict[str, int]:
        """All rows go in one transaction; the commit only happens after verification."""
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            if confirm_title != current.title:
                raise WorkspaceError(422, "confirmation_mismatch", "Type the exact title.")
            if con.execute(
                "SELECT 1 FROM runs WHERE investigation_id=? AND status IN ('queued','running')",
                (investigation,),
            ).fetchone():
                raise WorkspaceError(409, "run_active", "Cancel the active run before deleting.")
            removed: dict[str, int] = {}
            runs = "(SELECT id FROM runs WHERE investigation_id=?)"
            plans = "(SELECT id FROM plans WHERE investigation_id=?)"
            for table, where in (
                ("generated_reports", "investigation_id=?"),
                ("generated_citations", "investigation_id=?"),
                ("generated_claims", "investigation_id=?"),
                ("generated_answers", "investigation_id=?"),
                ("report_versions", "investigation_id=?"),
                ("citations", "investigation_id=?"),
                ("claims", "investigation_id=?"),
                ("answers", "investigation_id=?"),
                ("evidence_notes", "investigation_id=?"),
                ("saved_urls", "investigation_id=?"),
                ("passages", "investigation_id=?"),
                ("sources", "investigation_id=?"),
                ("search_queries", "investigation_id=?"),
                ("provider_usage", f"run_id IN {runs}"),
                ("run_events", f"run_id IN {runs}"),
                ("run_stages", f"run_id IN {runs}"),
                ("runs", "investigation_id=?"),
                ("plan_items", f"plan_id IN {plans}"),
                ("plans", "investigation_id=?"),
                ("investigation_archives", "investigation_id=?"),
                ("investigations", "id=?"),
            ):
                # Table names and predicates are internal constants, never request strings.
                removed[table] = con.execute(
                    f"DELETE FROM {table} WHERE {where}",  # noqa: S608
                    (investigation,),
                ).rowcount
            for table in ("sources", "passages", "runs", "plans", "generated_reports"):
                if con.execute(
                    f"SELECT 1 FROM {table} WHERE investigation_id=? LIMIT 1",  # noqa: S608
                    (investigation,),
                ).fetchone():
                    raise WorkspaceError(500, "delete_incomplete", "Deletion could not complete.")
            return removed
