import pygame
import math
import random
import damage_number


class Bullet:
    RADIUS = 5

    def __init__(self, x, y, vx, vy, damage):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.is_deflected = False
        self.alive = True
        self.rect = pygame.Rect(int(x) - self.RADIUS, int(y) - self.RADIUS,
                                self.RADIUS * 2, self.RADIUS * 2)

    def update(self, dt, walls):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.center = (int(self.x), int(self.y))
        for wall in walls:
            if self.rect.colliderect(wall):
                self.alive = False
                return

    def draw(self, screen, cam_x, cam_y):
        color = (0, 200, 255) if self.is_deflected else (255, 210, 60)
        pygame.draw.circle(screen, color,
                           (int(self.x - cam_x), int(self.y - cam_y)), self.RADIUS)


class Enemy:
    SIZE = 32

    def __init__(self, x, y, hp, speed):
        self.x = float(x)
        self.y = float(y)
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.alive = True
        self.rect = pygame.Rect(int(x), int(y), self.SIZE, self.SIZE)
        self.bullets    = []
        self.burn_timer = 0.0   # seconds remaining of burn DoT
        self.slow_timer = 0.0   # seconds remaining of slow debuff

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return amount

    def _apply_status(self, dt):
        """Call at the top of each subclass update(). Handles burn and slow timers."""
        if self.burn_timer > 0:
            self.burn_timer -= dt
            self.hp -= 3 * dt
            if self.hp <= 0:
                self.hp = 0
                self.alive = False
        if self.slow_timer > 0:
            self.slow_timer -= dt

    def update(self, player, dt, walls):
        pass

    def draw(self, screen, cam_x, cam_y):
        pass

    def _sync_rect(self):
        self.rect.topleft = (int(self.x), int(self.y))

    def _push_out_of_walls(self, walls):
        for wall in walls:
            if not self.rect.colliderect(wall):
                continue
            ol  = self.rect.right  - wall.left
            or_ = wall.right - self.rect.left
            ot  = self.rect.bottom - wall.top
            ob  = wall.bottom - self.rect.top
            if min(ol, or_) < min(ot, ob):
                self.x -= ol if ol < or_ else -or_
            else:
                self.y -= ot if ot < ob else -ob
            self._sync_rect()

    def _draw_hp_bar(self, screen, cam_x, cam_y):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        bar_w = self.SIZE
        filled = int(bar_w * self.hp / self.max_hp)
        pygame.draw.rect(screen, (80, 0, 0),   (sx, sy - 8, bar_w, 5))
        pygame.draw.rect(screen, (220, 50, 50), (sx, sy - 8, filled, 5))


class RangedEnemy(Enemy):
    COLOR          = (180, 60, 60)
    PREFERRED_DIST = 380
    SHOOT_COOLDOWN = 2.0
    BULLET_SPEED   = 300
    BULLET_DAMAGE  = 10
    MAX_SHOOT_DIST = 650

    def __init__(self, x, y, floor_number=1):
        hp = 40 + floor_number * 15
        super().__init__(x, y, hp, speed=100)
        self.floor_number  = floor_number
        self.bullets       = []
        self.shoot_timer   = random.uniform(0.5, self.SHOOT_COOLDOWN)
        self.strafe_dir    = random.choice([-1, 1])
        self.strafe_timer  = random.uniform(1.0, 2.5)

    # ------------------------------------------------------------------ AI

    def update(self, player, dt, walls):
        if not self.alive:
            return
        self._apply_status(dt)
        if not self.alive:
            return

        px = player.x + 16
        py = player.y + 16
        ex = self.x + 16
        ey = self.y + 16
        dx, dy = px - ex, py - ey
        dist = math.hypot(dx, dy)

        self._move(dx, dy, dist, dt, walls)
        self._try_shoot(ex, ey, px, py, dist, dt)

        for b in self.bullets:
            b.update(dt, walls)
        self.bullets = [b for b in self.bullets if b.alive]

    def _move(self, dx, dy, dist, dt, walls):
        if dist == 0:
            return
        spd = self.speed * (0.5 if self.slow_timer > 0 else 1.0)
        nx, ny = dx / dist, dy / dist       # toward player
        perp_x, perp_y = -ny, nx            # perpendicular (strafe axis)

        self.strafe_timer -= dt
        if self.strafe_timer <= 0:
            self.strafe_dir   = random.choice([-1, 1])
            self.strafe_timer = random.uniform(1.0, 2.5)

        gap = dist - self.PREFERRED_DIST
        if gap > 60:
            move_x = nx * spd * dt
            move_y = ny * spd * dt
        elif gap < -60:
            move_x = -nx * spd * dt
            move_y = -ny * spd * dt
        else:
            move_x = perp_x * spd * self.strafe_dir * dt
            move_y = perp_y * spd * self.strafe_dir * dt

        self.x += move_x
        self.y += move_y
        self._sync_rect()
        self._push_out_of_walls(walls)

    def _try_shoot(self, ex, ey, px, py, dist, dt):
        self.shoot_timer -= dt
        if self.shoot_timer > 0 or dist > self.MAX_SHOOT_DIST:
            return
        self.shoot_timer = self.SHOOT_COOLDOWN
        speed = self.BULLET_SPEED + self.floor_number * 20
        if dist == 0:
            return
        vx = (px - ex) / dist * speed
        vy = (py - ey) / dist * speed
        self.bullets.append(Bullet(ex, ey, vx, vy, self.BULLET_DAMAGE))

    # ---------------------------------------------------------------- Draw

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        pygame.draw.rect(screen, self.COLOR, (sx, sy, self.SIZE, self.SIZE))
        self._draw_hp_bar(screen, cam_x, cam_y)
        for b in self.bullets:
            b.draw(screen, cam_x, cam_y)


