import pygame
import math
import random

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
