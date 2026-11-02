-- User-authored evidence review and deterministic reports. No model output is stored.
-- Composite parent key so citations and notes cannot reference another investigation's passage.
CREATE UNIQUE INDEX passages_id_investigation ON passages(id,investigation_id);
CREATE TABLE evidence_notes (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id),
 passage_id TEXT NOT NULL,
 target_key TEXT NOT NULL CHECK(length(target_key) BETWEEN 1 AND 64),
 target_label TEXT NOT NULL CHECK(length(target_label) BETWEEN 1 AND 1000),
 stance TEXT NOT NULL CHECK(stance IN ('unreviewed','supports','contradicts','context','insufficient')),
 note TEXT CHECK(note IS NULL OR length(note) <= 5000),
 revision_no INTEGER NOT NULL CHECK(revision_no > 0),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(investigation_id,passage_id,target_key),
 FOREIGN KEY(passage_id,investigation_id) REFERENCES passages(id,investigation_id)
);
CREATE INDEX evidence_notes_investigation ON evidence_notes(investigation_id,updated_at);
-- One mutable user-authored draft per investigation. Spec columns for model provenance
-- remain NULL: no model, provider or run produced this text.
CREATE TABLE answers (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL UNIQUE REFERENCES investigations(id),
 run_id TEXT, prompt_version TEXT, provider_id TEXT CHECK(provider_id IS NULL),
 model_id TEXT CHECK(model_id IS NULL), generated_at TEXT,
 authorship TEXT NOT NULL CHECK(authorship = 'user'),
 status TEXT NOT NULL CHECK(status IN ('draft','validated','partial','rejected')),
 mode TEXT NOT NULL CHECK(mode IN ('mock','live_free')),
 scope_text TEXT CHECK(scope_text IS NULL OR length(scope_text) <= 5000),
 methodology_text TEXT CHECK(methodology_text IS NULL OR length(methodology_text) <= 5000),
 summary_text TEXT CHECK(summary_text IS NULL OR length(summary_text) <= 10000),
 limitations_text TEXT CHECK(limitations_text IS NULL OR length(limitations_text) <= 5000),
 next_steps_text TEXT CHECK(next_steps_text IS NULL OR length(next_steps_text) <= 5000),
 revision_no INTEGER NOT NULL CHECK(revision_no > 0),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(id,investigation_id),
 FOREIGN KEY(run_id,investigation_id) REFERENCES runs(id,investigation_id)
);
CREATE TABLE claims (
 id TEXT PRIMARY KEY, answer_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL CHECK(ordinal > 0),
 claim_type TEXT NOT NULL CHECK(claim_type IN ('finding','interpretation','conflict','hypothesis','gap','conclusion')),
 claim_text TEXT NOT NULL CHECK(length(claim_text) BETWEEN 1 AND 2000),
 evidence_state TEXT NOT NULL CHECK(evidence_state IN ('cited','not_established')),
 explanation TEXT,
 UNIQUE(answer_id,ordinal), UNIQUE(id,investigation_id),
 FOREIGN KEY(answer_id,investigation_id) REFERENCES answers(id,investigation_id)
);
CREATE TABLE citations (
 id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
 passage_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal > 0),
 relation TEXT NOT NULL CHECK(relation IN ('supports','contradicts','context')),
 origin TEXT NOT NULL CHECK(origin = 'manual'),
 quoted_text TEXT CHECK(quoted_text IS NULL OR length(quoted_text) BETWEEN 1 AND 2000),
 passage_sha256 TEXT NOT NULL CHECK(length(passage_sha256) = 64),
 reference_valid INTEGER NOT NULL CHECK(reference_valid IN (0,1)),
 quote_valid INTEGER CHECK(quote_valid IS NULL OR quote_valid IN (0,1)),
 validation_version TEXT NOT NULL, validated_at TEXT NOT NULL,
 active INTEGER NOT NULL CHECK(active IN (0,1)), invalid_reason TEXT,
 UNIQUE(claim_id,passage_id), UNIQUE(claim_id,ordinal),
 FOREIGN KEY(claim_id,investigation_id) REFERENCES claims(id,investigation_id),
 FOREIGN KEY(passage_id,investigation_id) REFERENCES passages(id,investigation_id)
);
CREATE INDEX citations_passage ON citations(passage_id);
CREATE TABLE report_versions (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id),
 answer_id TEXT NOT NULL, run_id TEXT, answer_revision INTEGER NOT NULL CHECK(answer_revision > 0),
 version_no INTEGER NOT NULL CHECK(version_no > 0),
 markdown_text TEXT NOT NULL CHECK(length(markdown_text) BETWEEN 1 AND 2000000),
 markdown_sha256 TEXT NOT NULL CHECK(length(markdown_sha256) = 64),
 created_at TEXT NOT NULL, prompt_version TEXT NOT NULL,
 mode TEXT NOT NULL CHECK(mode IN ('mock','live_free')),
 validation_summary_json TEXT NOT NULL, report_schema_version TEXT NOT NULL,
 UNIQUE(investigation_id,version_no),
 FOREIGN KEY(answer_id,investigation_id) REFERENCES answers(id,investigation_id)
);
CREATE TRIGGER immutable_report_version BEFORE UPDATE ON report_versions
BEGIN SELECT RAISE(ABORT,'Report versions are immutable'); END;
