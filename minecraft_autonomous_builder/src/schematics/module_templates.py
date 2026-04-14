from __future__ import annotations


def simple_cube(module_name: str, material: str = "minecraft:stone") -> list[dict]:
    blocks = []
    for y in range(2):
        for x in range(3):
            for z in range(3):
                blocks.append({"x": x, "y": y, "z": z, "block_id": material})
    return blocks
