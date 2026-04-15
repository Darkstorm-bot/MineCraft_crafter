from __future__ import annotations

import logging
import os
import sys
from typing import Optional


class _TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return True


def configure_logging(level: Optional[str] = None) -> None:
    """Configure structured-ish application logging once."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s trace=%(trace_id)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger().addFilter(_TraceFilter())


class TraceAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("trace_id", self.extra.get("trace_id", "-"))
        return msg, kwargs


def get_logger(name: str, trace_id: str = "-") -> TraceAdapter:
    return TraceAdapter(logging.getLogger(name), {"trace_id": trace_id})
