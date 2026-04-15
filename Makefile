PYTHON ?= python3
PIP ?= pip3
NPM ?= npm

.PHONY: setup lint test run-api init-db format

setup:
        $(PIP) install -r requirements.txt
        $(PIP) install -e .[dev]
        @if [ -f package.json ]; then $(NPM) install; fi

lint:
        ruff check src tests scripts
        black --check src tests scripts
        @if [ -f package.json ]; then $(NPM) run lint || true; fi

test:
        pytest
        @if [ -f package.json ]; then $(NPM) run test || true; fi

format:
        black src tests scripts
        ruff check --fix src tests scripts

init-db:
        PYTHONPATH=src $(PYTHON) scripts/init_db.py

run-api:
        PYTHONPATH=src uvicorn api.app:app --host 0.0.0.0 --port 8080 --reload
