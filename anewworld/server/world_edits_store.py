"""
SQLite-backed persistent store for world edits.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable
from dataclasses import dataclass

from anewworld.shared.resource import Resource

from .world_edits_registry import PlacedObject


@dataclass(slots=True)
class WorldEditsStore:
    """
    SQLite implementation of the world edits store.

    Notes
    -----
    This store is synchronous and guarded by a lock to ensure
    safe access across threads. For early development this is
    sufficient and avoids async complexity.
    """

    path: str
    """
    Path to sqlite database file.
    """

    _conn: sqlite3.Connection
    """
    SQLite connection.
    """

    _lock: threading.Lock
    """
    Lock guarding sqlite access.
    """

    @classmethod
    def new(cls, *, path: str) -> WorldEditsStore:
        """
        Construct a new sqlite store and ensure schema exists.

        Parameters
        ----------
        path : str
            Path to sqlite database file.

        Returns
        -------
        WorldEditsStore
            Newly created store.
        """
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        store = cls(path=path, _conn=conn, _lock=threading.Lock())
        store._init_schema()
        return store

    def _init_schema(self) -> None:
        """
        Initialize sqlite schema if missing.

        Returns
        -------
        None
        """
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS placements (
                    cx INTEGER NOT NULL,
                    cy INTEGER NOT NULL,
                    lx INTEGER NOT NULL,
                    ly INTEGER NOT NULL,
                    obj TEXT NOT NULL,
                    rot INTEGER NOT NULL,
                    owner_id INTEGER,
                    updated_at_s REAL NOT NULL,
                    PRIMARY KEY (cx, cy, lx, ly)
                )
                """
            )

            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_placements_chunk ON placements (cx, cy)"
            )

            self._conn.commit()

    def load_chunk(
        self,
        *,
        cx: int,
        cy: int,
    ) -> Iterable[tuple[int, int, PlacedObject]]:
        """
        Load all placements for a chunk.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.

        Returns
        -------
        Iterable[tuple[int, int, PlacedObject]]
            Iterable of (lx, ly, placement) records.
        """
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT lx, ly, obj, rot, owner_id, updated_at_s
                FROM placements
                WHERE cx = ? AND cy = ?
                """,
                (cx, cy),
            )
            rows = list(cur.fetchall())

        out: list[tuple[int, int, PlacedObject]] = []

        for lx, ly, obj, rot, owner_id, updated_at_s in rows:
            placement = PlacedObject(
                obj=Resource(obj),
                rot=int(rot),
                owner_id=int(owner_id) if owner_id is not None else None,
                updated_at_s=float(updated_at_s),
            )
            out.append((int(lx), int(ly), placement))

        return out

    def upsert(
        self,
        *,
        cx: int,
        cy: int,
        lx: int,
        ly: int,
        placement: PlacedObject,
    ) -> None:
        """
        Insert or replace a placement record.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.
        lx : int
            Local x coordinate within chunk.
        ly : int
            Local y coordinate within chunk.
        placement : PlacedObject
            Placement record.

        Returns
        -------
        None
        """
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO placements (
                    cx, cy, lx, ly,
                    obj, rot, owner_id, updated_at_s
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cx, cy, lx, ly)
                DO UPDATE SET
                    obj = excluded.obj,
                    rot = excluded.rot,
                    owner_id = excluded.owner_id,
                    updated_at_s = excluded.updated_at_s
                """,
                (
                    cx,
                    cy,
                    lx,
                    ly,
                    placement.obj.value,
                    placement.rot,
                    placement.owner_id,
                    placement.updated_at_s,
                ),
            )
            self._conn.commit()

    def delete(
        self,
        *,
        cx: int,
        cy: int,
        lx: int,
        ly: int,
    ) -> None:
        """
        Delete a placement record.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.
        lx : int
            Local x coordinate within chunk.
        ly : int
            Local y coordinate within chunk.

        Returns
        -------
        None
        """
        with self._lock:
            self._conn.execute(
                """
                DELETE FROM placements
                WHERE cx = ? AND cy = ? AND lx = ? AND ly = ?
                """,
                (cx, cy, lx, ly),
            )
            self._conn.commit()
