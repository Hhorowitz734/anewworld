"""
Entire map of game.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chunk import Chunk


@dataclass(slots=True)
class WorldMap:
    """
    Infinite map of fixed size `Chunk`s.
    """

    chunk_size: int
    """
    With and height of each
    """

    generator: TerrainGenerator
