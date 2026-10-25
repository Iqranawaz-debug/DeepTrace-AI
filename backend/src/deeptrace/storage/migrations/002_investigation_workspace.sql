ALTER TABLE investigations ADD COLUMN description TEXT CHECK (description IS NULL OR length(description) <= 5000);
CREATE TABLE plans (
    id TEXT PRIMARY KEY NOT NULL,
    investigation_id TEXT NOT NULL UNIQUE REFERENCES investigations(id),
    revision_no INTEGER NOT NULL CHECK (revision_no > 0),
    prompt_version TEXT,
    provider_id TEXT,
    model_id TEXT,
    created_at TEXT NOT NULL,
    approved_at TEXT,
    UNIQUE (investigation_id, revision_no)
);
CREATE TABLE plan_items (
    id TEXT PRIMARY KEY NOT NULL,
    plan_id TEXT NOT NULL REFERENCES plans(id),
    ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 8),
    sub_question TEXT NOT NULL CHECK (length(trim(sub_question)) BETWEEN 1 AND 1000),
    search_query TEXT CHECK (search_query IS NULL OR length(search_query) <= 500),
    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
    omission_reason TEXT,
    UNIQUE (plan_id, ordinal)
);
