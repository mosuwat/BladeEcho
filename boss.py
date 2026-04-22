import pygame
import math
import random
from enemy import Enemy, Bullet
import ui


class GlobBullet(Bullet):
    RADIUS = 9

    def __init__(self, x, y, vx, vy, damage):
        super().__init__(x, y, vx, vy, damage)
        self.rect = pygame.Rect(int(x) - self.RADIUS, int(y) - self.RADIUS,
                                self.RADIUS * 2, self.RADIUS * 2)

    def draw(self, screen, cam_x, cam_y):
        cx = int(self.x - cam_x)
        cy = int(self.y - cam_y)
        color = (0, 200, 255) if self.is_deflected else (100, 220, 70)
        pygame.draw.circle(screen, color, (cx, cy), self.RADIUS)
        pygame.draw.circle(screen, (50, 130, 30), (cx, cy), self.RADIUS, 2)


class SlimeKing(Enemy):
    SIZE    = 64
    NAME    = 'SLIME KING'
    is_boss = True

    # ── Tuning ────────────────────────────────────────────────────────────────
    CHASE_SPEED      = 95
    DASH_SPEED       = 480
    DASH_RANGE       = 460
    WINDUP_DUR       = 0.55
    GLOB_SPEED_BASE  = 170
    GLOB_DAMAGE      = 18
    SPREAD_COUNT     = 7
    SHOOT_CD         = 1.6
    DASH_CD          = 2.0
    TOUCH_DAMAGE     = 20
    TOUCH_INTERVAL   = 0.8
    DASH_DAMAGE      = 30
    STUN_DURATION    = 1   # seconds stunned after a normal dash is parried
    DESPERATE_PCT    = 0.10

    DESP_INTRO_DUR   = 1.5   # red pause before first shoot phase
    DESP_SHOOT_DUR   = 7.0
    DESP_SHOOT_CD    = 0.15  # interval between rings
    DESP_RING_COUNT  = 8     # bullets per ring during rapid phase
    DESP_RISE_DUR    = 1.00  # time to rise into air (0.5s longer)
    DESP_HANG_DUR    = 0.30  # pause at peak before dropping
    DESP_FALL_DUR    = 0.28  # time to fall down
    DESP_IMPACT_DUR  = 0.40  # pause after each slam
    DESP_SLAM_COUNT  = 5     # slams before vulnerable window
    DESP_STUN_DUR    = 1.5   # vulnerable window duration
    AIR_HEIGHT       = 90    # pixels boss rises during jump

    # ── Colors ────────────────────────────────────────────────────────────────
    _COL_NORMAL   = ( 80, 200,  80)
    _COL_WINDUP   = (230, 220,  50)
    _COL_DASH     = (255, 255, 255)

    def __init__(self, x, y, floor_number=1):
        hp = 500 + floor_number * 100
        super().__init__(x, y, hp, speed=self.CHASE_SPEED)
        self.floor_number = floor_number

        self.state       = 'idle'
        self.state_timer = 0.0
        self.action_cd   = random.uniform(0.6, 1.2)
        self.dash_vx = self.dash_vy = 0.0
        self.touch_timer = 0.0

        self.desperate       = False
        self.invulnerable    = False
        self.flash_timer     = 0.0
        self.desp_state      = 'shoot'
        self.desp_timer      = 0.0
        self.desp_shoot_cd   = 0.0
        self.slam_count      = 0
        self.air_offset      = 0.0
        self.slam_tx         = 0.0
        self.slam_ty         = 0.0
        self.desp_ring_angle      = 0.0
        self.desp_burst_remaining = 0
        self.desp_burst_cd        = 0.0
        self.stun_timer      = 0.0
        self.parry_vulnerable = False
        self.parry_dmg_mult   = 1.5

    @property
    def phase_label(self):
        if self.desperate:
            return '[ DESPERATE ]'
        return ''

    # ── Damage ────────────────────────────────────────────────────────────────

    def parry_slam(self):
        """Called when player parries a slam impact. Skips burst and advances the cycle correctly."""
        self.desp_burst_remaining = 0
        if self.slam_count >= self.DESP_SLAM_COUNT:
            self.desp_state       = 'stun'
            self.desp_timer       = 0.0
            self.invulnerable     = False
            self.parry_vulnerable = True
        else:
            self.desp_state = 'rise'
            self.desp_timer = 0.0

    def stun(self, duration, dmg_mult=1.5):
        self.state            = 'idle'
        self.state_timer      = 0.0
        self.dash_vx = self.dash_vy = 0.0
        self.stun_timer       = duration
        self.parry_vulnerable = True
        self.parry_dmg_mult   = dmg_mult

    def take_damage(self, amount):
        if self.invulnerable:
            return 0
        if self.parry_vulnerable:
            amount = int(amount * self.parry_dmg_mult)
        dealt = super().take_damage(amount)
        if not self.desperate and self.hp <= 0:
            self.hp    = 1
            self.alive = True
        return dealt

    # ── Bullets ───────────────────────────────────────────────────────────────

    def _glob_speed(self):
        return self.GLOB_SPEED_BASE + self.floor_number * 12

    def _shoot_aimed(self, ex, ey, px, py):
        dist = math.hypot(px - ex, py - ey) or 1
        spd  = self._glob_speed() * 1.8
        self.bullets.append(
            GlobBullet(ex, ey, (px - ex) / dist * spd, (py - ey) / dist * spd,
                       self.GLOB_DAMAGE))

    def _shoot_spread(self, ex, ey, px, py):
        base  = math.atan2(py - ey, px - ex)
        spread = math.radians(65)
        spd    = self._glob_speed()
        for i in range(self.SPREAD_COUNT):
            t = i / (self.SPREAD_COUNT - 1)
            a = base - spread / 2 + spread * t
            self.bullets.append(
                GlobBullet(ex, ey, math.cos(a) * spd, math.sin(a) * spd,
                           self.GLOB_DAMAGE))

    def _shoot_ring(self, ex, ey, count=12, offset_angle=0.0):
        spd = self._glob_speed() * 1.2
        for i in range(count):
            a = offset_angle + 2 * math.pi * i / count
            self.bullets.append(
                GlobBullet(ex, ey, math.cos(a) * spd, math.sin(a) * spd,
                           self.GLOB_DAMAGE + 5))

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, player, dt, walls):
        if not self.alive:
            return
        self._apply_status(dt)
        if not self.alive:
            return

        ex = self.x + self.SIZE // 2
        ey = self.y + self.SIZE // 2
        px = player.x + 16
        py = player.y + 16
        dist = math.hypot(px - ex, py - ey)

        if self.stun_timer > 0:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.parry_vulnerable = False
            for b in self.bullets:
                b.update(dt, walls)
            self.bullets = [b for b in self.bullets if b.alive]
            self.flash_timer = max(0.0, self.flash_timer - dt)
            return

        if not self.desperate and self.hp / self.max_hp <= self.DESPERATE_PCT:
            self._enter_desperate()

        if self.desperate:
            self._update_desperate(ex, ey, px, py, dt)
        else:
            self._update_normal(ex, ey, px, py, dist, dt, walls, player)

        for b in self.bullets:
            b.update(dt, walls)
        self.bullets = [b for b in self.bullets if b.alive]

        self.flash_timer = max(0.0, self.flash_timer - dt)

    def _enter_desperate(self):
        self.desperate     = True
        self.invulnerable  = True
        self.state         = 'desperate'
        self.flash_timer   = 0.0
        self.dash_vx = self.dash_vy = 0.0
        self.desp_state    = 'intro'
        self.desp_timer    = 0.0

    def _update_normal(self, ex, ey, px, py, dist, dt, walls, player):
        # Always drift slowly toward player
        if dist > 0:
            spd = self.speed * (0.5 if self.slow_timer > 0 else 1.0)
            self.x += (px - ex) / dist * spd * dt
            self.y += (py - ey) / dist * spd * dt
            self._sync_rect()
            self._push_out_of_walls(walls)

        if self.state == 'idle':
            self.action_cd -= dt
            if self.action_cd <= 0:
                if dist < self.DASH_RANGE and random.random() < 0.45:
                    self.state       = 'windup_dash'
                    self.state_timer = self.WINDUP_DUR
                else:
                    self.state       = 'windup_shoot'
                    self.state_timer = 0.3

        elif self.state == 'windup_dash':
            self.state_timer -= dt
            if self.state_timer <= 0:
                if dist > 0:
                    self.dash_vx = (px - ex) / dist * self.DASH_SPEED
                    self.dash_vy = (py - ey) / dist * self.DASH_SPEED
                self.state       = 'dash'
                self.state_timer = (dist + 180) / self.DASH_SPEED

        elif self.state == 'dash':
            self.state_timer -= dt
            self.x += self.dash_vx * dt
            self.y += self.dash_vy * dt
            self._sync_rect()
            self._push_out_of_walls(walls)

            parry_box = player.get_parry_sword_hitbox()
            blocked   = parry_box is not None and parry_box.colliderect(self.rect)
            if self.rect.colliderect(player.rect) and not blocked:
                dealt = max(1, self.DASH_DAMAGE - getattr(player, 'defense', 0))
                player.hp -= dealt
                ui.spawn(player.x + 16, player.y - 8,
                         dealt, ui.PLAYER_HIT_COLOR)

            if self.state_timer <= 0:
                ex2 = self.x + self.SIZE // 2
                ey2 = self.y + self.SIZE // 2
                self._shoot_spread(ex2, ey2, player.x + 16, player.y + 16)
                if random.random() < 0.5:
                    self._shoot_aimed(ex2, ey2, player.x + 16, player.y + 16)
                self.state     = 'idle'
                self.action_cd = self.DASH_CD

        elif self.state == 'windup_shoot':
            self.state_timer -= dt
            if self.state_timer <= 0:
                r = random.random()
                if r < 0.35:
                    self._shoot_spread(ex, ey, px, py)
                elif r < 0.65:
                    self._shoot_aimed(ex, ey, px, py)
                else:
                    self._shoot_spread(ex, ey, px, py)
                    self._shoot_aimed(ex, ey, px, py)
                self.state     = 'idle'
                self.action_cd = self.SHOOT_CD

        if self.touch_timer > 0:
            self.touch_timer -= dt
        if self.state != 'dash' and self.rect.colliderect(player.rect) and self.touch_timer <= 0:
            dealt = max(1, self.TOUCH_DAMAGE - getattr(player, 'defense', 0))
            player.hp -= dealt
            self.touch_timer = self.TOUCH_INTERVAL
            ui.spawn(player.x + 16, player.y - 8,
                     dealt, ui.PLAYER_HIT_COLOR)

    def _restart_desperate(self):
        self.desp_state           = 'shoot'
        self.desp_timer           = 0.0
        self.desp_shoot_cd        = 0.0
        self.slam_count           = 0
        self.air_offset           = 0.0
        self.desp_burst_remaining = 0
        self.desp_burst_cd        = 0.0
        self.invulnerable         = True
        self.parry_vulnerable     = False

    def _update_desperate(self, ex, ey, px, py, dt):
        self.desp_timer += dt

        if self.desp_state == 'intro':
            if self.desp_timer >= self.DESP_INTRO_DUR:
                self._restart_desperate()
            return

        if self.desp_state == 'shoot':
            self.desp_shoot_cd -= dt
            if self.desp_shoot_cd <= 0:
                self._shoot_ring(ex, ey, count=self.DESP_RING_COUNT,
                                 offset_angle=self.desp_ring_angle)
                self.desp_ring_angle += math.pi / 10
                self.desp_shoot_cd = self.DESP_SHOOT_CD
            if self.desp_timer >= self.DESP_SHOOT_DUR:
                self.desp_state = 'rise'
                self.desp_timer = 0.0
                self.air_offset = 0.0

        elif self.desp_state == 'rise':
            self.air_offset = -self.AIR_HEIGHT * min(self.desp_timer / self.DESP_RISE_DUR, 1.0)
            if self.desp_timer >= self.DESP_RISE_DUR:
                self.air_offset  = -self.AIR_HEIGHT
                self.slam_tx     = px - self.SIZE // 2
                self.slam_ty     = py - self.SIZE // 2
                self.desp_state  = 'hang'
                self.desp_timer  = 0.0

        elif self.desp_state == 'hang':
            if self.desp_timer >= self.DESP_HANG_DUR:
                self.x = self.slam_tx
                self.y = self.slam_ty
                self._sync_rect()
                self.desp_state = 'fall'
                self.desp_timer = 0.0

        elif self.desp_state == 'fall':
            self.air_offset = -self.AIR_HEIGHT * max(0.0, 1.0 - self.desp_timer / self.DESP_FALL_DUR)
            if self.desp_timer >= self.DESP_FALL_DUR:
                self.air_offset  = 0.0
                self.slam_count += 1
                self.desp_state  = 'impact'
                self.desp_timer  = 0.0

        elif self.desp_state == 'impact':
            if self.desp_timer >= self.DESP_IMPACT_DUR:
                if self.slam_count >= self.DESP_SLAM_COUNT:
                    self.desp_state       = 'stun'
                    self.desp_timer       = 0.0
                    self.invulnerable     = False
                    self.parry_vulnerable = True
                else:
                    self.desp_burst_remaining = self.slam_count
                    self.desp_burst_cd        = 0.0
                    self.desp_state           = 'burst'
                    self.desp_timer           = 0.0

        elif self.desp_state == 'burst':
            self.desp_burst_cd -= dt
            if self.desp_burst_cd <= 0:
                if self.desp_burst_remaining > 0:
                    ex2 = self.x + self.SIZE // 2
                    ey2 = self.y + self.SIZE // 2
                    self._shoot_ring(ex2, ey2, count=10, offset_angle=self.desp_ring_angle)
                    self.desp_ring_angle      += math.pi / 10
                    self.desp_burst_remaining -= 1
                    self.desp_burst_cd         = 0.15
                else:
                    self.desp_state = 'rise'
                    self.desp_timer = 0.0

        elif self.desp_state == 'stun':
            if self.desp_timer >= self.DESP_STUN_DUR:
                self._restart_desperate()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx  = int(self.x - cam_x)
        sy  = int(self.y - cam_y)
        asy = sy + int(self.air_offset)   # visual y with jump offset

        # Shadow when airborne
        if self.air_offset < 0:
            shadow_alpha = max(40, 160 + int(self.air_offset * 1.2))
            shadow = pygame.Surface((self.SIZE, 20), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, shadow_alpha))
            screen.blit(shadow, (sx, sy + self.SIZE - 10))

        desp_stun = self.desperate and self.desp_state == 'stun'
        if self.stun_timer > 0 or desp_stun:
            color = (180, 100, 255)
        elif self.desperate and self.desp_state == 'intro':
            color = (255, 30, 30)
        elif self.desperate:
            t     = (pygame.time.get_ticks() % 500) / 500
            pulse = int(t * 255)
            color = (255, pulse // 3, pulse // 3)
        elif self.flash_timer > 0:
            color = (255, 255, 255)
        elif self.state == 'windup_dash':
            color = self._COL_WINDUP
        elif self.state == 'dash':
            color = self._COL_DASH
        else:
            color = self._COL_NORMAL

        pygame.draw.rect(screen, color, (sx, asy, self.SIZE, self.SIZE), border_radius=12)

        # Eyes
        ey_y = asy + self.SIZE // 3
        for ex_off in (self.SIZE // 3, 2 * self.SIZE // 3):
            pygame.draw.circle(screen, (15, 15, 15), (sx + ex_off, ey_y), 7)
            pygame.draw.circle(screen, (255, 255, 255), (sx + ex_off + 2, ey_y - 2), 3)

        # Glow ring — red in desperate, purple in stun window
        if desp_stun:
            pygame.draw.rect(screen, (180, 80, 255),
                             (sx - 3, asy - 3, self.SIZE + 6, self.SIZE + 6),
                             3, border_radius=14)
        elif self.desperate:
            pygame.draw.rect(screen, (255, 80, 80),
                             (sx - 3, asy - 3, self.SIZE + 6, self.SIZE + 6),
                             3, border_radius=14)

        for b in self.bullets:
            b.draw(screen, cam_x, cam_y)
