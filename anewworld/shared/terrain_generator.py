"""
Generates terrain for map.
"""

from __future__ import annotations

from dataclasses import dataclass

from noise import pnoise2

from .tile_type import TileType


@dataclass(frozen=True, slots=True)
class _TerrainParameter:
    """
    One level of perlin terrain noise.
    """

    seed: int
    """
    World seed.
    """

    scale: int
    """
    Noise scale.

    Higher = smoother, larger features.
    """

    octaves: int
    """
    Perlin octaves.
    """

    persistence: float
    """
    Perlin persistence.
    """

    lacunarity: float
    """
    Perlin lacunarity
    """

    amplitude: float
    """
    Multiplier applied to noise value before quantization.
    """

    bias: float
    """
    Bias added to noise value before quantization.
    """

    def sample(self, *, x: float, y: float) -> float:
        """
        Sample raw perlin noise at (x, y).

        Parameters
        ----------
        x : float
            World x-coordinate in tiles
        y : float
            World y-coordinate in tiles
        """
        inv_scale = 1.0 / self.scale
        return pnoise2(
            x * inv_scale,
            y * inv_scale,
            octaves = self.octaves,
            persistence = self.persistence,
            lacunarity = self.lacunarity,
            base = self.seed
        )

    def sample_q(self, *, x: float, y: float) -> int:
        """
        Sample and quantize perlin noise at (x, y).

        Parameters
        ----------
        x : float
            World x-coordinate in tiles.
        y : float
            World y-coordinate in tiles.

        Returns
        -------
        int
            Quantized noise value.
        """
        v = self.sample(x = x, y = y)
        return int((v + self.bias) * self.amplitude)


@dataclass(frozen=True, slots=True)
class TerrainGenerator:
    """
    Deterministic procedural generator for base terrain.
    """

    seed: int
    """
    World seed used to generate terrain determiniarically.
    """

    elevation: _TerrainParameter = _TerrainParameter(
        seed = self.seed,
        scale = 100.0,
        octaves = 3,
        persistence = 0.5,
        lacunarity = 4.0,
        amplitude = 5.0 ,
        bias = 0.0
    )

    moisture: _TerrainParameter = _TerrainParameter(
        seed = self.seed,
        scale = 200.0,
        octaves = 2,
        persistence = 0.5,
        lacunarity = 2.5,
        amplitude = 5.0,
        bias = 0.0
    )

    
