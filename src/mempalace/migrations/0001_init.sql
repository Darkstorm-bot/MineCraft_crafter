CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  project_type TEXT NOT NULL,
  mc_version TEXT NOT NULL,
  origin_x INTEGER NOT NULL,
  origin_y INTEGER NOT NULL,
  origin_z INTEGER NOT NULL,
  requirements_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'init',
  iteration_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blueprints (
  blueprint_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  module_name TEXT NOT NULL,
  bounds_json TEXT,
  block_data_json TEXT NOT NULL,
  material_manifest_json TEXT NOT NULL,
  quality_score REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(project_id, version, module_name),
  FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS critiques (
  critique_id TEXT PRIMARY KEY,
  blueprint_id TEXT NOT NULL,
  iteration INTEGER NOT NULL,
  delta_score REAL NOT NULL,
  issues_json TEXT NOT NULL,
  approval_flag INTEGER NOT NULL,
  quality_score REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(blueprint_id) REFERENCES blueprints(blueprint_id)
);
