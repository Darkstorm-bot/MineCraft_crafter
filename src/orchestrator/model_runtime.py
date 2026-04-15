from __future__ import annotations

import logging
import os
from contextlib import contextmanager

import httpx

logger = logging.getLogger(__name__)


class SequentialModelRuntime:
    """Manages model resource allocation with sequential load/unload semantics.

    Tracks which model is currently loaded and enforces that only one model
    is active at a time. When Ollama is available, it can preload models
    into memory for faster inference.
    """

    def __init__(self, ollama_url: str | None = None):
        self.ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self._currently_loaded: str | None = None

    def _is_ollama_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.ollama_url}/api/tags", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _preload_model(self, model_name: str) -> bool:
        """Attempt to preload a model into Ollama's memory for faster inference."""
        if not self._is_ollama_available():
            return False
        try:
            # Ollama doesn't have a direct preload endpoint, but we can
            # trigger a lightweight load by sending a minimal prompt
            payload = {
                "model": model_name,
                "prompt": "",
                "stream": False,
                "keep_alive": "30m",  # Keep model in memory for 30 minutes
            }
            resp = httpx.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=5.0,  # Short timeout, we just want to trigger the load
            )
            if resp.status_code == 200:
                logger.info("Model '%s' preloaded into Ollama (keep_alive=30m)", model_name)
                return True
        except Exception as exc:
            logger.debug("Model preload failed for '%s': %s", model_name, exc)
        return False

    def _unload_model(self, model_name: str) -> None:
        """Signal Ollama to unload a model from memory."""
        if not self._is_ollama_available():
            return
        try:
            # Set keep_alive to 0 to immediately unload
            payload = {
                "model": model_name,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            }
            httpx.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=5.0,
            )
            logger.info("Model '%s' unloaded from Ollama", model_name)
        except Exception as exc:
            logger.debug("Model unload failed for '%s': %s", model_name, exc)

    @contextmanager
    def load(self, model_name: str):
        """Load a model, yield control, then unload it.

        Enforces sequential semantics: only one model is loaded at a time.
        If a different model was already loaded, it is unloaded first.
        """
        # Unload any previously loaded model
        if self._currently_loaded and self._currently_loaded != model_name:
            logger.debug("Unloading previous model '%s' before loading '%s'",
                         self._currently_loaded, model_name)
            self._unload_model(self._currently_loaded)
            self._currently_loaded = None

        # Preload the requested model
        if self._preload_model(model_name):
            self._currently_loaded = model_name

        try:
            yield
        finally:
            # Always unload the model when exiting the context
            if self._currently_loaded == model_name:
                self._unload_model(model_name)
                self._currently_loaded = None
