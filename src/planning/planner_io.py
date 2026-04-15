from __future__ import annotations

from pydantic import BaseModel, Field


class ArchitectInput(BaseModel):
    project: dict
    latest_blueprint: dict = Field(default_factory=dict)
    open_critiques: list[dict] = Field(default_factory=list)
    vision_critiques: list[dict] = Field(default_factory=list)
    scale_reference: dict = Field(default_factory=dict)
    mc_version_rules: dict = Field(default_factory=dict)


class ArchitectOutput(BaseModel):
    blueprint_modules: list[dict]
    material_manifest: dict[str, int]
    coord_proposals: list[dict]
    change_summary: str


class EngineerInput(BaseModel):
    project: dict
    blueprint_modules: list[dict]
    material_manifest: dict[str, int]
    coord_index_snapshot: dict


class EngineerOutput(BaseModel):
    delta_score: float
    issues: list[dict]
    approval_flag: bool
    quality_score: float
