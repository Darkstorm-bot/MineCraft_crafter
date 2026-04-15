from __future__ import annotations

import json
import logging
import os

import httpx
from jsonschema import validate as json_validate

from .planner_io import EngineerInput, EngineerOutput

logger = logging.getLogger(__name__)

SCHEMA_PATH = (
    __import__("pathlib").Path(__file__).resolve().parent.parent.parent
    / "schemas"
    / "critique.schema.json"
)

PRIORITY_WEIGHTS = {"P0": 40.0, "P1": 25.0, "P2": 10.0, "P3": 5.0}

_ENGINEER_PROMPT_PATH = (
    __import__("pathlib").Path(__file__).resolve().parent.parent.parent
    / "prompts"
    / "engineer_system.md"
)


def _load_engineer_prompt() -> str:
    try:
        return _ENGINEER_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "Validate blueprint quality and safety. Output strict JSON."


def _build_engineer_prompt(payload: EngineerInput) -> str:
    system = _load_engineer_prompt()
    project = payload.project
    project_id = project.get("project_id", "unknown")
    project_type = project.get("project_type", "unknown")
    mc_version = project.get("mc_version", "1.20.4")

    prompt_parts = [
        system,
        "",
        f"Project: {project_id} (type={project_type}, mc_version={mc_version})",
        "",
        f"Number of blueprint modules: {len(payload.blueprint_modules)}",
        "",
    ]

    for mod in payload.blueprint_modules:
        block_count = len(mod.get("block_data", []))
        bounds = mod.get("bounds", {})
        mat = mod.get("material_manifest", {})
        prompt_parts.extend([
            f"Module: {mod['module_name']}",
            f"  Blocks: {block_count}",
            f"  Bounds: {bounds}",
            f"  Materials: {len(mat)} unique types",
            f"  Quality Score (self-reported): {mod.get('quality_score', 'N/A')}",
            "",
        ])

    prompt_parts.extend([
        "Perform these validation checks:",
        "1. Structural integrity: blocks must have contiguous support (no floating blocks without support below)",
        "2. Material feasibility: all block_ids must be valid Minecraft blocks",
        "3. Bounds consistency: all block coordinates must fall within declared bounds",
        "4. Redstone safety: redstone components must have proper power sources",
        "5. Coordinate conflicts: no duplicate (x,y,z) positions across modules",
        "",
        "Output ONLY valid JSON matching this structure:",
        '{"delta_score": <number 0-100>, "issues": [{"issue_code": "string", "priority": "P0|P1|P2|P3", "message": "string", "module_name": "string", "suggested_fix": "string"}], "approval_flag": <boolean>, "quality_score": <number 0-100>}',
    ])

    return "\n".join(prompt_parts)


def _validate_block_ids(modules: list[dict]) -> list[dict]:
    """Check for obviously invalid block IDs."""
    issues = []
    valid_prefixes = {"minecraft:", "create:", "mekanism:", "thermal:", "immersiveengineering:"}
    for mod in modules:
        for block in mod.get("block_data", []):
            bid = block.get("block_id", "")
            if not any(bid.startswith(p) for p in valid_prefixes):
                # Allow bare block IDs like "stone" but flag them
                if ":" not in bid:
                    issues.append({
                        "issue_code": "BARE_BLOCK_ID",
                        "priority": "P2",
                        "message": f"Block '{bid}' missing namespace in module '{mod['module_name']}'",
                        "module_name": mod["module_name"],
                        "suggested_fix": f"Prefix with 'minecraft:' -> 'minecraft:{bid}'",
                    })
                    break  # One warning per module
    return issues


def _validate_bounds(modules: list[dict]) -> list[dict]:
    """Verify all block coordinates fall within declared bounds."""
    issues = []
    for mod in modules:
        bounds = mod.get("bounds", {})
        if not bounds:
            continue
        bmin = bounds.get("min", {})
        bmax = bounds.get("max", {})
        for block in mod.get("block_data", []):
            bx, by, bz = block.get("x", 0), block.get("y", 0), block.get("z", 0)
            if (bx < bmin.get("x", -999999) or bx > bmax.get("x", 999999) or
                by < bmin.get("y", -999999) or by > bmax.get("y", 999999) or
                bz < bmin.get("z", -999999) or bz > bmax.get("z", 999999)):
                issues.append({
                    "issue_code": "BOUNDS_OVERFLOW",
                    "priority": "P1",
                    "message": f"Block at ({bx},{by},{bz}) outside bounds in module '{mod['module_name']}'",
                    "module_name": mod["module_name"],
                    "suggested_fix": "Expand bounds or reposition block",
                })
                break  # One warning per module
    return issues


def _validate_coord_conflicts(modules: list[dict]) -> list[dict]:
    """Check for duplicate coordinates across modules."""
    issues = []
    seen: dict[tuple[int, int, int], str] = {}
    for mod in modules:
        for block in mod.get("block_data", []):
            key = (block.get("x", 0), block.get("y", 0), block.get("z", 0))
            if key in seen and seen[key] != mod["module_name"]:
                issues.append({
                    "issue_code": "CROSS_MODULE_COLLISION",
                    "priority": "P0",
                    "message": f"Coordinate {key} claimed by both '{seen[key]}' and '{mod['module_name']}'",
                    "module_name": mod["module_name"],
                    "suggested_fix": f"Offset one of the modules to avoid overlap at {key}",
                })
                break
            seen[key] = mod["module_name"]
    return issues


