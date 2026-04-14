from __future__ import annotations

import uuid
from collections import Counter

from .planner_io import ArchitectInput, ArchitectOutput


class ArchitectAgent:
    """Deterministic planner stub: emits module blueprint blocks from module list."""

    def run(self, payload: ArchitectInput, modules: list[str], version: int) -> ArchitectOutput:
        blueprint_modules = []
        material_counter: Counter[str] = Counter()
        coord_proposals = []

        for i, module in enumerate(modules):
            blocks = []
            for y in range(2):
                for x in range(3):
                    for z in range(3):
                        bid = "minecraft:stone" if y == 0 else "minecraft:oak_planks"
                        blocks.append({"x": x + i * 4, "y": y, "z": z, "block_id": bid})
                        material_counter[bid] += 1
                        coord_proposals.append({"x": x + i * 4, "y": y, "z": z})

            blueprint_modules.append(
                {
                    "blueprint_id": str(uuid.uuid4()),
                    "project_id": payload.project["project_id"],
                    "version": version,
                    "module_name": module,
                    "bounds": {
                        "min": {"x": i * 4, "y": 0, "z": 0},
                        "max": {"x": i * 4 + 2, "y": 1, "z": 2},
                    },
                    "block_data": blocks,
                    "material_manifest": dict(Counter([b["block_id"] for b in blocks])),
                    "quality_score": 75,
                }
            )

        return ArchitectOutput(
            blueprint_modules=blueprint_modules,
            material_manifest=dict(material_counter),
            coord_proposals=coord_proposals,
            change_summary="Generated deterministic scaffold modules",
        )
