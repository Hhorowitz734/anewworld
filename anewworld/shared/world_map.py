"""
Entire map of game.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chunk import Chunk
from .terrain_generator import TerrainGenerator
from .utils.lru_cache import LRUCache


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

    max_cached_chunks: int
    """
    Maximum number of chunks to retain in memory.
    """

    _chunks: LRUCache[tuple[int, int], Chunk]
    """
    Mapping from chunk coords (cx, cy) to generated chunks.
    """

    @classmethod
    def new(cls, 
            *, 
            chunk_size: int, 
            generator: TerrainGenerator,
            max_cached_chunks: int,
            ) -> WorldMap:
        """
        Construct a new infinite world map.

        Parameters
        ----------
        chunk_size : int
            Width and height of each chunk (tiles).
        generator : TerrainGenerator
            Seeded generator used to produce terrain.
        max_cached_chunks : int
            Size of LRU cache for chunks.

        Returns
        -------
        WorldMap
            A newly created WorldMap. 
        """
        return cls(
            chunk_size=chunk_size,
            generator=generator,
            max_cached_chunks=max_cached_chunks,
            _chunks=LRUCache(capacity=max_cached_chunks)
        )


    def _split_coords(self, 
                      x: int, 
                      y: int,
                      ) -> tuple[int, int, int, int]:
        """
        Convert world coords into chunk and local coords.

        Parameters
        ----------
        x : int
            World x-coordinates in tiles.
        y : int
            World y-coordinates in tiles.

        Returns
        -------
        tuple[int, int, int, int]
            Chunk x, chunk y, local x, local y.
        """
        s = self.chunk_size
        cx = x // s
        cy = y // s
        lx = x - cx * s
        ly = y - cy * s
        return cx, cy, lx, ly

    def _get_chunk(self, cx: int, cy: int) -> Chunk:
        """
        Retrieve a chunk by chunk coords.

        Parameters
        ----------
        cx : int
            Chunk x-coordinates
        cy : int
            Chunk y-coordinates

        Returns
        -------
        Chunk
            The requested chunk.
        """
        key = (cx, cy)

        chunk = self._chunks.get(key)
        if chunk is not None:
            return chunk

        terrain = self.generator.generate_chunk(
            cx = cx,
            cy = cy,
            chunk_size = chunk_size,
        )

        chunk = Chunk(size=self.chunk_size, terrain=terrain)
        self._chunks.put(key, chunk)
        return chunk

    def chunk_at(self, cx: int, cy: int) -> Chunk:
        """
        Retrieve a chunk at chunk coordinates.

        Parameters
        ----------
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.

        Returns
        -------
        Chunk
            Chunk at (cx, cy).
        """
        return self._get_chunk(cx, cy)

    def terrain_at(self, x: int, y: int):
        """
        Retrieve the terrain type at world coordinates.

        Parameters
        ----------
        x : int
            World-space X coordinate in tiles.
        y : int
            World-space Y coordinate in tiles.

        Returns
        -------
        TileType
            Terrain type at the given world position.
        """
        cx, cy, lx, ly = self._split_coords(x, y)
        return self._get_chunk(cx, cy).terrain_at(lx, ly)

    def chunk_count(self) -> int:
        """
        Return the number of currently cached chunks.

        Returns
        -------
        int
            Number of chunks stored in the world map cache.
        """
        return len(self._chunks)
