"""
Possible types of tiles.
"""

from enum import IntEnum


class TileType(IntEnum):
    """
    Terrain types.
    """

    LAND = 1
    WATER = 2

    RAINFOREST = 3
    DEEPWATER = 4
