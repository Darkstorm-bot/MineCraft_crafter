from __future__ import annotations

from contextlib import contextmanager


class SequentialModelRuntime:
    """Ensures sequential load/unload semantics for architect/engineer models."""

    @contextmanager
    def load(self, model_name: str):
        _ = model_name
        # In production: allocate model resources / VRAM.
        try:
            yield
        finally:
            # In production: release model resources.
            pass
