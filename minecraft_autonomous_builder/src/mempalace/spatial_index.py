from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .repositories import Coord, SQLiteRepository, ensure_iterable_coords


@dataclass(slots=True)
class CollisionReport:
    has_collision: bool
    collisions: list[dict]


@dataclass(slots=True)
class ReservationResult:
    success: bool
    reserved_count: int
    collisions: list[dict]


class SpatialIndexService:
    def __init__(self, repo: SQLiteRepository, stale_minutes: int = 30):
        self.repo = repo
        self.stale_minutes = stale_minutes

    def detect_collision(self, coords: Iterable[Coord]) -> CollisionReport:
        voxel_list = ensure_iterable_coords(coords)
        with self.repo.transaction() as conn:
            collisions: list[dict] = []
            for c in voxel_list:
                row = conn.execute(
                    "SELECT x,y,z,project_id,module_name,reservation_status,reserved_at "
                    "FROM coord_index WHERE x=? AND y=? AND z=? "
                    "AND reservation_status IN ('reserved', 'placed')",
                    (c.x, c.y, c.z),
                ).fetchone()
                if row:
                    collisions.append(row)
        return CollisionReport(has_collision=bool(collisions), collisions=collisions)

    def reserve_coords(
        self,
        project_id: str,
        module_name: str,
        blueprint_id: str,
        coords: Iterable[Coord],
    ) -> ReservationResult:
        voxel_list = ensure_iterable_coords(coords)
        with self.repo.transaction() as conn:
            collisions: list[dict] = []
            for c in voxel_list:
                existing = conn.execute(
                    "SELECT x,y,z,project_id,module_name,reservation_status,reserved_at "
                    "FROM coord_index WHERE x=? AND y=? AND z=?",
                    (c.x, c.y, c.z),
                ).fetchone()
                if existing and existing["reservation_status"] in {"reserved", "placed"}:
                    collisions.append(existing)
            if collisions:
                return ReservationResult(False, 0, collisions)

            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT INTO coord_index "
                "(x,y,z,project_id,module_name,blueprint_id,reservation_status,reserved_at) "
                "VALUES(?,?,?,?,?,?,'reserved',?)",
                [(c.x, c.y, c.z, project_id, module_name, blueprint_id, now) for c in voxel_list],
            )
            return ReservationResult(True, len(voxel_list), [])

    def mark_rolled_back(self, project_id: str, module_name: str) -> int:
        with self.repo.transaction() as conn:
            cur = conn.execute(
                "UPDATE coord_index SET reservation_status='rolled_back', released_at=CURRENT_TIMESTAMP "
                "WHERE project_id=? AND module_name=? AND reservation_status='reserved'",
                (project_id, module_name),
            )
            return cur.rowcount

    def release_stale_reservations(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.stale_minutes)
        with self.repo.transaction() as conn:
            cur = conn.execute(
                "UPDATE coord_index SET reservation_status='released', released_at=CURRENT_TIMESTAMP "
                "WHERE reservation_status='reserved' AND reserved_at < ?",
                (cutoff.isoformat(),),
            )
            return cur.rowcount

    def nearby_structures(self, x: int, y: int, z: int, radius: int) -> list[dict]:
        with self.repo.transaction() as conn:
            rows = conn.execute(
                "SELECT DISTINCT project_id,module_name,blueprint_id FROM coord_index "
                "WHERE ABS(x-?)<=? AND ABS(y-?)<=? AND ABS(z-?)<=? "
                "AND reservation_status IN ('reserved','placed')",
                (x, radius, y, radius, z, radius),
            ).fetchall()
            return rows
