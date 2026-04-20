import pygame
from constants import SCREEN_W, SCREEN_H


class Button:
    def __init__(self, rect, label, font,
                 color=(60, 60, 80), hover=(90, 90, 120),
                 text_color=(220, 220, 220), disabled=False):
        self.rect       = pygame.Rect(rect)
        self.label      = label
        self.font       = font
        self.color      = color
        self.hover      = hover
        self.text_color = text_color
        self.disabled   = disabled

    def draw(self, surface):
        mx, my = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mx, my) and not self.disabled
        col = (40, 40, 50) if self.disabled else (self.hover if hovered else self.color)
        pygame.draw.rect(surface, col, self.rect, border_radius=6)
        pygame.draw.rect(surface, (100, 100, 140), self.rect, 2, border_radius=6)
        tc  = (80, 80, 80) if self.disabled else self.text_color
        txt = self.font.render(self.label, True, tc)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return (not self.disabled
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))


def make_menu_buttons(font_lg, save_exists_fn):
    cx = SCREEN_W // 2
    w, h, gap = 280, 55, 20
    y0 = SCREEN_H // 2 - 20
    return [
        Button((cx - w//2, y0,             w, h), "Play",           font_lg),
        Button((cx - w//2, y0 + h+gap,     w, h), "Load Last Save", font_lg,
               disabled=not save_exists_fn()),
        Button((cx - w//2, y0 + (h+gap)*2, w, h), "Quit",           font_lg,
               color=(80, 40, 40), hover=(120, 60, 60)),
    ]
