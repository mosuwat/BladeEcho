import pygame

ENEMY_HIT_COLOR  = (255, 230,  80)   # yellow — player damages enemy
PLAYER_HIT_COLOR = (255,  80,  80)   # red    — enemy damages player

_active = []

LIFETIME = 0.9
RISE_PX  = 55   # pixels floated upward over lifetime


class _DamageNumber:
    def __init__(self, x, y, value, color):
        self.x     = float(x)
        self.y     = float(y)
        self.value = value
        self.color = color
        self.age   = 0.0

    def update(self, dt):
        self.age += dt
        self.y   -= (RISE_PX / LIFETIME) * dt

    @property
    def alive(self):
        return self.age < LIFETIME

    def draw(self, surface, font, cam_x, cam_y):
        alpha = max(0, 255 - int(255 * self.age / LIFETIME))
        txt = font.render(str(self.value), True, self.color)
        txt.set_alpha(alpha)
        surface.blit(txt, txt.get_rect(center=(int(self.x - cam_x),
                                               int(self.y - cam_y))))


def spawn(x, y, value, color=ENEMY_HIT_COLOR):
    _active.append(_DamageNumber(x, y, value, color))


def update_all(dt):
    global _active
    for dn in _active:
        dn.update(dt)
    _active = [dn for dn in _active if dn.alive]


def draw_all(surface, font, cam_x, cam_y):
    for dn in _active:
        dn.draw(surface, font, cam_x, cam_y)
