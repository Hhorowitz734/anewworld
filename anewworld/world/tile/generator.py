"""
Generates terrain given world seed.
"""

from __future__ import annotations

from dataclasses import dataclass
import random

from anewworld.world.tile.tiletype import TileType


@dataclass(frozen=True, slots=True)
class TerrainGenerator:
    """
    Deterministic procedural generator for base terrain.
    """

    seed: int
    """
    World seed used to generate terrain deterministically.
    """

    lake_chance: float = 0.06
    """
    Probability that a chunk has at least one lake seed.
    """

    min_lake_radius: int = 3
    """
    Minimum lake radius in tiles.
    """

    river_chance: float = 0.10
    """
    Probability that a chunk contains a river segment.
    """

    river_width: int = 2
    """
    River half-width in tiles.

    A width of 2 produces a river roughly 5 tiles wide.
    """

    river_steps:
    """
    Number of steps used to trace a river polyline within a chunk.
    """

    def generate_chunk(
        self,
        *,
        cx: int,
        cy: int, 
        chunk_size: int,
    ) -> list[TileType]:
        """
        Generate base terrain for single chunk.

        Parameters
        ----------
        cx:
        """
        pass

