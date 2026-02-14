"""
Client side configuration module.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowConfig:
    """
    Configuration of instance window.
    """

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


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """
    Configuration of client connection.
    """

    singleplayer: bool = False
    """
    Decides whether to connect to server.
    """


@dataclass(frozen=True, slots=True)
class DevConfig:
    """
    Developer only configuration.
    """

    debug: bool = True
    """
    Debug mode.
    """
