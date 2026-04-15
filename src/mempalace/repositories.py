from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Coord:
    x: int
    y: int
    z: int


def dict_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class SQLiteRepository:
    def __init__(self, db_path: str, busy_timeout_ms: int = 5000):
        self.db_path = db_path
        self.busy_timeout_ms = busy_timeout_ms
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def transaction(self):
        conn = self.connect()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class JsonCodec:
    @staticmethod
    def dumps(payload: Any) -> str:
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def loads(payload: str | None, default: Any = None) -> Any:
        if payload is None:
            return default
        return json.loads(payload)


def ensure_iterable_coords(coords: Iterable[Coord]) -> list[Coord]:
    out = list(coords)
    if not out:
        raise ValueError("coords cannot be empty")
    return out
