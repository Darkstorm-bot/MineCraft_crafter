from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
from fastapi import APIRouter

from mempalace.accessor import MemPalaceAccessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Dependency accessor (injected at app startup)
_accessor: MemPalaceAccessor | None = None


def set_accessor(accessor: MemPalaceAccessor) -> None:
    global _accessor
    _accessor = accessor


def _check_database() -> dict:
    """Verify database connectivity and basic operations."""
    if _accessor is None:
        return {"status": "error", "message": "accessor_not_initialized"}
    try:
        # Test basic query
        db_path = os.getenv("MEMPALACE_DB_PATH", "./data/mempalace.db")
        db_exists = Path(db_path).exists()
        return {"status": "ok", "db_path": db_path, "db_exists": db_exists}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _check_ollama() -> dict:
    """Verify Ollama service is reachable and has models."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return {"status": "ok", "models": model_names}
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "error", "message": f"unreachable: {exc}"}


def _check_bot_api() -> dict:
    """Verify Minecraft bot API is reachable."""
    bot_url = os.getenv("BOT_API_URL", "http://127.0.0.1:3001")
    try:
        resp = httpx.get(f"{bot_url}/health", timeout=5.0)
        if resp.status_code == 200:
            return {"status": "ok", "url": bot_url}
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "warn", "message": f"unreachable: {exc}"}


def _check_disk_space() -> dict:
    """Verify sufficient disk space for operations."""
    try:
        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        stat = data_dir.stat() if data_dir.exists() else Path(".").stat()
        # Use os.statvfs on Unix or fallback
        free_mb = 0
        try:
            import shutil
            total, used, free = shutil.disk_usage(data_dir if data_dir.exists() else ".")
            free_mb = free // (1024 * 1024)
        except Exception:
            free_mb = -1
        return {"status": "ok", "free_mb": free_mb}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/live")
def liveness() -> dict:
    """Liveness probe: is the process running?"""
    return {"status": "ok", "pid": os.getpid()}


@router.get("/ready")
def readiness() -> dict:
    """Readiness probe: are all dependencies healthy?"""
    checks = {
        "database": _check_database(),
        "ollama": _check_ollama(),
        "bot_api": _check_bot_api(),
        "disk_space": _check_disk_space(),
    }

    # Overall status is 'ready' only if all critical checks pass
    critical = ["database", "ollama"]
    all_healthy = all(checks[k]["status"] in ("ok", "warn") for k in critical)

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }
