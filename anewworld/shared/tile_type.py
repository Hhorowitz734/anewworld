"""
Enum that defines the type of terrain.
"""

from enum import IntEnum


class TileType(IntEnum):
    """
    Types of terrain.
    """

    DEFAULT_GRASS = 1
    DEFAULT_WATER = 2

    DARK_GRASS = 3
    DEEP_WATER = 4
