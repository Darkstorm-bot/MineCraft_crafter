CREATE TABLE IF NOT EXISTS build_log (
  log_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  blueprint_id TEXT NOT NULL,
  batch_index INTEGER NOT NULL,
  blocks_placed INTEGER NOT NULL,
  checkpoint_state_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(project_id, blueprint_id, batch_index)
);

CREATE TABLE IF NOT EXISTS vision_critiques (
  critique_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  blueprint_id TEXT,
  version INTEGER NOT NULL,
  vision_score REAL NOT NULL,
  flagged_modules_json TEXT NOT NULL,
  diff_detail_json TEXT NOT NULL,
  resolved INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
