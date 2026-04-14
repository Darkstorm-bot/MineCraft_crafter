from __future__ import annotations

import json

from jsonschema import validate


class VisionScorer:
    def __init__(self, schema_path: str = "schemas/vision_diff.schema.json"):
        self.schema = json.loads(open(schema_path, "r", encoding="utf-8").read())

    def parse_strict(self, raw_json: str) -> dict:
        payload = json.loads(raw_json)
        validate(instance=payload, schema=self.schema)
        return payload
