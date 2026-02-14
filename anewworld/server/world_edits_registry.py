"""
World edits registry with on-demand chunk loading and persistent storage.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

from anewworld.shared.resource import Resource


def _world_to_chunk(wx: int, wy: int, *, chunk_size: int) -> tuple[int, int, int, int]:
    """
    Convert world tile coordinates to (cx, cy, lx, ly).

    Parameters
    ----------
    wx : int
        World x coordinate in tiles.
    wy : int
        World y coordinate in tiles.
    chunk_size : int
        Chunk width and height in tiles.

    Returns
    -------
    tuple[int, int, int, int]
        (cx, cy, lx, ly) where (lx, ly) are local tile coordinates within
        the chunk in the range [0, chunk_size).
    """
    cx = wx // chunk_size
    cy = wy // chunk_size
    lx = wx - cx * chunk_size
    ly = wy - cy * chunk_size
    return cx, cy, lx, ly


@dataclass(frozen=True, slots=True)
class PlacedObject:
    """
    Placed object overlay stored on top of procedural terrain.
    """

    obj: Resource
    """
    Object type identifier.
    """

    rot: int
    """
    Rotation / variant integer.
    """

    owner_id: int | None
    """
    Player id of the placer, if available.
    """

    updated_at_s: float
    """
    Server timestamp when last updated.
    """

    def to_wire(self, *, lx: int, ly: int) -> dict[str, Any]:
        """
        Convert placement to JSON-serializable wire format.

        Parameters
        ----------
        lx : int
            Local x coordinate within chunk.
        ly : int
            Local y coordinate within chunk.

        Returns
        -------
        dict[str, Any]
            JSON-serializable placement record.
        """
        return {
            "lx": lx,
            "ly": ly,
            "obj": self.obj.value,
            "rot": self.rot,
            "owner_id": self.owner_id,
            "updated_at_s": self.updated_at_s,
        }


@dataclass(slots=True)
class ChunkEdits:
    """
    In-memory edit overlay for a single chunk.
    """

    tiles: dict[tuple[int, int], PlacedObject] = field(default_factory=dict)
    """
    Mapping from (lx, ly) to placed object.
    """

    last_access_s: float = 0.0
    """
    Last time this chunk was accessed.
    """


class WorldEditsStore(Protocol):
    """
    Persistent store interface for world edits.
    """

    def load_chunk(
        self, *, cx: int, cy: int
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
        ...

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
        ...

    def delete(self, *, cx: int, cy: int, lx: int, ly: int) -> None:
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
        ...


@dataclass(slots=True)
class WorldEditsRegistry:
    """
    Registry of persistent world edits with an in-memory chunk cache.

    This registry is responsible for:
    - Loading chunk overlays on demand from a persistent store (SQLite).
    - Caching recently used chunks in memory with LRU eviction.
    - Applying place/remove operations authoritatively.

    Notes
    -----
    This implementation is write-through: edits are persisted immediately
    via the store on each mutation. That makes correctness easy and avoids
    dirty-flush complexity while you build out gameplay.
    """

    store: WorldEditsStore
    """
    Persistent store backend.
    """

    chunk_size: int
    """
    Chunk width and height in tiles.
    """

    max_cached_chunks: int
    """
    Maximum number of chunks to keep in memory.
    """

    _cache: OrderedDict[tuple[int, int], ChunkEdits]
    """
    LRU cache mapping (cx, cy) to chunk edits.
    """

    @classmethod
    def new(
        cls,
        *,
        store: WorldEditsStore,
        chunk_size: int,
        max_cached_chunks: int = 2048,
    ) -> WorldEditsRegistry:
        """
        Construct a new world edits registry.

        Parameters
        ----------
        store : WorldEditsStore
            Persistent store backend.
        chunk_size : int
            Chunk width and height in tiles.
        max_cached_chunks : int
            Maximum number of chunks to keep in memory.

        Returns
        -------
        WorldEditsRegistry
            Newly created registry.
        """
        return cls(
            store=store,
            chunk_size=chunk_size,
            max_cached_chunks=max_cached_chunks,
            _cache=OrderedDict(),
        )

    def _touch(self, key: tuple[int, int], chunk: ChunkEdits) -> None:
        """
        Update LRU state for a cached chunk.

        Parameters
        ----------
        key : tuple[int, int]
            Chunk cache key (cx, cy).
        chunk : ChunkEdits
            Cached chunk edits.

        Returns
        -------
        None
        """
        now = time.time()
        chunk.last_access_s = now

        if key in self._cache:
            self._cache.move_to_end(key, last=True)
        else:
            self._cache[key] = chunk

        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        """
        Evict least-recently-used chunks until within cache limit.

        Returns
        -------
        None
        """
        while len(self._cache) > self.max_cached_chunks:
            self._cache.popitem(last=False)

    def _get_or_load_chunk(self, *, cx: int, cy: int) -> ChunkEdits:
        """
        Get a chunk from cache or load it from the store.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.

        Returns
        -------
        ChunkEdits
            Loaded or cached chunk overlay.
        """
        key = (cx, cy)
        existing = self._cache.get(key)
        if existing is not None:
            self._touch(key, existing)
            return existing

        chunk = ChunkEdits()
        for lx, ly, placement in self.store.load_chunk(cx=cx, cy=cy):
            chunk.tiles[(lx, ly)] = placement

        self._touch(key, chunk)
        return chunk

    def get_chunk_snapshot(self, *, cx: int, cy: int) -> list[dict[str, Any]]:
        """
        Get the full overlay snapshot for a chunk.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.

        Returns
        -------
        list[dict[str, Any]]
            List of placement records suitable for sending over the wire.
        """
        chunk = self._get_or_load_chunk(cx=cx, cy=cy)
        out: list[dict[str, Any]] = []
        for (lx, ly), placement in chunk.tiles.items():
            out.append(placement.to_wire(lx=lx, ly=ly))
        return out

    def can_place(self, *, wx: int, wy: int) -> bool:
        """
        Check whether a tile is currently unoccupied by an overlay.

        Parameters
        ----------
        wx : int
            World x coordinate in tiles.
        wy : int
            World y coordinate in tiles.

        Returns
        -------
        bool
            True if the overlay tile is empty, False otherwise.
        """
        cx, cy, lx, ly = _world_to_chunk(wx, wy, chunk_size=self.chunk_size)
        chunk = self._get_or_load_chunk(cx=cx, cy=cy)
        return (lx, ly) not in chunk.tiles

    def apply_place(
        self,
        *,
        player_id: int,
        wx: int,
        wy: int,
        obj: Resource,
        rot: int = 0,
    ) -> dict[str, Any]:
        """
        Apply a placement to the world overlay.

        Parameters
        ----------
        player_id : int
            Player id performing the placement.
        wx : int
            World x coordinate in tiles.
        wy : int
            World y coordinate in tiles.
        obj : Resource
            Object type identifier.
        rot : int
            Rotation / variant integer.

        Returns
        -------
        dict[str, Any]
            Applied edit record suitable for broadcasting.
        """
        cx, cy, lx, ly = _world_to_chunk(wx, wy, chunk_size=self.chunk_size)
        chunk = self._get_or_load_chunk(cx=cx, cy=cy)

        now = time.time()
        placement = PlacedObject(obj=obj, rot=rot, owner_id=player_id, updated_at_s=now)

        chunk.tiles[(lx, ly)] = placement
        self.store.upsert(cx=cx, cy=cy, lx=lx, ly=ly, placement=placement)

        return {
            "op": "place",
            "cx": cx,
            "cy": cy,
            "lx": lx,
            "ly": ly,
            "obj": obj.value,
            "rot": rot,
            "owner_id": player_id,
            "updated_at_s": now,
        }

    def apply_remove(
        self,
        *,
        player_id: int,
        wx: int,
        wy: int,
    ) -> dict[str, Any]:
        """
        Remove a placement from the world overlay if present.

        Parameters
        ----------
        player_id : int
            Player id performing the removal.
        wx : int
            World x coordinate in tiles.
        wy : int
            World y coordinate in tiles.

        Returns
        -------
        dict[str, Any]
            Applied edit record suitable for broadcasting.
        """
        cx, cy, lx, ly = _world_to_chunk(wx, wy, chunk_size=self.chunk_size)
        chunk = self._get_or_load_chunk(cx=cx, cy=cy)

        existing = chunk.tiles.pop((lx, ly), None)
        if existing is not None:
            self.store.delete(cx=cx, cy=cy, lx=lx, ly=ly)

        now = time.time()
        return {
            "op": "remove",
            "cx": cx,
            "cy": cy,
            "lx": lx,
            "ly": ly,
            "owner_id": player_id,
            "had_object": existing is not None,
            "updated_at_s": now,
        }
