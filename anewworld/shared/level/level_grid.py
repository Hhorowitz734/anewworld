"""
N-dimensional LUT for level combinations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Mapping, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen = True, slots = True)
class LevelGrid(Generic[K, V]):
    """
    N-dimensional LUT mapping tuple of Levels to a TileType.
    """

    table: Mapping[tuple[K, ...], V]
    """
    Mapping from key tuples to outputs.
    """

    default: V
    """
    Default output if a key tuple is not explicitly mapped.
    """

    def get(self, *keys: K) -> V:
        """
        Get LUT output for given set of Levels.

        Parameters
        ----------
        *keys : K
            Ordered levels.

        Returns
        -------
        V
            Mapped output if present, default otherwise.
        """
        return self.table.get(tuple(keys), self.default)
