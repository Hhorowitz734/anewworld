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
    Enter anewworld session.
    """
    pygame.init()

    cfg = GameConfig()

    screen = pygame.display.set_mode((cfg.screen_width, cfg.screen_height))
    pygame.display.set_caption("A New World")

    clock = pygame.time.Clock()

    tiles_w = cfg.screen_width // cfg.tile_size
    tiles_h = cfg.screen_height // cfg.tile_size

    tilemap = TileMap.new(
        chunk_size=cfg.chunk_size,
        default_terrain=TileType.LAND,
    )

    cam_x = 0
    cam_y = 0

    dragging = False
    drag_start_mouse_x = 0
    drag_start_mouse_y = 0
    drag_start_cam_x = 0
    drag_start_cam_y = 0

    running = True
    while running:
        clock.tick(cfg.fps)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                drag_start_mouse_x, drag_start_mouse_y = event.pos
                drag_start_cam_x = cam_x
                drag_start_cam_y = cam_y

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False

            if event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                dx_px = mx - drag_start_mouse_x
                dy_px = my - drag_start_mouse_y

                dx_tiles = dx_px // cfg.tile_size
                dy_tiles = dy_px // cfg.tile_size

                cam_x = drag_start_cam_x - int(dx_tiles)
                cam_y = drag_start_cam_y - int(dy_tiles)

        screen.fill((0, 0, 0))

        for sy in range(tiles_h):
            wy = cam_y + sy
            for sx in range(tiles_w):
                wx = cam_x + sx
                t = tilemap.terrain_at(wx, wy)

                if t == TileType.LAND:
                    color = (70, 150, 80)
                else:
                    color = (50, 110, 190)

                pygame.draw.rect(
                    screen,
                    color,
                    (
                        sx * cfg.tile_size,
                        sy * cfg.tile_size,
                        cfg.tile_size,
                        cfg.tile_size,
                    ),
                )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
