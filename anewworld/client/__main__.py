"""
Client-side logic for anewworld.
"""

from __future__ import annotations

import asyncio
import sys

import pygame

from anewworld.client.config import ClientConfig, DevConfig, WindowConfig
from anewworld.client.controls import Controls
from anewworld.client.net.client import ServerConnection
from anewworld.client.net.client_state import ClientState
from anewworld.client.renderer.camera import Camera
from anewworld.client.renderer.chunk_renderer import ChunkRenderer
from anewworld.client.renderer.terrain_palette import TerrainPalette
from anewworld.shared.config import WorldConfig
from anewworld.shared.terrain_generator import TerrainGenerator
from anewworld.shared.world_map import WorldMap


async def main() -> None:
    """
    Start anewworld client.
    """
    pygame.init()

    world_cfg = WorldConfig()
    window_cfg = WindowConfig()
    client_cfg = ClientConfig()
    dev_cfg = DevConfig()

    conn: ServerConnection | None = None
    state: ClientState | None = None

    if not client_cfg.singleplayer:
        conn, state = await ServerConnection.connect(
            host="127.0.0.1",
            port=7777,
        )
        if dev_cfg.debug:
            print(f"Connected as {conn.player_id}")
            print(f"Inventory: {state.inventory.to_wire()}")

    try:
        screen = pygame.display.set_mode(
            (window_cfg.screen_width, window_cfg.screen_height)
        )
        pygame.display.set_caption("A New World")

        clock = pygame.time.Clock()

        land_grid = world_cfg.level_grid
        generator = TerrainGenerator(seed=world_cfg.world_seed, land_grid=land_grid)

        world_map = WorldMap.new(
            chunk_size=world_cfg.chunk_size,
            generator=generator,
            max_cached_chunks=256,
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
                if event.type == pygame.QUIT:
                    running = False
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    running = False
                    continue

                controls.handle_event(event)

            if conn is not None and state is not None:
                await conn.tick(
                    state=state,
                    camera_x_px=camera.x_px,
                    camera_y_px=camera.y_px,
                    screen_w_px=window_cfg.screen_width,
                    screen_h_px=window_cfg.screen_height,
                    chunk_size=world_cfg.chunk_size,
                    tile_size=window_cfg.tile_size,
                    padding_chunks=3,
                )

            screen.fill((0, 0, 0))
            renderer.draw(screen=screen, world_map=world_map, camera=camera)
            pygame.display.flip()

    finally:
        if conn is not None:
            await conn.close()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    asyncio.run(main())
