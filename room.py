import pygame
import random
from enemy import RangedEnemy, MeleeEnemy
from coin import Coin
from gate import Gate

import damage_number

EVENT_WEIGHTS = {
    'monster': 60,
    'item':    20,
    'shop':    15,
    'special': 5,
}

FLOOR_COLOR = (45, 45, 50)
WALL_COLOR  = (80, 80, 120)
LOCK_COLOR  = (140, 40, 40)


class Room:
    def __init__(self, grid_x, grid_y, event_type=None, is_boss=False, is_start=False):
        self.grid_x = grid_x
        self.grid_y = grid_y

        self.is_boss    = is_boss
        self.is_start   = is_start
        self.is_locked  = False
        self.is_cleared = False

        if is_boss:
            self.event_type = 'boss'
        elif is_start:
            self.event_type = 'start'
        else:
            self.event_type = event_type or self._pick_event_type()

        self.enemies     = []
        self.items       = []
        self.floor_coins = []
        self.gate        = None
        self.shop        = None
        self.visited     = is_start
        self.connections = set()

        # Geometry — populated by setup_geometry()
        self.wx = self.wy = 0
        self.room_w = self.room_h = 0
        self.wall_t = self.door_size = 0
        self.walls      = []
        self.lock_walls = []

    # ------------------------------------------------------------------
    # Geometry setup (call once after map generation)
    # ------------------------------------------------------------------

    def setup_geometry(self, wx, wy, room_w, room_h, wall_t, door_size):
        self.wx, self.wy           = wx, wy
        self.room_w, self.room_h   = room_w, room_h
        self.wall_t, self.door_size = wall_t, door_size
        self.walls      = self._build_walls()
        self.lock_walls = self._build_lock_walls()

    def _build_walls(self):
        wx, wy = self.wx, self.wy
        mx = wx + self.room_w // 2
        my = wy + self.room_h // 2
        d  = self.door_size // 2
        t  = self.wall_t
        rw, rh = self.room_w, self.room_h

        has_N = (self.grid_x, self.grid_y - 1) in self.connections
        has_S = (self.grid_x, self.grid_y + 1) in self.connections
        has_W = (self.grid_x - 1, self.grid_y) in self.connections
        has_E = (self.grid_x + 1, self.grid_y) in self.connections

        walls = []
        if has_N:
            walls += [pygame.Rect(wx, wy, mx - wx - d, t),
                      pygame.Rect(mx + d, wy, wx + rw - mx - d, t)]
        else:
            walls.append(pygame.Rect(wx, wy, rw, t))

        by = wy + rh - t
        if has_S:
            walls += [pygame.Rect(wx, by, mx - wx - d, t),
                      pygame.Rect(mx + d, by, wx + rw - mx - d, t)]
        else:
            walls.append(pygame.Rect(wx, by, rw, t))

        if has_W:
            walls += [pygame.Rect(wx, wy, t, my - wy - d),
                      pygame.Rect(wx, my + d, t, wy + rh - my - d)]
        else:
            walls.append(pygame.Rect(wx, wy, t, rh))

        rx = wx + rw - t
        if has_E:
            walls += [pygame.Rect(rx, wy, t, my - wy - d),
                      pygame.Rect(rx, my + d, t, wy + rh - my - d)]
        else:
            walls.append(pygame.Rect(rx, wy, t, rh))

        return walls

    def _build_lock_walls(self):
        wx, wy = self.wx, self.wy
        mx = wx + self.room_w // 2
        my = wy + self.room_h // 2
        d  = self.door_size // 2
        t  = self.wall_t
        walls = []
        for nx, ny in self.connections:
            if   nx == self.grid_x and ny == self.grid_y - 1:
                walls.append(pygame.Rect(mx - d, wy, self.door_size, t))
            elif nx == self.grid_x and ny == self.grid_y + 1:
                walls.append(pygame.Rect(mx - d, wy + self.room_h - t, self.door_size, t))
            elif nx == self.grid_x - 1 and ny == self.grid_y:
                walls.append(pygame.Rect(wx, my - d, t, self.door_size))
            elif nx == self.grid_x + 1 and ny == self.grid_y:
                walls.append(pygame.Rect(wx + self.room_w - t, my - d, t, self.door_size))
        return walls

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def _pick_event_type(self):
        return random.choices(list(EVENT_WEIGHTS), weights=EVENT_WEIGHTS.values(), k=1)[0]

    def connect(self, other):
        self.connections.add((other.grid_x, other.grid_y))
        other.connections.add((self.grid_x, self.grid_y))

    def spawn_event(self, wx, wy, room_w, room_h, floor_number=1):
        self.enemies.clear()
        self.items.clear()
        if self.event_type == 'monster':
            self._spawn_enemies(wx, wy, room_w, room_h, floor_number)
        elif self.event_type == 'boss':
            self._spawn_boss(wx, wy, room_w, room_h, floor_number)

    def _spawn_enemies(self, wx, wy, room_w, room_h, floor_number):
        margin = 100
        for _ in range(random.randint(2, 3 + floor_number)):
            ex = random.randint(wx + margin, wx + room_w - margin - 32)
            ey = random.randint(wy + margin, wy + room_h - margin - 32)
            cls = random.choices([RangedEnemy, MeleeEnemy], weights=[60, 40])[0]
            self.enemies.append(cls(ex, ey, floor_number))

    def _spawn_boss(self, wx, wy, room_w, room_h, floor_number):
        self.enemies.append(RangedEnemy(wx + room_w // 2 - 16,
                                        wy + room_h // 2 - 16,
                                        floor_number))

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def try_lock(self, player_rect):
        """Lock the room once the player's full body is past the doorway threshold."""
        if self.is_cleared or self.is_locked or self.event_type not in ('monster', 'boss'):
            return
        margin = self.wall_t + 8
        if (player_rect.left   >= self.wx + margin and
                player_rect.right  <= self.wx + self.room_w - margin and
                player_rect.top    >= self.wy + margin and
                player_rect.bottom <= self.wy + self.room_h - margin):
            self.is_locked = True

    def place_gate(self):
        cx = self.wx + self.room_w // 2
        cy = self.wy + self.room_h // 2
        self.gate = Gate(cx, cy)

    def clear(self):
        self.is_cleared = True
        self.is_locked  = False
        if self.is_boss:
            self.place_gate()

    # ------------------------------------------------------------------
    # Update  (call only for the room the player is currently in)
    # ------------------------------------------------------------------

    def update(self, player, dt, walls):
        # Coin pickup runs regardless of lock state
        remaining = []
        for coin in self.floor_coins:
            if coin.rect.colliderect(player.rect):
                player.coins += 1
            else:
                remaining.append(coin)
        self.floor_coins = remaining

        if not self.is_locked:
            return

        # Melee dash → parry check first so stun prevents damage in update()
        for enemy in self.enemies:
            player.try_parry_dash(enemy)

        for enemy in self.enemies:
            enemy.update(player, dt, walls)
        for enemy in self.enemies:
            if not enemy.alive:
                self.floor_coins += Coin.drop_at(enemy.x + 16, enemy.y + 16)
        self.enemies = [e for e in self.enemies if e.alive]

        # Sword hit → enemies
        hitbox = player.sword.get_hitbox(player.x + 16, player.y + 16)
        if hitbox:
            for enemy in self.enemies:
                if (id(enemy) not in player.sword.hit_this_swing
                        and hitbox.colliderect(enemy.rect)):
                    dealt = enemy.take_damage(player.sword.damage)
                    player.sword.hit_this_swing.add(id(enemy))
                    damage_number.spawn(enemy.x + 16, enemy.y - 8, dealt)
                    if player.sword.flame:
                        enemy.burn_timer = 3.0
                    if player.sword.slow:
                        enemy.slow_timer = 2.0
                    if (player.sword.execute_pct > 0 and enemy.alive
                            and enemy.hp / enemy.max_hp < player.sword.execute_pct):
                        enemy.take_damage(enemy.hp)

        # Enemy bullets → parry check → player damage
        for enemy in self.enemies:
            for bullet in enemy.bullets:
                if not bullet.alive:
                    continue
                if player.try_parry_bullet(bullet):
                    continue
                if bullet.rect.colliderect(player.rect):
                    player.hp -= bullet.damage
                    bullet.alive = False
                    damage_number.spawn(player.x + 16, player.y - 8,
                                        bullet.damage, damage_number.PLAYER_HIT_COLOR)

        # Player's deflected bullets → update + enemy damage
        for bullet in player.deflected_bullets:
            bullet.update(dt, walls)
        for bullet in player.deflected_bullets:
            if not bullet.alive:
                continue
            for enemy in self.enemies:
                if bullet.rect.colliderect(enemy.rect):
                    if isinstance(enemy, RangedEnemy):
                        dealt = enemy.take_damage(enemy.hp)
                    else:
                        dealt = enemy.take_damage(enemy.max_hp // 2)
                    damage_number.spawn(enemy.x + 16, enemy.y - 8, dealt)
                    bullet.alive = False
                    break
        player.deflected_bullets = [b for b in player.deflected_bullets if b.alive]

        if not self.enemies:
            self.clear()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, cam_x, cam_y, font):
        sx = self.wx - cam_x
        sy = self.wy - cam_y
        sw, sh = screen.get_size()
        if sx + self.room_w < 0 or sx > sw or sy + self.room_h < 0 or sy > sh:
            return

        pygame.draw.rect(screen, FLOOR_COLOR, (sx, sy, self.room_w, self.room_h))
        label = font.render(f"{self.event_type} ({self.grid_x},{self.grid_y})",
                            True, (110, 110, 110))
        screen.blit(label, (sx + self.wall_t + 4, sy + self.wall_t + 4))

        for w in self.walls:
            pygame.draw.rect(screen, WALL_COLOR,
                             (w.x - cam_x, w.y - cam_y, w.width, w.height))

        if self.is_locked:
            for w in self.lock_walls:
                pygame.draw.rect(screen, LOCK_COLOR,
                                 (w.x - cam_x, w.y - cam_y, w.width, w.height))

        for coin in self.floor_coins:
            coin.draw(screen, cam_x, cam_y)

        if self.gate:
            self.gate.draw(screen, cam_x, cam_y)

        for enemy in self.enemies:
            enemy.draw(screen, cam_x, cam_y)

    # ------------------------------------------------------------------

    def is_special(self): return self.event_type == 'special'
    def is_shop(self):    return self.event_type == 'shop'

    def __repr__(self):
        return (f"Room({self.grid_x},{self.grid_y} "
                f"type={self.event_type} locked={self.is_locked} cleared={self.is_cleared})")
