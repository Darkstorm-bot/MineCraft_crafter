from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

try:
    import mcschematic
except ImportError:
    mcschematic = None

logger = logging.getLogger(__name__)


def generate_placement_manifest(project_id: str, modules: list[dict]) -> str:
    manifest = {
        "project_id": project_id,
        "order": [m["module_name"] for m in modules],
        "modules": [
            {
                "module_name": m["module_name"],
                "blueprint_id": m["blueprint_id"],
                "version": m["version"],
                "origin": m.get("bounds", {}).get("min", {"x": 0, "y": 0, "z": 0}),
            }
            for m in modules
        ],
    }
    out = Path("data/schematics") / project_id / "placement_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return str(out)


def reconcile_materials(modules: list[dict], expected_manifest: dict[str, int]) -> dict:
    """Compare actual vs expected materials. Returns {missing, excess, ok}."""
    actual: Counter[str] = Counter()
    for m in modules:
        for k, v in m.get("material_manifest", {}).items():
            actual[k] += v

    expected = Counter(expected_manifest)
    missing = {}
    excess = {}
    for block_id, count in expected.items():
        if actual[block_id] < count:
            missing[block_id] = count - actual[block_id]
        elif actual[block_id] > count:
            excess[block_id] = actual[block_id] - count
    for block_id, count in actual.items():
        if block_id not in expected:
            excess[block_id] = count

    return {"missing": missing, "excess": excess, "is_balanced": not missing and not excess}


def generate_merged_schematic(project_id: str, modules: list[dict], schematic_dir: Path | None = None) -> str:
    """Merge all module block_data into a single schematic file.

    Blocks are deterministically sorted by y, then x, then z.
    Falls back to JSON merge if mcschematic is not installed.
    """
    out_dir = schematic_dir or (Path("data/schematics") / project_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    merged_path = out_dir / "merged_project.schem"

    # Collect all blocks from all modules, deterministically sorted
    all_blocks: list[dict] = []
    for mod in modules:
        sorted_blocks = sorted(mod["block_data"], key=lambda b: (b["y"], b["x"], b["z"]))
        all_blocks.extend(sorted_blocks)

    # Final sort across all modules
    all_blocks.sort(key=lambda b: (b["y"], b["x"], b["z"]))

    # Deduplicate: if two modules claim the same coord, last one wins
    seen: dict[tuple[int, int, int], dict] = {}
    for b in all_blocks:
        seen[(b["x"], b["y"], b["z"])] = b
    unique_blocks = list(seen.values())
    unique_blocks.sort(key=lambda b: (b["y"], b["x"], b["z"]))

    logger.info("Merged schematic: %d blocks from %d modules (%d unique)",
                len(all_blocks), len(modules), len(unique_blocks))

    if mcschematic is None:
        # Fallback: write merged block data as JSON
        merged_path = merged_path.with_suffix(".json")
        merged_path.write_text(
            json.dumps({"blocks": unique_blocks, "module_count": len(modules)}, indent=2),
            encoding="utf-8",
        )
        logger.warning("mcschematic not installed; wrote merged JSON fallback to %s", merged_path)
        return str(merged_path)

    # Build real merged schematic
    merged_schem = mcschematic.MCSchematic()
    for b in unique_blocks:
        merged_schem.setBlock((b["x"], b["y"], b["z"]), b["block_id"])

    # Map mc_version from first module or default
    version_tag = mcschematic.Version.JE_1_20_1
    merged_schem.save(str(out_dir), "merged_project", version_tag)

    real_path = out_dir / "merged_project.schem"
    logger.info("Merged schematic written: %s", real_path)
    return str(real_path)
