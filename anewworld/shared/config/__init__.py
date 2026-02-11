"""
Shared client-server configurations.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorldConfig:
    """
    Configuration of game world.
    """

    chunk_size: int = 64
    """
    Width and height of chunk (tiles).
    """

    world_seed: int = 1
    """
    Seed for procedural world generation.
    """
