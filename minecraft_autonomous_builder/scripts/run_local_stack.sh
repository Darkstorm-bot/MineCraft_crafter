#!/usr/bin/env bash
set -euo pipefail

cp -n .env.example .env || true
python3 scripts/init_db.py
PYTHONPATH=src uvicorn api.app:app --host 0.0.0.0 --port 8080 --reload
