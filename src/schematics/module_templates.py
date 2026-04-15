from __future__ import annotations

import uuid
from typing import Any


def _block(x: int, y: int, z: int, bid: str, state: dict | None = None) -> dict:
    b: dict[str, Any] = {"x": x, "y": y, "z": z, "block_id": bid}
    if state:
        b["state"] = state
    return b


def simple_cube(
    module_name: str,
    material: str = "minecraft:stone",
    width: int = 3,
    height: int = 2,
    depth: int = 3,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a solid rectangular cube of blocks."""
    ox, oy, oz = offset
    blocks = []
    for y in range(height):
        for x in range(width):
            for z in range(depth):
                blocks.append(_block(ox + x, oy + y, oz + z, material))
    return blocks


def hollow_box(
    module_name: str,
    wall_material: str = "minecraft:stone_bricks",
    floor_material: str = "minecraft:cobblestone",
    width: int = 5,
    height: int = 3,
    depth: int = 5,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a hollow box with distinct floor material."""
    ox, oy, oz = offset
    blocks = []
    for y in range(height):
        for x in range(width):
            for z in range(depth):
                is_wall = (x == 0 or x == width - 1 or z == 0 or z == depth - 1)
                is_floor = (y == 0)
                if is_floor:
                    blocks.append(_block(ox + x, oy + y, oz + z, floor_material))
                elif is_wall:
                    blocks.append(_block(ox + x, oy + y, oz + z, wall_material))
    return blocks


def pillar(
    module_name: str,
    material: str = "minecraft:oak_log",
    height: int = 5,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a vertical pillar."""
    ox, oy, oz = offset
    return [_block(ox, oy + y, oz, material) for y in range(height)]


def staircase(
    module_name: str,
    material: str = "minecraft:oak_stairs",
    length: int = 5,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a staircase going up in +x direction."""
    ox, oy, oz = offset
    blocks = []
    for i in range(length):
        # Each step: full width platform at this height
        for z in range(3):
            facing = "north" if i % 2 == 0 else "south"
            blocks.append(_block(ox + i, oy + i, oz + z, material, {"facing": facing, "half": "bottom"}))
        # Filler block underneath
        for z in range(3):
            blocks.append(_block(ox + i, oy + i - 1, oz + z, "minecraft:cobblestone"))
    return blocks


def roof_gable(
    module_name: str,
    material: str = "minecraft:spruce_stairs",
    width: int = 7,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a gable roof (A-frame) across +x with peak in center."""
    ox, oy, oz = offset
    blocks = []
    half = width // 2
    for x in range(width):
        # Distance from center determines height
        dist = abs(x - half)
        height = half - dist + 1
        for y in range(height):
            # Left slope
            facing = "east" if x <= half else "west"
            blocks.append(_block(ox + x, oy + y, oz, material, {"facing": facing, "half": "bottom"}))
            # Right slope
            blocks.append(_block(ox + x, oy + y, oz + 4, material, {"facing": facing, "half": "bottom"}))
            # Fill interior at peak level
            if y == height - 1 and 0 < x < width - 1:
                for z in range(1, 5):
                    blocks.append(_block(ox + x, oy + y, oz + z, "minecraft:spruce_planks"))
    return blocks


def room_grid(
    module_name: str,
    room_width: int = 5,
    room_depth: int = 5,
    room_height: int = 3,
    num_rooms_x: int = 3,
    num_rooms_z: int = 2,
    wall_material: str = "minecraft:oak_planks",
    floor_material: str = "minecraft:stone_bricks",
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a grid of rooms with shared walls (mansion layout)."""
    ox, oy, oz = offset
    blocks = []
    spacing_x = room_width + 1  # +1 for wall thickness
    spacing_z = room_depth + 1

    for rx in range(num_rooms_x):
        for rz in range(num_rooms_z):
            base_x = ox + rx * spacing_x
            base_z = oz + rz * spacing_z

            # Floor
            for x in range(room_width):
                for z in range(room_depth):
                    blocks.append(_block(base_x + x, oy, base_z + z, floor_material))

            # Walls (4 sides)
            for y in range(1, room_height):
                for x in range(room_width):
                    blocks.append(_block(base_x + x, oy + y, base_z, wall_material))  # North wall
                    blocks.append(_block(base_x + x, oy + y, base_z + room_depth - 1, wall_material))  # South wall
                for z in range(room_depth):
                    blocks.append(_block(base_x, oy + y, base_z + z, wall_material))  # West wall
                    blocks.append(_block(base_x + room_width - 1, oy + y, base_z + z, wall_material))  # East wall

            # Ceiling
            for x in range(room_width):
                for z in range(room_depth):
                    blocks.append(_block(base_x + x, oy + room_height, base_z + z, wall_material))

    return blocks


def launch_pad(
    module_name: str,
    size: int = 9,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a rocket launch pad with reinforced center."""
    ox, oy, oz = offset
    blocks = []
    half = size // 2

    for x in range(size):
        for z in range(size):
            dist = max(abs(x - half), abs(z - half))
            if dist <= 1:
                # Center: obsidian reinforced
                blocks.append(_block(ox + x, oy, oz + z, "minecraft:obsidian"))
            elif dist <= 2:
                blocks.append(_block(ox + x, oy, oz + z, "minecraft:nether_bricks"))
            else:
                blocks.append(_block(ox + x, oy, oz + z, "minecraft:stone_bricks"))

    return blocks


def fuel_tank(
    module_name: str,
    radius: int = 3,
    height: int = 6,
    offset: tuple[int, int, int] = (0, 0, 0),
) -> list[dict]:
    """Generate a cylindrical fuel tank (approximated with blocks)."""
    ox, oy, oz = offset
    blocks = []
    diameter = radius * 2 + 1

    for y in range(height):
        for x in range(diameter):
            for z in range(diameter):
                dx = x - radius
                dz = z - radius
                dist_sq = dx * dx + dz * dz
                if radius * radius - 1 <= dist_sq <= (radius + 1) * (radius + 1):
                    # Wall
                    if y == 0 or y == height - 1:
                        blocks.append(_block(ox + x, oy + y, oz + z, "minecraft:iron_block"))
                    else:
                        blocks.append(_block(ox + x, oy + y, oz + z, "minecraft:light_gray_concrete"))

    return blocks


def generate_module_template(
    template_type: str,
    module_name: str,
    project_id: str,
    version: int,
    offset: tuple[int, int, int] = (0, 0, 0),
    **kwargs,
) -> dict:
    """Factory function to generate a blueprint module from a template.

    Returns a dict matching the blueprint_module schema.
    """
    generator_map = {
        "simple_cube": lambda: simple_cube(module_name, offset=offset, **kwargs),
        "hollow_box": lambda: hollow_box(module_name, offset=offset, **kwargs),
        "pillar": lambda: pillar(module_name, offset=offset, **kwargs),
        "staircase": lambda: staircase(module_name, offset=offset, **kwargs),
        "roof_gable": lambda: roof_gable(module_name, offset=offset, **kwargs),
        "room_grid": lambda: room_grid(module_name, offset=offset, **kwargs),
        "launch_pad": lambda: launch_pad(module_name, offset=offset, **kwargs),
        "fuel_tank": lambda: fuel_tank(module_name, offset=offset, **kwargs),
    }

    if template_type not in generator_map:
        raise ValueError(f"Unknown template type: {template_type}")

    blocks = generator_map[template_type]()

    if not blocks:
        raise ValueError(f"Template '{template_type}' generated zero blocks")

    min_x = min(b["x"] for b in blocks)
    max_x = max(b["x"] for b in blocks)
    min_y = min(b["y"] for b in blocks)
    max_y = max(b["y"] for b in blocks)
    min_z = min(b["z"] for b in blocks)
    max_z = max(b["z"] for b in blocks)

    from collections import Counter
    mat = dict(Counter(b["block_id"] for b in blocks))

    return {
        "blueprint_id": str(uuid.uuid4()),
        "project_id": project_id,
        "version": version,
        "module_name": module_name,
        "bounds": {
            "min": {"x": min_x, "y": min_y, "z": min_z},
            "max": {"x": max_x, "y": max_y, "z": max_z},
        },
        "block_data": blocks,
        "material_manifest": mat,
        "quality_score": 80,
    }
