"""
Singular Tile on Tilemap.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tiletype import TileType


@dataclass(slots=True)
class Tile:
    """
    Individual Tile.
    """

    terrain: TileType
    """
    Type of tile.
    """
