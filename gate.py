import pygame
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Gate:
    SIZE = 80

    def __init__(self, x, y):
        self.x    = float(x)
        self.y    = float(y)
        self.rect = pygame.Rect(int(x) - self.SIZE // 2, int(y) - self.SIZE // 2,
                                self.SIZE, self.SIZE)
        path = os.path.join(BASE_DIR, 'images', 'placeholder.png')
        raw  = pygame.image.load(path).convert_alpha()
        self.image = pygame.transform.scale(raw, (self.SIZE, self.SIZE))

    def draw(self, screen, cam_x, cam_y):
        sx = int(self.x - cam_x) - self.SIZE // 2
        sy = int(self.y - cam_y) - self.SIZE // 2
        screen.blit(self.image, (sx, sy))
        pygame.draw.rect(screen, (0, 200, 255),
                         (sx - 3, sy - 3, self.SIZE + 6, self.SIZE + 6), 3)
