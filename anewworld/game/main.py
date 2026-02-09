"""
Starting point for anewworld runs.
"""

import sys

import pygame

from anewworld.config import GameConfig
from anewworld.render.camera import Camera
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

    camera = Camera()

    running = True
    while running:
        clock.tick(cfg.fps)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                camera.begin_drag(mouse_x=mx, mouse_y=my)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                camera.end_drag()

            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                camera.drag_to(mouse_x=mx, mouse_y=my)

        screen.fill((0, 0, 0))
        renderer.draw(screen=screen, tilemap=tilemap, camera=camera)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
