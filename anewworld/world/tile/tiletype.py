"""
Possible types of tiles.
"""

from enum import IntEnum


class TileType(IntEnum):
    """
    Terrain types.
    """

    LAND = 1
    RIVER = 2
