"""
Shared client-server configurations.
"""

from dataclasses import dataclass

from anewworld.shared.level.elevation import ElevationLevel
from anewworld.shared.level.level_grid import LevelGrid
from anewworld.shared.level.moisture import MoistureLevel
from anewworld.shared.tile_type import TileType


@dataclass(frozen=True, slots=True)
class WorldConfig:
    """
    Configuration of game world.
    """

    chunk_size: int = 32
    """
    Width and height of chunk (tiles).
    """

    world_seed: int = 1
    """
    Seed for procedural world generation.
    """

    level_grid = LevelGrid[object, TileType](
        table={
            (ElevationLevel.HIGH, MoistureLevel.DRY): TileType.DEFAULT_GRASS,
            (ElevationLevel.HIGH, MoistureLevel.WET): TileType.DARK_GRASS,
            (ElevationLevel.LOW, MoistureLevel.DRY): TileType.DEFAULT_WATER,
            (ElevationLevel.LOW, MoistureLevel.WET): TileType.DEEP_WATER,
        },
        default=TileType.DEFAULT_GRASS,
    )
    """
    Table to decide tiletypes based on env factors.
    """
