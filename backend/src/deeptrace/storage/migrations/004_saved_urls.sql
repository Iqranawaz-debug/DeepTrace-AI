-- Manually saved URLs are research leads only: never fetched, never evidence, never cited.
CREATE TABLE saved_urls (
 id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id),
 original_url TEXT NOT NULL CHECK(length(original_url) BETWEEN 1 AND 2048),
 canonical_url TEXT NOT NULL CHECK(length(canonical_url) BETWEEN 1 AND 2048),
 note TEXT CHECK(note IS NULL OR length(note) <= 1000),
 created_at TEXT NOT NULL,
 UNIQUE(investigation_id,canonical_url)
);
CREATE INDEX saved_urls_investigation_created ON saved_urls(investigation_id,created_at);
