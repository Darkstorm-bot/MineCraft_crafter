from __future__ import annotations

import json
import logging
import os

from jsonschema import validate as json_validate

logger = logging.getLogger(__name__)

VISION_PASS_THRESHOLD = int(os.getenv("VISION_PASS_THRESHOLD", "80"))


class VisionScorer:
    """Parses and evaluates vision verification results from LLaVA.

    Enforces strict JSON schema validation and pass/fail threshold logic.
    """

    def __init__(self, schema_path: str = "schemas/vision_diff.schema.json"):
        self.schema = json.loads(open(schema_path, "r", encoding="utf-8").read())
        self.pass_threshold = VISION_PASS_THRESHOLD

    def parse_strict(self, raw_json: str) -> dict:
        """Parse and validate vision diff output against schema."""
        payload = json.loads(raw_json)
        json_validate(instance=payload, schema=self.schema)
        return payload

    def evaluate(self, vision_diff: dict) -> dict:
        """Evaluate vision diff result against pass threshold.

        Returns:
            {
                "passed": bool,
                "score": float,
                "flagged_modules": list[str],
                "needs_reentry": bool,
            }
        """
        score = vision_diff.get("vision_score", 0)
        flagged = vision_diff.get("flagged_modules", [])
        passed = score >= self.pass_threshold

        result = {
            "passed": passed,
            "score": score,
            "flagged_modules": flagged,
            "needs_reentry": not passed,
        }

        if passed:
            logger.info("Vision verification PASSED: score=%d (threshold=%d)", score, self.pass_threshold)
        else:
            logger.warning("Vision verification FAILED: score=%d < threshold=%d, flagged=%s",
                           score, self.pass_threshold, flagged)

        return result

    def is_pass(self, score: float) -> bool:
        """Quick check if a score meets the threshold."""
        return score >= self.pass_threshold
