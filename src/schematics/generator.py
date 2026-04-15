from __future__ import annotations

import json
from pathlib import Path

import yaml

try:
    import mcschematic
except ImportError:  # pragma: no cover - optional in lightweight test env
    mcschematic = None


class BlockCompatibilityValidator:
    def __init__(
        self,
        versions_path: str = "configs/minecraft_versions.yaml",
        alias_path: str = "configs/block_aliases_1_20.yaml",
    ):
        self.version_cfg = yaml.safe_load(Path(versions_path).read_text(encoding="utf-8"))
        self.aliases = yaml.safe_load(Path(alias_path).read_text(encoding="utf-8")).get(
            "aliases", {}
        )

    def normalize(self, block_id: str) -> str:
        return self.aliases.get(block_id, block_id)

    def validate(self, mc_version: str, blocks: list[dict]) -> None:
        version_data = self.version_cfg["versions"].get(mc_version)
        if not version_data:
            raise ValueError(f"Unknown Minecraft version: {mc_version}")

        allowed_raw = version_data.get("allowed_prefixes", [])
        # Ensure allowed_prefixes is a list of strings
        allowed = [str(p) for p in allowed_raw] if allowed_raw else []
        denied_raw = version_data.get("deny_blocks", [])
        denied = set(str(d) for d in denied_raw) if denied_raw else set()

        for b in blocks:
            bid = self.normalize(b["block_id"])
            if bid in denied or not any(bid.startswith(p) for p in allowed):
                raise ValueError(f"Incompatible block for {mc_version}: {bid}")


class SchematicGenerator:
    def __init__(self):
        self.validator = BlockCompatibilityValidator()

    def emit_module_schematic(self, project_id: str, module: dict, mc_version: str) -> str:
        blocks = sorted(module["block_data"], key=lambda p: (p["y"], p["x"], p["z"]))
        self.validator.validate(mc_version, blocks)
        out_dir = Path("data/schematics") / project_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{module['module_name']}_v{module['version']}.schem"

        if mcschematic is None:
            path.write_text(json.dumps(blocks), encoding="utf-8")
            return str(path)

        schem = mcschematic.MCSchematic()
        for b in blocks:
            schem.setBlock((b["x"], b["y"], b["z"]), b["block_id"])
        schem.save(
            str(out_dir),
            f"{module['module_name']}_v{module['version']}",
            mcschematic.Version.JE_1_20_1,
        )
        return str(path)
