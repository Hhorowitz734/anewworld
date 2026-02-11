"""
Chunks of terrain.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tile_type import TileType


@dataclass(slots = True)
class Chunk:
    """
    Internal storage for fixed-size square region.
    """

    size: int
    """
    Width and height of chunk in tiles.
    """

    terrain: list[TileType]
    """
    Flat list of terrain values in row-major order.
    """

    def _idx(self, x: int, y: int) -> int:
        """
        Convert local (x, y) coords into flat list idx.

        Parameters
        ----------
        x : int
            x-coordinate
        y : int
            y-coordinate

        Returns
        -------
        int
            Index into flat terrain list
        """
        return y * self.size + x

    def terrain_at(self, x: int, y: int) -> TileType:
        """
        Retrieve terrain at chunk coord.

        Parameters
        ----------
        x : int
            x-coordinate
        y : int
            y-coordinate

        Returns
        -------
        TileType
            Terrain at (x, y)
        """
        return self.terrain[self._idx(x, y)]

