"""
Starting point for anewworld runs.
"""

import sys

import pygame

from anewworld.config import GameConfig
from anewworld.render.chunk_renderer import ChunkRenderer
from anewworld.render.palette import TerrainPalette
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

    tilemap = TileMap.new(
        chunk_size=cfg.chunk_size,
        default_terrain=TileType.LAND,
    )

    renderer = ChunkRenderer.new(
        tile_size=cfg.tile_size,
        chunk_size=cfg.chunk_size,
        max_cached_chunks=256,
        padding_chunks=1,
        palette=TerrainPalette(),
    )

    cam_px_x = 0
    cam_px_y = 0

    dragging = False
    drag_start_mouse_x = 0
    drag_start_mouse_y = 0
    drag_start_cam_px_x = 0
    drag_start_cam_px_y = 0

    running = True
    while running:
        clock.tick(cfg.fps)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                drag_start_mouse_x, drag_start_mouse_y = event.pos
                drag_start_cam_px_x = cam_px_x
                drag_start_cam_px_y = cam_px_y

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False

            if event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                dx_px = mx - drag_start_mouse_x
                dy_px = my - drag_start_mouse_y
                cam_px_x = drag_start_cam_px_x - dx_px
                cam_px_y = drag_start_cam_px_y - dy_px

        screen.fill((0, 0, 0))
        renderer.draw(
            screen=screen,
            tilemap=tilemap,
            cam_px_x=cam_px_x,
            cam_px_y=cam_px_y,
        )
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
