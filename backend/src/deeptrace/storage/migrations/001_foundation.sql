CREATE TABLE settings (
    key TEXT PRIMARY KEY CHECK (key = 'mode'),
    value_json TEXT NOT NULL CHECK (value_json IN ('"mock"', '"offline"')),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    updated_at TEXT NOT NULL
);
CREATE TABLE investigations (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 120),
    question TEXT NOT NULL CHECK (length(trim(question)) BETWEEN 10 AND 1000),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status = 'draft'),
    sensitive INTEGER NOT NULL DEFAULT 0 CHECK (sensitive IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at >= created_at),
    archived_at TEXT CHECK (archived_at IS NULL)
);
CREATE INDEX investigations_status_updated ON investigations(status, updated_at);
