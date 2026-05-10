import pygame
from constants import ROOM_W, ROOM_H, WALL_T, DOOR_SIZE, STEP_X, STEP_Y, SCREEN_W, SCREEN_H
from room import Room
from enemy import MeleeEnemy, RangedEnemy

_HINT_FONT    = None
_LUCK_FONT    = None
_CAT_FONT     = None   # catalog item name
_CAT_DESC_FONT = None  # catalog description

_RARITY_COLOR = {
    'common':    (180, 180, 180),
    'rare':      ( 80, 140, 255),
    'epic':      (180,  80, 255),
    'legendary': (255, 160,  30),
}

# (rarity, name, description)
_CATALOG = [
    ('common',    '+5 Sword Dmg',   'Blade deals more damage.'),
    ('common',    'Bigger Sword',   '+5% sword size and reach per purchase.'),
    ('common',    '+1 Max Heart',   'Maximum hearts +1.'),
    ('common',    '+2 Hearts',      'Restore 2 hearts  (shop only).'),
    ('rare',      'Wider Parry',    'Parry window lasts 50 ms longer.'),
    ('rare',      'Parry Weaken +', 'Weakened enemies take 20% more damage.'),
    ('rare',      'Iron Skin',      'Incoming damage reduced by 1.'),
    ('epic',      'Swift Parry',    '1.5x speed burst for 2 s after each parry.'),
    ('epic',      'Life Steal',     'Recover 10% max HP on each parry.'),
    ('epic',      'Execute',        'Insta-kill enemies below 20% HP on sword hit.'),
    ('legendary', 'Parry Execute',  'Insta-kill attacker on parry  (not bosses).'),
    ('legendary', 'Flame Blade',    'Hits ignite enemies.  Replaces Frost Blade.'),
    ('legendary', 'Frost Blade',    'Hits slow enemies.  Replaces Flame Blade.'),
]


def _hint_font():
    global _HINT_FONT
    if _HINT_FONT is None:
        _HINT_FONT = pygame.font.SysFont(None, 28)
    return _HINT_FONT


def _luck_font():
    global _LUCK_FONT
    if _LUCK_FONT is None:
        _LUCK_FONT = pygame.font.SysFont(None, 56)
    return _LUCK_FONT


def _cat_font():
    global _CAT_FONT
    if _CAT_FONT is None:
        _CAT_FONT = pygame.font.SysFont(None, 22)
    return _CAT_FONT


def _cat_desc_font():
    global _CAT_DESC_FONT
    if _CAT_DESC_FONT is None:
        _CAT_DESC_FONT = pygame.font.SysFont(None, 19)
    return _CAT_DESC_FONT


def _draw_label(screen, text, col, cx, y):
    font = _hint_font()
    surf = font.render(text, True, col)
    bg   = pygame.Surface((surf.get_width() + 18, surf.get_height() + 10), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 160))
    r = surf.get_rect(centerx=cx, y=y)
    screen.blit(bg, (r.x - 9, r.y - 5))
    screen.blit(surf, r)
    return y + surf.get_height() + 14


