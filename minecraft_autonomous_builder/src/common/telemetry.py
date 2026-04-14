from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(slots=True)
class TelemetryEvent:
    name: str
    duration_ms: int
    status: str


class Telemetry:
    """Simple pluggable telemetry hook for metrics export."""

    def emit(self, event: TelemetryEvent) -> None:
        # In production, send to OTEL/Prometheus exporter.
        _ = event

    def timed(self, name: str):
        start = time.perf_counter()

        def done(status: str = "ok") -> TelemetryEvent:
            return TelemetryEvent(
                name=name,
                duration_ms=int((time.perf_counter() - start) * 1000),
                status=status,
            )

        return done
