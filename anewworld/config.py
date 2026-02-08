"""
Game configuration for anewworld.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameConfig:
    """
    Global configuration settings for the game.
    """

    screen_width: int = 800
    """
    Width of the game window in pixels.
    """

    screen_height: int = 600
    """
    Height of the game window in pixels.
    """

    fps: int = 60
    """
    Target frames per second for the main loop.
    """

    tile_size: int = 10
    """
    Size of a single tile in pixels.
    """

    chunk_size: int = 32
    """
    Width and height of a tile chunk, in tiles.
    """

    debug: bool = True
    """
    Developer debug flag.
    """
