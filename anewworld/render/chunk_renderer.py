"""
Chunk-based renderer with surface caching.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict

import pygame

from anewworld.render.camera import Camera
from anewworld.render.palette import TerrainPalette
from anewworld.world.tile.tilemap import TileMap


@dataclass(slots=True)
class _CachedChunkSurface:
    """
    Cached rendering surface for a chunk.
    """

    surface: pygame.Surface
    """
    Pre-rendered chunk surface.
    """


@dataclass(slots=True)
class ChunkRenderer:
    """
    Render an infinite tile map using cached chunk surfaces.
    """

    tile_size: int
    """
    Size of a tile in pixels.
    """

    chunk_size: int
    """
    Width and height of a chunk in tiles.
    """

    max_cached_chunks: int
    """
    Maximum number of cached chunk surfaces to keep in memory.
    """

    padding_chunks: int
    """
    Number of extra chunks to render beyond the viewport in each
    direction.
    """

    palette: TerrainPalette
    """
    Palette mapping terrain types to tile surfaces.
    """

    _cache: dict[tuple[int, int], _CachedChunkSurface]
    """
    Cached surfaces keyed by chunk coordinates.
    """

    _lru: OrderedDict[tuple[int, int], None]
    """
    LRU ordering for cached chunk keys.
    """

    @classmethod
    def new(
        cls,
        *,
        tile_size: int,
        chunk_size: int,
        max_cached_chunks: int,
        padding_chunks: int,
        palette: TerrainPalette | None = None,
    ) -> ChunkRenderer:
        """
        Construct a new chunk renderer.

        Parameters
        ----------
        tile_size : int
            Size of a tile in pixels.
        chunk_size : int
            Width and height of a chunk in tiles.
        max_cached_chunks : int
            Maximum number of cached chunk surfaces to keep in memory.
        padding_chunks : int
            Number of extra chunks to render beyond the viewport.
        palette : TerrainPalette | None
            Palette mapping terrain types to surfaces.

        Returns
        -------
        ChunkRenderer
            A newly constructed renderer.
        """
        if palette is None:
            palette = TerrainPalette()

        return cls(
            tile_size=tile_size,
            chunk_size=chunk_size,
            max_cached_chunks=max_cached_chunks,
            padding_chunks=padding_chunks,
            palette=palette,
            _cache={},
            _lru=OrderedDict(),
        )

    def draw(
        self,
        *,
        screen: pygame.Surface,
        tilemap: TileMap,
        camera: Camera,
    ) -> None:
        """
        Draw visible chunks to the screen.

        Parameters
        ----------
        screen : pygame.Surface
            Destination surface for rendering.
        tilemap : TileMap
            Tile map to render.
        camera : Camera
            Camera describing visible region in world px.
        """
        screen_w = screen.get_width()
        screen_h = screen.get_height()

        chunk_px = self.chunk_size * self.tile_size

        left, top, right, bottom = camera.viewport_px(
            screen_width=screen_w,
            screen_height=screen_h,
        )

        cx0 = self._floor_div(left, chunk_px) - self.padding_chunks
        cy0 = self._floor_div(top, chunk_px) - self.padding_chunks
        cx1 = self._floor_div(right - 1, chunk_px) + self.padding_chunks
        cy1 = self._floor_div(bottom - 1, chunk_px) + self.padding_chunks

        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                surf = self._get_chunk_surface(tilemap=tilemap, cx=cx, cy=cy)
                dest_x = cx * chunk_px - camera.x_px
                dest_y = cy * chunk_px - camera.y_px
                screen.blit(surf, (dest_x, dest_y))

        self._evict_if_needed()

    def _get_chunk_surface(
        self, *, tilemap: TileMap, cx: int, cy: int
    ) -> pygame.Surface:
        """
        Retrieve a cached chunk surface, building it if missing.

        Parameters
        ----------
        tilemap : TileMap
            Tile map providing terrain data.
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.

        Returns
        -------
        pygame.Surface
            Cached (or newly built) surface for the chunk.
        """
        key = (cx, cy)
        cached = self._cache.get(key)
        if cached is None:
            surface = self._build_chunk_surface(tilemap=tilemap, cx=cx, cy=cy)
            cached = _CachedChunkSurface(surface=surface)
            self._cache[key] = cached

        self._touch_lru(key)
        return cached.surface

    def _build_chunk_surface(
        self, *, tilemap: TileMap, cx: int, cy: int
    ) -> pygame.Surface:
        """
        Build a surface for a chunk by drawing all tiles in it once.

        Parameters
        ----------
        tilemap : TileMap
            Tile map providing terrain data.
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.

        Returns
        -------
        pygame.Surface
            Newly created surface containing the chunk's pixels.
        """

        tile_size = self.tile_size

        chunk_size = self.chunk_size
        chunk_px = chunk_size * tile_size

        surface = pygame.Surface((chunk_px, chunk_px)).convert()

        base_x = cx * chunk_size
        base_y = cy * chunk_size

        tile_for: dict[object, pygame.Surface] = {}

        for ly in range(chunk_size):
            wy = base_y + ly
            py = ly * tile_size
            for lx in range(chunk_size):
                wx = base_x + lx
                px = lx * tile_size

                terrain = tilemap.terrain_at(wx, wy)

                tile = tile_for.get(terrain)
                if tile is None:
                    tile = self.palette.surface_for(terrain, tile_size=tile_size)
                    tile_for[terrain] = tile

                surface.blit(tile, (px, py))


        return surface

    def _touch_lru(self, key: tuple[int, int]) -> None:
        """
        Mark a chunk key as most recently used.

        Parameters
        ----------
        key : tuple[int, int]
            Chunk coordinate key.
        """
        self._lru[key] = None
        self._lru.move_to_end(key, last=True)

    def _evict_if_needed(self) -> None:
        """
        Evict least recently used cached chunk surfaces if cache is full.
        """
        while len(self._cache) > self.max_cached_chunks:
            oldest_key, _ = self._lru.popitem(last=False)
            self._cache.pop(oldest_key, None)

    @staticmethod
    def _floor_div(a: int, b: int) -> int:
        """
        Floor divide for chunk coordinate math.

        Parameters
        ----------
        a : int
            Dividend.
        b : int
            Divisor.

        Returns
        -------
        int
            Floor-divided result.
        """
        return a // b

