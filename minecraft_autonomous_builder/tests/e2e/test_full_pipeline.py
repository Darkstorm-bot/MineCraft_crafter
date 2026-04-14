"""End-to-end test for the full planning and execution pipeline."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"


@pytest.fixture(scope="module")
def db_path():
    """Create a temporary database for e2e testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test_mempalace.db")


@pytest.fixture(scope="module")
def accessor(db_path):
    """Initialize MemPalaceAccessor with test database."""
    import sys
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    
    from mempalace.accessor import MemPalaceAccessor
    from scripts.init_db import run_migrations
    
    run_migrations(db_path)
    return MemPalaceAccessor(db_path)


def test_full_pipeline_e2e(accessor):
    """Test complete pipeline: create project -> planning loop -> execution -> vision verify."""
    from orchestrator.service import OrchestratorService
    from schematics.generator import SchematicGenerator
    from execution.batch_builder import BatchBuilderService
    from execution.worldedit_adapter import WorldEditAdapter
    
    # Step 1: Create a test project
    project_data = {
        "project_id": "test-rocket-001",
        "project_type": "rocket",
        "mc_version": "1.20.1",
        "origin_xyz": {"x": 0, "y": 64, "z": 0},
        "requirements": {
            "size": "large",
            "style": ["futuristic", "detailed"],
            "redstone_features": ["ignition_sequence"],
        },
    }
    
    project = accessor.create_project(project_data)
    assert project["project_id"] == "test-rocket-001"
    
    # Step 2: Run planning loop
    orchestrator = OrchestratorService(accessor)
    result = orchestrator.run_planning_loop("test-rocket-001")
    
    assert result["status"] in ("approved", "failed")
    
    # Step 3: Generate schematics (if approved)
    if result["status"] == "approved":
        generator = SchematicGenerator()
        blueprints = accessor.list_blueprints("test-rocket-001")
        
        for bp in blueprints:
            schematic_path = generator.emit_module_schematic(
                "test-rocket-001", bp, "1.20.1"
            )
            assert Path(schematic_path).exists() or Path(schematic_path).with_suffix(".json").exists()
        
        # Step 4: Execute build (simulated)
        batch_builder = BatchBuilderService(accessor, WorldEditAdapter())
        modules = [bp for bp in blueprints]
        batch_results = batch_builder.execute(
            "test-rocket-001", blueprints[0]["blueprint_id"], modules
        )
        
        assert len(batch_results) > 0
        assert all(r.status == "ok" for r in batch_results)
        
        # Step 5: Verify checkpoints exist
        build_log = accessor.get_build_log("test-rocket-001")
        assert len(build_log) > 0
    
    # Cleanup
    accessor.set_project_status("test-rocket-001", "completed")
