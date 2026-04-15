from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---- Redstone component block definitions ----

REDSTONE_BLOCKS = {
    # Power sources
    "redstone_block": {"power_level": 15, "type": "source"},
    "redstone_torch": {"power_level": 15, "type": "source"},
    "lever": {"power_level": 15, "type": "toggle"},
    "stone_button": {"power_level": 15, "type": "pulse"},
    "oak_button": {"power_level": 15, "type": "pulse"},
    # Transmission
    "redstone_wire": {"power_level": 15, "type": "wire"},
    "redstone_lamp": {"power_level": 0, "type": "receiver"},
    # Logic
    "repeater": {"power_level": 15, "type": "delay"},
    "comparator": {"power_level": 15, "type": "compare"},
    # Output devices
    "piston": {"power_level": 0, "type": "actuator"},
    "sticky_piston": {"power_level": 0, "type": "actuator"},
    "dispenser": {"power_level": 0, "type": "actuator"},
    "dropper": {"power_level": 0, "type": "actuator"},
    "note_block": {"power_level": 0, "type": "actuator"},
    "door": {"power_level": 0, "type": "actuator"},
    "trapdoor": {"power_level": 0, "type": "actuator"},
    "fence_gate": {"power_level": 0, "type": "actuator"},
    "rail": {"power_level": 0, "type": "actuator"},
    "powered_rail": {"power_level": 0, "type": "actuator"},
    "tnt": {"power_level": 0, "type": "hazardous"},
}


def load_redstone_templates(path: str = "configs/redstone_components.yaml") -> dict:
    """Load redstone component templates from YAML config."""
    p = Path(path)
    if p.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _make_block(x: int, y: int, z: int, block_id: str, state: dict | None = None) -> dict:
    b: dict[str, Any] = {"x": x, "y": y, "z": z, "block_id": block_id}
    if state:
        b["state"] = state
    return b


def generate_redstone_circuit(
    circuit_type: str,
    origin: tuple[int, int, int],
    length: int = 4,
    config: dict | None = None,
) -> list[dict]:
    """Generate a redstone circuit layout starting at origin.

    Supported circuit types:
    - 'line': Simple redstone wire line with torches at end
    - 'repeater_chain': Repeater delay chain
    - 'clock': Redstone clock (pulse generator)
    - 'countdown': Sequential light countdown (3 stages)
    - 'ignition_sequence': TNT-safe ignition with gating (rocket/weapon)
    - 'traffic_signal': Timed district signal (city)
    """
    x, y, z = origin
    blocks: list[dict] = []
    cfg = config or {}

    if circuit_type == "line":
        # Simple redstone wire line
        for i in range(length):
            blocks.append(_make_block(x + i, y, z, "minecraft:redstone_wire"))
        # Torch at start
        blocks.append(_make_block(x, y - 1, z, "minecraft:redstone_torch"))
        # Torch at end
        blocks.append(_make_block(x + length, y, z, "minecraft:redstone_torch"))

    elif circuit_type == "repeater_chain":
        delay = cfg.get("delay_ticks", 2)
        for i in range(length):
            blocks.append(_make_block(x + i, y, z, "minecraft:redstone_wire"))
            if i > 0 and i < length - 1:
                blocks.append(_make_block(
                    x + i, y, z, "minecraft:repeater",
                    {"delay": delay, "facing": "north"},
                ))

    elif circuit_type == "clock":
        # Simple 5-clock pulse generator
        blocks.append(_make_block(x, y, z, "minecraft:comparator"))
        blocks.append(_make_block(x + 1, y, z, "minecraft:redstone_wire"))
        blocks.append(_make_block(x + 2, y, z, "minecraft:repeater", {"delay": 2}))
        blocks.append(_make_block(x + 3, y, z, "minecraft:redstone_wire"))
        blocks.append(_make_block(x + 4, y, z, "minecraft:comparator"))
        # Feedback wire
        blocks.append(_make_block(x + 4, y, z + 1, "minecraft:redstone_wire"))
        blocks.append(_make_block(x + 3, y, z + 1, "minecraft:redstone_wire"))
        blocks.append(_make_block(x + 2, y, z + 1, "minecraft:redstone_wire"))
        blocks.append(_make_block(x + 1, y, z + 1, "minecraft:redstone_wire"))
        blocks.append(_make_block(x, y, z + 1, "minecraft:redstone_wire"))

    elif circuit_type == "countdown":
        # 3-stage countdown lights (green -> yellow -> red)
        colors = [
            "minecraft:lime_concrete",   # green
            "minecraft:yellow_concrete", # yellow
            "minecraft:red_concrete",    # red
        ]
        for i, color in enumerate(colors):
            # Light block
            blocks.append(_make_block(x, y + i, z, color))
            # Redstone lamp behind it
            blocks.append(_make_block(x + 1, y + i, z, "minecraft:redstone_lamp"))
            # Repeater chain for timing
            blocks.append(_make_block(x + 2, y + i, z, "minecraft:repeater", {"delay": i + 1}))
            # Wire connecting them
            blocks.append(_make_block(x + 3, y + i, z, "minecraft:redstone_wire"))

    elif circuit_type == "ignition_sequence":
        # TNT-safe ignition with safety gating
        # Safety lever
        blocks.append(_make_block(x, y, z, "minecraft:lever", {"facing": "north", "powered": "false"}))
        # Safety gate (requires lever ON)
        blocks.append(_make_block(x + 1, y, z, "minecraft:redstone_wire"))
        blocks.append(_make_block(x + 2, y, z, "minecraft:repeater", {"delay": 3}))
        # Countdown lights
        for i, color in enumerate(["minecraft:green_concrete", "minecraft:yellow_concrete", "minecraft:red_concrete"]):
            blocks.append(_make_block(x + 3, y + i, z, color))
            blocks.append(_make_block(x + 4, y + i, z, "minecraft:redstone_lamp"))
        # Ignition point (TNT with safety enclosure)
        blocks.append(_make_block(x + 5, y, z, "minecraft:tnt"))
        # Obsidian safety enclosure
        for dy in range(3):
            for dz in range(3):
                if dz != 1 or dy != 1:  # Leave center open
                    blocks.append(_make_block(x + 5, y + dy, z + dz - 1, "minecraft:obsidian"))

    elif circuit_type == "traffic_signal":
        # Timed lighting districts for city
        for i in range(4):
            # Street light pole
            blocks.append(_make_block(x + i * 6, y, z, "minecraft:iron_block"))
            blocks.append(_make_block(x + i * 6, y + 1, z, "minecraft:iron_block"))
            blocks.append(_make_block(x + i * 6, y + 2, z, "minecraft:iron_block"))
            # Signal head (red/green alternating)
            if i % 2 == 0:
                blocks.append(_make_block(x + i * 6, y + 3, z, "minecraft:red_concrete"))
                blocks.append(_make_block(x + i * 6, y + 3, z, "minecraft:redstone_lamp"))
            else:
                blocks.append(_make_block(x + i * 6, y + 3, z, "minecraft:lime_concrete"))
                blocks.append(_make_block(x + i * 6, y + 3, z, "minecraft:redstone_lamp"))
            # Redstone wiring
            blocks.append(_make_block(x + i * 6, y + 1, z + 1, "minecraft:redstone_wire"))
            blocks.append(_make_block(x + i * 6, y + 1, z + 2, "minecraft:redstone_block"))

    else:
        logger.warning("Unknown redstone circuit type: %s, generating simple line", circuit_type)
        for i in range(length):
            blocks.append(_make_block(x + i, y, z, "minecraft:redstone_wire"))
        blocks.append(_make_block(x, y - 1, z, "minecraft:redstone_torch"))

    return blocks


