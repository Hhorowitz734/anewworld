"""
Client side configuration module.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowConfig:
    
    screen_width: int = 1000
    """
    Width of screen, pixels.
    """

    screen_height: int = 800
    """
    Height of screen, pixels.
    """

    tile_size: int = 10
    """
    Tile size, pixels.
    """

    fps: int = 120
    """
    Frames per second.
    """
