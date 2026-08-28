-- MisakaNet D1 Lesson Service — schema (PRD ④)
-- Apply: wrangler d1 execute misakanet-db --remote --file=workers/d1/schema.sql

CREATE TABLE IF NOT EXISTS lessons (
  id TEXT PRIMARY KEY,          -- slug (filename without .md)
  title TEXT NOT NULL,
  domain TEXT,
  status TEXT DEFAULT 'published',
  language TEXT DEFAULT 'en',
  tags TEXT,                    -- JSON array
  path TEXT,                    -- repo path, e.g. lessons/core/foo.md
  problem TEXT,                 -- first ~2000 chars of Problem/描述 section
  root_cause TEXT,
  solution TEXT,
  verification TEXT,
  content_md TEXT,              -- full markdown body (after frontmatter)
  frontmatter TEXT,             -- raw frontmatter JSON
  summary TEXT,                 -- short summary from lessons.json
  created TEXT,
  updated TEXT,
  synced_at TEXT,               -- sync run timestamp
  checksum TEXT                 -- content hash for repo<->D1 reconciliation
);

CREATE INDEX IF NOT EXISTS idx_lessons_domain ON lessons(domain);
CREATE INDEX IF NOT EXISTS idx_lessons_status ON lessons(status);
CREATE INDEX IF NOT EXISTS idx_lessons_updated ON lessons(updated);
CREATE INDEX IF NOT EXISTS idx_lessons_created ON lessons(created);

-- Sync ledger: one row per successful sync run (audit + reconciliation)
CREATE TABLE IF NOT EXISTS lesson_sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TEXT NOT NULL,
  source_commit TEXT,
  total INTEGER NOT NULL,
  upserted INTEGER NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0,
  checksums TEXT               -- JSON: {id: checksum} for reconciliation
);
