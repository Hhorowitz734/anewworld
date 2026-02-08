"""
Starting point for anewworld runs.
"""

import sys

import pygame

from anewworld.world.tile.tilemap import TileMap
from anewworld.world.tile.tiletype import TileType

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 16

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("A New World")

clock = pygame.time.Clock()
FPS = 60

map_w = SCREEN_WIDTH // TILE_SIZE
map_h = SCREEN_HEIGHT // TILE_SIZE

tilemap = TileMap.new(map_w, map_h, TileType.LAND)

# quick test: make a horizontal "river" stripe
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
                (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE),
            )

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
