import pygame
from constants import SCREEN_W, SCREEN_H

# ── Buff registry ─────────────────────────────────────────────────────────────

def _shrink_sword(p):
    p.sword.scale = max(1.0, p.sword.scale - 0.05)
    p.sword.reach = int(p.sword._base_reach * p.sword.scale)
    w = int(p.sword.img_base.get_width()  * p.sword.scale)
    h = int(p.sword.img_base.get_height() * p.sword.scale)
    p.sword.image = pygame.transform.scale(p.sword.img_base, (w, h))

# (display_name, give_fn, remove_fn)
_BUFFS = {
    'sword_dmg':    ('+5 Sword Dmg',
                     lambda p: setattr(p.sword, 'damage', p.sword.damage + 5),
                     lambda p: setattr(p.sword, 'damage', max(1, p.sword.damage - 5))),

    'sword_size':   ('Bigger Sword',
                     lambda p: p.sword.upgrade(damage_bonus=0, reach_bonus=15),
                     _shrink_sword),

    'max_heart':    ('+1 Max Heart',
                     lambda p: (setattr(p, 'max_hp', p.max_hp + 1),
                                setattr(p, 'hp',     p.hp     + 1)),
                     lambda p: (setattr(p, 'max_hp', max(1, p.max_hp - 1)),
                                setattr(p, 'hp',     min(p.hp, p.max_hp)))),

    'heal':         ('+2 Hearts',
                     lambda p: setattr(p, 'hp', min(p.hp + 2, p.max_hp)),
                     lambda p: setattr(p, 'hp', max(1, p.hp - 2))),

    'wider_parry':  ('Wider Parry',
                     lambda p: setattr(p, 'parry_window', round(p.parry_window + 0.05, 3)),
                     lambda p: setattr(p, 'parry_window', max(0.05, round(p.parry_window - 0.05, 3)))),

    'parry_weaken': ('Parry Weaken +',
                     lambda p: setattr(p, 'parry_dmg_mult', round(p.parry_dmg_mult + 0.2, 2)),
                     lambda p: setattr(p, 'parry_dmg_mult', max(1.0, round(p.parry_dmg_mult - 0.2, 2)))),

    'iron_skin':    ('Iron Skin',
                     lambda p: setattr(p, 'defense', p.defense + 1),
                     lambda p: setattr(p, 'defense', max(0, p.defense - 1))),

    'swift_parry':  ('Swift Parry',
                     lambda p: setattr(p, 'parry_speed_boost_dur', 2.0),
                     lambda p: setattr(p, 'parry_speed_boost_dur', 0.0)),

    'life_steal':   ('Life Steal',
                     lambda p: setattr(p, 'parry_heal_pct', round(p.parry_heal_pct + 0.1, 2)),
                     lambda p: setattr(p, 'parry_heal_pct', max(0.0, round(p.parry_heal_pct - 0.1, 2)))),

    'parry_kill':   ('Parry Execute',
                     lambda p: setattr(p, 'parry_instakill', True),
                     lambda p: setattr(p, 'parry_instakill', False)),

    'execute':      ('Execute',
                     lambda p: setattr(p.sword, 'execute_pct', 0.20),
                     lambda p: setattr(p.sword, 'execute_pct', 0.0)),

    'flame':        ('Flame Blade',
                     lambda p: (setattr(p.sword, 'flame', True),
                                setattr(p.sword, 'slow',  False)),
                     lambda p:  setattr(p.sword, 'flame', False)),

    'frost':        ('Frost Blade',
                     lambda p: (setattr(p.sword, 'slow',  True),
                                setattr(p.sword, 'flame', False)),
                     lambda p:  setattr(p.sword, 'slow',  False)),
}

# ── Visual constants ──────────────────────────────────────────────────────────

_H        = 220
_PAD      = 8
_LINE_H   = 16
_INPUT_H  = 24
_LOG_MAX  = 14

_C_BG     = (10,  12,  20)
_C_BORDER = (80,  80, 120)
_C_INPUT  = (20,  24,  38)
_C_PROMPT = (120, 200, 255)
_C_OK     = (100, 220, 100)
_C_ERR    = (255,  80,  80)
_C_INFO   = (200, 200, 200)
_C_DIM    = (120, 120, 140)


# ── DevConsole ────────────────────────────────────────────────────────────────

