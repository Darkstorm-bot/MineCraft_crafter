CREATE TABLE IF NOT EXISTS coord_index (
  x INTEGER NOT NULL,
  y INTEGER NOT NULL,
  z INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  module_name TEXT NOT NULL,
  blueprint_id TEXT,
  reservation_status TEXT NOT NULL DEFAULT 'reserved',
  reserved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  released_at TEXT,
  PRIMARY KEY (x, y, z)
);

CREATE INDEX IF NOT EXISTS idx_coord_index_project ON coord_index(project_id);
CREATE INDEX IF NOT EXISTS idx_coord_index_reserved_at ON coord_index(reserved_at);
