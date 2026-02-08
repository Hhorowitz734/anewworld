"""
Game configuration for anewworld.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameConfig:
    """
    Game settings.
    """

    screen_width: int = 800
    """
    Screen width of game.
    """

    screen_height: int = 600
    """
    Screen height of game.
    """

    fps: int = 60
    """
    Frames per second.
    """

    tile_size: int = 10
    """
    Size of tile.
    """

    map_width: int = 50
    """
    Map width (tiles).
    """

    map_height: int = 40
    """
    Map height (tiles).
    """

    debug: bool = True
    """
    Developer debug flag.
    """
