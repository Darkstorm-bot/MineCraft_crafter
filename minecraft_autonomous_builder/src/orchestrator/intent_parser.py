from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from project_builders.base_builder import get_builder


class IntentParser:
    def __init__(self, schema_path: str = "schemas/project_intent.schema.json"):
        self.schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))

    def parse(self, payload: dict) -> dict:
        validate(instance=payload, schema=self.schema)
        builder = get_builder(payload["project_type"])
        plan = builder.build_plan(payload)
        normalized = dict(payload)
        normalized["required_modules"] = plan.modules
        normalized["redstone_requirements"] = plan.redstone_requirements
        normalized["invariants"] = plan.invariants
        return normalized
