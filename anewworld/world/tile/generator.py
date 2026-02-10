"""
Generates terrain given world seed.
"""

from __future__ import annotations

from dataclasses import dataclass

from noise import pnoise2

from anewworld.world.tile.tiletype import TileType


@dataclass(frozen=True, slots=True)
class TerrainGenerator:
    """
    Deterministic procedural generator for base terrain.
    """

    seed: int
    """
    World seed used to generate terrain deterministically.
    """

    scale: float = 100.0
    """
    Noise scale (higher = smoother / larger features).
    """

    octaves: int = 3
    """
    Perlin octaves.
    """

    persistence: float = 0.5
    """
    Perlin persistence.
    """

    lacunarity: float = 4.0
    """
    Perlin lacunarity.
    """

    amplitude: float = 5.0
    """
    Multiplier applied to noise value before quantization.
    """

    bias: float = 0.0
    """
    Bias added to noise value before quantization.
    """

    water_threshold: int = -0.5
    """
    Tiles with quantized value <= this become water.
    """

    def generate_chunk(
        self,
        *,
        cx: int,
        cy: int,
        chunk_size: int,
    ) -> list[TileType]:
        """
        Generate base terrain for single chunk.

        Parameters
        ----------
        cx: int
            Chunk x coordinate.
        cy: int
            Chunk y coordinate.
        chunk_size: int
            Width and height of the chunk in tiles.

        Returns
        -------
        list[TileType]
            Terrain buffer to fill chunk.
        """
        wx0 = cx * chunk_size
        wy0 = cy * chunk_size

        inv_scale = 1.0 / self.scale

        pn2 = pnoise2
        octv = self.octaves
        pers = self.persistence
        lac = self.lacunarity
        base = self.seed
        amp = self.amplitude
        bias = self.bias
        thr = self.water_threshold

        xs = [(wx0 + lx) * inv_scale for lx in range(chunk_size)]

        out: list[TileType] = [TileType.LAND] * (chunk_size * chunk_size)
        for ly in range(chunk_size):
            y = (wy0 + ly) * inv_scale
            row_off = ly * chunk_size

            for lx, x in enumerate(xs):
                v = pn2(
                    x,
                    y,
                    octaves=octv,
                    persistence=pers,
                    lacunarity=lac,
                    base=base,
                )
                q = int((v + bias) * amp)
                out[row_off + lx] = TileType.WATER if q <= thr else TileType.LAND

        return out

    def terrain_at(
        self,
        *,
        x: int,
        y: int,
        chunk_size: int,
    ) -> TileType:
        """
        Query generated base terrain at specific world tile coord.

        Parameters
        ----------
        x: int
            World x coordinate in tiles.
        y: int
            World y coordinate in tiles.
        chunk_size: int
            Width and height of a chunk in tiles.

        Returns
        -------
        TileType
            Generated terrain type at (x, y).
        """
        inv_scale = 1.0 / self.scale

        pn2 = pnoise2
        octv = self.octaves
        pers = self.persistence
        lac = self.lacunarity
        base = self.seed
        amp = self.amplitude
        bias = self.bias
        thr = self.water_threshold

        nx = x * inv_scale
        ny = y * inv_scale

        v = pn2(
            nx,
            ny,
            octaves=octv,
            persistence=pers,
            lacunarity=lac,
            base=base,
        )
        q = int((v + bias) * amp)
        return TileType.WATER if q <= thr else TileType.LAND

