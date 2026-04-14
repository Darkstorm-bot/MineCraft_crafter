from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PreflightResult:
    ok: bool
    blockers: list[str]


class PreflightService:
    def run(
        self,
        required_manifest: dict[str, int],
        inventory_snapshot: dict[str, int],
        terrain_clear: bool = True,
        chunks_loaded: bool = True,
    ) -> PreflightResult:
        blockers: list[str] = []
        if not terrain_clear:
            blockers.append("terrain_not_clear")
        if not chunks_loaded:
            blockers.append("chunks_not_loaded")

        for item, count in required_manifest.items():
            if inventory_snapshot.get(item, 0) < count:
                blockers.append(f"insufficient_inventory:{item}")

        return PreflightResult(ok=not blockers, blockers=blockers)
