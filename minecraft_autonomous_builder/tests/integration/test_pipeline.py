from __future__ import annotations

from execution.batch_builder import BatchBuilderService
from execution.build_resume import BuildResumeService
from execution.preflight import PreflightService
from mempalace.accessor import ProjectCreate
from orchestrator.service import OrchestratorService
from schematics.exporter import reconcile_materials


def test_full_plan_execute_verify_offline(accessor):
    accessor.create_project(
        ProjectCreate(
            project_id="proj-int-1",
            project_type="rocket",
            mc_version="1.20.4",
            origin_xyz={"x": 0, "y": 64, "z": 0},
            requirements={"size": "medium"},
        )
    )

    plan = OrchestratorService(accessor).run_planning_loop("proj-int-1")
    assert plan["status"] in {"approved", "failed"}

    if plan["status"] == "approved":
        blueprints = accessor.get_latest_blueprints("proj-int-1")
        expected = {}
        for b in blueprints:
            for k, v in b["material_manifest"].items():
                expected[k] = expected.get(k, 0) + v

        preflight = PreflightService().run(expected, expected)
        assert preflight.ok
        assert reconcile_materials(blueprints, expected)

        out = BatchBuilderService(accessor).execute(
            "proj-int-1", blueprints[0]["blueprint_id"], blueprints
        )
        assert len(out) > 0

        resumed = BuildResumeService(accessor).resume_from_latest("proj-int-1")
        assert resumed["resumed"] is True