def _draw_catalog(screen):
    """Draw the full buff catalog panel in the centre of the screen."""
    pad   = 18
    col_w = (SCREEN_W - pad * 4) // 2
    panel_x = pad
    panel_y = 60
    panel_w = SCREEN_W - pad * 2
    panel_h = SCREEN_H - 130

    bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 185))
    screen.blit(bg, (panel_x, panel_y))

    fn   = _cat_font()
    fd   = _cat_desc_font()
    lh   = 36   # row height per item

    # split into two columns
    half  = (len(_CATALOG) + 1) // 2
    left  = _CATALOG[:half]
    right = _CATALOG[half:]

    title = _hint_font().render("ITEMS  &  BUFFS", True, (255, 240, 160))
    screen.blit(title, title.get_rect(centerx=SCREEN_W // 2, y=panel_y + 8))

    # column divider
    div_x = panel_x + col_w + pad * 2
    pygame.draw.line(screen, (80, 80, 100),
                     (div_x, panel_y + 34), (div_x, panel_y + panel_h - 10))

    for col_idx, entries in enumerate((left, right)):
        x = panel_x + pad + col_idx * (col_w + pad * 2)
        y = panel_y + 38

        for rarity, name, desc in entries:
            col = _RARITY_COLOR[rarity]
            name_surf = fn.render(f"[{rarity.upper()}]  {name}", True, col)
            desc_surf = fd.render(desc, True, (200, 200, 200))
            screen.blit(name_surf, (x, y))
            screen.blit(desc_surf, (x + 6, y + 16))
            y += lh


class DummyEnemy(MeleeEnemy):
    """Slime dummy — dashes at the player but never deals damage and never dies."""
    DASH_DAMAGE   = 0
    TOUCH_DAMAGE  = 0
    STUN_DURATION = 0.6

    def take_damage(self, _=0):
        return 0

    def update(self, player, dt, walls):
        old_hp     = player.hp
        super().update(player, dt, walls)
        player.hp  = max(old_hp, player.hp)
        self.alive = True


class DummyRangedEnemy(RangedEnemy):
    """Skeleton dummy — fires arrows (parriable) that deal no damage."""
    BULLET_DAMAGE = 0

    def take_damage(self, _=0):
        return 0

    def update(self, player, dt, walls):
        old_hp     = player.hp
        super().update(player, dt, walls)
        player.hp  = max(old_hp, player.hp)
        self.alive = True


class TutorialRoom(Room):
    PARRY_GOAL = 10

    def __init__(self, grid_x, grid_y, tut_type):
        is_start = (tut_type == 'walk')
        ev       = 'monster' if tut_type == 'fight' else 'item'
        super().__init__(grid_x, grid_y, event_type=ev,
                         is_boss=False, is_start=is_start)
        self.tut_type       = tut_type
        self._parry_count   = 0
        self._prev_parry_cd = 0.0
        self.visited        = True

    def try_lock(self, player_rect):
        if self.tut_type == 'fight':
            super().try_lock(player_rect)

    def clear(self):
        self.enemies.clear()
        self.is_cleared = True
        self.is_locked  = False

    def update(self, player, dt, walls):
        if self.tut_type == 'fight':
            if self._prev_parry_cd == 0 and player.parry_cooldown > 0:
                self._parry_count += 1
            self._prev_parry_cd = player.parry_cooldown
            if self._parry_count >= self.PARRY_GOAL and not self.is_cleared:
                self.enemies.clear()   # let super().update() → clear() open the room
            elif not self.enemies and not self.is_cleared:
                self._spawn_dummies()
        super().update(player, dt, walls)

    def _spawn_dummies(self):
        cx = self.wx + ROOM_W // 2
        cy = self.wy + ROOM_H // 2
        self.enemies = [
            DummyEnemy(cx - 90, cy,      1),   # slime
            DummyRangedEnemy(cx + 80, cy - 40, 1),  # skeleton
        ]

    def draw_hint(self, screen):
        cx = SCREEN_W // 2
        if self.tut_type == 'walk':
            y = SCREEN_H - 130
            y = _draw_label(screen, "Move:   W  A  S  D",  (200, 230, 255), cx, y)
            y = _draw_label(screen, "Slash:  Left Click",  (200, 230, 255), cx, y)
            y = _draw_label(screen, "Parry:  SPACE",       (200, 230, 255), cx, y)
            _draw_label(screen,     "Map:    M",           (200, 230, 255), cx, y)

        elif self.tut_type == 'parry':
            _draw_catalog(screen)
            _draw_label(screen,
                        "TAB — view your buffs  |  ESC — settings",
                        (200, 230, 255), cx, SCREEN_H - 56)

        elif self.tut_type == 'fight':
            remaining = max(0, self.PARRY_GOAL - self._parry_count)
            if remaining > 0:
                text = f"Parry  {remaining}  more time{'s' if remaining != 1 else ''}  to proceed"
                col  = (255, 230, 80)
            else:
                text = "Well done!   Head north!"
                col  = (100, 255, 120)
            _draw_label(screen, text, col, cx, SCREEN_H - 72)

        elif self.tut_type == 'gate':
            font = _luck_font()
            surf = font.render("GOOD  LUCK!", True, (255, 210, 50))
            bg   = pygame.Surface((surf.get_width() + 28, surf.get_height() + 16),
                                  pygame.SRCALPHA)
            bg.fill((0, 0, 0, 170))
            r = surf.get_rect(centerx=cx, centery=SCREEN_H // 2 - 80)
            screen.blit(bg, (r.x - 14, r.y - 8))
            screen.blit(surf, r)


def build_tutorial():
    """Return (rooms, start_room) for the 4-room tutorial sequence."""
    walk_room  = TutorialRoom(0, 3, 'walk')
    parry_room = TutorialRoom(0, 2, 'parry')
    fight_room = TutorialRoom(0, 1, 'fight')
    gate_room  = TutorialRoom(0, 0, 'gate')

    walk_room.connect(parry_room)
    parry_room.connect(fight_room)
    fight_room.connect(gate_room)

    all_rooms = [walk_room, parry_room, fight_room, gate_room]
    for room in all_rooms:
        wx = room.grid_x * STEP_X
        wy = room.grid_y * STEP_Y
        room.setup_geometry(wx, wy, ROOM_W, ROOM_H, WALL_T, DOOR_SIZE)
        room.visited = True

    fight_room._spawn_dummies()
    gate_room.place_gate()

    return all_rooms, walk_room
