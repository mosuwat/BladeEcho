import pygame
from constants import SCREEN_W, SCREEN_H

_BOSS_BAR_W  = SCREEN_W - 200
_BOSS_BAR_OX = 100
_BOSS_BAR_OY = SCREEN_H - 36

# ── Item pickup notifications ─────────────────────────────────────────────────

_NOTIF_LIFETIME = 2.5
_NOTIF_RISE_PX  = 50
_notifications  = []


class _Notification:
    def __init__(self, name, rarity, rarity_color):
        self.name         = name
        self.rarity       = rarity.upper()
        self.rarity_color = rarity_color
        self.timer        = _NOTIF_LIFETIME

    def update(self, dt):
        self.timer -= dt

    @property
    def alive(self):
        return self.timer > 0

    def draw(self, screen, font_name, font_rarity, index):
        t      = self.timer / _NOTIF_LIFETIME          # 1 → 0
        alpha  = int(255 * min(t * 4, 1.0))            # fade out last 25%
        y_base = SCREEN_H // 2 - 60 - index * 52
        rise   = int((1.0 - t) * _NOTIF_RISE_PX)
        cy     = y_base - rise

        rar_surf  = font_rarity.render(self.rarity, True, self.rarity_color)
        name_surf = font_name.render(self.name,     True, (240, 240, 240))

        total_w = max(rar_surf.get_width(), name_surf.get_width()) + 24
        total_h = rar_surf.get_height() + name_surf.get_height() + 14
        cx      = SCREEN_W // 2

        bg = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
        bg.fill((10, 10, 20, int(alpha * 0.75)))
        screen.blit(bg, (cx - total_w // 2, cy))

        rar_surf.set_alpha(alpha)
        name_surf.set_alpha(alpha)
        screen.blit(rar_surf,  rar_surf.get_rect(centerx=cx,  y=cy + 6))
        screen.blit(name_surf, name_surf.get_rect(centerx=cx, y=cy + 6 + rar_surf.get_height() + 4))


def notify_item(name, rarity, rarity_color):
    _notifications.append(_Notification(name, rarity, rarity_color))


def update_notifications(dt):
    for n in _notifications:
        n.update(dt)
    _notifications[:] = [n for n in _notifications if n.alive]


def draw_notifications(screen, font_name, font_rarity):
    for i, n in enumerate(_notifications):
        n.draw(screen, font_name, font_rarity, i)


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


def draw_hud(screen, player, cur_room, floor_num, sublevel, font):
    if cur_room:
        tag  = ' [START]' if cur_room.is_start else (' [BOSS]' if cur_room.is_boss else '')
        room_text = f"Room: {cur_room.event_type}{tag}"
        col = (220, 220, 220)
    else:
        room_text = 'Hallway'
        col = (160, 160, 160)
    screen.blit(font.render(room_text,                                    True, col),           (8, 8))
    screen.blit(font.render(f"HP: {player.hp}/{player.max_hp}",          True, (220, 80, 80)), (8, 28))
    screen.blit(font.render(f"Coins: {player.coins}",                    True, (255, 215, 0)), (8, 48))
    screen.blit(font.render(f"Floor {floor_num}  –  Sub-level {sublevel}/3",
                             True, (180, 180, 220)), (8, 68))
    if player.defense > 0:
        screen.blit(font.render(f"DEF: {player.defense}", True, (100, 180, 255)), (8, 88))


def draw_boss_bar(screen, boss, font_label):
    pct      = max(0.0, boss.hp / boss.max_hp)
    desperate = getattr(boss, 'desperate', False)
    col      = (255, 80, 80) if desperate else (220, 60, 60)
    ox, oy   = _BOSS_BAR_OX, _BOSS_BAR_OY
    bw       = _BOSS_BAR_W
    pygame.draw.rect(screen, (40, 20, 20),   (ox - 2, oy - 2, bw + 4, 20))
    pygame.draw.rect(screen, col,            (ox, oy, int(bw * pct), 16))
    pygame.draw.rect(screen, (180, 80, 80),  (ox, oy, bw, 16), 2)
    parts = [boss.NAME]
    if boss.phase_label:
        parts.append(boss.phase_label)
    label = font_label.render('  '.join(parts), True, (255, 200, 200))
    screen.blit(label, label.get_rect(centerx=SCREEN_W // 2, bottom=oy - 2))


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


# ── Damage numbers ────────────────────────────────────────────────────────────

ENEMY_HIT_COLOR  = (255, 230,  80)
PLAYER_HIT_COLOR = (255,  80,  80)

_dn_active   = []
_DN_LIFETIME = 0.9
_DN_RISE_PX  = 55


class _DamageNumber:
    def __init__(self, x, y, value, color):
        self.x     = float(x)
        self.y     = float(y)
        self.value = value
        self.color = color
        self.age   = 0.0

    def update(self, dt):
        self.age += dt
        self.y   -= (_DN_RISE_PX / _DN_LIFETIME) * dt

    @property
    def alive(self):
        return self.age < _DN_LIFETIME

    def draw(self, surface, font, cam_x, cam_y):
        alpha = max(0, 255 - int(255 * self.age / _DN_LIFETIME))
        txt = font.render(str(self.value), True, self.color)
        txt.set_alpha(alpha)
        surface.blit(txt, txt.get_rect(center=(int(self.x - cam_x),
                                               int(self.y - cam_y))))


def spawn(x, y, value, color=ENEMY_HIT_COLOR):
    _dn_active.append(_DamageNumber(x, y, value, color))


def update_all(dt):
    global _dn_active
    for dn in _dn_active:
        dn.update(dt)
    _dn_active = [dn for dn in _dn_active if dn.alive]


def draw_all(surface, font, cam_x, cam_y):
    for dn in _dn_active:
        dn.draw(surface, font, cam_x, cam_y)


# ── Minimap ───────────────────────────────────────────────────────────────────

_MM_COLORS = {
    'start':   ( 50, 200,  50),
    'monster': (180,  60,  60),
    'boss':    (220, 100,  20),
    'shop':    (200, 180,  50),
    'special': (150,  80, 200),
    'item':    ( 60, 120, 200),
    'exit':    (  0, 180, 220),
}

_MM_CELL = 18
_MM_GAP  = 3
_MM_STEP = _MM_CELL + _MM_GAP


def draw_minimap(screen, rooms, cur_room, font):
    from map_generator import MAP_COLS, MAP_ROWS   # lazy — avoids circular import
    sw, sh = screen.get_size()
    ox = (sw - MAP_COLS * _MM_STEP) // 2
    oy = (sh - MAP_ROWS * _MM_STEP) // 2

    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    room_dict = {(r.grid_x, r.grid_y): r for r in rooms}

    def adjacent_visited(room):
        return any(
            room_dict.get((nx, ny)) and room_dict[(nx, ny)].visited
            for nx, ny in room.connections
        )

    for room in rooms:
        visited    = room.visited
        discovered = not visited and adjacent_visited(room)
        if not visited and not discovered:
            continue

        rx = ox + room.grid_x * _MM_STEP
        ry = oy + room.grid_y * _MM_STEP
        base  = _MM_COLORS.get(room.event_type, (80, 80, 80))
        color = base if visited else tuple(int(c * 0.4) for c in base)

        for nx, ny in room.connections:
            nb = room_dict.get((nx, ny))
            if nb and (nb.visited or adjacent_visited(nb)):
                pygame.draw.line(screen, (60, 60, 80),
                                 (rx + _MM_CELL // 2, ry + _MM_CELL // 2),
                                 (ox + nx * _MM_STEP + _MM_CELL // 2,
                                  oy + ny * _MM_STEP + _MM_CELL // 2), 2)

        pygame.draw.rect(screen, color, (rx, ry, _MM_CELL, _MM_CELL))

        if room is cur_room:
            pygame.draw.rect(screen, (255, 255, 255), (rx, ry, _MM_CELL, _MM_CELL), 2)
            pygame.draw.circle(screen, (255, 255, 255),
                               (rx + _MM_CELL // 2, ry + _MM_CELL // 2), 3)

    title = font.render("MAP  (M to close)", True, (180, 180, 200))
    screen.blit(title, title.get_rect(centerx=sw // 2, y=oy - 28))
