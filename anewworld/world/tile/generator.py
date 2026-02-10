"""Generates terrain given world seed.
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

    elevation_thresholds: tuple[tuple[int, TileType], ...] = (
        (-2, TileType.DEEPWATER),
        (-1, TileType.WATER),
    )
    """
    Ordered elevation thresholds.

    Each entry is (threshold, TileType). The first entry whose threshold
    is >= the quantized elevation value is selected.
    """

    moisture_scale: float = 200.0
    """
    Noise scale for moisture field.
    """

    moisture_octaves: int = 2
    """
    Perlin octaves for moisture.
    """

    moisture_persistence: float = 0.5
    """
    Perlin persistence for moisture.
    """

    moisture_lacunarity: float = 2.5
    """
    Perlin lacunarity for moisture.
    """

    moisture_amplitude: float = 5.0
    """
    Multiplier applied to moisture noise before quantization.
    """

    moisture_bias: float = 0.0
    """
    Bias added to moisture noise before quantization.
    """

    rainforest_moisture_threshold: int = 1.5
    """
    Land tiles with moisture >= this become rainforest.
    """

    def _elevation_tile(self, q: int) -> TileType | None:
        """
        Map quantized elevation value to a terrain type.

        Parameters
        ----------
        q : int
            Quantized elevation value.

        Returns
        -------
        TileType | None
            Terrain type if elevation matches a threshold, otherwise None.
        """
        for thr, tile in self.elevation_thresholds:
            if q <= thr:
                return tile
        return None

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
        inv_mscale = 1.0 / self.moisture_scale

        pn2 = pnoise2

        xs_e = [(wx0 + lx) * inv_scale for lx in range(chunk_size)]
        xs_m = [(wx0 + lx) * inv_mscale for lx in range(chunk_size)]

        out: list[TileType] = [TileType.LAND] * (chunk_size * chunk_size)

        for ly in range(chunk_size):
            ye = (wy0 + ly) * inv_scale
            ym = (wy0 + ly) * inv_mscale
            row_off = ly * chunk_size

            for lx, (xe, xm) in enumerate(zip(xs_e, xs_m)):
                v = pn2(
                    xe,
                    ye,
                    octaves=self.octaves,
                    persistence=self.persistence,
                    lacunarity=self.lacunarity,
                    base=self.seed,
                )
                q = int((v + self.bias) * self.amplitude)

                tile = self._elevation_tile(q)
                if tile is not None:
                    out[row_off + lx] = tile
                    continue

                vm = pn2(
                    xm,
                    ym,
                    octaves=self.moisture_octaves,
                    persistence=self.moisture_persistence,
                    lacunarity=self.moisture_lacunarity,
                    base=self.seed + 1337,
                )
                qm = int((vm + self.moisture_bias) * self.moisture_amplitude)

                out[row_off + lx] = (
                    TileType.RAINFOREST
                    if qm >= self.rainforest_moisture_threshold
                    else TileType.LAND
                )

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
        inv_mscale = 1.0 / self.moisture_scale

        v = pnoise2(
            x * inv_scale,
            y * inv_scale,
            octaves=self.octaves,
            persistence=self.persistence,
            lacunarity=self.lacunarity,
            base=self.seed,
        )
        q = int((v + self.bias) * self.amplitude)

        tile = self._elevation_tile(q)
        if tile is not None:
            return tile

        vm = pnoise2(
            x * inv_mscale,
            y * inv_mscale,
            octaves=self.moisture_octaves,
            persistence=self.moisture_persistence,
            lacunarity=self.moisture_lacunarity,
            base=self.seed + 1337,
        )
        qm = int((vm + self.moisture_bias) * self.moisture_amplitude)

        return (
            TileType.RAINFOREST
            if qm >= self.rainforest_moisture_threshold
            else TileType.LAND
        )

