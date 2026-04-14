from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class NormalizedPlan:
    modules: list[str]
    redstone_requirements: list[str]
    invariants: list[str]


class BaseProjectBuilder(ABC):
    project_type: str

    @abstractmethod
    def normalize_intent(self, intent: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def emit_required_modules(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def emit_redstone_requirements(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def emit_validation_invariants(self) -> list[str]:
        raise NotImplementedError

    def build_plan(self, intent: dict) -> NormalizedPlan:
        _ = self.normalize_intent(intent)
        return NormalizedPlan(
            modules=self.emit_required_modules(),
            redstone_requirements=self.emit_redstone_requirements(),
            invariants=self.emit_validation_invariants(),
        )


class _SimpleBuilder(BaseProjectBuilder):
    def normalize_intent(self, intent: dict) -> dict:
        intent.setdefault("requirements", {})
        return intent


class RocketBuilder(_SimpleBuilder):
    project_type = "rocket"

    def emit_required_modules(self) -> list[str]:
        return ["launch_pad", "fuel_tanks", "body_stages", "nose_cone", "boosters", "command_bay"]

    def emit_redstone_requirements(self) -> list[str]:
        return ["ignition_sequence", "countdown_lights", "piston_animation_optional"]

    def emit_validation_invariants(self) -> list[str]:
        return ["thrust_axis_contiguous", "fuel_tank_sealed", "command_bay_accessible"]


class MansionBuilder(_SimpleBuilder):
    project_type = "mansion"

    def emit_required_modules(self) -> list[str]:
        return ["foundation_grid", "room_graph", "stair_cores", "facade", "roof", "interiors"]

    def emit_redstone_requirements(self) -> list[str]:
        return ["hidden_doors", "lighting_circuits", "defense_traps_optional"]

    def emit_validation_invariants(self) -> list[str]:
        return ["room_connectivity", "stair_access", "roof_waterproof"]


class CityBuilder(_SimpleBuilder):
    project_type = "city"

    def emit_required_modules(self) -> list[str]:
        return ["road_network", "zoning_blocks", "utilities", "towers", "public_spaces"]

    def emit_redstone_requirements(self) -> list[str]:
        return ["traffic_signals", "rail_dispatch", "timed_lighting"]

    def emit_validation_invariants(self) -> list[str]:
        return ["road_connectivity", "utility_coverage", "zoning_consistency"]


class PlaneBuilder(_SimpleBuilder):
    project_type = "plane"

    def emit_required_modules(self) -> list[str]:
        return ["fuselage", "wings", "tail_assembly", "landing_gear", "cockpit"]

    def emit_redstone_requirements(self) -> list[str]:
        return ["beacon_lights", "retract_simulation", "cockpit_instrumentation"]

    def emit_validation_invariants(self) -> list[str]:
        return ["bilateral_symmetry", "wing_attachment", "gear_clearance"]


class WeaponBuilder(_SimpleBuilder):
    project_type = "weapon"

    def emit_required_modules(self) -> list[str]:
        return ["shell", "mechanism_chamber", "trigger_logic", "ammo_handling", "safety_enclosure"]

    def emit_redstone_requirements(self) -> list[str]:
        return ["tnt_safe_gating", "lockout_states", "cooldown_circuit"]

    def emit_validation_invariants(self) -> list[str]:
        return ["safety_interlock_present", "isolated_testing_mode", "blast_containment"]


BUILDER_MAP = {
    "rocket": RocketBuilder,
    "mansion": MansionBuilder,
    "city": CityBuilder,
    "plane": PlaneBuilder,
    "weapon": WeaponBuilder,
}


def get_builder(project_type: str) -> BaseProjectBuilder:
    try:
        return BUILDER_MAP[project_type]()
    except KeyError as exc:
        raise ValueError(f"unsupported project_type: {project_type}") from exc
