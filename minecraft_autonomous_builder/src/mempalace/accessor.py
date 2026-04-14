from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from common.errors import NotFoundError

from .repositories import Coord, JsonCodec, SQLiteRepository
from .spatial_index import CollisionReport, ReservationResult, SpatialIndexService


@dataclass(slots=True)
class ProjectCreate:
    project_id: str
    project_type: str
    mc_version: str
    origin_xyz: dict[str, int]
    requirements: dict[str, Any]


class MemPalaceAccessor:
    """Authoritative API for all MemPalace reads/writes (no raw SQL in agents)."""

    def __init__(self, db_path: str | None = None):
        path = db_path or os.getenv("MEMPALACE_DB_PATH", "./data/mempalace.db")
        timeout = int(os.getenv("MEMPALACE_BUSY_TIMEOUT_MS", "5000"))
        stale = int(os.getenv("RESERVATION_STALE_MINUTES", "30"))
        self.repo = SQLiteRepository(path, busy_timeout_ms=timeout)
        self.spatial = SpatialIndexService(self.repo, stale_minutes=stale)

    def create_project(self, project: ProjectCreate) -> dict[str, Any]:
        with self.repo.transaction() as conn:
            conn.execute(
                "INSERT INTO projects "
                "(project_id,project_type,mc_version,origin_x,origin_y,origin_z,requirements_json,status) "
                "VALUES(?,?,?,?,?,?,?,'init')",
                (
                    project.project_id,
                    project.project_type,
                    project.mc_version,
                    project.origin_xyz["x"],
                    project.origin_xyz["y"],
                    project.origin_xyz["z"],
                    JsonCodec.dumps(project.requirements),
                ),
            )
        return self.get_project(project.project_id)

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self.repo.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE project_id=?", (project_id,)
            ).fetchone()
            if not row:
                raise NotFoundError(f"project {project_id} not found")
            row["requirements"] = JsonCodec.loads(row.pop("requirements_json"), default={})
            row["origin_xyz"] = {
                "x": row.pop("origin_x"),
                "y": row.pop("origin_y"),
                "z": row.pop("origin_z"),
            }
            return row

    def set_project_status(self, project_id: str, status: str) -> None:
        with self.repo.transaction() as conn:
            conn.execute(
                "UPDATE projects SET status=?, updated_at=CURRENT_TIMESTAMP WHERE project_id=?",
                (status, project_id),
            )

    def increment_iteration(self, project_id: str) -> int:
        with self.repo.transaction() as conn:
            conn.execute(
                "UPDATE projects SET iteration_count=iteration_count+1, updated_at=CURRENT_TIMESTAMP WHERE project_id=?",
                (project_id,),
            )
            row = conn.execute(
                "SELECT iteration_count FROM projects WHERE project_id=?", (project_id,)
            ).fetchone()
            return int(row["iteration_count"])

    def insert_blueprint(self, blueprint: dict[str, Any]) -> dict[str, Any]:
        with self.repo.transaction() as conn:
            conn.execute(
                "INSERT INTO blueprints "
                "(blueprint_id,project_id,version,module_name,bounds_json,block_data_json,material_manifest_json,quality_score) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    blueprint["blueprint_id"],
                    blueprint["project_id"],
                    blueprint["version"],
                    blueprint["module_name"],
                    JsonCodec.dumps(blueprint.get("bounds")),
                    JsonCodec.dumps(blueprint["block_data"]),
                    JsonCodec.dumps(blueprint["material_manifest"]),
                    blueprint.get("quality_score"),
                ),
            )
            return blueprint

    def get_latest_blueprints(self, project_id: str) -> list[dict[str, Any]]:
        with self.repo.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM blueprints WHERE project_id=? ORDER BY version DESC, module_name ASC",
                (project_id,),
            ).fetchall()
            for row in rows:
                row["bounds"] = JsonCodec.loads(row.pop("bounds_json"), default={})
                row["block_data"] = JsonCodec.loads(row.pop("block_data_json"), default=[])
                row["material_manifest"] = JsonCodec.loads(
                    row.pop("material_manifest_json"), default={}
                )
            return rows

    def reserve_coords(
        self, project_id: str, module_name: str, blueprint_id: str, voxels: list[Coord]
    ) -> ReservationResult:
        return self.spatial.reserve_coords(project_id, module_name, blueprint_id, voxels)

    def detect_collision(self, voxels: list[Coord]) -> CollisionReport:
        return self.spatial.detect_collision(voxels)

    def insert_critique(self, critique: dict[str, Any]) -> dict[str, Any]:
        critique_id = critique.get("critique_id") or str(uuid.uuid4())
        with self.repo.transaction() as conn:
            conn.execute(
                "INSERT INTO critiques "
                "(critique_id,blueprint_id,iteration,delta_score,issues_json,approval_flag,quality_score) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    critique_id,
                    critique["blueprint_id"],
                    critique["iteration"],
                    critique["delta_score"],
                    JsonCodec.dumps(critique.get("issues", [])),
                    1 if critique.get("approval_flag", False) else 0,
                    critique.get("quality_score"),
                ),
            )
            critique["critique_id"] = critique_id
            return critique

    def upsert_build_log(self, checkpoint: dict[str, Any]) -> dict[str, Any]:
        log_id = checkpoint.get("log_id") or str(uuid.uuid4())
        with self.repo.transaction() as conn:
            conn.execute(
                "INSERT INTO build_log (log_id,project_id,blueprint_id,batch_index,blocks_placed,checkpoint_state_json,status) "
                "VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(project_id,blueprint_id,batch_index) DO UPDATE SET "
                "blocks_placed=excluded.blocks_placed, "
                "checkpoint_state_json=excluded.checkpoint_state_json, "
                "status=excluded.status, updated_at=CURRENT_TIMESTAMP",
                (
                    log_id,
                    checkpoint["project_id"],
                    checkpoint["blueprint_id"],
                    checkpoint["batch_index"],
                    checkpoint["blocks_placed"],
                    JsonCodec.dumps(checkpoint["checkpoint_state"]),
                    checkpoint["status"],
                ),
            )
            checkpoint["log_id"] = log_id
            return checkpoint

    def get_latest_checkpoint(self, project_id: str) -> dict[str, Any] | None:
        with self.repo.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM build_log WHERE project_id=? ORDER BY batch_index DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            if not row:
                return None
            row["checkpoint_state"] = JsonCodec.loads(row.pop("checkpoint_state_json"), default={})
            return row

    def insert_vision_critique(self, payload: dict[str, Any]) -> dict[str, Any]:
        critique_id = payload.get("critique_id") or str(uuid.uuid4())
        with self.repo.transaction() as conn:
            conn.execute(
                "INSERT INTO vision_critiques "
                "(critique_id,project_id,blueprint_id,version,vision_score,flagged_modules_json,diff_detail_json,resolved) "
                "VALUES(?,?,?,?,?,?,?,0)",
                (
                    critique_id,
                    payload["project_id"],
                    payload.get("blueprint_id"),
                    payload.get("version", 1),
                    payload["vision_score"],
                    JsonCodec.dumps(payload.get("flagged_modules", [])),
                    JsonCodec.dumps(payload.get("diff_detail", [])),
                ),
            )
            payload["critique_id"] = critique_id
            return payload

    def mark_vision_critique_resolved(self, critique_id: str) -> None:
        with self.repo.transaction() as conn:
            conn.execute(
                "UPDATE vision_critiques SET resolved=1, resolved_at=CURRENT_TIMESTAMP WHERE critique_id=?",
                (critique_id,),
            )

    def list_open_vision_critiques(self, project_id: str) -> list[dict[str, Any]]:
        with self.repo.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM vision_critiques WHERE project_id=? AND resolved=0 ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
            for row in rows:
                row["flagged_modules"] = JsonCodec.loads(
                    row.pop("flagged_modules_json"), default=[]
                )
                row["diff_detail"] = JsonCodec.loads(row.pop("diff_detail_json"), default=[])
            return rows

    def list_blueprints(self, project_id: str) -> list[dict[str, Any]]:
        """List all blueprints for a project."""
        with self.repo.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM blueprints WHERE project_id=? ORDER BY version DESC, module_name ASC",
                (project_id,),
            ).fetchall()
            for row in rows:
                row["bounds"] = JsonCodec.loads(row.pop("bounds_json"), default={})
                row["block_data"] = JsonCodec.loads(row.pop("block_data_json"), default=[])
                row["material_manifest"] = JsonCodec.loads(
                    row.pop("material_manifest_json"), default={}
                )
            return rows

    def get_build_log(self, project_id: str) -> list[dict[str, Any]]:
        """Get all build log entries for a project."""
        with self.repo.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM build_log WHERE project_id=? ORDER BY batch_index ASC",
                (project_id,),
            ).fetchall()
            for row in rows:
                row["checkpoint_state"] = JsonCodec.loads(row.pop("checkpoint_state_json"), default={})
            return rows
