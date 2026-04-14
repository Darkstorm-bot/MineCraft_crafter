from __future__ import annotations

from mempalace.accessor import ProjectCreate
from mempalace.repositories import Coord


def _create_project(accessor, project_id: str = "p1"):
    return accessor.create_project(
        ProjectCreate(
            project_id=project_id,
            project_type="rocket",
            mc_version="1.20.4",
            origin_xyz={"x": 0, "y": 64, "z": 0},
            requirements={"size": "medium"},
        )
    )


def test_collision_detection_overlap(accessor):
    _create_project(accessor)
    coords = [Coord(0, 64, 0), Coord(1, 64, 0)]
    first = accessor.reserve_coords("p1", "m1", "b1", coords)
    assert first.success is True

    second = accessor.reserve_coords("p1", "m2", "b2", [Coord(1, 64, 0), Coord(2, 64, 0)])
    assert second.success is False
    assert len(second.collisions) == 1


def test_collision_detection_non_overlap(accessor):
    _create_project(accessor)
    assert accessor.reserve_coords("p1", "m1", "b1", [Coord(0, 64, 0)]).success
    assert accessor.reserve_coords("p1", "m2", "b2", [Coord(10, 64, 0)]).success


def test_transaction_rollback_no_partial_write(accessor):
    _create_project(accessor)
    coords = [Coord(0, 64, 0), Coord(1, 64, 0), Coord(2, 64, 0)]
    assert accessor.reserve_coords("p1", "m1", "b1", coords).success

    # intentional overlap should reject full reservation
    rejected = accessor.reserve_coords("p1", "m2", "b2", [Coord(2, 64, 0), Coord(3, 64, 0)])
    assert not rejected.success

    # verify non-overlapping voxel from rejected batch was not partially inserted
    report = accessor.detect_collision([Coord(3, 64, 0)])
    assert report.has_collision is False


def test_build_log_upsert_and_resume(accessor):
    _create_project(accessor)
    checkpoint = {
        "project_id": "p1",
        "blueprint_id": "b1",
        "batch_index": 0,
        "blocks_placed": 100,
        "status": "ok",
        "checkpoint_state": {
            "blueprint_id": "b1",
            "batch_index": 0,
            "completed_batches": [0],
            "current_origin": {"x": 0, "y": 64, "z": 0},
            "inventory_snapshot": {"minecraft:stone": 100},
        },
    }
    accessor.upsert_build_log(checkpoint)
    latest = accessor.get_latest_checkpoint("p1")
    assert latest is not None
    assert latest["batch_index"] == 0


def test_vision_critique_flow(accessor):
    _create_project(accessor)
    record = accessor.insert_vision_critique(
        {
            "project_id": "p1",
            "blueprint_id": "b1",
            "version": 1,
            "vision_score": 70,
            "flagged_modules": ["launch_pad"],
            "diff_detail": [],
        }
    )
    assert record["vision_score"] == 70
    open_items = accessor.list_open_vision_critiques("p1")
    assert len(open_items) == 1
    accessor.mark_vision_critique_resolved(record["critique_id"])
    assert accessor.list_open_vision_critiques("p1") == []


def test_stale_reservation_release(accessor):
    _create_project(accessor)
    assert accessor.reserve_coords("p1", "m1", "b1", [Coord(0, 64, 0)]).success
    released = accessor.spatial.release_stale_reservations()
    assert isinstance(released, int)
