"""
Client-side logic for anewworld.
"""

import sys

import pygame

from anewworld.client.config import WindowConfig
from anewworld.client.controls import Controls
from anewworld.client.renderer.camera import Camera
from anewworld.client.renderer.chunk_renderer import ChunkRenderer
from anewworld.client.renderer.terrain_palette import TerrainPalette
from anewworld.shared.config import WorldConfig
from anewworld.shared.terrain_generator import TerrainGenerator
from anewworld.shared.world_map import WorldMap


def main() -> None:
    """
    Start anewworld client.
    """
    pygame.init()

    world_cfg = WorldConfig()
    window_cfg = WindowConfig()

    screen = pygame.display.set_mode(
        (window_cfg.screen_width, window_cfg.screen_height)
    )
    pygame.display.set_caption("A New World")

    clock = pygame.time.Clock()

    land_grid = world_cfg.level_grid
    generator = TerrainGenerator(seed=world_cfg.world_seed, land_grid=land_grid)

    world_map = WorldMap.new(
        chunk_size=world_cfg.chunk_size, generator=generator, max_cached_chunks=256
    )

    renderer = ChunkRenderer.new(
        tile_size=window_cfg.tile_size,
        chunk_size=world_cfg.chunk_size,
        max_cached_chunks=256,
        padding_chunks=3,
        palette=TerrainPalette(),
    )

    camera = Camera()
    controls = Controls(camera=camera, pan_button=1)

    running = True
    while running:
        clock.tick(window_cfg.fps)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                running = False
                continue
            controls.handle_event(event)

        screen.fill((0, 0, 0))
        renderer.draw(screen=screen, world_map=world_map, camera=camera)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
