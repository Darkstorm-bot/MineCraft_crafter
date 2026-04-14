from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


class Screenshotter:
    def capture_module(self, project_id: str, module_name: str, phase: str) -> str:
        out_dir = Path("data/screenshots") / project_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{module_name}_{phase}.png"
        image = Image.new("RGB", (640, 360), (30, 30, 30))
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), f"{project_id}:{module_name}:{phase}", fill=(200, 200, 200))
        image.save(path)
        return str(path)
