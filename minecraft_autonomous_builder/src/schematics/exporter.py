from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


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


def reconcile_materials(modules: list[dict], expected_manifest: dict[str, int]) -> bool:
    actual: Counter[str] = Counter()
    for m in modules:
        for k, v in m.get("material_manifest", {}).items():
            actual[k] += v
    return dict(actual) == expected_manifest
