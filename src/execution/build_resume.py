from __future__ import annotations

from mempalace.accessor import MemPalaceAccessor


class BuildResumeService:
    def __init__(self, accessor: MemPalaceAccessor):
        self.accessor = accessor

    def resume_from_latest(self, project_id: str) -> dict:
        latest = self.accessor.get_latest_checkpoint(project_id)
        if latest is None:
            return {"resumed": False, "reason": "no_checkpoint"}
        completed = set(latest["checkpoint_state"].get("completed_batches", []))
        return {
            "resumed": True,
            "project_id": project_id,
            "start_from_batch": max(completed) + 1 if completed else 0,
            "checkpoint": latest,
        }
