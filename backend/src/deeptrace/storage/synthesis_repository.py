"""Saved URLs, evidence review, user-authored drafts and immutable report versions.

Every query is scoped by investigation. Citations are validated before they are
stored and revalidated when a report version is created.
"""

import json
import sqlite3
from typing import Any
from uuid import uuid4

from deeptrace.collection.policy import normalize_url
from deeptrace.evidence import kernel, report
from deeptrace.evidence.models import (
    MAX_SAVED_URLS,
    AnswerSave,
    NoteSave,
    ReportCreate,
    SavedUrlCreate,
)
from deeptrace.storage.database import Database
from deeptrace.storage.repository import Repository, WorkspaceError, lookup, stamp

ANSWER_FIELDS = (
    "scope_text",
    "methodology_text",
    "summary_text",
    "limitations_text",
    "next_steps_text",
)
PASSAGE_JOIN = (
    "SELECT p.id,p.display_id,p.source_id,p.ordinal,p.start_offset,p.end_offset,p.text,"
    "p.extraction_version,p.removed_at,s.title AS source_title,s.status AS source_status,"
    "s.origin AS source_origin,s.original_url FROM passages p JOIN sources s "
    "ON s.id=p.source_id AND s.investigation_id=p.investigation_id "
)


class SynthesisRepository:
    def __init__(self, database: Database):
        self.db = database

    # Saved URLs ------------------------------------------------------------------

    def save_url(self, investigation: str, data: SavedUrlCreate) -> dict[str, Any]:
        canonical = normalize_url(data.url)
        with self.db.transaction() as con:
            lookup(con, investigation)
            same = con.execute("SELECT * FROM saved_urls WHERE id=?", (str(data.id),)).fetchone()
            if same:
                if (same["investigation_id"], same["canonical_url"], same["note"]) != (
                    investigation,
                    canonical,
                    data.note,
                ):
                    raise WorkspaceError(
                        409, "conflict", "Identifier already belongs to saved work."
                    )
                return dict(same)
            if con.execute(
                "SELECT 1 FROM saved_urls WHERE investigation_id=? AND canonical_url=?",
                (investigation, canonical),
            ).fetchone():
                raise WorkspaceError(409, "duplicate", "This URL is already saved here.")
            count = con.execute(
                "SELECT COUNT(*) FROM saved_urls WHERE investigation_id=?", (investigation,)
            ).fetchone()[0]
            if count >= MAX_SAVED_URLS:
                raise WorkspaceError(409, "limit_reached", "This investigation has 200 saved URLs.")
            con.execute(
                "INSERT INTO saved_urls VALUES (?,?,?,?,?,?)",
                (str(data.id), investigation, data.url, canonical, data.note, stamp()),
            )
            return dict(
                con.execute("SELECT * FROM saved_urls WHERE id=?", (str(data.id),)).fetchone()
            )

    def saved_urls(self, investigation: str, offset: int) -> list[dict[str, Any]]:
        with self.db.connection() as con:
            lookup(con, investigation)
            rows = con.execute(
                "SELECT * FROM saved_urls WHERE investigation_id=? "
                "ORDER BY created_at DESC,id LIMIT 50 OFFSET ?",
                (investigation, offset),
            )
            return [dict(row) for row in rows]

    # Passages and evidence notes -----------------------------------------------------

    def investigation_passages(self, investigation: str, offset: int) -> list[dict[str, Any]]:
        with self.db.connection() as con:
            lookup(con, investigation)
            rows = con.execute(
                PASSAGE_JOIN + "WHERE p.investigation_id=? AND p.removed_at IS NULL "
                "ORDER BY s.rowid,p.ordinal LIMIT 50 OFFSET ?",
                (investigation, offset),
            )
            # Strict response models forbid internal columns; only active passages are listed.
            return [{k: row[k] for k in row.keys() if k != "removed_at"} for row in rows]

    @staticmethod
    def _passage(con: sqlite3.Connection, investigation: str, passage: str) -> sqlite3.Row | None:
        row: sqlite3.Row | None = con.execute(
            PASSAGE_JOIN + "WHERE p.id=? AND p.investigation_id=?", (passage, investigation)
        ).fetchone()
        return row

    @staticmethod
    def _targets(con: sqlite3.Connection, investigation: str) -> dict[str, str]:
        current = lookup(con, investigation)
        targets = {"question": current.question}
        for item in Repository._plan(con, investigation).items:
            targets[str(item.id)] = item.sub_question
        return targets

    def notes(self, investigation: str) -> list[dict[str, Any]]:
        with self.db.connection() as con:
            targets = self._targets(con, investigation)
            rows = con.execute(
                "SELECT n.*,p.display_id,p.source_id,s.title AS source_title FROM evidence_notes n "
                "JOIN passages p ON p.id=n.passage_id AND p.investigation_id=n.investigation_id "
                "JOIN sources s ON s.id=p.source_id AND s.investigation_id=p.investigation_id "
                "WHERE n.investigation_id=? ORDER BY p.display_id,n.created_at LIMIT 500",
                (investigation,),
            ).fetchall()
            return [self._note_view(dict(row), targets) for row in rows]

    @staticmethod
    def _note_view(row: dict[str, Any], targets: dict[str, str]) -> dict[str, Any]:
        row.pop("investigation_id")
        # A removed plan step keeps its snapshot label and is flagged, never retargeted.
        row["target_current"] = row["target_key"] in targets
        return row

    def save_note(self, investigation: str, data: NoteSave) -> dict[str, Any]:
        with self.db.transaction() as con:
            targets = self._targets(con, investigation)
            if data.target_key not in targets:
                raise WorkspaceError(422, "unknown_target", "Choose the question or a saved step.")
            if self._passage(con, investigation, str(data.passage_id)) is None:
                raise WorkspaceError(404, "not_found", "Passage not found in this investigation.")
            now = stamp()
            existing = con.execute(
                "SELECT * FROM evidence_notes WHERE id=?", (str(data.id),)
            ).fetchone()
            if data.expected_revision == 0:
                if (
                    existing
                    or con.execute(
                        "SELECT 1 FROM evidence_notes WHERE investigation_id=? AND passage_id=? "
                        "AND target_key=?",
                        (investigation, str(data.passage_id), data.target_key),
                    ).fetchone()
                ):
                    raise WorkspaceError(
                        409, "conflict", "A review for this passage and target already exists."
                    )
                con.execute(
                    "INSERT INTO evidence_notes VALUES (?,?,?,?,?,?,?,1,?,?)",
                    (
                        str(data.id),
                        investigation,
                        str(data.passage_id),
                        data.target_key,
                        targets[data.target_key],
                        data.stance,
                        data.note,
                        now,
                        now,
                    ),
                )
            else:
                if (
                    not existing
                    or existing["investigation_id"] != investigation
                    or existing["passage_id"] != str(data.passage_id)
                    or existing["target_key"] != data.target_key
                ):
                    raise WorkspaceError(404, "not_found", "Evidence review not found.")
                if existing["revision_no"] != data.expected_revision:
                    raise WorkspaceError(409, "conflict", "Newer review changes exist. Reload.")
                con.execute(
                    "UPDATE evidence_notes SET stance=?,note=?,revision_no=revision_no+1,"
                    "updated_at=? WHERE id=?",
                    (data.stance, data.note, stamp(existing["updated_at"]), str(data.id)),
                )
            row = con.execute(
                "SELECT n.*,p.display_id,p.source_id,s.title AS source_title FROM evidence_notes n "
                "JOIN passages p ON p.id=n.passage_id AND p.investigation_id=n.investigation_id "
                "JOIN sources s ON s.id=p.source_id AND s.investigation_id=p.investigation_id "
                "WHERE n.id=?",
                (str(data.id),),
            ).fetchone()
            return self._note_view(dict(row), targets)

    # Draft answers, claims and citations ------------------------------------------------

    def answer(self, investigation: str) -> dict[str, Any]:
        with self.db.connection() as con:
            con.execute("BEGIN")
            lookup(con, investigation)
            return self._answer(con, investigation)

    def _answer(self, con: sqlite3.Connection, investigation: str) -> dict[str, Any]:
        row = con.execute(
            "SELECT * FROM answers WHERE investigation_id=?", (investigation,)
        ).fetchone()
        if row is None:
            empty: dict[str, Any] = dict.fromkeys(ANSWER_FIELDS)
            return {"id": None, "revision_no": 0, "mode": "mock", "updated_at": None,
                    "claims": [], **empty}  # fmt: skip
        claims = []
        for claim in con.execute(
            "SELECT * FROM claims WHERE answer_id=? ORDER BY ordinal", (row["id"],)
        ).fetchall():
            citations = []
            for cite in con.execute(
                "SELECT * FROM citations WHERE claim_id=? ORDER BY ordinal", (claim["id"],)
            ).fetchall():
                passage = self._passage(con, investigation, cite["passage_id"])
                assert passage is not None  # Enforced by the composite foreign key.
                check = self._check(investigation, passage, cite["quoted_text"], cite)
                citations.append(
                    {
                        "id": cite["id"],
                        "passage_id": cite["passage_id"],
                        "display_id": passage["display_id"],
                        "source_id": passage["source_id"],
                        "source_title": passage["source_title"],
                        "relation": cite["relation"],
                        "quoted_text": cite["quoted_text"],
                        "reference_valid": check.reference_valid,
                        "quote_valid": check.quote_valid,
                        "invalid_reason": check.reason,
                        "start_offset": passage["start_offset"],
                        "end_offset": passage["end_offset"],
                        "passage_text": passage["text"],
                    }
                )
            claims.append(
                {
                    "id": claim["id"],
                    "ordinal": claim["ordinal"],
                    "claim_type": claim["claim_type"],
                    "claim_text": claim["claim_text"],
                    # Recomputed on read so a stored label can never outlive its evidence.
                    "evidence_state": self._state(citations),
                    "citations": citations,
                }
            )
        return {
            "id": row["id"],
            "revision_no": row["revision_no"],
            "mode": row["mode"],
            "updated_at": row["updated_at"],
            "claims": claims,
            **{field: row[field] for field in ANSWER_FIELDS},
        }

    @staticmethod
    def _check(
        investigation: str,
        passage: sqlite3.Row | None,
        quote: str | None,
        stored: sqlite3.Row | None = None,
    ) -> kernel.CitationCheck:
        record = (
            None
            if passage is None
            else kernel.PassageRecord(
                passage["id"], investigation, passage["text"], passage["removed_at"] is not None
            )
        )
        return kernel.check_citation(
            investigation, record, quote, stored["passage_sha256"] if stored else None
        )

    @staticmethod
    def _state(citations: list[dict[str, Any]]) -> str:
        supported = any(
            c["relation"] == "supports" and c["reference_valid"] and c["quote_valid"] is not False
            for c in citations
        )
        return "cited" if supported else "not_established"

    def save_answer(self, investigation: str, data: AnswerSave) -> dict[str, Any]:
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            row = con.execute(
                "SELECT id,revision_no FROM answers WHERE investigation_id=?", (investigation,)
            ).fetchone()
            if (row["revision_no"] if row else 0) != data.expected_revision:
                raise WorkspaceError(409, "conflict", "Newer draft changes exist. Reload first.")
            # Validate every citation before any write; report positions, never content.
            problems, checked = [], []
            for c_number, claim in enumerate(data.claims, 1):
                for r_number, cite in enumerate(claim.citations, 1):
                    passage = self._passage(con, investigation, str(cite.passage_id))
                    check = self._check(investigation, passage, cite.quoted_text)
                    if not check.reference_valid or check.quote_valid is False:
                        problems.append(f"claim {c_number} citation {r_number}: {check.reason}")
                    # Valid references imply the passage exists (see kernel.check_citation).
                    digest = kernel.sha256(passage["text"]) if passage is not None else ""
                    checked.append((claim.id, cite, digest, check))
            if problems:
                raise WorkspaceError(
                    422,
                    "invalid_citation",
                    "Citations were not saved: " + "; ".join(problems[:10]) + ".",
                )
            for claim in data.claims:
                if con.execute(
                    "SELECT 1 FROM claims WHERE id=? AND investigation_id<>?",
                    (str(claim.id), investigation),
                ).fetchone():
                    raise WorkspaceError(409, "ownership_conflict", "Claim belongs to other work.")
            now = stamp()
            answer_id = row["id"] if row else str(uuid4())
            values = [getattr(data, field) or None for field in ANSWER_FIELDS]
            if row:
                con.execute(
                    "UPDATE answers SET "
                    + ",".join(f"{field}=?" for field in ANSWER_FIELDS)
                    + ",revision_no=revision_no+1,updated_at=? WHERE id=?",
                    (*values, now, answer_id),
                )
            else:
                con.execute(
                    "INSERT INTO answers(id,investigation_id,authorship,status,mode,"
                    + ",".join(ANSWER_FIELDS)
                    + ",revision_no,created_at,updated_at) VALUES "
                    "(?,?,'user','draft','mock',?,?,?,?,?,1,?,?)",
                    (answer_id, investigation, *values, now, now),
                )
            con.execute(
                "DELETE FROM citations WHERE claim_id IN (SELECT id FROM claims WHERE answer_id=?)",
                (answer_id,),
            )
            con.execute("DELETE FROM claims WHERE answer_id=?", (answer_id,))
            for ordinal, claim in enumerate(data.claims, 1):
                mine = [(cite, p, chk) for cid, cite, p, chk in checked if cid == claim.id]
                # Every stored citation passed validation above.
                state = self._state(
                    [{"relation": c.relation, "reference_valid": True, "quote_valid": k.quote_valid}
                     for c, _, k in mine]
                )  # fmt: skip
                con.execute(
                    "INSERT INTO claims VALUES (?,?,?,?,?,?,?,NULL)",
                    (str(claim.id), answer_id, investigation, ordinal, claim.claim_type,
                     claim.claim_text, state),
                )  # fmt: skip
                for number, (cite, digest, check) in enumerate(mine, 1):
                    con.execute(
                        "INSERT INTO citations VALUES (?,?,?,?,?,?,'manual',?,?,1,?,?,?,1,NULL)",
                        (
                            str(uuid4()),
                            str(claim.id),
                            investigation,
                            str(cite.passage_id),
                            number,
                            cite.relation,
                            cite.quoted_text,
                            digest,
                            None if check.quote_valid is None else int(check.quote_valid),
                            kernel.VALIDATION_VERSION,
                            now,
                        ),
                    )
            con.execute(
                "UPDATE investigations SET updated_at=? WHERE id=?",
                (stamp(current.updated_at), investigation),
            )
            return self._answer(con, investigation)

    # Immutable report versions -------------------------------------------------------

    def create_report(self, investigation: str, data: ReportCreate) -> dict[str, Any]:
        with self.db.transaction() as con:
            current = lookup(con, investigation)
            answer = con.execute(
                "SELECT * FROM answers WHERE investigation_id=?", (investigation,)
            ).fetchone()
            if answer is None:
                raise WorkspaceError(409, "no_draft", "Save a report draft before creating one.")
            if answer["revision_no"] != data.expected_revision:
                raise WorkspaceError(409, "conflict", "The draft changed. Reload, then create.")
            view = self._answer(con, investigation)  # Revalidates every citation now.
            notes = self.notes_in(con, investigation)
            source_ids = {c["source_id"] for cl in view["claims"] for c in cl["citations"]}
            source_ids |= {n["source_id"] for n in notes}
            sources = {}
            for source_id in source_ids:
                s = con.execute(
                    "SELECT * FROM sources WHERE id=? AND investigation_id=?",
                    (source_id, investigation),
                ).fetchone()
                sources[source_id] = report.SourceRef(
                    s["id"], s["title"], s["original_url"], s["canonical_url"], s["status"],
                    s["origin"], s["fetched_at"], s["extracted_at"], s["extraction_version"],
                    s["text_sha256"], s["limitation"],
                )  # fmt: skip
            version = con.execute(
                "SELECT COALESCE(MAX(version_no),0)+1 FROM report_versions "
                "WHERE investigation_id=?",
                (investigation,),
            ).fetchone()[0]
            created = stamp()
            data_in = report.ReportInput(
                title=current.title,
                question=current.question,
                scope=view["scope_text"],
                methodology=view["methodology_text"],
                summary=view["summary_text"],
                limitations=view["limitations_text"],
                next_steps=view["next_steps_text"],
                mode=answer["mode"],
                version_no=version,
                created_at=created,
                answer_revision=answer["revision_no"],
                claims=[
                    report.ClaimRef(
                        cl["ordinal"], cl["claim_type"], cl["claim_text"], cl["evidence_state"],
                        [
                            report.CitationRef(
                                c["display_id"], c["source_id"], c["relation"], c["start_offset"],
                                c["end_offset"], c["quoted_text"], c["reference_valid"],
                                c["quote_valid"], c["invalid_reason"],
                            )
                            for c in cl["citations"]
                        ],
                    )
                    for cl in view["claims"]
                ],
                notes=[
                    report.NoteRef(
                        n["display_id"], n["source_id"], n["target_label"], n["stance"], n["note"]
                    )
                    for n in notes
                ],
                sources=sources,
                saved_url_count=con.execute(
                    "SELECT COUNT(*) FROM saved_urls WHERE investigation_id=?", (investigation,)
                ).fetchone()[0],
                run_count=con.execute(
                    "SELECT COUNT(*) FROM runs WHERE investigation_id=?", (investigation,)
                ).fetchone()[0],
            )  # fmt: skip
            markdown = report.render(data_in)
            if len(markdown) > report.MAX_REPORT_CHARS:
                raise WorkspaceError(413, "report_too_large", "The report exceeds the size limit.")
            counts = report.summary(data_in)
            con.execute(
                "INSERT INTO report_versions VALUES (?,?,?,NULL,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    investigation,
                    answer["id"],
                    answer["revision_no"],
                    version,
                    markdown,
                    kernel.sha256(markdown),
                    created,
                    report.TEMPLATE_VERSION,
                    answer["mode"],
                    json.dumps(counts, sort_keys=True),
                    report.REPORT_SCHEMA_VERSION,
                ),
            )
        return self.report(investigation, version)

    @staticmethod
    def notes_in(con: sqlite3.Connection, investigation: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in con.execute(
                "SELECT n.*,p.display_id,p.source_id FROM evidence_notes n JOIN passages p "
                "ON p.id=n.passage_id AND p.investigation_id=n.investigation_id "
                "WHERE n.investigation_id=? ORDER BY p.display_id,n.target_key",
                (investigation,),
            )
        ]

    @staticmethod
    def _summary(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "version_no": row["version_no"],
            "created_at": row["created_at"],
            "answer_revision": row["answer_revision"],
            "markdown_sha256": row["markdown_sha256"],
            "mode": row["mode"],
            "report_schema_version": row["report_schema_version"],
            "validation_summary": json.loads(row["validation_summary_json"]),
        }

    def reports(self, investigation: str) -> list[dict[str, Any]]:
        with self.db.connection() as con:
            lookup(con, investigation)
            rows = con.execute(
                "SELECT * FROM report_versions WHERE investigation_id=? "
                "ORDER BY version_no DESC LIMIT 100",
                (investigation,),
            ).fetchall()
            return [self._summary(row) for row in rows]

    def report(self, investigation: str, version: int) -> dict[str, Any]:
        with self.db.connection() as con:
            lookup(con, investigation)
            row = con.execute(
                "SELECT * FROM report_versions WHERE investigation_id=? AND version_no=?",
                (investigation, version),
            ).fetchone()
            if row is None:
                raise WorkspaceError(404, "not_found", "Report version not found.")
            if kernel.sha256(row["markdown_text"]) != row["markdown_sha256"]:
                raise WorkspaceError(500, "report_integrity", "Saved report failed its checksum.")
            warnings = []
            latest = con.execute(
                "SELECT revision_no FROM answers WHERE investigation_id=?", (investigation,)
            ).fetchone()
            if latest and latest[0] != row["answer_revision"]:
                warnings.append("The draft has changed since this version was created.")
            newest = con.execute(
                "SELECT MAX(version_no) FROM report_versions WHERE investigation_id=?",
                (investigation,),
            ).fetchone()[0]
            if newest != version:
                warnings.append("You are viewing an older version.")
            return {
                **self._summary(row),
                "markdown_text": row["markdown_text"],
                "current_warnings": warnings,
            }
