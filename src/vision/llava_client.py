from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class LLaVAClient:
    """Ollama LLaVA multimodal client for vision scoring.

    Sends both image and prompt to Ollama's /api/generate endpoint.
    Supports the llava model family for visual question answering.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llava:latest")

    def _encode_image(self, image_path: str) -> str:
        """Encode image file as base64 string."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Screenshot not found: {image_path}")
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def score(self, prompt: str, image_path: str) -> str:
        """Score a Minecraft build screenshot against expected specs.

        Args:
            prompt: Structured prompt describing expected module specs
            image_path: Path to screenshot PNG file

        Returns:
            Raw JSON response string from LLaVA
        """
        try:
            image_b64 = self._encode_image(image_path)
        except FileNotFoundError as exc:
            logger.error("Vision scoring failed: %s", exc)
            return '{"vision_score": 0, "flagged_modules": [], "diff_detail": []}'

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024,
            },
        }

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            body = response.json()
            return body.get("response", "{}")
        except httpx.HTTPError as exc:
            logger.warning("Ollama LLaVA call failed: %s", exc)
            return '{"vision_score": 0, "flagged_modules": [], "diff_detail": []}'

    def is_available(self) -> bool:
        """Check if Ollama with vision model is running."""
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            if resp.status_code != 200:
                return False
            tags = resp.json().get("models", [])
            return any(self.model in t.get("name", "") for t in tags)
        except Exception:
            return False
