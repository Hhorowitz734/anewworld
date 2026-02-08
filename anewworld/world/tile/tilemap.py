"""
Manages all tiles for anewworld.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tile import Tile
from .tiletype import TileType


@dataclass(slots=True)
class TileMap:
    """
    Tile map manager.
    """

    w: int
    """
    Width (tiles) of map.
    """

    h: int
    """
    Height (tiles) of map.
    """

    tiles: list[Tile]
    """
    Main tile container.
    """

    @classmethod
    def new(cls, w: int, h: int, default_terrain: TileType) -> TileMap:
        """
        Instantiate a new TileMap.
        """
        tiles = [Tile(default_terrain) for _ in range(w * h)]
        return cls(w=w, h=h, tiles=tiles)

    def in_bounds(self, x: int, y: int) -> bool:
        """
        Verify a tile is in bounds.
        """
        return 0 <= x < self.w and 0 <= y < self.h

    def _idx(self, x: int, y: int) -> int:
        """
        Get the index of a tile given its location on screen.
        """
        return y * self.w + x

    def tile_at(self, x: int, y: int) -> Tile:
        """
        Get a tile given its coordinates on the tilemap.
        """
        return self.tiles[self._idx(x, y)]
