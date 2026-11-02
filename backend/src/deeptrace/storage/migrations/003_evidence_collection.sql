CREATE TABLE provider_consents (
 id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, purpose TEXT NOT NULL,
 disclosure_version TEXT NOT NULL, granted_at TEXT NOT NULL, revoked_at TEXT,
 CHECK(revoked_at IS NULL OR revoked_at >= granted_at)
);
CREATE TABLE runs (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id),
 kind TEXT NOT NULL DEFAULT 'research' CHECK(kind='research'),
 status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed','cancelled','budget_reached','interrupted')),
 mode TEXT NOT NULL CHECK(mode IN ('mock','live_free')),
 plan_id TEXT REFERENCES plans(id), plan_revision INTEGER NOT NULL CHECK(plan_revision>=0),
 config_snapshot_json TEXT NOT NULL, question_snapshot TEXT NOT NULL,
 created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
 cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0,1)),
 worker_claim_token TEXT, last_heartbeat_at TEXT, error_code TEXT,
 UNIQUE(id,investigation_id)
);
CREATE UNIQUE INDEX one_active_collection ON runs((1)) WHERE status IN ('queued','running');
CREATE INDEX runs_investigation_created ON runs(investigation_id,created_at);
CREATE TABLE run_stages (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
 stage_key TEXT NOT NULL CHECK(stage_key IN ('discover','fetch','extract')),
 stage_revision INTEGER NOT NULL CHECK(stage_revision>0), status TEXT NOT NULL,
 started_at TEXT, completed_at TEXT, output_ref_json TEXT, error_code TEXT,
 UNIQUE(run_id,stage_key,stage_revision)
);
CREATE TABLE run_events (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), sequence_no INTEGER NOT NULL,
 event_type TEXT NOT NULL, stage_key TEXT, safe_message TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(run_id,sequence_no)
);
CREATE TABLE provider_usage (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), provider_id TEXT NOT NULL,
 operation TEXT NOT NULL, attempt_no INTEGER NOT NULL CHECK(attempt_no>0),
 requested_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
 reported_units_json TEXT, estimated_units_json TEXT, quota_state TEXT,
 is_estimate INTEGER NOT NULL CHECK(is_estimate IN (0,1)), provider_request_id TEXT
);
CREATE TABLE search_queries (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
 query_text TEXT NOT NULL, provider_id TEXT NOT NULL, status TEXT NOT NULL,
 searched_at TEXT, results_count INTEGER, credits_reported INTEGER,
 usage_id TEXT REFERENCES provider_usage(id),
 FOREIGN KEY(run_id,investigation_id) REFERENCES runs(id,investigation_id)
);
CREATE TABLE sources (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id),
 run_id TEXT NOT NULL, source_type TEXT NOT NULL DEFAULT 'web' CHECK(source_type='web'),
 origin TEXT NOT NULL CHECK(origin IN ('mock','manual','tavily')),
 original_url TEXT NOT NULL, canonical_url TEXT NOT NULL,
 title TEXT, author TEXT, published_at TEXT,
 status TEXT NOT NULL CHECK(status IN ('fetched','partial','blocked','paywalled','failed','duplicate','unsupported')),
 extracted_text TEXT, text_sha256 TEXT, extraction_version TEXT, normalization_version TEXT,
 fetched_at TEXT, extracted_at TEXT, limitation TEXT, duplicate_of TEXT,
 UNIQUE(id,investigation_id),
 FOREIGN KEY(run_id,investigation_id) REFERENCES runs(id,investigation_id),
 FOREIGN KEY(duplicate_of,investigation_id) REFERENCES sources(id,investigation_id)
);
CREATE INDEX sources_investigation_url ON sources(investigation_id,canonical_url);
CREATE TABLE passages (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL, source_id TEXT NOT NULL,
 display_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal>0), text TEXT NOT NULL,
 start_offset INTEGER NOT NULL CHECK(start_offset>=0), end_offset INTEGER NOT NULL,
 extraction_version TEXT NOT NULL, text_sha256 TEXT NOT NULL, extracted_at TEXT NOT NULL,
 page_index INTEGER CHECK(page_index IS NULL), removed_at TEXT CHECK(removed_at IS NULL),
 CHECK(end_offset>start_offset), UNIQUE(investigation_id,display_id), UNIQUE(source_id,ordinal),
 FOREIGN KEY(source_id,investigation_id) REFERENCES sources(id,investigation_id)
);
CREATE INDEX passages_source ON passages(investigation_id,source_id,ordinal);
CREATE TRIGGER immutable_source BEFORE UPDATE ON sources BEGIN SELECT RAISE(ABORT,'Source snapshots are immutable'); END;
CREATE TRIGGER immutable_passage BEFORE UPDATE ON passages BEGIN SELECT RAISE(ABORT,'Passages are immutable'); END;
