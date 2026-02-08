"""
Tile map and chunk dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass

from .generator import TerrainGenerator
from .tiletype import TileType


@dataclass(slots=True)
class _Chunk:
    """
    Internal storage unit for a fixed-size square region of terrain.
    """

    size: int
    """
    Width and height of the chunk in tiles.
    """

    terrain: list[TileType]
    """
    Flat list of terrain values stored in row-major order.
    Length is size * size.
    """

    def _idx(self, x: int, y: int) -> int:
        """
        Convert local (x, y) coordinates into a flat list index.

        Parameters
        ----------
        x : int
            X-coordinate within the chunk.
        y : int
            Y-coordinate within the chunk.

        Returns
        -------
        int
            Index into the flat terrain list.
        """
        return y * self.size + x

    def terrain_at(self, x: int, y: int) -> TileType:
        """
        Retrieve the terrain at local chunk coordinates.

        Parameters
        ----------
        x : int
            X-coordinate within the chunk.
        y : int
            Y-coordinate within the chunk.

        Returns
        -------
        TileType
            Terrain type at the given local position.
        """
        return self.terrain[self._idx(x, y)]


@dataclass(slots=True)
class TileMap:
    """
    Infinite tile map backed by lazily-generated fixed-size chunks.

    The tile map supports unbounded integer coordinates. Chunks are
    generated on demand using a seeded terrain generator.
    """

    chunk_size: int
    """
    Width and height of each chunk in tiles.
    """

    generator: TerrainGenerator
    """
    Seeded terrain generator used to produce base terrain.
    """

    _chunks: dict[tuple[int, int], _Chunk]
    """
    Mapping from chunk coordinates (cx, cy) to generated chunks.
    """

    @classmethod
    def new(cls, *, chunk_size: int, generator: TerrainGenerator) -> TileMap:
        """
        Construct a new infinite tile map.

        Parameters
        ----------
        chunk_size : int
            Width and height of each chunk in tiles.
        generator : TerrainGenerator
            Seeded generator used to produce terrain.

        Returns
        -------
        TileMap
            A newly created infinite tile map.
        """
        return cls(
            chunk_size=chunk_size,
            generator=generator,
            _chunks={},
        )

    def _split_coords(self, x: int, y: int) -> tuple[int, int, int, int]:
        """
        Convert world coordinates into chunk and local coordinates.

        Parameters
        ----------
        x : int
            World-space X coordinate in tiles.
        y : int
            World-space Y coordinate in tiles.

        Returns
        -------
        tuple[int, int, int, int]
            Chunk X, chunk Y, local X, local Y.
        """
        s = self.chunk_size
        cx = x // s
        cy = y // s
        lx = x - cx * s
        ly = y - cy * s
        return cx, cy, lx, ly

    def _get_chunk(self, cx: int, cy: int) -> _Chunk:
        """
        Retrieve a chunk by chunk coordinates, generating it if missing.

        Parameters
        ----------
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.

        Returns
        -------
        _Chunk
            The requested chunk.
        """
        key = (cx, cy)
        chunk = self._chunks.get(key)
        if chunk is None:
            terrain = self.generator.generate_chunk(
                cx=cx,
                cy=cy,
                chunk_size=self.chunk_size,
            )
            chunk = _Chunk(size=self.chunk_size, terrain=terrain)
            self._chunks[key] = chunk
        return chunk

    def terrain_at(self, x: int, y: int) -> TileType:
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
        Return the number of currently allocated chunks.

        Returns
        -------
        int
            Number of chunks stored in the tile map.
        """
        return len(self._chunks)

