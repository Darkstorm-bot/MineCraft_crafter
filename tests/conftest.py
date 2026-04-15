from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
from scripts.init_db import run_migrations
from mempalace.accessor import MemPalaceAccessor


@pytest.fixture()
def temp_db(tmp_path: Path) -> str:
    db_path = tmp_path / "test.db"
    run_migrations(str(db_path))
    return str(db_path)


@pytest.fixture()
def accessor(temp_db: str) -> MemPalaceAccessor:
    os.environ["MEMPALACE_DB_PATH"] = temp_db
    return MemPalaceAccessor(temp_db)
