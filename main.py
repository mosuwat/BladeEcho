import pygame
import sys
from player import Player

pygame.init()

# Create the window
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Blade Echo")
clock = pygame.time.Clock()
FPS = 60
player = Player(SCREEN_HEIGHT / 2, SCREEN_WIDTH / 2, 300)

# Game loop
running = True
while running:
    dt = clock.tick(FPS) / 1000  # delta time in seconds

    # 1. Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.perform_parry()

    # 2. Update game state
    # (move player, enemies, check collisions, etc.)
    keys = pygame.key.get_pressed()
    player.handle_input(keys, dt)
    player.update(dt)

    # 3. Draw everything
    screen.fill((0, 0, 0))  # clear screen with black
    # draw your stuff here
    player.draw(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()