def _validate_redstone_safety(modules: list[dict]) -> list[dict]:
    """Basic redstone safety checks."""
    issues = []
    redstone_blocks = {"redstone_block", "redstone_torch", "repeater", "comparator", "redstone_wire", "redstone_lamp"}
    for mod in modules:
        has_redstone = False
        has_power = False
        for block in mod.get("block_data", []):
            bid = block.get("block_id", "")
            if any(rb in bid for rb in redstone_blocks):
                has_redstone = True
            if "redstone_block" in bid or "lever" in bid or "button" in bid:
                has_power = True
        if has_redstone and not has_power:
            issues.append({
                "issue_code": "REDSTONE_UNPOWERED",
                "priority": "P1",
                "message": f"Module '{mod['module_name']}' has redstone components but no visible power source",
                "module_name": mod["module_name"],
                "suggested_fix": "Add a power source (redstone_block, lever, or button)",
            })
    return issues


def _compute_quality(modules: list[dict], issues: list[dict]) -> float:
    """Compute quality score based on issue severity and module completeness."""
    score = 100.0
    for issue in issues:
        weight = PRIORITY_WEIGHTS.get(issue["priority"], 5.0)
        score -= weight
    # Penalize empty modules
    for mod in modules:
        if not mod.get("block_data"):
            score -= 20.0
    # Penalize small modules (less than 10 blocks)
    for mod in modules:
        if 0 < len(mod.get("block_data", [])) < 10:
            score -= 5.0
    return max(0.0, min(100.0, score))


def _compute_delta(previous_score: float | None, current_score: float) -> float:
    """Compute delta between previous and current quality scores."""
    if previous_score is None:
        return 0.0
    return abs(current_score - previous_score)


def _parse_engineer_response(raw: str) -> dict:
    """Extract JSON from LLM response."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return json.loads(raw)


def _validate_critique_schema(output: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    json_validate(instance=output, schema=schema)


class EngineerAgent:
    """LLM-powered engineer validator with deterministic fallback checks."""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = os.getenv("ENGINEER_MODEL", "qwen3-14b")
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
            "options": {"temperature": 0.1, "num_predict": 2048},
        }
        resp = httpx.post(f"{self.ollama_url}/api/generate", json=payload, timeout=120.0)
        resp.raise_for_status()
        result = resp.json()
        return result.get("response", "")

    def run(self, payload: EngineerInput, previous_quality: float | None = None) -> EngineerOutput:
        # Always run deterministic checks
        issues: list[dict] = []
        issues.extend(_validate_block_ids(payload.blueprint_modules))
        issues.extend(_validate_bounds(payload.blueprint_modules))
        issues.extend(_validate_coord_conflicts(payload.blueprint_modules))
        issues.extend(_validate_redstone_safety(payload.blueprint_modules))

        if not payload.blueprint_modules:
            issues.append({
                "issue_code": "EMPTY_BLUEPRINT",
                "priority": "P0",
                "message": "No modules generated",
                "module_name": "global",
                "suggested_fix": "Regenerate blueprint modules",
            })

        # Compute deterministic quality
        quality_score = _compute_quality(payload.blueprint_modules, issues)
        delta_score = _compute_delta(previous_quality, quality_score)
        # Auto-approve if no P0/P1 issues
        approval_flag = not any(i["priority"] in ("P0", "P1") for i in issues)

        # Try LLM enrichment if available
        if self._check_llm() and payload.blueprint_modules:
            try:
                prompt = _build_engineer_prompt(payload)
                logger.info("Calling LLM for engineer validation (model=%s)", self.model)
                raw_response = self._call_llm(prompt)
                parsed = _parse_engineer_response(raw_response)

                # Validate LLM output against critique schema
                _validate_critique_schema(parsed)

                # Merge LLM issues with deterministic ones (deduplicate by issue_code+module_name)
                seen_keys = {(i["issue_code"], i["module_name"]) for i in issues}
                for llm_issue in parsed.get("issues", []):
                    key = (llm_issue["issue_code"], llm_issue["module_name"])
                    if key not in seen_keys:
                        issues.append(llm_issue)
                        seen_keys.add(key)

                # Use LLM scores if they are reasonable
                llm_quality = parsed.get("quality_score")
                llm_delta = parsed.get("delta_score")
                llm_approval = parsed.get("approval_flag")

                if llm_quality is not None:
                    quality_score = llm_quality
                if llm_delta is not None:
                    delta_score = llm_delta
                if llm_approval is not None:
                    approval_flag = llm_approval

                logger.info("LLM engineer validation complete: quality=%s, delta=%s, approved=%s",
                            quality_score, delta_score, approval_flag)

            except Exception as exc:
                logger.warning("LLM engineer call failed (%s), using deterministic results", exc)

        return EngineerOutput(
            delta_score=delta_score,
            issues=issues,
            approval_flag=approval_flag,
            quality_score=quality_score,
        )
