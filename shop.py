import pygame
import random
import math
from constants import SCREEN_W, SCREEN_H
from ui import notify_item

# ── Layout ────────────────────────────────────────────────────────────────────
CARD_W   = 160
CARD_H   = 230
CARD_GAP = 18


_CARD_COLOR   = (40, 40, 62)
_CARD_HOVER   = (60, 62, 95)
_CARD_BOUGHT  = (28, 28, 40)
_GOLD         = (255, 215,   0)
_TEXT         = (220, 220, 230)
_DIM          = (120, 120, 120)
_TITLE        = (180, 120, 255)
_BORDER       = ( 80,  80, 120)

RARITY_WEIGHT_BY_FLOOR = {
    1: {'common': 80, 'rare': 15, 'epic':  5, 'legendary':  0},
    2: {'common': 55, 'rare': 25, 'epic': 15, 'legendary':  5},
    3: {'common': 20, 'rare': 30, 'epic': 30, 'legendary': 20},
}
RARITY_COLOR  = {
    'common':    (180, 180, 180),
    'rare':      ( 80, 140, 255),
    'epic':      (180,  80, 255),
    'legendary': (255, 160,  30),
}


# ── Item definition ───────────────────────────────────────────────────────────

class ShopItem:
    def __init__(self, name, desc, price, effect, rarity='common', max_uses=None):
        self.name     = name
        self.desc     = desc
        self.price    = price
        self._effect  = effect
        self.rarity   = rarity
        self.max_uses = max_uses
        self.uses     = 0

    @property
    def sold_out(self):
        return self.max_uses is not None and self.uses >= self.max_uses

    def buy(self, player):
        if self.sold_out or player.coins < self.price:
            return False
        player.coins -= self.price
        self._effect(player)
        self.uses += 1
        return True


def _guaranteed():
    return ShopItem("+20 HP", "Restore 20 health points.", 3,
                    lambda p: setattr(p, 'hp', min(p.hp + 20, p.max_hp)))


def _make_pool():
    return [
        # common ──────────────────────────────────────────────────────────
        ShopItem("+5 Sword Dmg",   "Blade deals more damage.", 4,
                 lambda p: setattr(p.sword, 'damage', p.sword.damage + 5),
                 rarity='common'),

        ShopItem("Bigger Sword", "Your blade grows slightly each purchase (+5% size and reach).", 4,
                 lambda p: p.sword.upgrade(damage_bonus=0, reach_bonus=15),
                 rarity='common'),

        ShopItem("+20 Max HP", "Increase maximum health by 20.", 5,
                 lambda p: (setattr(p, 'max_hp', p.max_hp + 20),
                            setattr(p, 'hp',     p.hp     + 20)),
                 rarity='common'),

        # rare ────────────────────────────────────────────────────────────
        ShopItem("Wider Parry",    "Parry window lasts 50 ms longer.", 5,
                 lambda p: setattr(p, 'parry_window',
                                   round(p.parry_window + 0.05, 3)),
                 rarity='rare'),

        ShopItem("Bigger Parry Box", "Parry hitbox catches attacks from further away.", 5,
                 lambda p: setattr(p.sword, 'parry_pad', p.sword.parry_pad + 5),
                 rarity='rare'),

        ShopItem("Parry Weaken +", "Weakened enemies take 20% more bonus damage.", 6,
                 lambda p: setattr(p, 'parry_dmg_mult',
                                   round(p.parry_dmg_mult + 0.2, 2)),
                 rarity='rare'),

        ShopItem("Iron Skin", "Reduce all incoming damage by 3.", 7,
                 lambda p: setattr(p, 'defense', getattr(p, 'defense', 0) + 3),
                 rarity='rare'),

        # epic ────────────────────────────────────────────────────────────
        ShopItem("Swift Parry",  "Gain a 1.5x speed burst for 2 s after each parry.", 8,
                 lambda p: setattr(p, 'parry_speed_boost_dur', 2.0),
                 rarity='epic', max_uses=1),

        ShopItem("Life Steal",   "Recover 10% max HP on each successful parry.", 9,
                 lambda p: setattr(p, 'parry_heal_pct',
                                   round(p.parry_heal_pct + 0.10, 2)),
                 rarity='epic', max_uses=1),

        # legendary ───────────────────────────────────────────────────────
        ShopItem("Parry Execute", "Instantly kill the attacker on parry (not bosses).", 14,
                 lambda p: setattr(p, 'parry_instakill', True),
                 rarity='legendary', max_uses=1),

        ShopItem("Execute",      "Instantly kill enemies below 20% HP on sword hit.", 13,
                 lambda p: setattr(p.sword, 'execute_pct', 0.20),
                 rarity='epic', max_uses=1),

        # legendary ───────────────────────────────────────────────────────
        ShopItem("Flame Blade",  "Hits ignite enemies. Replaces Frost Blade.", 12,
                 lambda p: (setattr(p.sword, 'flame', True),
                            setattr(p.sword, 'slow',  False)),
                 rarity='legendary', max_uses=1),

        ShopItem("Frost Blade",  "Hits slow enemies. Replaces Flame Blade.", 12,
                 lambda p: (setattr(p.sword, 'slow',  True),
                            setattr(p.sword, 'flame', False)),
                 rarity='legendary', max_uses=1),
    ]


