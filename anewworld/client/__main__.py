"""
Client-side logic for anewworld.
"""

import sys

import pygame

from anewworld.shared.terrain_generator import TerrainGenerator
from anewworld.shared.world_map import WorldMap
from anewworld.shared.level.level_grid import LevelGrid
from anewworld.shared.level.elevation import ElevationLevel
from anewworld.shared.level.moisture import MoistureLevel
from anewworld.shared.tile_type import TileType
from anewworld.shared.config import WorldConfig
from anewworld.client.renderer.chunk_renderer import ChunkRenderer
from anewworld.client.renderer.terrain_palette import TerrainPalette
from anewworld.client.renderer.camera import Camera
from anewworld.client.controls import Controls


def main() -> None:
    """
    Start anewworld client.
    """

    pygame.init()

    world_cfg = WorldConfig()

    screen = pygame.display.set_mode((800, 800))
    pygame.display.set_caption("A New World")

    clock = pygame.time.Clock()

    land_grid = LevelGrid[
        object,
        TileType,
    ](
        table={
            (ElevationLevel.HIGH, MoistureLevel.DRY): TileType.DEFAULT_GRASS,
            (ElevationLevel.HIGH, MoistureLevel.WET): TileType.DARK_GRASS,

            # You can explicitly include LOW if you want land behavior there
            # or let elevation gate water before lookup.
        },
        default=TileType.DEFAULT_GRASS,
    )

    generator = TerrainGenerator(seed = world_cfg.world_seed, 
                                 land_grid = land_grid)

    world_map = WorldMap.new(
        chunk_size = world_cfg.chunk_size,
        generator = generator,
        max_cached_chunks = 256
    )

    renderer = ChunkRenderer.new(
        tile_size = 10,
        chunk_size = world_cfg.chunk_size,
        max_cached_chunks = 256,
        padding_chunks = 3,
        palette = TerrainPalette()
    )

    camera = Camera()
    controls = Controls(camera = camera,
                        pan_button = 1)

    running = True
    while running:
        clock.tick(120)
        
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                running = False
                continue
            controls.handle_event(event)

        
        screen.fill((0, 0, 0))
        renderer.draw(screen = screen,
                      world_map = world_map,
                      camera = camera)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

    
