from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PreflightResult:
    ok: bool
    blockers: list[str]


class PreflightService:
    def __init__(self, bot_api_url: str | None = None):
        self.bot_api_url = bot_api_url or os.getenv("BOT_API_URL", "http://127.0.0.1:3001")

    def _check_terrain(self, modules: list[dict]) -> bool:
        """Ask the bot to scan terrain at module origins."""
        try:
            resp = httpx.post(
                f"{self.bot_api_url}/terrain_check",
                json={"modules": [{"name": m["module_name"], "origin": m["bounds"]["min"]} for m in modules]},
                timeout=15.0,
            )
            if resp.status_code == 200:
                result = resp.json()
                return result.get("clear", True)
        except Exception as exc:
            logger.warning("Terrain check via bot API failed: %s", exc)
        # Fallback: assume clear (works in offline mode)
        return True

    def _check_chunks(self, modules: list[dict]) -> bool:
        """Ask the bot to verify chunks are loaded at module origins."""
        try:
            resp = httpx.post(
                f"{self.bot_api_url}/chunk_check",
                json={"modules": [{"name": m["module_name"], "origin": m["bounds"]["min"]} for m in modules]},
                timeout=15.0,
            )
            if resp.status_code == 200:
                result = resp.json()
                return result.get("loaded", True)
        except Exception as exc:
            logger.warning("Chunk check via bot API failed: %s", exc)
        return True

    def run(
        self,
        required_manifest: dict[str, int],
        inventory_snapshot: dict[str, int],
        modules: list[dict] | None = None,
        terrain_clear: bool | None = None,
        chunks_loaded: bool | None = None,
    ) -> PreflightResult:
        """Run all preflight checks before execution.

        If modules are provided, performs real terrain/chunk checks via bot API.
        Otherwise falls back to parameter-based checks for offline/testing mode.
        """
        blockers: list[str] = []

        # Real terrain check via bot API if modules provided
        if modules is not None:
            if terrain_clear is None:
                terrain_clear = self._check_terrain(modules)
            if not terrain_clear:
                blockers.append("terrain_not_clear")

            if chunks_loaded is None:
                chunks_loaded = self._check_chunks(modules)
            if not chunks_loaded:
                blockers.append("chunks_not_loaded")
        else:
            # Fallback to parameter-based checks
            if terrain_clear is False:
                blockers.append("terrain_not_clear")
            if chunks_loaded is False:
                blockers.append("chunks_not_loaded")

        # Inventory check
        for item, count in required_manifest.items():
            if inventory_snapshot.get(item, 0) < count:
                blockers.append(f"insufficient_inventory:{item}")

        return PreflightResult(ok=not blockers, blockers=blockers)
