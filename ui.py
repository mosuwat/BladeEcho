import pygame
import math
import os
from constants import SCREEN_W, SCREEN_H

_BOSS_BAR_W  = SCREEN_W - 200
_BOSS_BAR_OX = 100
_BOSS_BAR_OY = SCREEN_H - 36

# ── HUD icon assets ───────────────────────────────────────────────────────────

_ICONS_DIR = os.path.join(os.path.dirname(__file__), 'Images', 'Icons')

_heart_imgs      = None   # [full, half, empty] each 20×20
_coin_spin_imgs  = None   # [frame0, frame1] each 20×20
_coin_spin_timer = 0.0
_COIN_SPIN_FPS   = 6.0
_HP_PER_HEART    = 1
_HEART_SIZE      = 20
_COIN_ICON_SIZE  = 20


def _get_heart_imgs():
    global _heart_imgs
    if _heart_imgs is None:
        import tilemap as tilemap_mod
        tmx = tilemap_mod.load(os.path.join(_ICONS_DIR, 'Hearts.tmx'))
        raw = tmx.get_frames(frame_tile_w=1)
        _heart_imgs = [pygame.transform.scale(f, (_HEART_SIZE, _HEART_SIZE)) for f in raw]
    return _heart_imgs


def _get_coin_spin_imgs():
    global _coin_spin_imgs
    if _coin_spin_imgs is None:
        import tilemap as tilemap_mod
        tmx = tilemap_mod.load(os.path.join(_ICONS_DIR, 'Coin_Spin.tmx'))
        raw = tmx.get_frames(frame_tile_w=1)
        _coin_spin_imgs = [pygame.transform.scale(f, (_COIN_ICON_SIZE, _COIN_ICON_SIZE)) for f in raw]
    return _coin_spin_imgs

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
    screen.blit(font.render(room_text, True, col), (8, 8))

    # Hearts
    hearts = _get_heart_imgs()
    num_hearts = max(player.max_hp // _HP_PER_HEART, 1)
    hx, hy = 8, 30
    if hearts:
        for i in range(num_hearts):
            filled = player.hp - i * _HP_PER_HEART
            if filled >= _HP_PER_HEART:
                img = hearts[0]
            elif filled > 0:
                img = hearts[1]
            else:
                img = hearts[2]
            screen.blit(img, (hx + i * (_HEART_SIZE + 2), hy))
    else:
        screen.blit(font.render(f"HP: {player.hp}/{player.max_hp}", True, (220, 80, 80)), (8, 30))

    # Coin icon + count
    coin_frames = _get_coin_spin_imgs()
    cy = 54
    if coin_frames:
        idx = int(_coin_spin_timer * _COIN_SPIN_FPS) % len(coin_frames)
        screen.blit(coin_frames[idx], (8, cy))
        screen.blit(font.render(str(player.coins), True, (255, 215, 0)),
                    (8 + _COIN_ICON_SIZE + 4, cy + (_COIN_ICON_SIZE - font.size("0")[1]) // 2))
    else:
        screen.blit(font.render(f"Coins: {player.coins}", True, (255, 215, 0)), (8, cy))

    screen.blit(font.render(f"Floor {floor_num}  –  Sub-level {sublevel}/3",
                             True, (180, 180, 220)), (8, 78))
    if player.defense > 0:
        screen.blit(font.render(f"DEF: {player.defense}", True, (100, 180, 255)), (8, 102))

    screen.blit(font.render("TAB Buffs  |  ESC Settings", True, (90, 90, 110)),
                (8, SCREEN_H - 22))


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
    w, h, gap = 280, 55, 16
    y0 = SCREEN_H // 2 - 120
    return [
        Button((cx - w//2, y0,             w, h), "Play",           font_lg),
        Button((cx - w//2, y0 + (h+gap),   w, h), "Load Last Save", font_lg,
               disabled=not save_exists_fn()),
        Button((cx - w//2, y0 + (h+gap)*2, w, h), "Tutorial",       font_lg,
               color=(40, 70, 50), hover=(60, 110, 75)),
        Button((cx - w//2, y0 + (h+gap)*3, w, h), "Stats",          font_lg,
               color=(40, 40, 80), hover=(60, 60, 120)),
        Button((cx - w//2, y0 + (h+gap)*4, w, h), "Quit",           font_lg,
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
    global _dn_active, _coin_spin_timer
    for dn in _dn_active:
        dn.update(dt)
    _dn_active = [dn for dn in _dn_active if dn.alive]
    _coin_spin_timer += dt


def draw_all(surface, font, cam_x, cam_y):
    for dn in _dn_active:
        dn.draw(surface, font, cam_x, cam_y)


# ── Minimap ───────────────────────────────────────────────────────────────────

_MM_COLORS = {
    'start':   ( 50, 200,  50),
    'monster': (180,  60,  60),
    'boss':    (220, 100,  20),
    'shop':    (200, 180,  50),
    'item':    ( 60, 120, 200),
    'exit':    (  0, 180, 220),
}

_MM_CELL = 18
_MM_GAP  = 3
_MM_STEP = _MM_CELL + _MM_GAP


class SettingsOverlay:
    _STEP = 0.1

    def __init__(self, font_md, font_lg):
        self.font_md = font_md
        self.font_lg = font_lg
        bw, bh = 36, 30
        cx = SCREEN_W // 2
        self._sfx_minus   = Button((cx - 168, 0, bw, bh), "-", font_lg)
        self._sfx_plus    = Button((cx + 132, 0, bw, bh), "+", font_lg)
        self._music_minus = Button((cx - 168, 0, bw, bh), "-", font_lg)
        self._music_plus  = Button((cx + 132, 0, bw, bh), "+", font_lg)

    def handle_event(self, event):
        import sound as _sound
        if self._sfx_minus.is_clicked(event):
            _sound.set_sfx_volume(_sound.SFX_VOL - self._STEP)
            _sound.save_settings()
        elif self._sfx_plus.is_clicked(event):
            _sound.set_sfx_volume(_sound.SFX_VOL + self._STEP)
            _sound.save_settings()
        elif self._music_minus.is_clicked(event):
            _sound.set_music_volume(_sound.MUSIC_VOL - self._STEP)
            _sound.save_settings()
        elif self._music_plus.is_clicked(event):
            _sound.set_music_volume(_sound.MUSIC_VOL + self._STEP)
            _sound.save_settings()

    def draw(self, screen):
        import sound as _sound
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        pw, ph = 500, 260
        px = (SCREEN_W - pw) // 2
        py = (SCREEN_H - ph) // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((18, 18, 38, 235))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (90, 90, 150), (px, py, pw, ph), 2, border_radius=8)

        title = self.font_lg.render("SETTINGS", True, (200, 175, 255))
        screen.blit(title, title.get_rect(centerx=SCREEN_W // 2, y=py + 16))

        cx = SCREEN_W // 2
        self._draw_row(screen, cx, py + 100, "SFX Volume",   _sound.SFX_VOL,
                       self._sfx_minus, self._sfx_plus)
        self._draw_row(screen, cx, py + 165, "Music Volume", _sound.MUSIC_VOL,
                       self._music_minus, self._music_plus)

        hint = self.font_md.render("ESC  to close", True, (130, 130, 155))
        screen.blit(hint, hint.get_rect(centerx=SCREEN_W // 2, y=py + ph - 30))

    def _draw_row(self, screen, cx, y, label, pct, btn_minus, btn_plus):
        lbl = self.font_md.render(label, True, (190, 190, 215))
        screen.blit(lbl, lbl.get_rect(centerx=cx, y=y - 22))

        bw = 240
        bx = cx - bw // 2
        pygame.draw.rect(screen, (35, 35, 55), (bx, y, bw, 18), border_radius=4)
        fill = int(bw * pct)
        if fill > 0:
            pygame.draw.rect(screen, (70, 130, 240), (bx, y, fill, 18), border_radius=4)
        pygame.draw.rect(screen, (90, 90, 145), (bx, y, bw, 18), 2, border_radius=4)

        pct_lbl = self.font_md.render(f"{int(round(pct * 100))}%", True, (230, 230, 230))
        screen.blit(pct_lbl, (cx + bw // 2 + 10, y))

        btn_minus.rect.topleft = (cx - bw // 2 - 40, y - 4)
        btn_plus.rect.topleft  = (cx + bw // 2 + 58, y - 4)
        btn_minus.draw(screen)
        btn_plus.draw(screen)


def _get_player_buffs(player):
    stat_rows = [
        ("Sword Damage",    str(player.sword.damage)),
        ("Sword Reach",     str(player.sword.reach)),
        ("Defense",         str(player.defense)),
        ("Parry Window",    f"{int(player.parry_window * 1000)} ms"),
        ("Parry DMG Mult",  f"{player.parry_dmg_mult:.1f}×"),
    ]
    if player.parry_heal_pct > 0:
        stat_rows.append(("Life Steal", f"{int(player.parry_heal_pct * 100)}%"))
    if player.parry_speed_boost_dur > 0:
        stat_rows.append(("Swift Parry", f"{player.parry_speed_boost_dur:.0f}s boost"))
    if player.sword.execute_pct > 0:
        stat_rows.append(("Execute", f"< {int(player.sword.execute_pct * 100)}% HP"))

    active_rows = []
    if player.parry_cooldown > 0:
        active_rows.append(("Parry",        f"CD {player.parry_cooldown:.1f}s", False))
    else:
        active_rows.append(("Parry",        "Ready",   True))
    if player.parry_speed_boost_timer > 0:
        active_rows.append(("Speed Boost",  f"{player.parry_speed_boost_timer:.1f}s", True))
    if player.sword.flame:
        active_rows.append(("Flame Blade",  "Active",  True))
    if player.sword.slow:
        active_rows.append(("Frost Blade",  "Active",  True))
    if player.parry_instakill:
        active_rows.append(("Parry Instakill", "Active", True))
    if player.invulnerable_timer > 0:
        active_rows.append(("Invulnerable", f"{player.invulnerable_timer:.1f}s", True))

    return stat_rows, active_rows


def draw_buff_screen(screen, player, font_md, font_lg, font_sm):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    pw, ph = 640, 430
    px = (SCREEN_W - pw) // 2
    py = (SCREEN_H - ph) // 2
    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    panel.fill((18, 18, 38, 235))
    screen.blit(panel, (px, py))
    pygame.draw.rect(screen, (90, 90, 150), (px, py, pw, ph), 2, border_radius=8)

    title = font_lg.render("BUFFS & STATS", True, (200, 175, 255))
    screen.blit(title, title.get_rect(centerx=SCREEN_W // 2, y=py + 12))

    mid = px + pw // 2
    pygame.draw.line(screen, (70, 70, 110), (mid, py + 55), (mid, py + ph - 30), 1)

    lx = px + 18
    rx = mid + 14
    header_y = py + 56

    screen.blit(font_md.render("Passive Stats", True, (140, 190, 255)),  (lx, header_y))
    screen.blit(font_md.render("Active Effects", True, (255, 190, 100)), (rx, header_y))
    pygame.draw.line(screen, (70, 70, 110), (px + 8, header_y + 22), (px + pw - 8, header_y + 22), 1)

    stat_rows, active_rows = _get_player_buffs(player)
    col_w  = pw // 2 - 30
    row_h  = 26
    y0     = header_y + 30

    for i, (name, val) in enumerate(stat_rows):
        ry = y0 + i * row_h
        if ry + row_h > py + ph - 28:
            break
        screen.blit(font_sm.render(name, True, (180, 180, 215)), (lx, ry))
        vs = font_sm.render(val, True, (240, 215, 80))
        screen.blit(vs, (lx + col_w - vs.get_width(), ry))

    for i, (name, val, active) in enumerate(active_rows):
        ry = y0 + i * row_h
        if ry + row_h > py + ph - 28:
            break
        screen.blit(font_sm.render(name, True, (200, 180, 220)), (rx, ry))
        color = (100, 240, 130) if active else (160, 100, 100)
        vs = font_sm.render(val, True, color)
        screen.blit(vs, (rx + col_w - vs.get_width(), ry))

    hint = font_sm.render("TAB  to close", True, (130, 130, 155))
    screen.blit(hint, hint.get_rect(centerx=SCREEN_W // 2, y=py + ph - 22))


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

    # ── legend (top-right) ────────────────────────────────────────────────
    legend = [
        ((50,  200,  50), "Start"),
        ((180,  60,  60), "Monster"),
        ((220, 100,  20), "Boss"),
        ((200, 180,  50), "Shop"),
        ((60,  120, 200), "Item"),
        ((0,   180, 220), "Exit"),
    ]
    sq   = 13
    lg_x = sw - 130
    lg_y = 18
    lg_w = 118
    lg_h = len(legend) * 22 + 28
    leg_bg = pygame.Surface((lg_w, lg_h), pygame.SRCALPHA)
    leg_bg.fill((0, 0, 0, 170))
    screen.blit(leg_bg, (lg_x - 4, lg_y - 4))
    head = font.render("LEGEND", True, (180, 180, 200))
    screen.blit(head, (lg_x + (lg_w - head.get_width()) // 2 - 4, lg_y))
    y_off = lg_y + head.get_height() + 6
    for col, label in legend:
        pygame.draw.rect(screen, col, (lg_x, y_off, sq, sq))
        txt = font.render(label, True, (210, 210, 210))
        screen.blit(txt, (lg_x + sq + 7, y_off - 1))
        y_off += 22
    # "you are here" indicator row
    pygame.draw.rect(screen, (60, 60, 60), (lg_x, y_off, sq, sq))
    pygame.draw.rect(screen, (255, 255, 255), (lg_x, y_off, sq, sq), 2)
    txt = font.render("You", True, (210, 210, 210))
    screen.blit(txt, (lg_x + sq + 7, y_off - 1))


# ── Stats screen (pure pygame, no matplotlib) ─────────────────────────────────

_SC = {
    'bg':     ( 12,  12,  22),
    'panel':  ( 22,  22,  40),
    'border': ( 70,  70, 110),
    'grid':   ( 35,  35,  55),
    'axis':   ( 80,  80, 110),
    'text':   (210, 210, 230),
    'dim':    (130, 130, 155),
    'title':  (180, 140, 255),
    'blue':   ( 70, 130, 200),
    'orange': (220, 100,  60),
    'green':  (  0, 178, 128),
    'red':    (200,  60,  60),
    'purple': (108,  92, 220),
    'pie':    [(255,110,110),(70,200,180),(160,130,255),(250,195,80)],
}

_PAD_L, _PAD_R, _PAD_T, _PAD_B = 58, 8, 26, 40


def _chart_area(panel_rect):
    px, py, pw, ph = panel_rect
    return pygame.Rect(px + _PAD_L, py + _PAD_T,
                       pw - _PAD_L - _PAD_R, ph - _PAD_T - _PAD_B)


def _y_ticks(y_max, n=5):
    """Return list of (value, label_str) for y-axis, from 0 to above y_max."""
    if y_max <= 0:
        return [(0, '0')]
    raw = y_max / (n - 1)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = math.ceil(raw / mag) * mag
    if step == 0:
        step = 1
    top = math.ceil(y_max / step) * step
    ticks, v = [], 0.0
    while v <= top + step * 0.01:
        lbl = str(int(v)) if v == int(v) else f'{v:.1f}'
        ticks.append((v, lbl))
        v = round(v + step, 10)
    return ticks


def _x_int_labels(x_vals, max_labels=10):
    """Subset of x_vals to label on x-axis — always integers, never decimals."""
    n = len(x_vals)
    if n == 0:
        return []
    if n <= max_labels:
        return list(x_vals)
    step = math.ceil(n / max_labels)
    shown = [x_vals[i] for i in range(0, n, step)]
    if x_vals[-1] not in shown:
        shown.append(x_vals[-1])
    return shown


def _draw_axes(surface, chart_rect, y_max, font_tick):
    """Draw grid lines + y-axis labels. Returns the actual top tick value."""
    ticks = _y_ticks(y_max)
    top_val = ticks[-1][0] if ticks else 1
    if top_val <= 0:
        top_val = 1
    cx, cy, cw, ch = chart_rect
    for val, lbl in ticks:
        sy = cy + ch - int(val / top_val * ch)
        if not (cy <= sy <= cy + ch):
            continue
        pygame.draw.line(surface, _SC['grid'], (cx, sy), (cx + cw, sy), 1)
        t = font_tick.render(lbl, True, _SC['dim'])
        surface.blit(t, (cx - t.get_width() - 4, sy - t.get_height() // 2))
    pygame.draw.line(surface, _SC['axis'], (cx, cy),      (cx, cy + ch), 1)
    pygame.draw.line(surface, _SC['axis'], (cx, cy + ch), (cx + cw, cy + ch), 1)
    return top_val


def _panel_bg(surface, panel_rect, title, font_title):
    pygame.draw.rect(surface, _SC['panel'],  panel_rect, border_radius=5)
    pygame.draw.rect(surface, _SC['border'], panel_rect, 1, border_radius=5)
    px, py, pw, _ = panel_rect
    t = font_title.render(title, True, _SC['title'])
    surface.blit(t, t.get_rect(centerx=px + pw // 2, y=py + 4))


def _ylabel(surface, panel_rect, label, font):
    px, py, _, ph = panel_rect
    t = pygame.transform.rotate(font.render(label, True, _SC['dim']), 90)
    cy = py + _PAD_T + (ph - _PAD_T - _PAD_B) // 2
    surface.blit(t, t.get_rect(centerx=px + 10, centery=cy))


def _xlabel_center(surface, panel_rect, label, font):
    px, py, pw, ph = panel_rect
    t = font.render(label, True, _SC['dim'])
    surface.blit(t, t.get_rect(centerx=px + pw // 2, y=py + ph - font.get_height() - 2))


def _draw_bar(surface, panel_rect, run_nums, y_vals, color,
              title, xlabel, ylabel, font_title, font_tick):
    _panel_bg(surface, panel_rect, title, font_title)
    if not run_nums:
        return
    cr = _chart_area(panel_rect)
    y_max  = max(y_vals) if y_vals else 1
    top    = _draw_axes(surface, cr, y_max, font_tick)
    n      = len(run_nums)
    spacing = cr.width / n
    bar_w   = max(2, int(spacing * 0.7))
    for i, yv in enumerate(y_vals):
        bh = int(yv / top * cr.height) if top > 0 else 0
        bx = cr.x + int(i * spacing + (spacing - bar_w) / 2)
        pygame.draw.rect(surface, color, (bx, cr.y + cr.height - bh, bar_w, bh))
    shown = _x_int_labels(run_nums)
    for rn in shown:
        idx = run_nums.index(rn)
        bx  = cr.x + int(idx * spacing + spacing / 2)
        t   = font_tick.render(str(rn), True, _SC['dim'])
        surface.blit(t, t.get_rect(centerx=bx, y=cr.y + cr.height + 4))
    _xlabel_center(surface, panel_rect, xlabel, font_tick)
    _ylabel(surface, panel_rect, ylabel, font_tick)


def _draw_line(surface, panel_rect, run_nums, y_vals, color,
               title, xlabel, ylabel, font_title, font_tick):
    _panel_bg(surface, panel_rect, title, font_title)
    if not run_nums:
        return
    cr  = _chart_area(panel_rect)
    y_max = max(y_vals) if y_vals else 1
    top   = _draw_axes(surface, cr, y_max, font_tick)
    n     = len(run_nums)
    spacing = cr.width / n

    def _pt(i, yv):
        x = cr.x + int(i * spacing + spacing / 2)
        y = cr.y + cr.height - int(yv / top * cr.height) if top > 0 else cr.y + cr.height
        return (x, y)

    pts = [_pt(i, yv) for i, yv in enumerate(y_vals)]
    if len(pts) >= 2:
        pygame.draw.lines(surface, color, False, pts, 2)
    for p in pts:
        pygame.draw.circle(surface, color, p, 4)
    shown = _x_int_labels(run_nums)
    for rn in shown:
        idx = run_nums.index(rn)
        t   = font_tick.render(str(rn), True, _SC['dim'])
        surface.blit(t, t.get_rect(centerx=_pt(idx, 0)[0], y=cr.y + cr.height + 4))
    _xlabel_center(surface, panel_rect, xlabel, font_tick)
    _ylabel(surface, panel_rect, ylabel, font_tick)


def _draw_grouped_bars(surface, panel_rect, p_totals, m_totals, title, font_title, font_tick):
    _panel_bg(surface, panel_rect, title, font_title)
    cr    = _chart_area(panel_rect)
    y_max = max(p_totals + m_totals + [1])
    top   = _draw_axes(surface, cr, y_max, font_tick)
    grp_w = cr.width / 3
    bw    = int(grp_w * 0.28)
    for i, (pv, mv) in enumerate(zip(p_totals, m_totals)):
        gc = cr.x + int(i * grp_w + grp_w / 2)
        ph = int(pv / top * cr.height) if top > 0 else 0
        mh = int(mv / top * cr.height) if top > 0 else 0
        pygame.draw.rect(surface, _SC['green'], (gc - bw - 1, cr.y + cr.height - ph, bw, ph))
        pygame.draw.rect(surface, _SC['red'],   (gc + 1,      cr.y + cr.height - mh, bw, mh))
        t = font_tick.render(f'Floor {i+1}', True, _SC['dim'])
        surface.blit(t, t.get_rect(centerx=gc, y=cr.y + cr.height + 4))
    # Legend
    px, py = panel_rect[0], panel_rect[1]
    lx, ly = px + _PAD_L + 4, py + _PAD_T + 4
    pygame.draw.rect(surface, _SC['green'], (lx, ly, 9, 9))
    surface.blit(font_tick.render('Success', True, _SC['text']), (lx + 13, ly - 1))
    pygame.draw.rect(surface, _SC['red'], (lx + 68, ly, 9, 9))
    surface.blit(font_tick.render('Missed',  True, _SC['text']), (lx + 81, ly - 1))
    _ylabel(surface, panel_rect, 'Count', font_tick)


def _draw_histogram(surface, panel_rect, values, title, font_title, font_tick):
    _panel_bg(surface, panel_rect, title, font_title)
    if not values:
        return
    BIN = 10
    counts = {}
    for v in values:
        b = (v // BIN) * BIN
        counts[b] = counts.get(b, 0) + 1
    # fill empty bins so the range is continuous
    lo = min(counts)
    hi = max(counts)
    x_vals = list(range(lo, hi + BIN, BIN))
    y_vals = [counts.get(x, 0) for x in x_vals]
    cr      = _chart_area(panel_rect)
    y_max   = max(y_vals) if y_vals else 1
    top     = _draw_axes(surface, cr, y_max, font_tick)
    n       = len(x_vals)
    spacing = cr.width / max(n, 1)
    bar_w   = max(2, int(spacing * 0.8))
    for i, (xv, yv) in enumerate(zip(x_vals, y_vals)):
        bh = int(yv / top * cr.height) if top > 0 else 0
        bx = cr.x + int(i * spacing + (spacing - bar_w) / 2)
        pygame.draw.rect(surface, _SC['purple'], (bx, cr.y + cr.height - bh, bar_w, bh))
        label = f'{xv}-{xv + BIN - 1}'
        t = font_tick.render(label, True, _SC['dim'])
        surface.blit(t, t.get_rect(centerx=bx + bar_w // 2, y=cr.y + cr.height + 4))
    _xlabel_center(surface, panel_rect, 'Enemies Killed', font_tick)
    _ylabel(surface, panel_rect, 'Frequency', font_tick)


def _draw_pie(surface, panel_rect, values, labels, colors, title, font_title, font_tick):
    _panel_bg(surface, panel_rect, title, font_title)
    px, py, pw, ph = panel_rect
    total = sum(values)
    if total <= 0:
        t = font_tick.render('No purchases yet', True, _SC['dim'])
        surface.blit(t, t.get_rect(centerx=px + pw // 2, centery=py + ph // 2))
        return
    cr     = _chart_area(panel_rect)
    radius = min(cr.width, cr.height) // 2 - 12
    cx     = px + pw // 2
    cy     = cr.y + cr.height // 2 + 4
    angle  = -math.pi / 2
    wedges = []
    for val, label, color in zip(values, labels, colors):
        sweep = val / total * 2 * math.pi
        wedges.append((angle, sweep, angle + sweep / 2, val, label, color))
        angle += sweep
    for sa, sweep, mid, val, label, color in wedges:
        if sweep <= 0:
            continue
        n_pts = max(3, int(sweep / (2 * math.pi) * 48))
        pts   = [(cx, cy)]
        for k in range(n_pts + 1):
            a = sa + sweep * k / n_pts
            pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, _SC['panel'], pts, 1)
        lx = cx + (radius + 16) * math.cos(mid)
        ly = cy + (radius + 16) * math.sin(mid)
        t  = font_tick.render(f'{val/total*100:.0f}%', True, _SC['text'])
        surface.blit(t, t.get_rect(center=(int(lx), int(ly))))
    # Legend at bottom of panel
    lg_x = px + 6
    lg_y = py + ph - len(values) * 13 - 4
    for label, color in zip(labels, colors):
        pygame.draw.rect(surface, color, (lg_x, lg_y, 8, 8))
        surface.blit(font_tick.render(label, True, _SC['text']), (lg_x + 12, lg_y - 1))
        lg_y += 13


def _draw_summary(surface, panel_rect, cd, font_title, font_label, font_tick):
    _panel_bg(surface, panel_rect, 'Summary Table', font_title)
    px, py, pw, ph = panel_rect
    if cd['n_runs'] == 0:
        t = font_label.render('No data yet', True, _SC['dim'])
        surface.blit(t, t.get_rect(centerx=px + pw // 2, centery=py + ph // 2))
        return
    rows = [
        ('Metric',         'Best',                             'Average'),
        ('Survived Time',  f"{cd['best_time']:.0f}s",         f"{cd['avg_time']:.0f}s"),
        ('Damage Dealt',   f"{cd['best_damage']:.0f}",        f"{cd['avg_damage']:.0f}"),
        ('Enemies Killed', str(cd['best_kills']),              f"{cd['avg_kills']:.1f}"),
        ('Runs / Clears',  str(cd['n_runs']),                  str(cd['n_clears'])),
        ('Clear Rate',     f"{cd['clear_pct']:.1f}%",         ''),
    ]
    col_xs = [px + 8, px + pw // 2 - 40, px + pw - 6]
    row_h  = 28
    y0     = py + _PAD_T + 10
    for i, (m, b, a) in enumerate(rows):
        ry   = y0 + i * row_h
        font = font_label if i == 0 else font_tick
        mc   = _SC['title'] if i == 0 else _SC['text']
        bc   = _SC['title'] if i == 0 else (255, 215, 80)
        ac   = _SC['title'] if i == 0 else _SC['dim']
        if i == 1:
            pygame.draw.line(surface, _SC['border'],
                             (px + 4, ry - 3), (px + pw - 4, ry - 3), 1)
        surface.blit(font.render(m, True, mc), (col_xs[0], ry))
        tb = font.render(b, True, bc)
        surface.blit(tb, tb.get_rect(right=col_xs[1] + 40, y=ry))
        ta = font.render(a, True, ac)
        surface.blit(ta, ta.get_rect(right=col_xs[2], y=ry))


def draw_stats_screen(surface, chart_data, font_title, font_label, font_tick):
    """Render all 5 graphs + summary table using pure pygame (no matplotlib)."""
    surface.fill(_SC['bg'])
    # Header
    hdr = font_title.render('Blade Echo — Run Statistics', True, _SC['title'])
    surface.blit(hdr, hdr.get_rect(centerx=SCREEN_W // 2, y=5))
    # Footer hint
    hint = font_tick.render('ESC  to close', True, _SC['dim'])
    surface.blit(hint, hint.get_rect(centerx=SCREEN_W // 2, y=SCREEN_H - 18))

    cd = chart_data
    if not cd or cd.get('n_runs', 0) == 0:
        msg = font_label.render('No run data yet — play a run first!', True, _SC['dim'])
        surface.blit(msg, msg.get_rect(centerx=SCREEN_W // 2, centery=SCREEN_H // 2))
        return

    # 2-row × 3-col panel grid
    M       = 6
    top_y   = 34
    bot_y   = SCREEN_H - 22
    panel_h = (bot_y - top_y - M) // 2
    panel_w = (SCREEN_W - M * 4) // 3

    def _pr(row, col):
        return (M + col * (panel_w + M), top_y + row * (panel_h + M), panel_w, panel_h)

    rn = cd['run_nums']

    # Row 0
    _draw_bar(surface, _pr(0, 0), rn, cd['survived'], _SC['blue'],
              'Graph 1: Survived Time per Run',
              'Run Number', 'Time (s)', font_label, font_tick)

    _draw_pie(surface, _pr(0, 1),
              [cd['money_by_cat'][k] for k in ('healing', 'sword', 'parry', 'other')],
              ['Healing', 'Sword Upgrades', 'Parry Upgrades', 'Other'],
              _SC['pie'], 'Graph 2: Money Spent by Category', font_label, font_tick)

    _draw_grouped_bars(surface, _pr(0, 2), cd['p_totals'], cd['m_totals'],
                       'Graph 3: Parries by Floor (all runs)', font_label, font_tick)

    # Row 1
    _draw_line(surface, _pr(1, 0), rn, cd['damage'], _SC['orange'],
               'Graph 4: Damage Dealt per Run',
               'Run Number', 'Damage (HP)', font_label, font_tick)

    _draw_histogram(surface, _pr(1, 1), cd['kills'],
                    'Graph 5: Enemies Killed Distribution', font_label, font_tick)

    _draw_summary(surface, _pr(1, 2), cd, font_label, font_label, font_tick)
