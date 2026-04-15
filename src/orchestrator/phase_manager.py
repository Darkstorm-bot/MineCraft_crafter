from __future__ import annotations

from enum import Enum


class OrchestrationState(str, Enum):
    INIT = "INIT"
    PLAN_A = "PLAN_A"
    VALIDATE_B = "VALIDATE_B"
    GATE = "GATE"
    EXECUTE = "EXECUTE"
    VISION_VERIFY = "VISION_VERIFY"
    REENTER = "REENTER"
    DONE = "DONE"
    FAILED = "FAILED"