class DevConsole:
    def __init__(self):
        self.open          = False
        self._input        = ''
        self._log          = []
        self._font         = pygame.font.SysFont('Consolas', 14)
        self._cursor_timer = 0.0
        self._show_cursor  = True
        self._log_msg('Dev console  —  type  help  for commands.', _C_DIM)

    # ── public API ────────────────────────────────────────────────────────

    def toggle(self):
        self.open = not self.open
        self._input = ''

    def handle_event(self, event, player):
        """Pass KEYDOWN events here while playing. Returns True if consumed."""
        if not self.open:
            return False
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_RETURN:
            self._execute(self._input.strip(), player)
            self._input = ''
        elif event.key == pygame.K_BACKSPACE:
            self._input = self._input[:-1]
        elif event.unicode and event.unicode.isprintable():
            self._input += event.unicode
        return True

    def update(self, dt):
        if not self.open:
            return
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._show_cursor  = not self._show_cursor

    def draw(self, screen):
        if not self.open:
            return
        sw = screen.get_width()
        y0 = SCREEN_H - _H

        bg = pygame.Surface((sw, _H), pygame.SRCALPHA)
        bg.fill((*_C_BG, 210))
        screen.blit(bg, (0, y0))
        pygame.draw.line(screen, _C_BORDER, (0, y0), (sw, y0), 1)

        # log area
        max_lines = (_H - _INPUT_H - _PAD * 3) // _LINE_H
        ly = y0 + _PAD
        for text, col in self._log[-max_lines:]:
            screen.blit(self._font.render(text, True, col), (_PAD, ly))
            ly += _LINE_H

        # input bar
        iy = SCREEN_H - _INPUT_H - _PAD
        bar_rect = pygame.Rect(_PAD, iy, sw - _PAD * 2, _INPUT_H)
        pygame.draw.rect(screen, _C_INPUT,  bar_rect, border_radius=3)
        pygame.draw.rect(screen, _C_BORDER, bar_rect, 1, border_radius=3)

        prompt = self._font.render('> ', True, _C_PROMPT)
        px     = _PAD + 4
        py     = iy + (_INPUT_H - prompt.get_height()) // 2
        screen.blit(prompt, (px, py))

        cursor = '|' if self._show_cursor else ' '
        screen.blit(self._font.render(self._input + cursor, True, _C_INFO),
                    (px + prompt.get_width(), py))

    # ── command execution ─────────────────────────────────────────────────

    def _log_msg(self, text, color=_C_INFO):
        self._log.append((text, color))
        if len(self._log) > _LOG_MAX:
            self._log.pop(0)

    def _execute(self, text, player):
        if not text:
            return
        self._log_msg(f'> {text}', _C_PROMPT)
        parts = text.lower().split()
        cmd   = parts[0] if parts else ''

        if cmd == 'help':
            self._log_msg('give <buff> [n]   remove <buff> [n]   list', _C_DIM)
            self._log_msg('hp <n>            maxhp <n>           coins <n>', _C_DIM)
            self._log_msg('damage <n>        speed <n>           defense <n>', _C_DIM)
            self._log_msg('scale <f>         (sword size, e.g. scale 1.5)', _C_DIM)

        elif cmd == 'list':
            for key, (label, *_) in _BUFFS.items():
                self._log_msg(f'  {key:<16} {label}', _C_INFO)

        elif cmd in ('give', 'remove'):
            if len(parts) < 2:
                self._log_msg(f'Usage: {cmd} <buff> [count]', _C_ERR)
                return
            key = parts[1]
            if key not in _BUFFS:
                self._log_msg(f'Unknown buff "{key}"  —  use  list  to see all', _C_ERR)
                return
            count = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
            label, fn_give, fn_remove = _BUFFS[key]
            if cmd == 'give':
                for _ in range(count):
                    fn_give(player)
                self._log_msg(f'+ {label}{"  x" + str(count) if count > 1 else ""}', _C_OK)
            else:
                for _ in range(count):
                    fn_remove(player)
                self._log_msg(f'- {label}{"  x" + str(count) if count > 1 else ""}', _C_ERR)

        elif cmd == 'hp':
            if len(parts) < 2 or not parts[1].lstrip('-').isdigit():
                self._log_msg('Usage: hp <n>', _C_ERR)
                return
            n = int(parts[1])
            player.hp = max(1, min(n, player.max_hp))
            self._log_msg(f'HP  →  {player.hp} / {player.max_hp}', _C_OK)

        elif cmd == 'maxhp':
            if len(parts) < 2 or not parts[1].isdigit():
                self._log_msg('Usage: maxhp <n>', _C_ERR)
                return
            n = max(1, int(parts[1]))
            player.max_hp = n
            player.hp     = min(player.hp, n)
            self._log_msg(f'Max HP  →  {player.max_hp}  (HP {player.hp})', _C_OK)

        elif cmd == 'coins':
            if len(parts) < 2 or not parts[1].lstrip('-').isdigit():
                self._log_msg('Usage: coins <n>', _C_ERR)
                return
            player.coins = max(0, player.coins + int(parts[1]))
            self._log_msg(f'Coins  →  {player.coins}', _C_OK)

        elif cmd == 'damage':
            if len(parts) < 2 or not parts[1].isdigit():
                self._log_msg('Usage: damage <n>', _C_ERR)
                return
            player.sword.damage = max(1, int(parts[1]))
            self._log_msg(f'Sword damage  →  {player.sword.damage}', _C_OK)

        elif cmd == 'speed':
            if len(parts) < 2 or not parts[1].isdigit():
                self._log_msg('Usage: speed <n>', _C_ERR)
                return
            player.speed = max(1, int(parts[1]))
            self._log_msg(f'Speed  →  {player.speed}', _C_OK)

        elif cmd == 'defense':
            if len(parts) < 2 or not parts[1].lstrip('-').isdigit():
                self._log_msg('Usage: defense <n>', _C_ERR)
                return
            player.defense = max(0, int(parts[1]))
            self._log_msg(f'Defense  →  {player.defense}', _C_OK)

        elif cmd == 'scale':
            try:
                val = float(parts[1]) if len(parts) >= 2 else None
                assert val is not None
            except (ValueError, AssertionError):
                self._log_msg('Usage: scale <f>  (e.g. scale 1.5)', _C_ERR)
                return
            s = player.sword
            s.scale = max(1.0, val)
            s.reach = int(s._base_reach * s.scale)
            s.image = pygame.transform.scale(s.img_base,
                          (int(s.img_base.get_width()  * s.scale),
                           int(s.img_base.get_height() * s.scale)))
            self._log_msg(f'Sword scale  →  {s.scale:.2f}  (reach {s.reach})', _C_OK)

        else:
            self._log_msg(f'Unknown command "{cmd}"', _C_ERR)
