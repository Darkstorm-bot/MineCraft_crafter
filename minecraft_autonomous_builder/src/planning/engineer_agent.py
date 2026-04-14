from __future__ import annotations

from .planner_io import EngineerInput, EngineerOutput


class EngineerAgent:
    """Structured deterministic validator."""

    def run(self, payload: EngineerInput) -> EngineerOutput:
        issues: list[dict] = []
        if not payload.blueprint_modules:
            issues.append(
                {
                    "issue_code": "EMPTY_BLUEPRINT",
                    "priority": "P0",
                    "message": "No modules generated",
                    "module_name": "global",
                    "suggested_fix": "Regenerate blueprint modules",
                }
            )

        quality_score = 85.0 if not issues else 20.0
        delta_score = 0.0 if not issues else 100.0
        approval_flag = not issues
        return EngineerOutput(
            delta_score=delta_score,
            issues=issues,
            approval_flag=approval_flag,
            quality_score=quality_score,
        )
