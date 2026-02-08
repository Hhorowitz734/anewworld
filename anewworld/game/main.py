"""
Starting point for anewworld runs.
"""

import sys

import pygame

from anewworld.config import GameConfig
from anewworld.world.tile.tilemap import TileMap
from anewworld.world.tile.tiletype import TileType


def main() -> None:
    """
    Entry point into anewworld.
    """
    pygame.init()

    cfg = GameConfig()

    screen = pygame.display.set_mode((cfg.screen_width, cfg.screen_height))
    pygame.display.set_caption("A New World")

    clock = pygame.time.Clock()

    map_w = cfg.screen_width // cfg.tile_size
    map_h = cfg.screen_height // cfg.tile_size

    tilemap = TileMap.new(map_w, map_h, TileType.LAND)

    for x in range(map_w):
        tilemap.tile_at(x, map_h // 2).terrain = TileType.RIVER

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))

        for y in range(tilemap.h):
            for x in range(tilemap.w):
                t = tilemap.tile_at(x, y).terrain

                if t == TileType.LAND:
                    color = (70, 150, 80)
                else:
                    color = (50, 110, 190)

                pygame.draw.rect(
                    screen,
                    color,
                    (
                        x * cfg.tile_size,
                        y * cfg.tile_size,
                        cfg.tile_size,
                        cfg.tile_size,
                    ),
                )

        pygame.display.flip()
        clock.tick(cfg.fps)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
