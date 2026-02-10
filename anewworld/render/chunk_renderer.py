"""
Chunk-based renderer with surface caching.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from anewworld.render.camera import Camera
from anewworld.render.palette import TerrainPalette
from anewworld.world.tile.tilemap import TileMap
from anewworld.render.chunk_residency import ChunkResidency, ChunkKey


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

    build_budget_ms: float
    """
    Maximum time to spend building new chunk surfaces per frame.
    """

    residency: ChunkResidency
    """
    Shared chunk residency policy (LRU + build queue).
    """

    _cache: dict[ChunkKey, _CachedChunkSurface]
    """
    Cached surfaces keyed by chunk coordinates.
    """

    _placeholder: pygame.Surface
    """
    Placeholder surface used for chunks not yet built.
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
        build_budget_ms: float = 3.0,
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
        build_budget_ms : float
            Maximum time to spend building new chunk surfaces per frame.

        Returns
        -------
        ChunkRenderer
            A newly constructed renderer.
        """
        if palette is None:
            palette = TerrainPalette()

        placeholder_px = chunk_size * tile_size
        placeholder = pygame.Surface((placeholder_px, placeholder_px)).convert()
        placeholder.fill((200, 50, 200))

        return cls(
            tile_size=tile_size,
            chunk_size=chunk_size,
            max_cached_chunks=max_cached_chunks,
            padding_chunks=padding_chunks,
            palette=palette,
            build_budget_ms=build_budget_ms,
            residency=ChunkResidency.new(max_cached_chunks=max_cached_chunks),
            _cache={},
            _placeholder=placeholder,
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

        tile_size = self.tile_size
        chunk_size = self.chunk_size
        chunk_px = chunk_size * tile_size

        cam_x = int(round(camera.x_px))
        cam_y = int(round(camera.y_px))

        left = cam_x
        top = cam_y
        right = cam_x + screen_w
        bottom = cam_y + screen_h

        cx0 = self._floor_div(left, chunk_px) - self.padding_chunks
        cy0 = self._floor_div(top, chunk_px) - self.padding_chunks
        cx1 = self._floor_div(right - 1, chunk_px) + self.padding_chunks
        cy1 = self._floor_div(bottom - 1, chunk_px) + self.padding_chunks

        visible_keys = self.residency.visible_keys(cx0=cx0, cy0=cy0, cx1=cx1, cy1=cy1)

        self.residency.queue_missing(visible_keys, is_present=self._is_cached)
        self._build_budgeted(tilemap=tilemap)
        self._evict_if_needed()

        blit = screen.blit
        placeholder = self._placeholder
        cache = self._cache
        touch = self.residency.touch

        for cy in range(cy0, cy1 + 1):
            dest_y = cy * chunk_px - cam_y
            for cx in range(cx0, cx1 + 1):
                key = (cx, cy)
                cached = cache.get(key)
                if cached is None:
                    surf = placeholder
                else:
                    surf = cached.surface
                    touch(key)

                dest_x = cx * chunk_px - cam_x
                blit(surf, (dest_x, dest_y))

    def _is_cached(self, key: ChunkKey) -> bool:
        """
        Return True if a chunk surface is already cached.
        """
        return key in self._cache

    def _build_budgeted(self, *, tilemap: TileMap) -> None:
        """
        Build queued chunk surfaces up to the per-frame time budget.

        Parameters
        ----------
        tilemap : TileMap
            Tile map providing terrain data.
        """
        import time

        t0 = time.perf_counter()
        budget = self.build_budget_ms / 1000.0

        pop_next = self.residency.pop_next_build
        touch = self.residency.touch
        cache = self._cache

        while (time.perf_counter() - t0) < budget:
            key = pop_next()
            if key is None:
                return

            if key in cache:
                continue

            cx, cy = key
            surf = self._build_chunk_surface(tilemap=tilemap, cx=cx, cy=cy)
            cache[key] = _CachedChunkSurface(surface=surf)
            touch(key)

    def _get_chunk_surface(self, *, tilemap: TileMap, cx: int, cy: int) -> pygame.Surface:
        """
        Retrieve a cached chunk surface if available.

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
            Cached surface for the chunk, or the placeholder if missing.
        """
        key = (cx, cy)
        cached = self._cache.get(key)
        if cached is None:
            self.residency.queue_missing([key], is_present=self._is_cached)
            return self._placeholder

        self.residency.touch(key)
        return cached.surface

    def _build_chunk_surface(self, *, tilemap: TileMap, cx: int, cy: int) -> pygame.Surface:
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
        surface_for = self.palette.surface_for
        terrain_at = tilemap.terrain_at
        blit = surface.blit

        for ly in range(chunk_size):
            wy = base_y + ly
            py = ly * tile_size
            for lx in range(chunk_size):
                wx = base_x + lx
                px = lx * tile_size

                terrain = terrain_at(wx, wy)

                tile = tile_for.get(terrain)
                if tile is None:
                    tile = surface_for(terrain, tile_size=tile_size)
                    tile_for[terrain] = tile

                blit(tile, (px, py))

        return surface

    def _evict_if_needed(self) -> None:
        """
        Evict least recently used cached chunk surfaces if cache is full.
        """
        to_evict = self.residency.evict_keys(resident_count=len(self._cache))
        if not to_evict:
            return

        cache = self._cache
        for key in to_evict:
            cache.pop(key, None)

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

