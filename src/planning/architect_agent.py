from __future__ import annotations

import json
import logging
import os
import uuid
from collections import Counter
from pathlib import Path

import httpx
from jsonschema import validate as json_validate

from .planner_io import ArchitectInput, ArchitectOutput

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "blueprint_module.schema.json"
PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "architect_system.md"


def _load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "Generate deterministic, schema-valid blueprint modules for Minecraft."


def _build_architect_prompt(payload: ArchitectInput, modules: list[str], version: int) -> str:
    system = _load_prompt()
    project = payload.project
    reqs = project.get("requirements", {})

    prompt_parts = [
        system,
        "",
        f"Project ID: {project.get('project_id', 'unknown')}",
        f"Project Type: {project.get('project_type', 'unknown')}",
        f"Minecraft Version: {project.get('mc_version', '1.20.4')}",
        f"Blueprint Version: {version}",
        f"Origin: {project.get('origin_xyz', {'x': 0, 'y': 64, 'z': 0})}",
        "",
        f"Required Modules: {', '.join(modules)}",
        f"Style Tags: {', '.join(reqs.get('style', []))}",
        f"Size: {reqs.get('size', 'medium')}",
        f"Redstone Features: {', '.join(reqs.get('redstone_features', []))}",
        "",
    ]

    if payload.open_critiques:
        prompt_parts.append("Open Critiques to address:")
        for c in payload.open_critiques:
            for issue in c.get("issues", []):
                prompt_parts.append(f"  - [{issue['priority']}] {issue['issue_code']}: {issue['message']} (module: {issue['module_name']})")
        prompt_parts.append("")

    if payload.vision_critiques:
        prompt_parts.append("Vision Critiques from previous build:")
        for vc in payload.vision_critiques:
            prompt_parts.append(f"  - Score: {vc.get('vision_score', 'N/A')}, Flagged: {vc.get('flagged_modules', [])}")
            for dd in vc.get("diff_detail", []):
                prompt_parts.append(f"    Module {dd['module_name']}: expected={dd['expected_blocks']}, observed={dd['observed_blocks']}, symmetry={dd['symmetry_score']}")
        prompt_parts.append("")

    if payload.latest_blueprint:
        prompt_parts.append(f"Previous blueprint version {payload.latest_blueprint.get('version', '?')} exists. Improve upon it.")
        prompt_parts.append(f"Change summary from last iteration: {payload.latest_blueprint.get('change_summary', 'N/A')}")
        prompt_parts.append("")

    prompt_parts.extend([
        "Generate block_data for each module. Use appropriate blocks for the project type.",
        "Each module must have:",
        "  - blueprint_id (UUID string)",
        "  - project_id",
        "  - version (integer)",
        "  - module_name",
        "  - bounds (min/max with x,y,z)",
        "  - block_data (array of {x,y,z,block_id} objects, sorted by y then x then z)",
        "  - material_manifest (object mapping block_id to count)",
        "  - quality_score (0-100)",
        "",
        "Output ONLY valid JSON matching this structure:",
        '{"modules": [...], "material_manifest": {...}, "change_summary": "..."}',
    ])

    return "\n".join(prompt_parts)