class MeleeEnemy(Enemy):
    COLOR          = (160, 80, 200)   # purple
    CHASE_SPEED    = 110
    DASH_SPEED     = 650
    DASH_RANGE     = 260    # start wind-up within this distance
    WINDUP_DUR     = 0.45   # pause before dash
    DASH_DUR       = 0.22   # duration of dash burst
    DASH_COOLDOWN  = 2.2
    DASH_DAMAGE    = 18
    TOUCH_DAMAGE   = 6
    TOUCH_INTERVAL = 0.8    # seconds between passive contact hits

    def __init__(self, x, y, floor_number=1):
        hp = 60 + floor_number * 20
        super().__init__(x, y, hp, speed=self.CHASE_SPEED + floor_number * 5)
        self.floor_number  = floor_number
        self.state         = 'chase'   # chase | windup | dash | cooldown
        self.state_timer   = 0.0
        self.dash_cd       = random.uniform(0.5, 1.5)
        self.dash_vx       = 0.0
        self.dash_vy       = 0.0
        self.touch_timer   = 0.0
        self.stun_timer       = 0.0
        self.parry_vulnerable = False
        self.parry_dmg_mult   = 1.5

    def stun(self, duration, dmg_mult=1.5):
        self.state            = 'chase'
        self.state_timer      = 0.0
        self.dash_vx          = 0.0
        self.dash_vy          = 0.0
        self.stun_timer       = duration
        self.parry_vulnerable = True
        self.parry_dmg_mult   = dmg_mult

    def take_damage(self, amount):
        if self.parry_vulnerable:
            amount = int(amount * self.parry_dmg_mult)
        return super().take_damage(amount)

    # ------------------------------------------------------------------ AI

    def update(self, player, dt, walls):
        if not self.alive:
            return
        self._apply_status(dt)
        if not self.alive:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.parry_vulnerable = False
            return

        px = player.x + 16
        py = player.y + 16
        ex = self.x + 16
        ey = self.y + 16
        dist = math.hypot(px - ex, py - ey)

        if self.touch_timer > 0:
            self.touch_timer -= dt

        if self.state == 'chase':
            self._move_toward(px, py, ex, ey, dist, dt, walls)
            self.dash_cd -= dt
            if dist < self.DASH_RANGE and self.dash_cd <= 0:
                self.state       = 'windup'
                self.state_timer = self.WINDUP_DUR
            self._passive_contact(player)

        elif self.state == 'windup':
            # Pause and lock onto player before dashing
            self.state_timer -= dt
            if self.state_timer <= 0:
                if dist > 0:
                    self.dash_vx = (px - ex) / dist * self.DASH_SPEED
                    self.dash_vy = (py - ey) / dist * self.DASH_SPEED
                self.state       = 'dash'
                self.state_timer = (dist + 100) / self.DASH_SPEED  # always overshoot by 100px

        elif self.state == 'dash':
            self.state_timer -= dt
            self.x += self.dash_vx * dt
            self.y += self.dash_vy * dt
            self._sync_rect()
            self._push_out_of_walls(walls)
            parry_box   = player.get_parry_sword_hitbox()
            blocked     = parry_box is not None and parry_box.colliderect(self.rect)
            if self.rect.colliderect(player.rect) and self.touch_timer <= 0 and not blocked:
                player.hp       -= self.DASH_DAMAGE
                self.touch_timer = self.TOUCH_INTERVAL
                damage_number.spawn(player.x + 16, player.y - 8,
                                    self.DASH_DAMAGE, damage_number.PLAYER_HIT_COLOR)
            if self.state_timer <= 0:
                self.state  = 'cooldown'
                self.dash_cd = self.DASH_COOLDOWN

        elif self.state == 'cooldown':
            self._move_toward(px, py, ex, ey, dist, dt, walls)
            self.dash_cd -= dt
            if self.dash_cd <= 0:
                self.state = 'chase'
            self._passive_contact(player)

    def _move_toward(self, px, py, ex, ey, dist, dt, walls):
        if dist == 0:
            return
        spd = self.speed * (0.5 if self.slow_timer > 0 else 1.0)
        self.x += (px - ex) / dist * spd * dt
        self.y += (py - ey) / dist * spd * dt
        self._sync_rect()
        self._push_out_of_walls(walls)

    def _passive_contact(self, player):
        if self.rect.colliderect(player.rect) and self.touch_timer <= 0:
            player.hp       -= self.TOUCH_DAMAGE
            self.touch_timer = self.TOUCH_INTERVAL
            damage_number.spawn(player.x + 16, player.y - 8,
                                self.TOUCH_DAMAGE, damage_number.PLAYER_HIT_COLOR)

    # ---------------------------------------------------------------- Draw

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        if self.state == 'windup':
            color = (255, 200, 80)   # yellow telegraph
        elif self.state == 'dash':
            color = (255, 255, 255)  # white flash during dash
        else:
            color = self.COLOR
        pygame.draw.rect(screen, color, (sx, sy, self.SIZE, self.SIZE))
        self._draw_hp_bar(screen, cam_x, cam_y)
