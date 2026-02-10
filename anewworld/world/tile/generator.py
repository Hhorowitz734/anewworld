"""
Generates terrain given world seed.
"""

from __future__ import annotations

from dataclasses import dataclass
import random

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

    lake_chance: float = 0.06
    """
    Probability that a chunk has at least one lake seed.
    """

    min_lake_radius: int = 3
    """
    Minimum lake radius in tiles.
    """

    max_lake_radius: int = 10
    """
    Maximum lake radius in tiles.
    """

    river_chance: float = 0.10
    """
    Probability that a chunk contains a river segment.
    """

    river_width: int = 2
    """
    River half-width in tiles.

    A width of 2 produces a river roughly 5 tiles wide.
    """

    river_steps: int = 96
    """
    Number of steps used to trace a river polyline within a chunk.
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
        out: list[TileType] = [TileType.LAND] * (chunk_size ** 2)

        rng = self._chunk_rng(cx = cx, cy = cy)

        self._apply_lakes(
            out = out, 
            rng = rng,
            cx = cx,
            cy = cy,
            chunk_size = chunk_size,
        )

        self._apply_river(
            out = out, 
            rng = rng,
            cx = cx,
            cy = cy,
            chunk_size = chunk_size,
        )

        return out

    def terrain_at(self,
                   *,
                   x: int,
                   y: int,
                   chunk_size: int) -> TileType:
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
        cx = self._floor_div(x, chunk_size)
        cy = self._floor_div(y, chunk_size)
        lx = x - cx * chunk_size
        ly = y - cy * chunk_size

        buf = self.generate_chunk(cx=cx, cy=cy, chunk_size=chunk_size)
        return buf[ly * chunk_size + lx]

    def _chunk_rng(self, *, cx: int, cy: int) -> random.Random:
        """
        Create a deterministic RNG for a given chunk.

        Parameters
        ----------
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.

        Returns
        -------
        random.Random
            RNG seeded deterministically for the chunk.
        """
        s = self._mix_seed(self.seed, cx, cy)
        return random.Random(s)

    def _apply_lakes(
        self,
        *,
        out: list[TileType],
        rng: random.Random,
        cx: int,
        cy: int,
        chunk_size: int,
    ) -> None:
        """
        Apply lake features to a chunk terrain buffer.

        Parameters
        ----------
        out : list[TileType]
            Row-major terrain buffer to modify in-place.
        rng : random.Random
            RNG for this chunk.
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.
        chunk_size : int
            Width and height of the chunk in tiles.
        """
        if rng.random() >= self.lake_chance:
            return

        lake_count = 1 if rng.random() < 0.75 else 2
        for _ in range(lake_count):
            center_x = rng.randrange(0, chunk_size)
            center_y = rng.randrange(0, chunk_size)
            radius = rng.randrange(self.min_lake_radius, self.max_lake_radius + 1)

            r2 = radius * radius
            for ly in range(chunk_size):
                dy = ly - center_y
                for lx in range(chunk_size):
                    dx = lx - center_x
                    if dx * dx + dy * dy <= r2:
                        out[ly * chunk_size + lx] = TileType.WATER

    def _apply_river(
        self,
        *,
        out: list[TileType],
        rng: random.Random,
        cx: int,
        cy: int,
        chunk_size: int,
    ) -> None:
        """
        Apply a river polyline to a chunk terrain buffer.

        Parameters
        ----------
        out : list[TileType]
            Row-major terrain buffer to modify in-place.
        rng : random.Random
            RNG for this chunk.
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.
        chunk_size : int
            Width and height of the chunk in tiles.
        """
        if rng.random() >= self.river_chance:
            return

        side = rng.randrange(0, 4)
        if side == 0:
            x = 0
            y = rng.randrange(0, chunk_size)
            dx = 1
            dy = 0
        elif side == 1:
            x = chunk_size - 1
            y = rng.randrange(0, chunk_size)
            dx = -1
            dy = 0
        elif side == 2:
            x = rng.randrange(0, chunk_size)
            y = 0
            dx = 0
            dy = 1
        else:
            x = rng.randrange(0, chunk_size)
            y = chunk_size - 1
            dx = 0
            dy = -1

        steps = max(8, self.river_steps)
        for _ in range(steps):
            self._paint_disk(
                out=out,
                chunk_size=chunk_size,
                cx=x,
                cy=y,
                radius=self.river_width,
                terrain=TileType.WATER,
            )

            turn = rng.random()
            if turn < 0.20:
                dx, dy = -dy, dx
            elif turn < 0.40:
                dx, dy = dy, -dx

            drift = rng.random()
            if drift < 0.15:
                x += rng.choice([-1, 0, 1])
                y += rng.choice([-1, 0, 1])

            x += dx
            y += dy

            if x < -self.river_width or y < -self.river_width:
                break
            if x > chunk_size - 1 + self.river_width:
                break
            if y > chunk_size - 1 + self.river_width:
                break

    def _paint_disk(
        self,
        *,
        out: list[TileType],
        chunk_size: int,
        cx: int,
        cy: int,
        radius: int,
        terrain: TileType,
    ) -> None:
        """
        Paint a filled disk into a chunk terrain buffer.

        Parameters
        ----------
        out : list[TileType]
            Row-major terrain buffer to modify in-place.
        chunk_size : int
            Width and height of the chunk in tiles.
        cx : int
            Disk center X coordinate in local chunk tiles.
        cy : int
            Disk center Y coordinate in local chunk tiles.
        radius : int
            Disk radius in tiles.
        terrain : TileType
            Terrain type to paint.
        """
        r2 = radius * radius
        x0 = max(0, cx - radius)
        x1 = min(chunk_size - 1, cx + radius)
        y0 = max(0, cy - radius)
        y1 = min(chunk_size - 1, cy + radius)

        for y in range(y0, y1 + 1):
            dy = y - cy
            row = y * chunk_size
            for x in range(x0, x1 + 1):
                dx = x - cx
                if dx * dx + dy * dy <= r2:
                    out[row + x] = terrain

    @staticmethod
    def _mix_seed(seed: int, cx: int, cy: int) -> int:
        """
        Mix the world seed with chunk coordinates into a new seed.

        Parameters
        ----------
        seed : int
            World seed.
        cx : int
            Chunk X coordinate.
        cy : int
            Chunk Y coordinate.

        Returns
        -------
        int
            Mixed integer seed.
        """
        x = seed & 0xFFFFFFFFFFFFFFFF
        x ^= (cx * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        x ^= (cy * 0xC2B2AE3D27D4EB4F) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 33) & 0xFFFFFFFFFFFFFFFF
        x = (x * 0xFF51AFD7ED558CCD) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 33) & 0xFFFFFFFFFFFFFFFF
        x = (x * 0xC4CEB9FE1A85EC53) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 33) & 0xFFFFFFFFFFFFFFFF
        return int(x)

    @staticmethod
    def _floor_div(a: int, b: int) -> int:
        """
        Floor divide for chunk coordinate math.

        Parameters
        ----------
        a : int
            Dividend.
        b : int
            Divisor.

        Returns
        -------
        int
            Floor-divided result.
        """
        return a // b

    


