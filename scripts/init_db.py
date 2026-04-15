#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from common.logging import configure_logging, get_logger
from mempalace.repositories import SQLiteRepository


def run_migrations(db_path: str) -> None:
    repo = SQLiteRepository(db_path)
    migration_dir = Path(__file__).resolve().parents[1] / "src" / "mempalace" / "migrations"
    migrations = sorted(migration_dir.glob("*.sql"))

    with repo.transaction() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        applied = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for path in migrations:
            if path.name in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(version) VALUES(?)", (path.name,))


def main() -> None:
    configure_logging()
    logger = get_logger(__name__)
    db_path = os.getenv("MEMPALACE_DB_PATH", "./data/mempalace.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    run_migrations(db_path)
    logger.info("database initialized", extra={"trace_id": "init-db"})


if __name__ == "__main__":
    main()
