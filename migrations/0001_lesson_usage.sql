CREATE TABLE IF NOT EXISTS lesson_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event TEXT NOT NULL,
  query TEXT,
  lesson_id TEXT,
  domain TEXT,
  ip TEXT,
  user_agent TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_usage_event ON lesson_usage(event);
CREATE INDEX IF NOT EXISTS idx_usage_created ON lesson_usage(created_at);
