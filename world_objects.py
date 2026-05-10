import pygame
import os
import math
import random

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_coin_sprite = None


def _get_coin_sprite():
    global _coin_sprite
    if _coin_sprite is None:
        import tilemap as tilemap_mod
        path = os.path.join(_BASE_DIR, 'Images', 'Icons', 'Coin.tmx')
        tmx = tilemap_mod.load(path)
        frames = tmx.get_frames(frame_tile_w=1)
        if frames:
            _coin_sprite = pygame.transform.scale(frames[0], (40, 40))
    return _coin_sprite


class Coin:
    RADIUS     = 20
    _FLOAT_AMP  = 4      # pixels
    _FLOAT_FREQ = 2.0    # cycles per second

    def __init__(self, x, y):
        self.x      = float(x)
        self.y      = float(y)
        self._phase = random.uniform(0, 2 * math.pi)
        self.rect   = pygame.Rect(int(x) - self.RADIUS, int(y) - self.RADIUS,
                                  self.RADIUS * 2, self.RADIUS * 2)

    @staticmethod
    def drop_at(cx, cy, count=None):
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
        img    = _get_coin_sprite()
        t      = pygame.time.get_ticks() / 1000.0
        float_y = int(math.sin(t * self._FLOAT_FREQ * math.pi * 2 + self._phase) * self._FLOAT_AMP)
        sx = int(self.x - cam_x) - self.RADIUS
        sy = int(self.y - cam_y) - self.RADIUS + float_y
        if img:
            screen.blit(img, (sx, sy))
        else:
            cx = sx + self.RADIUS
            cy = sy + self.RADIUS
            pygame.draw.circle(screen, (255, 215, 0),   (cx, cy), self.RADIUS)
            pygame.draw.circle(screen, (255, 255, 180), (cx - 2, cy - 2), 2)
