"""
Generic least-recently-used (LRU) cache implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import OrderedDict
from typing import Callable, Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass(slots=True)
class LRUCache(Generic[K, V]):
    """
    Least-recently-used (LRU) cache with a fixed maximum capacity.
    """

    capacity: int
    """
    Maximum number of entries to retain in the cache.

    Must be greater than zero.
    """

    on_evict: Optional[Callable[[K, V], None]] = None
    """
    Optional callback invoked when an entry is evicted.

    The callback is passed the evicted key and value.
    """

    _data: OrderedDict[K, V] = field(default_factory=OrderedDict, init=False)
    """
    Internal ordered mapping storing cache entries.

    The order reflects usage, with the most recently used entry at
    the end of the mapping.
    """

    def __post_init__(self) -> None:
        """
        Validate cache configuration after initialization.
        """
        if self.capacity <= 0:
            raise ValueError("LRUCache capacity must be greater than zero.")

    def __len__(self) -> int:
        """
        Return the number of entries currently stored in the cache.

        Returns
        -------
        int
            Number of cached entries.
        """
        return len(self._data)

    def __contains__(self, key: K) -> bool:
        """
        Test whether a key exists in the cache.

        Parameters
        ----------
        key : K
            Cache key.

        Returns
        -------
        bool
            True if the key is present, False otherwise.
        """
        return key in self._data

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """
        Retrieve a value from the cache and mark it as most recently used.

        Parameters
        ----------
        key : K
            Cache key.
        default : Optional[V]
            Value to return if the key is not present.

        Returns
        -------
        Optional[V]
            Cached value if present, otherwise the default.
        """
        if key not in self._data:
            return default

        value = self._data.pop(key)
        self._data[key] = value
        return value

    def put(self, key: K, value: V) -> None:
        """
        Insert or update a cache entry and mark it as most recently used.

        If the cache exceeds its capacity, the least recently used
        entry is evicted.

        Parameters
        ----------
        key : K
            Cache key.
        value : V
            Value to store.
        """
        if key in self._data:
            self._data.pop(key)

        self._data[key] = value
        self._evict_if_needed()

    def pop(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """
        Remove and return a cache entry without treating it as eviction.

        This does not invoke the eviction callback.

        Parameters
        ----------
        key : K
            Cache key.
        default : Optional[V]
            Value to return if the key is not present.

        Returns
        -------
        Optional[V]
            Removed value if present, otherwise the default.
        """
        return self._data.pop(key, default)

    def clear(self) -> None:
        """
        Remove all entries from the cache without invoking eviction callbacks.
        """
        self._data.clear()

    def _evict_if_needed(self) -> None:
        """
        Evict least recently used entries until capacity is satisfied.
        """
        while len(self._data) > self.capacity:
            key, value = self._data.popitem(last=False)
            if self.on_evict is not None:
                self.on_evict(key, value)

