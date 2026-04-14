from __future__ import annotations


def should_approve(delta_score: float, approval_flag: bool, iteration_count: int) -> bool:
    if delta_score < 5:
        return True
    if approval_flag:
        return True
    return iteration_count >= 3
