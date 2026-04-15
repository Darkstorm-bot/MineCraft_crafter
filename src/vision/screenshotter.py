from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class Screenshotter:
    """Captures screenshots of Minecraft builds for vision verification.

    Supports two modes:
    1. Real: Requests screenshot from Minecraft bot via HTTP API
    2. Synthetic fallback: Generates placeholder image for offline testing
    """

    def __init__(self, bot_api_url: str | None = None):
        self.bot_api_url = bot_api_url or os.getenv("BOT_API_URL", "http://127.0.0.1:3001")

    def _request_screenshot(self, project_id: str, module_name: str, phase: str) -> str | None:
        """Request a real screenshot from the Minecraft bot."""
        try:
            resp = httpx.post(
                f"{self.bot_api_url}/screenshot",
                json={
                    "project_id": project_id,
                    "module_name": module_name,
                    "phase": phase,
                },
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("screenshot_path")
        except Exception as exc:
            logger.debug("Bot screenshot request failed: %s", exc)
        return None

    def _generate_synthetic(self, project_id: str, module_name: str, phase: str) -> str:
        """Generate a synthetic placeholder image for offline testing."""
        out_dir = Path(os.getenv("SCREENSHOT_DIR", "data/screenshots")) / project_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{module_name}_{phase}.png"

        image = Image.new("RGB", (640, 360), (30, 30, 30))
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), f"{project_id}:{module_name}:{phase}", fill=(200, 200, 200))
        draw.text((10, 40), "SYNTHETIC PLACEHOLDER - No Minecraft connection", fill=(150, 150, 150))
        image.save(path)
        logger.info("Generated synthetic screenshot: %s", path)
        return str(path)

    def capture_module(self, project_id: str, module_name: str, phase: str) -> str:
        """Capture a screenshot for a specific module and phase.

        Tries real Minecraft bot first, falls back to synthetic image.
        """
        # Try real screenshot first
        real_path = self._request_screenshot(project_id, module_name, phase)
        if real_path:
            logger.info("Captured real screenshot: %s", real_path)
            return real_path

        # Fallback to synthetic
        return self._generate_synthetic(project_id, module_name, phase)
