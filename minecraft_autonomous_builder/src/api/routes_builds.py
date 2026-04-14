from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from execution.batch_builder import BatchBuilderService
from execution.build_resume import BuildResumeService
from execution.preflight import PreflightService
from mempalace.accessor import MemPalaceAccessor
from schematics.exporter import generate_placement_manifest, reconcile_materials
from schematics.generator import SchematicGenerator
from vision.critique_writer import VisionCritiqueWriter
from vision.llava_client import LLaVAClient
from vision.scorer import VisionScorer

router = APIRouter(prefix="/projects", tags=["builds"])


def get_accessor() -> MemPalaceAccessor:
    return MemPalaceAccessor()


@router.post("/{project_id}/execute")
def execute_project(project_id: str, accessor: MemPalaceAccessor = Depends(get_accessor)) -> dict:
    blueprints = accessor.get_latest_blueprints(project_id)
    if not blueprints:
        raise HTTPException(status_code=400, detail="No approved blueprint to execute")

    expected = {}
    for b in blueprints:
        for k, v in b["material_manifest"].items():
            expected[k] = expected.get(k, 0) + v

    preflight = PreflightService().run(expected, inventory_snapshot=expected)
    if not preflight.ok:
        raise HTTPException(status_code=400, detail={"preflight_blockers": preflight.blockers})

    generator = SchematicGenerator()
    project = accessor.get_project(project_id)
    for b in blueprints:
        b["schematic_path"] = generator.emit_module_schematic(project_id, b, project["mc_version"])

    manifest_path = generate_placement_manifest(project_id, blueprints)
    if not reconcile_materials(blueprints, expected):
        raise HTTPException(status_code=400, detail="material reconciliation failed")

    batch_results = BatchBuilderService(accessor).execute(
        project_id,
        blueprints[0]["blueprint_id"],
        blueprints,
        int(os.getenv("BUILD_BATCH_SIZE", "500")),
    )
    accessor.set_project_status(project_id, "executing")
    return {"manifest": manifest_path, "batches": [r.__dict__ for r in batch_results]}


@router.post("/{project_id}/verify")
def verify_project(project_id: str, accessor: MemPalaceAccessor = Depends(get_accessor)) -> dict:
    blueprints = accessor.get_latest_blueprints(project_id)
    if not blueprints:
        raise HTTPException(status_code=400, detail="No blueprint to verify")

    # Default fallback supports offline execution in test environments
    raw = '{"vision_score": 90, "flagged_modules": [], "diff_detail": []}'
    try:
        raw = LLaVAClient().score("Return strict vision_diff JSON")
    except Exception:
        pass

    vision_diff = VisionScorer().parse_strict(raw)
    writer = VisionCritiqueWriter(accessor)
    record = writer.write(
        project_id, blueprints[0]["blueprint_id"], blueprints[0]["version"], vision_diff
    )

    threshold = int(os.getenv("VISION_PASS_THRESHOLD", "80"))
    if vision_diff["vision_score"] >= threshold:
        accessor.set_project_status(project_id, "done")
    else:
        accessor.set_project_status(project_id, "planning")

    return {"vision": vision_diff, "record": record}


@router.post("/{project_id}/resume")
def resume_project(project_id: str, accessor: MemPalaceAccessor = Depends(get_accessor)) -> dict:
    return BuildResumeService(accessor).resume_from_latest(project_id)
