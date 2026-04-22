import pygame
import os
import math
import random

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Coin ──────────────────────────────────────────────────────────────────────

class Coin:
    RADIUS = 10
    COLOR  = (255, 215, 0)
    SHINE  = (255, 255, 180)

    def __init__(self, x, y):
        self.x    = float(x)
        self.y    = float(y)
        self.rect = pygame.Rect(int(x) - self.RADIUS, int(y) - self.RADIUS,
                                self.RADIUS * 2, self.RADIUS * 2)

    @staticmethod
    def drop_at(cx, cy, count=None):
        """Return a list of 0-3 coins scattered around (cx, cy)."""
        if count is None:
            count = random.choices([0, 1, 2, 3], weights=[20, 40, 30, 10])[0]
        coins = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(0, 28)
            coins.append(Coin(cx + math.cos(angle) * dist,
                              cy + math.sin(angle) * dist))
        return coins

    def draw(self, screen, cam_x, cam_y):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        pygame.draw.circle(screen, self.COLOR, (sx, sy), self.RADIUS)
        pygame.draw.circle(screen, self.SHINE,  (sx - 2, sy - 2), 2)


# ── Gate ──────────────────────────────────────────────────────────────────────

class Gate:
    SIZE = 80

    def __init__(self, x, y):
        self.x    = float(x)
        self.y    = float(y)
        self.rect = pygame.Rect(int(x) - self.SIZE // 2, int(y) - self.SIZE // 2,
                                self.SIZE, self.SIZE)
        path = os.path.join(_BASE_DIR, 'images', 'placeholder.png')
        raw  = pygame.image.load(path).convert_alpha()
        self.image = pygame.transform.scale(raw, (self.SIZE, self.SIZE))

    def draw(self, screen, cam_x, cam_y):
        sx = int(self.x - cam_x) - self.SIZE // 2
        sy = int(self.y - cam_y) - self.SIZE // 2
        screen.blit(self.image, (sx, sy))
        pygame.draw.rect(screen, (0, 200, 255),
                         (sx - 3, sy - 3, self.SIZE + 6, self.SIZE + 6), 3)
