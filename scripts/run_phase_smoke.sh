#!/usr/bin/env bash
set -euo pipefail

python3 scripts/init_db.py
pytest -q tests/unit/test_mempalace.py
python3 scripts/export_blueprint.py || true
