from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PasteCommand:
    schematic_path: str
    origin: dict


class WorldEditAdapter:
    def __init__(self, command_prefix: str = "//"):
        self.command_prefix = command_prefix

    def build_paste_command(self, cmd: PasteCommand) -> str:
        origin = cmd.origin
        return (
            f"{self.command_prefix}schem load {cmd.schematic_path}; "
            f"{self.command_prefix}paste -a {origin['x']},{origin['y']},{origin['z']}"
        )
