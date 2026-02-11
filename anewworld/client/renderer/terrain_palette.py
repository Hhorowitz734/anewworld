"""
Palette mappings used by the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from anewworld.shared.tile_type import TileType


@dataclass(frozen=True, slots=True)
class TerrainPalette:
    """
    Surface palette for terrain rendering.
    """

    land: tuple[int, int, int] = (70, 150, 80)
    """
    RGB color for land tiles.
    """

    water: tuple[int, int, int] = (50, 110, 190)
    """
    RGB color for water tiles.
    """

    rainforest: tuple[int, int, int] = (10, 48, 10)
    """
    RGB color for rainforest.
    """

    deepwater: tuple[int, int, int] = (10, 70, 130)
    """
    RGB color for deep water.
    """

    unknown: tuple[int, int, int] = (200, 50, 200)
    """
    RGB color for unknown tiles.
    """

    def surface_for(self, terrain: TileType, *, tile_size: int) -> pygame.Surface:
        """
        Map a terrain type to a pre-colored tile surface.

        Parameters
        ----------
        terrain : TileType
            Terrain type to map.
        tile_size : int
            Square tile size in pixels.

        Returns
        -------
        pygame.Surface
            A surface of size (tile_size, tile_size) filled with the
            terrain's color, converted for fast blitting.
        """
        cache = self._surface_cache()
        key = (tile_size, terrain)

        surf = cache.get(key)
        if surf is not None:
            return surf

        color = self._color_for(terrain)
        surf = pygame.Surface((tile_size, tile_size)).convert()
        surf.fill(color)
        cache[key] = surf
        return surf

    def _color_for(self, terrain: TileType) -> tuple[int, int, int]:
        """
        Map a terrain type to an RGB color.
        """
        if terrain == TileType.DEFAULT_GRASS:
            return self.land
        if terrain == TileType.DEFAULT_WATER:
            return self.water
        if terrain == TileType.DARK_GRASS:
            return self.rainforest
        if terrain == TileType.DEEP_WATER:
            return self.deepwater
        return self.unknown

    @staticmethod
    def _surface_cache() -> dict[tuple[int, TileType], pygame.Surface]:
        """
        Per-process surface cache shared across TerrainPalette instances.

        The cache is keyed by (tile_size, terrain) and stores converted
        surfaces for fast blitting.
        """
        cache = getattr(TerrainPalette._surface_cache, "_cache", None)
        if cache is None:
            cache = {}
            setattr(TerrainPalette._surface_cache, "_cache", cache)
        return cache
