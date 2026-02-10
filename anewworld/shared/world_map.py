"""
Entire map of game.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chunk import Chunk
from .terrain_generator import TerrainGenerator


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
    """
    Seeded generator used to produce base terrain.
    """

    _chunks: dict[tuple[int, int], Chunk]
    """
    Mapping from chunk coords (cx, cy) to generated chunks.
    """

    @classmethod
    def new(cls, 
            *, 
            chunk_size: int, 
            generator: TerrainGenerator) -> WorldMap:
        """
        Construct a new infinite world map.

        Parameters
        ----------
        chunk_size : int
            Width and height of each chunk (tiles).
        generator : TerrainGenerator
            Seeded generator used to produce terrain.

        Returns
        -------
        WorldMap
            A newly created WorldMap. 
        """
        return cls(
            chunk_size=chunk_size,
            generator=generator,
            _chunks={}
                )
        pass

    ## TODO CHANGE _chunks to an LRU cache
    ## Then, make a renderer as before.
    ## Then, instantiate everything including that nd table
