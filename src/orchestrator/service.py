from __future__ import annotations

import logging
import os
from pathlib import Path

from mempalace.accessor import MemPalaceAccessor
from mempalace.repositories import Coord
from planning.architect_agent import ArchitectAgent
from planning.engineer_agent import EngineerAgent
from planning.planner_io import ArchitectInput, EngineerInput
from planning.validators import validate_with_schema

from .convergence_gate import should_approve
from .intent_parser import IntentParser
from .model_runtime import SequentialModelRuntime

logger = logging.getLogger(__name__)

SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"


class OrchestratorService:
    def __init__(self, accessor: MemPalaceAccessor):
        self.accessor = accessor
        self.intent_parser = IntentParser()
        self.architect = ArchitectAgent()
        self.engineer = EngineerAgent()
        self.runtime = SequentialModelRuntime()
        self._previous_quality: float | None = None

    def _validate_blueprint_modules(self, modules: list[dict]) -> None:
        """Validate each module against the blueprint_module JSON schema."""
        schema_path = str(SCHEMA_DIR / "blueprint_module.schema.json")
        for mod in modules:
            validate_with_schema(mod, schema_path)
            logger.debug("Blueprint module '%s' passed schema validation", mod["module_name"])

    def run_planning_loop(self, project_id: str) -> dict:
        project = self.accessor.get_project(project_id)
        modules = project["requirements"].get("required_modules") or []
        if not modules:
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
        latest_blueprint: dict = {}

        for iteration_num in range(max_iterations):
            iteration = self.accessor.increment_iteration(project_id)

            # Sequential load/unload: Architect agent
            with self.runtime.load(os.getenv("ARCHITECT_MODEL", "architect-stub")):
                logger.info("Planning iteration %d: running Architect agent", iteration)
                a_out = self.architect.run(
                    ArchitectInput(
                        project=project,
                        latest_blueprint=latest_blueprint,
                        open_critiques=[],
                        vision_critiques=self.accessor.list_open_vision_critiques(project_id),
                    ),
                    modules=modules,
                    version=iteration,
                )

            # Validate output against schema before persisting
            try:
                self._validate_blueprint_modules(a_out.blueprint_modules)
            except Exception as exc:
                logger.error("Blueprint schema validation failed: %s", exc)
                return {"status": "failed", "reason": f"schema_validation_error: {exc}"}

            # Persist blueprints and reserve coordinates
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

            # Sequential load/unload: Engineer agent
            with self.runtime.load(os.getenv("ENGINEER_MODEL", "engineer-stub")):
                logger.info("Planning iteration %d: running Engineer agent", iteration)
                b_out = self.engineer.run(
                    EngineerInput(
                        project=project,
                        blueprint_modules=a_out.blueprint_modules,
                        material_manifest=a_out.material_manifest,
                        coord_index_snapshot={},
                    ),
                    previous_quality=self._previous_quality,
                )

            self._previous_quality = b_out.quality_score

            critique = self.accessor.insert_critique(
                {
                    "blueprint_id": a_out.blueprint_modules[0]["blueprint_id"] if a_out.blueprint_modules else "none",
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
                    "blueprint_modules": a_out.blueprint_modules,
                }

            latest_blueprint = {
                "version": iteration,
                "module_count": len(a_out.blueprint_modules),
                "change_summary": a_out.change_summary,
            }

            if should_approve(b_out.delta_score, b_out.approval_flag, iteration):
                logger.info("Convergence gate approved at iteration %d", iteration)
                self.accessor.set_project_status(project_id, "approved")
                return {
                    "status": "approved",
                    "iteration": iteration,
                    "quality_score": b_out.quality_score,
                }

        logger.info("Planning loop exhausted after %d iterations, best quality=%s", max_iterations, best["quality_score"])
        self.accessor.set_project_status(project_id, "approved" if best["approved"] else "failed")
        return {"status": "approved" if best["approved"] else "failed", "best": best}

    def trigger_vision_reentry(self, project_id: str, flagged_modules: list[str]) -> dict:
        """Trigger targeted re-entry into the planning loop for flagged modules only.

        Called when vision verification scores below threshold.
        Only regenerates blueprints for the specific flagged modules.
        """
        logger.info("Vision re-entry triggered for project %s, flagged modules: %s",
                     project_id, flagged_modules)

        project = self.accessor.get_project(project_id)
        max_iterations = int(os.getenv("MAX_ITERATIONS", "3"))
        best = {"quality_score": -1, "approved": False, "iteration": 0}

        for iteration_num in range(max_iterations):
            iteration = self.accessor.increment_iteration(project_id)

            # Run architect only for flagged modules
            with self.runtime.load(os.getenv("ARCHITECT_MODEL", "architect-stub")):
                logger.info("Re-entry iteration %d: running Architect for flagged modules", iteration)
                a_out = self.architect.run(
                    ArchitectInput(
                        project=project,
                        latest_blueprint={},
                        open_critiques=[],
                        vision_critiques=self.accessor.list_open_vision_critiques(project_id),
                    ),
                    modules=flagged_modules,
                    version=iteration,
                )

            # Validate and persist
            try:
                self._validate_blueprint_modules(a_out.blueprint_modules)
            except Exception as exc:
                logger.error("Re-entry blueprint schema validation failed: %s", exc)
                continue

            for module in a_out.blueprint_modules:
                self.accessor.insert_blueprint(module)
                coords = [Coord(x=b["x"], y=b["y"], z=b["z"]) for b in module["block_data"]]
                reserve = self.accessor.reserve_coords(
                    project_id, module["module_name"], module["blueprint_id"], coords
                )
                if not reserve.success:
                    logger.warning("Re-entry coordinate collision for module %s", module["module_name"])
                    continue

            # Run engineer validation
            with self.runtime.load(os.getenv("ENGINEER_MODEL", "engineer-stub")):
                b_out = self.engineer.run(
                    EngineerInput(
                        project=project,
                        blueprint_modules=a_out.blueprint_modules,
                        material_manifest=a_out.material_manifest,
                        coord_index_snapshot={},
                    ),
                    previous_quality=self._previous_quality,
                )

            self._previous_quality = b_out.quality_score

            self.accessor.insert_critique({
                "blueprint_id": a_out.blueprint_modules[0]["blueprint_id"] if a_out.blueprint_modules else "none",
                "iteration": iteration,
                "delta_score": b_out.delta_score,
                "issues": b_out.issues,
                "approval_flag": b_out.approval_flag,
                "quality_score": b_out.quality_score,
            })

            if b_out.quality_score > best["quality_score"]:
                best = {
                    "quality_score": b_out.quality_score,
                    "approved": b_out.approval_flag,
                    "iteration": iteration,
                    "blueprint_modules": a_out.blueprint_modules,
                }

            if should_approve(b_out.delta_score, b_out.approval_flag, iteration):
                logger.info("Vision re-entry converged at iteration %d", iteration)
                return {"status": "approved", "iteration": iteration, "quality_score": b_out.quality_score}

        # Exhausted iterations
        if best["approved"]:
            return {"status": "approved", "best": best}
        return {"status": "failed", "best": best}
