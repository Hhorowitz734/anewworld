"""
Chunk-based renderer with surface caching.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict, deque
from typing import Deque, Set

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

    build_budget_ms: float
    """
    Maximum time to spend building new chunk surfaces per frame.
    """

    _cache: dict[tuple[int, int], _CachedChunkSurface]
    """
    Cached surfaces keyed by chunk coordinates.
    """

    _lru: OrderedDict[tuple[int, int], None]
    """
    LRU ordering for cached chunk keys.
    """

    _build_queue: Deque[tuple[int, int]]
    """
    Queue of chunk keys awaiting surface construction.
    """

    _build_set: Set[tuple[int, int]]
    """
    Set of queued chunk keys to avoid duplicates.
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
            _cache={},
            _lru=OrderedDict(),
            _build_queue=deque(),
            _build_set=set(),
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
        import time

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

        self._enqueue_visible(cx0=cx0, cy0=cy0, cx1=cx1, cy1=cy1)
        self._build_budgeted(tilemap=tilemap)

        blit = screen.blit
        placeholder = self._placeholder

        for cy in range(cy0, cy1 + 1):
            dest_y = cy * chunk_px - cam_y
            for cx in range(cx0, cx1 + 1):
                key = (cx, cy)
                cached = self._cache.get(key)
                if cached is None:
                    surf = placeholder
                else:
                    surf = cached.surface
                    self._touch_lru(key)

                dest_x = cx * chunk_px - cam_x
                blit(surf, (dest_x, dest_y))

        self._evict_if_needed()

    def _enqueue_visible(self, *, cx0: int, cy0: int, cx1: int, cy1: int) -> None:
        """
        Queue missing chunk surfaces for the current visible region.

        Parameters
        ----------
        cx0 : int
            Minimum visible chunk X.
        cy0 : int
            Minimum visible chunk Y.
        cx1 : int
            Maximum visible chunk X.
        cy1 : int
            Maximum visible chunk Y.
        """
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                key = (cx, cy)
                if key in self._cache or key in self._build_set:
                    continue
                self._build_queue.append(key)
                self._build_set.add(key)

    def _build_budgeted(self, *, tilemap: TileMap) -> None:
        """
        Build queued chunk surfaces up to the per-frame time budget.

        Parameters
        ----------
        tilemap : TileMap
            Tile map providing terrain data.
        """
        import time

        if not self._build_queue:
            return

        t0 = time.perf_counter()
        budget = self.build_budget_ms / 1000.0

        while self._build_queue and (time.perf_counter() - t0) < budget:
            cx, cy = self._build_queue.popleft()
            key = (cx, cy)
            self._build_set.discard(key)

            if key in self._cache:
                continue

            surf = self._build_chunk_surface(tilemap=tilemap, cx=cx, cy=cy)
            self._cache[key] = _CachedChunkSurface(surface=surf)
            self._touch_lru(key)

    def _get_chunk_surface(
        self, *, tilemap: TileMap, cx: int, cy: int
    ) -> pygame.Surface:
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
            if key not in self._build_set:
                self._build_queue.append(key)
                self._build_set.add(key)
            return self._placeholder

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