# ── Shop UI ───────────────────────────────────────────────────────────────────

class Shop:
    N_RANDOM = 2

    def __init__(self, floor_num=1):
        w_map   = RARITY_WEIGHT_BY_FLOOR.get(floor_num, RARITY_WEIGHT_BY_FLOOR[1])
        pool    = _make_pool()
        weights = [w_map[item.rarity] for item in pool]
        picked  = []
        seen    = set()
        while len(picked) < self.N_RANDOM and len(seen) < len(pool):
            choice = random.choices(pool, weights=weights, k=1)[0]
            if id(choice) not in seen:
                seen.add(id(choice))
                picked.append(choice)
        self._items = [_guaranteed()] + picked
        self.open   = False
        self._rects = []

        self._font_title = pygame.font.SysFont(None, 34)
        self._font_name  = pygame.font.SysFont(None, 21)
        self._font_desc  = pygame.font.SysFont(None, 17)
        self._font_price = pygame.font.SysFont(None, 22)

    def toggle(self):
        self.open = not self.open

    def handle_click(self, pos, player):
        if not self.open:
            return
        for i, rect in enumerate(self._rects):
            if rect.collidepoint(pos):
                item = self._items[i]
                if item.buy(player):
                    notify_item(item.name, item.rarity,
                                RARITY_COLOR.get(item.rarity, (200, 200, 200)))

    def draw(self, screen):
        if not self.open:
            return
        sw, sh = screen.get_size()

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))

        n       = len(self._items)
        total_w = n * CARD_W + (n - 1) * CARD_GAP
        ox      = (sw - total_w) // 2
        oy      = (sh - CARD_H) // 2

        title = self._font_title.render("SHOP  (E to close)", True, _TITLE)
        screen.blit(title, title.get_rect(centerx=sw // 2, y=oy - 46))

        self._rects = []
        mx, my = pygame.mouse.get_pos()
        for i, item in enumerate(self._items):
            rx   = ox + i * (CARD_W + CARD_GAP)
            rect = pygame.Rect(rx, oy, CARD_W, CARD_H)
            self._rects.append(rect)

            if item.sold_out:
                bg = _CARD_BOUGHT
            elif rect.collidepoint(mx, my):
                bg = _CARD_HOVER
            else:
                bg = _CARD_COLOR
            rarity_col = RARITY_COLOR.get(getattr(item, 'rarity', 'common'), _BORDER)
            pygame.draw.rect(screen, bg, rect, border_radius=8)
            pygame.draw.rect(screen, rarity_col, rect, 2, border_radius=8)

            rar_surf = self._font_desc.render(getattr(item, 'rarity', '').upper(),
                                              True, rarity_col)
            screen.blit(rar_surf, rar_surf.get_rect(centerx=rect.centerx, y=oy + 8))

            name_surf = self._font_name.render(item.name, True, _TEXT)
            screen.blit(name_surf, name_surf.get_rect(centerx=rect.centerx, y=oy + 24))

            self._wrap_text(screen, item.desc, rect.centerx, oy + 50, CARD_W - 16)

            if item.sold_out:
                price_surf = self._font_price.render("SOLD OUT", True, _DIM)
            else:
                price_surf = self._font_price.render(f"{item.price} coins", True, _GOLD)
            screen.blit(price_surf, price_surf.get_rect(centerx=rect.centerx,
                                                         y=oy + CARD_H - 32))

    def draw_hint(self, screen, font):
        if self.open:
            return
        hint = font.render("[E]  Open Shop", True, (255, 220, 80))
        r = hint.get_rect(centerx=SCREEN_W // 2, y=SCREEN_H - 40)
        bg = pygame.Surface((r.width + 16, r.height + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (r.x - 8, r.y - 4))
        screen.blit(hint, r)

    # ── internal ──────────────────────────────────────────────────────────────

    def _wrap_text(self, screen, text, cx, y, max_w):
        words, line = text.split(), []
        for word in words:
            test = ' '.join(line + [word])
            if self._font_desc.size(test)[0] > max_w and line:
                surf = self._font_desc.render(' '.join(line), True, (180, 180, 200))
                screen.blit(surf, surf.get_rect(centerx=cx, y=y))
                y   += 17
                line = [word]
            else:
                line.append(word)
        if line:
            surf = self._font_desc.render(' '.join(line), True, (180, 180, 200))
            screen.blit(surf, surf.get_rect(centerx=cx, y=y))


# ── Floor item (item rooms) ───────────────────────────────────────────────────

class FloorItem:
    SIZE = 26
    _font = None

    def __init__(self, x, y, shop_item):
        self._item     = shop_item
        self.x, self.y = x, y
        self.rect      = pygame.Rect(x - self.SIZE // 2, y - self.SIZE // 2,
                                     self.SIZE, self.SIZE)
        self.collected = False

    @property
    def name(self):   return self._item.name
    @property
    def rarity(self): return self._item.rarity

    def apply(self, player):
        self._item._effect(player)
        self.collected = True

    def draw(self, screen, cam_x, cam_y):
        if self.collected:
            return
        if FloorItem._font is None:
            FloorItem._font = pygame.font.SysFont(None, 17)
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        col = RARITY_COLOR.get(self._item.rarity, (200, 200, 200))
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() / 300)
        glow_col = tuple(int(c * pulse) for c in col)
        pygame.draw.rect(screen, (30, 30, 40),
                         (sx - self.SIZE // 2, sy - self.SIZE // 2, self.SIZE, self.SIZE),
                         border_radius=5)
        pygame.draw.rect(screen, glow_col,
                         (sx - self.SIZE // 2, sy - self.SIZE // 2, self.SIZE, self.SIZE),
                         2, border_radius=5)
        label = FloorItem._font.render(self._item.name, True, col)
        screen.blit(label, label.get_rect(centerx=sx, bottom=sy - self.SIZE // 2 - 2))


def _pick_floor_item(x, y, floor_num):
    w_map   = RARITY_WEIGHT_BY_FLOOR.get(floor_num, RARITY_WEIGHT_BY_FLOOR[1])
    pool    = _make_pool()
    weights = [w_map[item.rarity] for item in pool]
    picked  = random.choices(pool, weights=weights, k=1)[0]
    return FloorItem(x, y, picked)


def make_floor_items(cx, cy, floor_num, count=1):
    spread = 48
    xs = [cx] if count == 1 else [cx - spread * i + spread * (count - 1) // 2
                                   for i in range(count)]
    return [_pick_floor_item(x, cy, floor_num) for x in xs]
