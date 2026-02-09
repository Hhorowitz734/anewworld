"""
Tile map and chunk dataclasses.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .tile import Tile
from .tiletype import TileType


@dataclass(slots=True)
class _Chunk:
    """
    Internal storage unit for a fixed-size square region of tiles.
    """

    size: int
    """
    Width and height of the chunk in tiles.
    """

    tiles: list[Tile]
    """
    Flat list of tiles stored in row-major order.
    Length is size * size.
    """

    @classmethod
    def filled(cls, *, size: int, default_terrain: TileType) -> _Chunk:
        """
        Create a chunk completely filled with a single terrain type.

        Parameters
        ----------
        size : int
            Width and height of the chunk in tiles.
        default_terrain : TileType
            Terrain type assigned to all tiles in the chunk.

        Returns
        -------
        _Chunk
            A newly created chunk filled with default tiles.
        """
        ttype = random.choice(list(TileType))
        return cls(
            size=size,
            tiles=[Tile(ttype) for _ in range(size * size)],
        )

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
            Index into the flat tile list.
        """
        return y * self.size + x

    def tile_at(self, x: int, y: int) -> Tile:
        """
        Retrieve the tile at local chunk coordinates.

        Parameters
        ----------
        x : int
            X-coordinate within the chunk.
        y : int
            Y-coordinate within the chunk.

        Returns
        -------
        Tile
            The tile at the given local position.
        """
        return self.tiles[self._idx(x, y)]


@dataclass(slots=True)
class TileMap:
    """
    Infinite tile map backed by lazily-created fixed-size chunks.

    The tile map supports unbounded integer coordinates. Tiles are
    created on demand and default to a specified terrain type.
    """

    chunk_size: int
    """
    Width and height of each chunk in tiles.
    """

    default_terrain: TileType
    """
    Terrain type assigned to all tiles in newly created chunks.
    """

    _chunks: dict[tuple[int, int], _Chunk]
    """
    Mapping from chunk coordinates (cx, cy) to chunk instances.
    """

    @classmethod
    def new(cls, *, chunk_size: int, default_terrain: TileType) -> TileMap:
        """
        Construct a new infinite tile map.

        Parameters
        ----------
        chunk_size : int
            Width and height of each chunk in tiles.
        default_terrain : TileType
            Terrain type used for all tiles until explicitly changed.

        Returns
        -------
        TileMap
            A newly created infinite tile map.
        """
        return cls(
            chunk_size=chunk_size,
            default_terrain=default_terrain,
            _chunks={},
        )

    def _split_coords(self, x: int, y: int) -> tuple[int, int, int, int]:
        """
        Convert world coordinates into chunk and local coordinates.

        Parameters
        ----------
        x : int
            World-space X coordinate.
        y : int
            World-space Y coordinate.

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
        Retrieve a chunk by chunk coordinates, creating it if missing.

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
            chunk = _Chunk.filled(
                size=self.chunk_size,
                default_terrain=self.default_terrain,
            )
            self._chunks[key] = chunk
        return chunk

    def tile_at(self, x: int, y: int) -> Tile:
        """
        Retrieve the tile at world coordinates.

        Parameters
        ----------
        x : int
            World-space X coordinate.
        y : int
            World-space Y coordinate.

        Returns
        -------
        Tile
            The tile at the given world position.
        """
        cx, cy, lx, ly = self._split_coords(x, y)
        return self._get_chunk(cx, cy).tile_at(lx, ly)

    def terrain_at(self, x: int, y: int) -> TileType:
        """
        Retrieve the terrain type at world coordinates.

        Parameters
        ----------
        x : int
            World-space X coordinate.
        y : int
            World-space Y coordinate.

        Returns
        -------
        TileType
            Terrain type of the tile.
        """
        return self.tile_at(x, y).terrain

    def set_terrain(self, x: int, y: int, terrain: TileType) -> None:
        """
        Set the terrain type at world coordinates.

        Parameters
        ----------
        x : int
            World-space X coordinate.
        y : int
            World-space Y coordinate.
        terrain : TileType
            New terrain type for the tile.
        """
        self.tile_at(x, y).terrain = terrain

    def chunk_count(self) -> int:
        """
        Return the number of currently allocated chunks.

        Returns
        -------
        int
            Number of chunks stored in the tile map.
        """
        return len(self._chunks)
