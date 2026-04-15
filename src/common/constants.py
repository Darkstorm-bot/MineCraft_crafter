from __future__ import annotations

from enum import Enum


class ProjectStatus(str, Enum):
    INIT = "init"
    PLANNING = "planning"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    DONE = "done"
    FAILED = "failed"


class BuildBatchStatus(str, Enum):
    OK = "ok"
    RETRY = "retry"
    FAILED = "failed"
