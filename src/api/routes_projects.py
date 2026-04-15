from __future__ import annotations

from fastapi import APIRouter, Depends

from mempalace.accessor import MemPalaceAccessor, ProjectCreate
from orchestrator.service import OrchestratorService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_accessor() -> MemPalaceAccessor:
    return MemPalaceAccessor()


@router.post("")
def create_project(payload: dict, accessor: MemPalaceAccessor = Depends(get_accessor)) -> dict:
    project = accessor.create_project(ProjectCreate(**payload))
    return {"project_id": project["project_id"], "status": project["status"]}


@router.post("/{project_id}/plan")
def plan_project(project_id: str, accessor: MemPalaceAccessor = Depends(get_accessor)) -> dict:
    orchestrator = OrchestratorService(accessor)
    return orchestrator.run_planning_loop(project_id)


@router.get("/{project_id}/state")
def get_project_state(project_id: str, accessor: MemPalaceAccessor = Depends(get_accessor)) -> dict:
    return {
        "project": accessor.get_project(project_id),
        "blueprints": accessor.get_latest_blueprints(project_id),
        "checkpoint": accessor.get_latest_checkpoint(project_id),
        "vision_critiques": accessor.list_open_vision_critiques(project_id),
    }
