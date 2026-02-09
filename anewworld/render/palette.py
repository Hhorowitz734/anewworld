"""
Palette mappings used by the renderer.
"""

from dataclasses import dataclass

from anewworld.world.tile.tiletype import TileType


@dataclass(frozen=True, slots=True)
class TerrainPalette:
    """
    Color palette for terrain rendering.
    """

    land: tuple[int, int, int] = (70, 150, 80)
    """
    RGB color for land tiles.
    """

    river: tuple[int, int, int] = (50, 110, 190)
    """
    RGB color for river tiles.
    """

    unknown: tuple[int, int, int] = (200, 50, 200)
    """
    RGB color for unknown tiles.
    """

    def color_for(self, terrain: TileType) -> tuple[int, int, int]:
        """
        Map a terrain type to an RGB color.

        Parameters
        ----------
        terrain : TileType
            Terrain type to map.

        Returns
        -------
        tuple[int, int, int]
            RGB color for the terrain.
        """
        if terrain == TileType.LAND:
            return self.land
        if terrain == TileType.RIVER:
            return self.river
        return self.unknown
