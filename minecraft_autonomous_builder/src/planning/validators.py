from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import validate


def validate_with_schema(payload: dict[str, Any], schema_path: str) -> None:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validate(instance=payload, schema=schema)
