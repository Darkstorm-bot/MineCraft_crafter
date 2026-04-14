from __future__ import annotations

from dataclasses import dataclass

from mempalace.accessor import MemPalaceAccessor

from .worldedit_adapter import PasteCommand, WorldEditAdapter


@dataclass(slots=True)
class BatchResult:
    batch_index: int
    blocks_placed: int
    status: str


class BatchBuilderService:
    def __init__(self, accessor: MemPalaceAccessor, adapter: WorldEditAdapter | None = None):
        self.accessor = accessor
        self.adapter = adapter or WorldEditAdapter()

    def execute(
        self, project_id: str, blueprint_id: str, modules: list[dict], batch_size: int = 500
    ) -> list[BatchResult]:
        results: list[BatchResult] = []
        batch_index = 0
        completed = []

        for module in modules:
            command = self.adapter.build_paste_command(
                PasteCommand(
                    schematic_path=module.get("schematic_path", "unknown.schem"),
                    origin=module["bounds"]["min"],
                )
            )
            _ = command  # dispatch through bot runtime in production
            blocks_placed = len(module["block_data"])
            status = "ok"
            checkpoint = {
                "project_id": project_id,
                "blueprint_id": blueprint_id,
                "batch_index": batch_index,
                "blocks_placed": blocks_placed,
                "status": status,
                "checkpoint_state": {
                    "blueprint_id": blueprint_id,
                    "batch_index": batch_index,
                    "completed_batches": completed + [batch_index],
                    "current_origin": module["bounds"]["min"],
                    "inventory_snapshot": module.get("material_manifest", {}),
                    "retry_count": 0,
                    "last_error": None,
                },
            }
            self.accessor.upsert_build_log(checkpoint)
            completed.append(batch_index)
            results.append(
                BatchResult(batch_index=batch_index, blocks_placed=blocks_placed, status=status)
            )
            batch_index += 1

        return results