def _parse_architect_response(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    raw = raw.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first line (```json or ```) and last line (```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return json.loads(raw)


def _validate_module_schema(module: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    json_validate(instance=module, schema=schema)


def _build_real_blocks(module_name: str, project_type: str, index: int, size_hint: str = "medium") -> list[dict]:
    """Fallback deterministic block builder when LLM is unavailable."""
    size_map = {"small": (2, 1, 2), "medium": (4, 3, 4), "large": (6, 5, 6), "xl": (8, 7, 8)}
    w, h, d = size_map.get(size_hint, (4, 3, 4))
    offset_x = index * (w + 2)

    # Project-type-aware block selection
    block_palette = {
        "rocket": {"base": "minecraft:iron_block", "body": "minecraft:white_concrete", "accent": "minecraft:redstone_block", "top": "minecraft:light_blue_concrete"},
        "mansion": {"base": "minecraft:cobblestone", "body": "minecraft:oak_planks", "accent": "minecraft:stone_bricks", "top": "minecraft:spruce_planks"},
        "city": {"base": "minecraft:stone_bricks", "body": "minecraft:bricks", "accent": "minecraft:glass", "top": "minecraft:smooth_stone"},
        "plane": {"base": "minecraft:iron_block", "body": "minecraft:light_gray_concrete", "accent": "minecraft:redstone_lamp", "top": "minecraft:gray_concrete"},
        "weapon": {"base": "minecraft:obsidian", "body": "minecraft:nether_bricks", "accent": "minecraft:redstone_block", "top": "minecraft:ancient_debris"},
    }
    palette = block_palette.get(project_type, {"base": "minecraft:stone", "body": "minecraft:oak_planks", "accent": "minecraft:iron_block", "top": "minecraft:glass"})

    blocks = []
    for y in range(h):
        for x in range(w):
            for z in range(d):
                if y == 0:
                    bid = palette["base"]
                elif y == h - 1:
                    bid = palette["top"]
                elif (x == 0 or x == w - 1 or z == 0 or z == d - 1):
                    bid = palette["accent"] if (x + z) % 4 == 0 else palette["body"]
                else:
                    bid = palette["body"]

                blocks.append({"x": offset_x + x, "y": y, "z": z, "block_id": bid})

    return blocks


class ArchitectAgent:
    """LLM-powered architect agent with deterministic fallback."""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = os.getenv("ARCHITECT_MODEL", "qwen3-14b")
        self._llm_available: bool | None = None

    def _check_llm(self) -> bool:
        if self._llm_available is not None:
            return self._llm_available
        try:
            resp = httpx.get(f"{self.ollama_url}/api/tags", timeout=3.0)
            self._llm_available = resp.status_code == 200
        except Exception:
            self._llm_available = False
        return self._llm_available

    def _call_llm(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 4096},
        }
        resp = httpx.post(f"{self.ollama_url}/api/generate", json=payload, timeout=120.0)
        resp.raise_for_status()
        result = resp.json()
        return result.get("response", "")

    def run(self, payload: ArchitectInput, modules: list[str], version: int) -> ArchitectOutput:
        project_type = payload.project.get("project_type", "unknown")
        size_hint = payload.project.get("requirements", {}).get("size", "medium")

        if self._check_llm():
            try:
                prompt = _build_architect_prompt(payload, modules, version)
                logger.info("Calling LLM for architect (model=%s)", self.model)
                raw_response = self._call_llm(prompt)
                parsed = _parse_architect_response(raw_response)

                blueprint_modules = parsed.get("modules", [])
                # Validate each module against schema
                for mod in blueprint_modules:
                    _validate_module_schema(mod)

                material_counter: Counter[str] = Counter()
                for mod in blueprint_modules:
                    for bid, count in mod.get("material_manifest", {}).items():
                        material_counter[bid] += count

                return ArchitectOutput(
                    blueprint_modules=blueprint_modules,
                    material_manifest=dict(material_counter),
                    coord_proposals=[
                        {"x": b["x"], "y": b["y"], "z": b["z"]}
                        for mod in blueprint_modules for b in mod["block_data"]
                    ],
                    change_summary=parsed.get("change_summary", "LLM-generated blueprint"),
                )
            except Exception as exc:
                logger.warning("LLM call failed (%s), falling back to deterministic planner", exc)

        # Deterministic fallback
        logger.info("Using deterministic planner fallback (model=%s unavailable)", self.model)
        blueprint_modules = []
        material_counter: Counter[str] = Counter()
        coord_proposals = []

        for i, module in enumerate(modules):
            blocks = _build_real_blocks(module, project_type, i, size_hint)
            mat = dict(Counter([b["block_id"] for b in blocks]))
            min_x = min(b["x"] for b in blocks)
            max_x = max(b["x"] for b in blocks)
            min_y = min(b["y"] for b in blocks)
            max_y = max(b["y"] for b in blocks)
            min_z = min(b["z"] for b in blocks)
            max_z = max(b["z"] for b in blocks)

            blueprint_modules.append({
                "blueprint_id": str(uuid.uuid4()),
                "project_id": payload.project["project_id"],
                "version": version,
                "module_name": module,
                "bounds": {
                    "min": {"x": min_x, "y": min_y, "z": min_z},
                    "max": {"x": max_x, "y": max_y, "z": max_z},
                },
                "block_data": blocks,
                "material_manifest": mat,
                "quality_score": 75,
            })
            material_counter.update(Counter([b["block_id"] for b in blocks]))
            coord_proposals.extend([{"x": b["x"], "y": b["y"], "z": b["z"]} for b in blocks])

        return ArchitectOutput(
            blueprint_modules=blueprint_modules,
            material_manifest=dict(material_counter),
            coord_proposals=coord_proposals,
            change_summary=f"Deterministic fallback for {project_type} modules",
        )