def generate_project_redstone(
    project_type: str,
    origin: tuple[int, int, int],
    config: dict | None = None,
) -> list[dict]:
    """Generate all redstone circuits required for a project type.

    Maps project type -> required circuits per AGENT.md spec.
    """
    all_blocks: list[dict] = []
    cfg = config or {}
    ox, oy, oz = origin

    redstone_map = {
        "rocket": [
            ("ignition_sequence", (ox, oy, oz), cfg.get("ignition", {})),
            ("countdown", (ox + 8, oy, oz), cfg.get("countdown", {})),
            ("line", (ox, oy + 4, oz), {"length": 6}),
        ],
        "mansion": [
            ("line", (ox, oy, oz), {"length": 8}),
            ("repeater_chain", (ox + 10, oy, oz), {"delay_ticks": 2, "length": 4}),
            ("clock", (ox + 20, oy, oz), {}),
        ],
        "city": [
            ("traffic_signal", (ox, oy, oz), {}),
            ("line", (ox + 30, oy, oz), {"length": 12}),
        ],
        "plane": [
            ("line", (ox, oy, oz), {"length": 6}),
            ("countdown", (ox + 8, oy, oz), {}),
            ("repeater_chain", (ox + 14, oy, oz), {"delay_ticks": 1, "length": 3}),
        ],
        "weapon": [
            ("ignition_sequence", (ox, oy, oz), cfg.get("ignition", {})),
            ("clock", (ox + 10, oy, oz), {}),
        ],
    }

    circuits = redstone_map.get(project_type, [])
    for circuit_type, circ_origin, circuit_cfg in circuits:
        blocks = generate_redstone_circuit(circuit_type, circ_origin, config=circuit_cfg)
        all_blocks.extend(blocks)
        logger.debug("Generated redstone circuit '%s' for %s: %d blocks",
                      circuit_type, project_type, len(blocks))

    return all_blocks


def validate_redstone_safety(blocks: list[dict]) -> list[dict]:
    """Validate redstone circuit safety rules.

    Returns list of safety issues found.
    """
    issues = []
    has_tnt = False
    has_safety_gate = False
    has_lockout = False

    for b in blocks:
        bid = b.get("block_id", "")
        if "tnt" in bid:
            has_tnt = True
        if "obsidian" in bid:
            has_safety_gate = True
        if "lever" in bid or "button" in bid:
            has_lockout = True

    if has_tnt and not has_safety_gate:
        issues.append({
            "issue_code": "TNT_UNENCLOSED",
            "priority": "P0",
            "message": "TNT detected but no obsidian safety enclosure found",
            "module_name": "redstone",
            "suggested_fix": "Add obsidian enclosure around TNT to prevent chain detonation",
        })

    if has_tnt and not has_lockout:
        issues.append({
            "issue_code": "TNT_NO_LOCKOUT",
            "priority": "P0",
            "message": "TNT detected but no manual lockout switch (lever/button)",
            "module_name": "redstone",
            "suggested_fix": "Add a lever or button as manual safety lockout",
        })

    return issues
