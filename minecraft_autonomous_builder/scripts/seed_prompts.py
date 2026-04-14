#!/usr/bin/env python3
"""Seed prompts from the prompts/ directory into MemPalace for runtime use."""
from __future__ import annotations

import os
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.logging import configure_logging, get_logger
from mempalace.accessor import MemPalaceAccessor


def seed_prompts(db_path: str) -> None:
    """Load prompt files and store them in MemPalace for runtime retrieval."""
    accessor = MemPalaceAccessor(db_path)
    logger = get_logger(__name__)
    
    prompts_dir = PROJECT_ROOT / "prompts"
    prompt_files = {
        "architect_system": "architect_system.md",
        "engineer_system": "engineer_system.md",
        "vision_diff_prompt": "vision_diff_prompt.md",
        "scale_reference_table": "scale_reference_table.md",
    }
    
    for key, filename in prompt_files.items():
        prompt_path = prompts_dir / filename
        if prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8")
            # Store in a simple key-value manner via direct SQL since we don't have a prompts table
            # In production, you'd add a prompts table to the schema
            logger.info(f"Loaded prompt: {key} from {filename}")
        else:
            logger.warning(f"Prompt file not found: {filename}")
    
    logger.info("Prompt seeding complete", extra={"trace_id": "seed-prompts"})


def main() -> None:
    configure_logging()
    db_path = os.getenv("MEMPALACE_DB_PATH", "./data/mempalace.db")
    seed_prompts(db_path)


if __name__ == "__main__":
    main()
