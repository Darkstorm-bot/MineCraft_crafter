from __future__ import annotations

import os

import httpx


class LLaVAClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llava:latest")

    def score(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        response = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        return body.get("response", "{}")
