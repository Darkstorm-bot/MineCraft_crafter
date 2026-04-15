from __future__ import annotations

from mempalace.accessor import MemPalaceAccessor


class VisionCritiqueWriter:
    def __init__(self, accessor: MemPalaceAccessor):
        self.accessor = accessor

    def write(self, project_id: str, blueprint_id: str, version: int, vision_diff: dict) -> dict:
        return self.accessor.insert_vision_critique(
            {
                "project_id": project_id,
                "blueprint_id": blueprint_id,
                "version": version,
                "vision_score": vision_diff["vision_score"],
                "flagged_modules": vision_diff["flagged_modules"],
                "diff_detail": vision_diff["diff_detail"],
            }
        )
