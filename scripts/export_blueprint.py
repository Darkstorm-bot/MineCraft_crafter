#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from mempalace.accessor import MemPalaceAccessor


def main() -> None:
    accessor = MemPalaceAccessor(os.getenv("MEMPALACE_DB_PATH", "./data/mempalace.db"))
    export_dir = Path("data/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    # export latest blueprints for all known projects
    # lightweight helper for operators
    for pid in []:
        blueprints = accessor.get_latest_blueprints(pid)
        (export_dir / f"{pid}_blueprints.json").write_text(
            json.dumps(blueprints, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
