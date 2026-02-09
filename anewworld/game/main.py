"""
Starting point for anewworld runs.
"""

import sys

import pygame

from anewworld.config import GameConfig
from anewworld.game.controls import Controls
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
    controls = Controls(camera=camera, pan_button=1)

    running = True
    while running:
        clock.tick(cfg.fps)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            controls.handle_event(event)

        screen.fill((0, 0, 0))
        renderer.draw(screen=screen, tilemap=tilemap, camera=camera)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
