from __future__ import annotations

import os

from mempalace.accessor import MemPalaceAccessor
from mempalace.repositories import Coord
from planning.architect_agent import ArchitectAgent
from planning.engineer_agent import EngineerAgent
from planning.planner_io import ArchitectInput, EngineerInput

from .convergence_gate import should_approve
from .intent_parser import IntentParser
from .model_runtime import SequentialModelRuntime


class OrchestratorService:
    def __init__(self, accessor: MemPalaceAccessor):
        self.accessor = accessor
        self.intent_parser = IntentParser()
        self.architect = ArchitectAgent()
        self.engineer = EngineerAgent()
        self.runtime = SequentialModelRuntime()

    def run_planning_loop(self, project_id: str) -> dict:
        project = self.accessor.get_project(project_id)
        modules = project["requirements"].get("required_modules") or []
        if not modules:
            # fallback from normalized intent if not yet embedded
            parsed = self.intent_parser.parse(
                {
                    "project_id": project["project_id"],
                    "project_type": project["project_type"],
                    "mc_version": project["mc_version"],
                    "origin_xyz": project["origin_xyz"],
                    "requirements": project["requirements"],
                }
            )
            modules = parsed["required_modules"]
            project["requirements"].update(
                {
                    "required_modules": modules,
                    "redstone_requirements": parsed["redstone_requirements"],
                    "invariants": parsed["invariants"],
                }
            )

        max_iterations = int(os.getenv("MAX_ITERATIONS", "3"))
        best = {"quality_score": -1, "approved": False, "iteration": 0}

        for _ in range(max_iterations):
            iteration = self.accessor.increment_iteration(project_id)
            with self.runtime.load(os.getenv("ARCHITECT_MODEL", "architect-stub")):
                a_out = self.architect.run(
                    ArchitectInput(
                        project=project,
                        latest_blueprint={},
                        open_critiques=[],
                        vision_critiques=self.accessor.list_open_vision_critiques(project_id),
                    ),
                    modules=modules,
                    version=iteration,
                )

            for module in a_out.blueprint_modules:
                self.accessor.insert_blueprint(module)
                coords = [Coord(x=b["x"], y=b["y"], z=b["z"]) for b in module["block_data"]]
                reserve = self.accessor.reserve_coords(
                    project_id, module["module_name"], module["blueprint_id"], coords
                )
                if not reserve.success:
                    return {
                        "status": "failed",
                        "reason": "coordinate_collision",
                        "collisions": reserve.collisions,
                    }

            with self.runtime.load(os.getenv("ENGINEER_MODEL", "engineer-stub")):
                b_out = self.engineer.run(
                    EngineerInput(
                        project=project,
                        blueprint_modules=a_out.blueprint_modules,
                        material_manifest=a_out.material_manifest,
                        coord_index_snapshot={},
                    )
                )

            critique = self.accessor.insert_critique(
                {
                    "blueprint_id": a_out.blueprint_modules[0]["blueprint_id"],
                    "iteration": iteration,
                    "delta_score": b_out.delta_score,
                    "issues": b_out.issues,
                    "approval_flag": b_out.approval_flag,
                    "quality_score": b_out.quality_score,
                }
            )

            if b_out.quality_score > best["quality_score"]:
                best = {
                    "quality_score": b_out.quality_score,
                    "approved": b_out.approval_flag,
                    "iteration": iteration,
                    "critique": critique,
                }

            if should_approve(b_out.delta_score, b_out.approval_flag, iteration):
                self.accessor.set_project_status(project_id, "approved")
                return {
                    "status": "approved",
                    "iteration": iteration,
                    "quality_score": b_out.quality_score,
                }

        self.accessor.set_project_status(project_id, "approved" if best["approved"] else "failed")
        return {"status": "approved" if best["approved"] else "failed", "best": best}
