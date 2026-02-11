"""
Generates terrain for map.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic

from noise import pnoise2

from .level import LevelT
from .level.elevation import ElevationLevel
from .level.level_grid import LevelGrid
from .level.moisture import MoistureLevel
from .tile_type import TileType


@dataclass(frozen=True, slots=True)
class _TerrainParameter(Generic[LevelT]):
    """
    One level of perlin terrain noise.
    """

    seed: int
    """
    World seed.
    """

    scale: float
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

    cutoffs: tuple[tuple[int, LevelT], ...]
    """
    Ordered cutoffs mapping quantized values to levels.

    Entries of form (threshold, level).
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
            octaves=self.octaves,
            persistence=self.persistence,
            lacunarity=self.lacunarity,
            base=self.seed,
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
        v = self.sample(x=x, y=y)
        return int((v + self.bias) * self.amplitude)

    def level_at(self, *, x: float, y: float) -> LevelT:
        """
        Sample and classify into a level using cutoffs.

        Parameters
        ----------
        x : float
            World x-coordinate in tiles.
        y : float
            World y-coordinate in tiles.

        Returns
        -------
        LevelT
            Classified level.
        """
        q = self.sample_q(x=x, y=y)
        for thr, lvl in self.cutoffs:
            if q <= thr:
                return lvl
        raise ValueError("Cutoffs do not cover quantized range.")


@dataclass(frozen=True, slots=True)
class TerrainGenerator:
    """
    Deterministic procedural generator for base terrain.
    """

    seed: int
    """
    World seed used to generate terrain determiniarically.
    """

    land_grid: LevelGrid
    """
    Level grid mapping land levels to tile types.
    """

    elevation: _TerrainParameter = field(init=False)
    """
    Elevation noise parameter.
    """

    moisture: _TerrainParameter = field(init=False)
    """
    Moisture noise parameter.
    """

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "elevation",
            _TerrainParameter(
                seed=self.seed,
                scale=100.0,
                octaves=3,
                persistence=0.5,
                lacunarity=4.0,
                amplitude=5.0,
                bias=0.0,
                cutoffs=(
                    (-1, ElevationLevel.LOW),
                    (999999, ElevationLevel.HIGH),
                ),
            ),
        )

        object.__setattr__(
            self,
            "moisture",
            _TerrainParameter(
                seed=self.seed + 1337,
                scale=200.0,
                octaves=2,
                persistence=0.5,
                lacunarity=2.5,
                amplitude=5.0,
                bias=0.0,
                cutoffs=(
                    (-0.8, MoistureLevel.DRY),
                    (999999, MoistureLevel.WET),
                ),
            ),
        )

    def generate_chunk(self, *, cx: int, cy: int, chunk_size: int) -> list[TileType]:
        """
        Generate terrain for a single chunk.

        Parameters
        ----------
        cx : int
            Chunk x-coordinate
        cy : int
            Chunk y-coordinate
        chunk_size : int
            Widtgh and height of chunk in tiles.

        Returns
        -------
        list[TileType]
            Flat row-major buffer of TileType values.
        """
        wx0 = cx * chunk_size
        wy0 = cy * chunk_size

        out: list[TileType] = [TileType.DEFAULT_GRASS] * (chunk_size**2)

        xs = [float(wx0 + lx) for lx in range(chunk_size)]

        for ly in range(chunk_size):
            y = float(wy0 + ly)
            row_off = ly * chunk_size

            for lx, x in enumerate(xs):
                elev = self.elevation.level_at(x=x, y=y)

                if elev is ElevationLevel.LOW:
                    out[row_off + lx] = TileType.DEFAULT_WATER
                    continue

                moist = self.moisture.level_at(x=x, y=y)

                out[row_off + lx] = self.land_grid.get(elev, moist)

        return out
