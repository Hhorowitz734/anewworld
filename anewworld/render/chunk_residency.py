"""
Chunk residency and LRU eviction policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict, deque
from typing import Deque, Iterable, Iterator, OrderedDict as ODType, Set


ChunkKey = tuple[int, int]


@dataclass(slots=True)
class ChunkResidency:
    """
    Shared chunk residency policy for caches keyed by (cx, cy).
    """

    max_cached_chunks: int
    """
    Maximum number of chunk keys allowed to remain resident.
    """

    _lru: ODType[ChunkKey, None]
    """
    LRU ordering for keys.
    """

    _build_queue: Deque[ChunkKey]
    """
    Queue of keys awaiting construction in some dependent cache.
    """

    _build_set: Set[ChunkKey]
    """
    Set of queued keys to avoid duplicates.
    """

    @classmethod
    def new(cls, *, max_cached_chunks: int) -> ChunkResidency:
        """
        Construct a new residency policy.
        """
        return cls(
            max_cached_chunks=max_cached_chunks,
            _lru=OrderedDict(),
            _build_queue=deque(),
            _build_set=set(),
        )

    def visible_keys(self, *, cx0: int, cy0: int, cx1: int, cy1: int) -> Iterator[ChunkKey]:
        """
        Iterate all chunk keys in an inclusive visible rectangle.
        """
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                yield (cx, cy)

    def touch(self, key: ChunkKey) -> None:
        """
        Mark a key as most recently used.
        """
        self._lru[key] = None
        self._lru.move_to_end(key, last=True)

    def is_queued(self, key: ChunkKey) -> bool:
        """
        Return True if the key is currently queued for building.
        """
        return key in self._build_set

    def queue_missing(self, keys: Iterable[ChunkKey], *, is_present) -> None:
        """
        Enqueue keys that are not present and not already queued.

        Parameters
        ----------
        keys : Iterable[ChunkKey]
            Candidate keys to ensure are queued.
        is_present : callable
            Function (key) -> bool indicating whether a dependent cache already has the key.
        """
        for key in keys:
            if is_present(key) or key in self._build_set:
                continue
            self._build_queue.append(key)
            self._build_set.add(key)

    def pop_next_build(self) -> ChunkKey | None:
        """
        Pop the next queued key to build, or None if empty.
        """
        if not self._build_queue:
            return None
        key = self._build_queue.popleft()
        self._build_set.discard(key)
        return key

    def evict_keys(self, *, resident_count: int) -> list[ChunkKey]:
        """
        Return a list of least-recently-used keys to evict until resident_count
        is <= max_cached_chunks.

        Parameters
        ----------
        resident_count : int
            The current number of resident keys in the dependent cache.

        Returns
        -------
        list[ChunkKey]
            Keys that should be evicted (oldest first).
        """
        to_evict: list[ChunkKey] = []
        n = resident_count
        while n > self.max_cached_chunks and self._lru:
            oldest_key, _ = self._lru.popitem(last=False)
            to_evict.append(oldest_key)
            n -= 1
        return to_evict
