-- M1 pipeline: archive state, wider stage keys, generated answers and reports.
-- Migration 001 constrains investigations.archived_at to NULL, so archive state is additive.
CREATE TABLE investigation_archives (
 investigation_id TEXT PRIMARY KEY REFERENCES investigations(id), archived_at TEXT NOT NULL
);
-- Nothing references run_stages, so it can be rebuilt to widen stage_key safely.
CREATE TABLE run_stages_new (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
 stage_key TEXT NOT NULL CHECK(stage_key IN ('plan','discover','fetch','extract','rank','synthesize','validate','report')),
 stage_revision INTEGER NOT NULL CHECK(stage_revision>0), status TEXT NOT NULL,
 started_at TEXT, completed_at TEXT, output_ref_json TEXT, error_code TEXT,
 UNIQUE(run_id,stage_key,stage_revision)
);
INSERT INTO run_stages_new SELECT * FROM run_stages;
DROP TABLE run_stages;
ALTER TABLE run_stages_new RENAME TO run_stages;
CREATE INDEX provider_usage_run ON provider_usage(run_id,requested_at);
CREATE INDEX search_queries_run ON search_queries(run_id,searched_at);
-- Model-generated output is stored apart from user-authored answers, claims and citations.
CREATE TABLE generated_answers (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id),
 run_id TEXT NOT NULL UNIQUE, prompt_version TEXT NOT NULL, provider_id TEXT NOT NULL,
 model_id TEXT NOT NULL, generated_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('validated','partial')),
 mode TEXT NOT NULL CHECK(mode IN ('mock','live_free')),
 summary_text TEXT NOT NULL CHECK(length(summary_text) <= 5000),
 limitations_text TEXT CHECK(limitations_text IS NULL OR length(limitations_text) <= 5000),
 needed_evidence_text TEXT CHECK(needed_evidence_text IS NULL OR length(needed_evidence_text) <= 5000),
 suppressed_citations INTEGER NOT NULL CHECK(suppressed_citations >= 0),
 UNIQUE(id,investigation_id),
 FOREIGN KEY(run_id,investigation_id) REFERENCES runs(id,investigation_id)
);
CREATE TABLE generated_claims (
 id TEXT PRIMARY KEY, answer_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL CHECK(ordinal > 0),
 claim_text TEXT NOT NULL CHECK(length(claim_text) BETWEEN 1 AND 2000),
 evidence_state TEXT NOT NULL CHECK(evidence_state IN ('cited','not_established')),
 explanation TEXT,
 UNIQUE(answer_id,ordinal), UNIQUE(id,investigation_id),
 FOREIGN KEY(answer_id,investigation_id) REFERENCES generated_answers(id,investigation_id)
);
CREATE TABLE generated_citations (
 id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
 passage_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal > 0),
 quoted_text TEXT CHECK(quoted_text IS NULL OR length(quoted_text) BETWEEN 1 AND 2000),
 passage_sha256 TEXT NOT NULL CHECK(length(passage_sha256) = 64),
 validation_version TEXT NOT NULL, validated_at TEXT NOT NULL,
 UNIQUE(claim_id,passage_id), UNIQUE(claim_id,ordinal),
 FOREIGN KEY(claim_id,investigation_id) REFERENCES generated_claims(id,investigation_id),
 FOREIGN KEY(passage_id,investigation_id) REFERENCES passages(id,investigation_id)
);
CREATE INDEX generated_citations_passage ON generated_citations(passage_id);
CREATE TABLE generated_reports (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id),
 answer_id TEXT NOT NULL, run_id TEXT NOT NULL, version_no INTEGER NOT NULL CHECK(version_no > 0),
 markdown_text TEXT NOT NULL CHECK(length(markdown_text) BETWEEN 1 AND 2000000),
 markdown_sha256 TEXT NOT NULL CHECK(length(markdown_sha256) = 64),
 created_at TEXT NOT NULL, prompt_version TEXT NOT NULL,
 mode TEXT NOT NULL CHECK(mode IN ('mock','live_free')),
 validation_summary_json TEXT NOT NULL, report_schema_version TEXT NOT NULL,
 UNIQUE(investigation_id,version_no),
 FOREIGN KEY(answer_id,investigation_id) REFERENCES generated_answers(id,investigation_id)
);
CREATE TRIGGER immutable_generated_report BEFORE UPDATE ON generated_reports
BEGIN SELECT RAISE(ABORT,'Report versions are immutable'); END;
