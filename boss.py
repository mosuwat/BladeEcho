import pygame
import math
import random
import os
import tilemap as tilemap_mod
from constants import ROOM_W, ROOM_H, WALL_T
from enemy import Enemy, Bullet, _get_bow_frames, _get_arrow_surf, _get_frost_frames, _FROST_FPS, _FROST_PARTICLE_SIZE, _FLAME_FPS
import ui
import stats
import sound

# ── SlimeBoss sprites ─────────────────────────────────────────────────────────
_BOSS_IMG_DIR     = os.path.join(os.path.dirname(__file__), 'images', 'Enemy', 'SlimeBoss')

# ── RangedBoss sprites ────────────────────────────────────────────────────────
_RBOSS_IMG_DIR     = os.path.join(os.path.dirname(__file__), 'images', 'Enemy', 'RangedBoss')
_RBOSS_WALK_FRAMES = None
_RBOSS_IDLE_FRAMES = None
_RBOSS_ANIM_FPS    = 8


def _get_rboss_frames():
    global _RBOSS_WALK_FRAMES, _RBOSS_IDLE_FRAMES
    if _RBOSS_WALK_FRAMES is None:
        def load(name):
            tmx    = tilemap_mod.load(os.path.join(_RBOSS_IMG_DIR, name))
            frames = tmx.get_frames(frame_tile_w=1)
            return [pygame.transform.scale(f, (_RBOSS_SIZE, _RBOSS_SIZE)) for f in frames]
        _RBOSS_WALK_FRAMES = load('walk.tmx')
        _RBOSS_IDLE_FRAMES = load('idle.tmx')
    return _RBOSS_WALK_FRAMES, _RBOSS_IDLE_FRAMES

_RBOSS_SIZE = 40   # 1.25 × player hitbox (32)

_TILE_FLAME_FRAMES = None
_TILE_FLAME_CELL   = 16

def _get_tile_flame_frames(size):
    global _TILE_FLAME_FRAMES
    if _TILE_FLAME_FRAMES is None:
        path  = os.path.join(os.path.dirname(__file__), 'images', 'Debuff', 'flamme.png')
        sheet = pygame.image.load(path).convert_alpha()
        cols  = sheet.get_width() // _TILE_FLAME_CELL
        raw   = [sheet.subsurface(_TILE_FLAME_CELL * i, 0, _TILE_FLAME_CELL, _TILE_FLAME_CELL)
                 for i in range(cols)]
        _TILE_FLAME_FRAMES = [pygame.transform.scale(f, (size, size)) for f in raw]
    return _TILE_FLAME_FRAMES


class IceBullet(Bullet):
    """Arrow that stuns BoneArcher when parried back at it. Trails frost particles."""
    _SPAWN_RATE = 14
    _LIFE       = 0.45
    _PART_SPEED = 45

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._frost_particles = []   # [x, y, vx, vy, life, anim_t]
        self._spawn_acc = 0.0

    def update(self, dt, walls):
        super().update(dt, walls)
        self._spawn_acc += dt
        interval = 1.0 / self._SPAWN_RATE
        while self._spawn_acc >= interval:
            self._spawn_acc -= interval
            a   = random.uniform(0, math.pi * 2)
            spd = random.uniform(self._PART_SPEED * 0.4, self._PART_SPEED)
            self._frost_particles.append([self.x, self.y,
                                          math.cos(a) * spd, math.sin(a) * spd,
                                          self._LIFE, 0.0])
        surviving = []
        for p in self._frost_particles:
            p[4] -= dt
            p[5] += dt
            if p[4] > 0:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                surviving.append(p)
        self._frost_particles = surviving

    def draw(self, screen, cam_x, cam_y):
        frames = _get_frost_frames()
        if frames:
            half = _FROST_PARTICLE_SIZE // 2
            for px, py, _, _, life, anim_t in self._frost_particles:
                idx = int(anim_t * _FROST_FPS) % len(frames)
                f   = frames[idx].copy()
                f.set_alpha(int(255 * (life / self._LIFE)))
                screen.blit(f, (int(px - cam_x) - half, int(py - cam_y) - half))
        super().draw(screen, cam_x, cam_y)


class FallingArrow:
    """Animated arrow that falls from above and sticks in a floor tile."""
    FALL_SPEED = 820

    def __init__(self, tile_cx, tile_cy, tile_size):
        self.tile_cx   = float(tile_cx)
        self.tile_cy   = float(tile_cy)
        self.tile_size = tile_size
        self.fall_y    = float(tile_cy - 780)
        self.stuck     = False
        pad = tile_size // 6
        self.rect = pygame.Rect(int(tile_cx) - tile_size // 2 + pad,
                                int(tile_cy) - tile_size // 2 + pad,
                                tile_size - 2 * pad, tile_size - 2 * pad)

    def update(self, dt):
        if self.stuck:
            return
        self.fall_y += self.FALL_SPEED * dt
        if self.fall_y >= self.tile_cy:
            self.fall_y = self.tile_cy
            self.stuck  = True

    def draw(self, screen, cam_x, cam_y):
        sx = int(self.tile_cx - cam_x)
        sy = int(self.fall_y  - cam_y)
        tile_sx = sx - self.tile_size // 2
        tile_sy = int(self.tile_cy - cam_y) - self.tile_size // 2
        frames = _get_tile_flame_frames(self.tile_size)
        if frames:
            idx = (pygame.time.get_ticks() // (1000 // _FLAME_FPS)) % len(frames)
            f   = frames[idx].copy()
            f.set_alpha(200 if self.stuck else 90)
            screen.blit(f, (tile_sx, tile_sy))
        # Arrow shaft falling perpendicular to floor
        col = (210, 170, 70)
        pygame.draw.line(screen, col, (sx, sy - 38), (sx, sy), 3)
        pygame.draw.polygon(screen, col, [(sx, sy), (sx - 6, sy - 14), (sx + 6, sy - 14)])


class SkyArrow(Bullet):
    """Arrow that travels from outside the room ignoring walls — used in desperate cluster."""
    MAX_TRAVEL = 1500

    def __init__(self, x, y, vx, vy, damage, image=None):
        super().__init__(x, y, vx, vy, damage, image=image)
        self._traveled = 0.0

    def update(self, dt, walls):
        spd = math.hypot(self.vx, self.vy)
        self._traveled += spd * dt
        if self._traveled > self.MAX_TRAVEL:
            self.alive = False
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, screen, cam_x, cam_y):
        super().draw(screen, cam_x, cam_y)
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        pygame.draw.circle(screen, (180, 80, 255), (sx, sy), 7)


class FlameArrow(SkyArrow):
    """SkyArrow variant; deflected back at boss counts as a flame hit (3 = kill).
    When deflected, homes toward its source boss."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._homing_target = None

    def update(self, dt, walls):
        if self.is_deflected and self._homing_target is not None and self._homing_target.alive:
            tx = self._homing_target.x + getattr(self._homing_target, 'SIZE', 32) // 2
            ty = self._homing_target.y + getattr(self._homing_target, 'SIZE', 32) // 2
            dx, dy = tx - self.x, ty - self.y
            spd  = math.hypot(self.vx, self.vy)
            dist = math.hypot(dx, dy) or 1
            self.vx = dx / dist * spd
            self.vy = dy / dist * spd
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.rect.center = (int(self.x), int(self.y))
        else:
            super().update(dt, walls)

    def draw(self, screen, cam_x, cam_y):
        super().draw(screen, cam_x, cam_y)
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        pygame.draw.circle(screen, (255, 120,   0), (sx, sy), 11, 2)
        pygame.draw.circle(screen, (255, 220,  50), (sx, sy),  5)


_BJUMP_HEIGHT    = 70
_BJUMP_RISE_DUR  = 0.35
_BJUMP_HANG_DUR  = 0.15
_BJUMP_FALL_DUR  = 0.25
_BOSS_MOVE_FRAMES = None
_BOSS_DASH_FRAMES = None
_BOSS_ANIM_FPS    = 8


def _get_boss_frames():
    global _BOSS_MOVE_FRAMES, _BOSS_DASH_FRAMES
    if _BOSS_MOVE_FRAMES is None:
        def load(name):
            tmx    = tilemap_mod.load(os.path.join(_BOSS_IMG_DIR, name))
            frames = tmx.get_frames(frame_tile_w=2)
            return [pygame.transform.scale(f, (128, 128)) for f in frames]
        _BOSS_MOVE_FRAMES = load('move.tmx')
        _BOSS_DASH_FRAMES = load('dash.tmx')
    return _BOSS_MOVE_FRAMES, _BOSS_DASH_FRAMES


class BoneBullet(Bullet):
    RADIUS = 8

    def __init__(self, x, y, vx, vy, damage):
        super().__init__(x, y, vx, vy, damage)
        self.rect = pygame.Rect(int(x) - self.RADIUS, int(y) - self.RADIUS,
                                self.RADIUS * 2, self.RADIUS * 2)

    def draw(self, screen, cam_x, cam_y):
        cx = int(self.x - cam_x)
        cy = int(self.y - cam_y)
        color = (0, 200, 255) if self.is_deflected else (230, 220, 180)
        pygame.draw.circle(screen, color, (cx, cy), self.RADIUS)
        pygame.draw.circle(screen, (160, 150, 110), (cx, cy), self.RADIUS, 2)


class GlobBullet(Bullet):
    RADIUS = 9

    def __init__(self, x, y, vx, vy, damage, **_):
        super().__init__(x, y, vx, vy, damage)
        self.rect = pygame.Rect(int(x) - self.RADIUS, int(y) - self.RADIUS,
                                self.RADIUS * 2, self.RADIUS * 2)

    def draw(self, screen, cam_x, cam_y):
        cx = int(self.x - cam_x)
        cy = int(self.y - cam_y)
        color = (0, 200, 255) if self.is_deflected else (220, 50, 50)
        pygame.draw.circle(screen, color, (cx, cy), self.RADIUS)
        pygame.draw.circle(screen, (140, 20, 20), (cx, cy), self.RADIUS, 2)


class SlimeKing(Enemy):
    SIZE    = 128
    NAME    = 'SLIME KING'
    is_boss = True

    # ── Tuning ────────────────────────────────────────────────────────────────
    CHASE_SPEED      = 95
    DASH_SPEED       = 480
    DASH_RANGE       = 460
    WINDUP_DUR       = 0.825
    GLOB_SPEED_BASE  = 170
    GLOB_DAMAGE      = 1
    SPREAD_COUNT     = 7
    SHOOT_CD         = 1.6
    DASH_CD          = 2.0
    TOUCH_DAMAGE     = 2
    TOUCH_INTERVAL   = 0.8
    DASH_DAMAGE      = 3
    STUN_DURATION    = 2.5   # seconds stunned after a normal dash is parried
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
    DESP_STUN_DUR    = 3   # vulnerable window duration
    AIR_HEIGHT       = 90    # pixels boss rises during jump

    # ── Colors ────────────────────────────────────────────────────────────────
    _COL_NORMAL   = ( 80, 200,  80)
    _COL_WINDUP   = (230, 220,  50)
    _COL_DASH     = (255, 255, 255)

    def __init__(self, x, y, floor_number=1):
        hp = 700 + floor_number * 100
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
        self._facing_right   = True
        self._dash_hit       = False
        self._alert_font     = pygame.font.SysFont(None, 48)

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
        self.action_cd        = self.DASH_CD
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
        elif not self.alive:
            stats.recorder.log_kill()
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
                           self.GLOB_DAMAGE + 1))

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
            self._facing_right = px > ex

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
                    self._facing_right = self.dash_vx > 0
                self._dash_hit   = False
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
            if self.rect.colliderect(player.rect) and not blocked and player.invulnerable_timer <= 0 and not self._dash_hit:
                dealt = max(1, self.DASH_DAMAGE - getattr(player, 'defense', 0))
                self._dash_hit = True
                player.hp -= dealt
                player.invulnerable_timer = 0.5
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

        # Pick sprite frame
        move_frames, dash_frames = _get_boss_frames()
        if self.desperate and self.desp_state == 'rise':
            progress  = min(1.0, self.desp_timer / self.DESP_RISE_DUR)
            frame_idx = max(0, 2 - int(progress * 3))
            frame = dash_frames[frame_idx]
        elif self.desperate and self.desp_state == 'hang':
            frame = dash_frames[2]
        elif self.desperate and self.desp_state == 'fall':
            frame = dash_frames[1]
        elif self.desperate and self.desp_state in ('impact', 'burst'):
            frame = dash_frames[0]
        elif self.stun_timer > 0 or desp_stun:
            frame = dash_frames[3]
        elif self.state == 'dash':
            frame = dash_frames[2]
        elif self.state == 'windup_dash':
            progress  = 1.0 - self.state_timer / self.WINDUP_DUR
            frame_idx = min(1, int(progress * 2))
            frame = dash_frames[frame_idx]
        else:
            frame_idx = (pygame.time.get_ticks() // (1000 // _BOSS_ANIM_FPS)) % len(move_frames)
            frame = move_frames[frame_idx]
        if not self._facing_right:
            frame = pygame.transform.flip(frame, True, False)

        # Flash tint overlay
        if self.flash_timer > 0:
            frame = frame.copy()
            frame.fill((255, 255, 255, 100), special_flags=pygame.BLEND_RGBA_ADD)

        fw, fh = frame.get_size()
        screen.blit(frame, (sx + (self.SIZE - fw) // 2, asy + self.SIZE - fh))

        if self.state == 'windup_dash':
            cx    = sx + self.SIZE // 2
            alert = self._alert_font.render("!", True, (255, 60, 60))
            screen.blit(alert, (cx - alert.get_width() // 2, asy - alert.get_height() - 4))

        # Glow ring — purple in stun window only
        if desp_stun:
            pygame.draw.rect(screen, (180, 80, 255),
                             (sx - 3, asy - 3, self.SIZE + 6, self.SIZE + 6),
                             3, border_radius=14)

        for b in self.bullets:
            b.draw(screen, cam_x, cam_y)


# ── BoneArcher ────────────────────────────────────────────────────────────────

class BoneArcher(Enemy):
    SIZE    = _RBOSS_SIZE
    NAME    = 'ELF ARCHER'
    is_boss = True

    # ── Tuning ────────────────────────────────────────────────────────────────
    CHASE_SPEED    = 160
    BULLET_SPEED   = 260
    BULLET_DAMAGE  = 2
    MAX_SHOOT_DIST = 700
    STILL_DUR       = 0.5
    CHARGE_DUR      = 1.1
    SHOOT_DUR       = 0.25
    RETREAT_DUR     = 1.8
    STUN_DURATION   = 1.5
    TOUCH_DAMAGE    = 1
    TOUCH_INTERVAL  = 0.8
    DASH_SPEED_BOSS = 550
    DASH_DUR        = 0.55
    DASH_CHANCE     = 0.80
    stun_on_deflect = False

    _DASH_DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # up, down, left, right

    DESPERATE_PCT              = 0.20
    DESP_GRID_N                = 7
    DESP_INTRO_DUR             = 1.5
    DESP_RING_CHARGE_DUR       = 0.5
    DESP_CLUSTER_CHARGE_DUR    = 0.25
    DESP_CLUSTER_FIRE_INTERVAL = 0.35   # time between consecutive cluster arrows
    DESP_WAIT_DUR              = 1.25
    SKY_ARROW_SPEED         = 700
    SKY_ARROW_DMG           = 2
    PILLAR_DAMAGE           = 2
    FLAME_HITS_KILL         = 3

    def __init__(self, x, y, floor_number=1):
        hp = 500 + floor_number * 80
        super().__init__(x, y, hp, speed=self.CHASE_SPEED)
        self.floor_number     = floor_number
        self.state            = 'chase'
        self.state_timer      = 0.0
        self.stun_timer       = 0.0
        self.touch_timer      = 0.0
        self.parry_vulnerable = False
        self.parry_dmg_mult   = 1.5
        self._facing_right    = True
        self._aim_angle       = 0.0
        self._anim_state      = 'walk'
        self._anim_frame      = 0
        self._anim_timer      = 0.0
        self._bow             = _get_bow_frames()
        self._arrow           = _get_arrow_surf()
        self._room_cx         = x + self.SIZE // 2
        self._room_cy         = y + self.SIZE // 2
        self.air_offset       = 0.0
        self._jump_phase      = None   # None | 'rise' | 'hang' | 'fall'
        self._jump_timer      = 0.0
        self._dash_vx         = 0.0
        self._dash_vy         = 0.0
        self._charge_is_ice   = False
        # Desperate phase
        self.desperate         = False
        self.invulnerable      = False
        self.flash_timer       = 0.0
        self.desp_state        = None
        self.desp_timer        = 0.0
        self._desp_ring          = 3
        self._desp_pillars       = []
        self._desp_cluster_queue = []
        self._desp_flame_hits    = 0
        self._touch_pillar_cd  = 0.0
        self._room_connections = set()
        self._room_grid_x      = 0
        self._room_grid_y      = 0

    @property
    def phase_label(self):
        return ''

    def stun(self, duration, dmg_mult=1.5):
        self.state            = 'chase'
        self.state_timer      = 0.0
        self.stun_timer       = duration
        self.parry_vulnerable = True
        self.parry_dmg_mult   = dmg_mult

    def take_damage(self, amount):
        if self.invulnerable:
            return 0
        if self.parry_vulnerable:
            amount = int(amount * self.parry_dmg_mult)
        dealt = super().take_damage(amount)
        if not self.desperate:
            self.hp   = max(1, self.hp)
            self.alive = True
        if not self.alive:
            stats.recorder.log_kill()
        return dealt

    def _set_anim(self, state):
        if state != self._anim_state:
            self._anim_state = state
            self._anim_frame = 0
            self._anim_timer = 0.0

    # ── Update ────────────────────────────────────────────────────────────────

    # ── Desperate phase ───────────────────────────────────────────────────────

    def _enter_desperate(self):
        self.desperate    = True
        self.invulnerable = True
        self.desp_state   = 'intro'
        self.desp_timer   = 0.0
        self.flash_timer  = 1.0
        self._desp_ring   = 3
        self._desp_pillars.clear()
        self._desp_cluster_queue = []
        self._desp_flame_hits = 0

    def _tile_center(self, row, col):
        tile_size = (ROOM_W - 2 * WALL_T) // self.DESP_GRID_N
        wx = self._room_cx - ROOM_W // 2
        wy = self._room_cy - ROOM_H // 2
        return (wx + WALL_T + col * tile_size + tile_size // 2,
                wy + WALL_T + row * tile_size + tile_size // 2)

    def _fire_ring(self, ring):
        tile_size  = (ROOM_W - 2 * WALL_T) // self.DESP_GRID_N
        center_idx = self.DESP_GRID_N // 2
        for r in range(self.DESP_GRID_N):
            for c in range(self.DESP_GRID_N):
                if max(abs(r - center_idx), abs(c - center_idx)) == ring:
                    tx, ty = self._tile_center(r, c)
                    self._desp_pillars.append(FallingArrow(tx, ty, tile_size))

    def _prepare_cluster(self):
        dirs      = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        chosen    = [random.choice(dirs) for _ in range(5)]
        flame_idx = random.randint(0, 4)
        img = _get_arrow_surf()
        self._desp_cluster_queue = [
            (ddx, ddy, FlameArrow if i == flame_idx else SkyArrow, img)
            for i, (ddx, ddy) in enumerate(chosen)
        ]

    def _fire_next_cluster_arrow(self, player):
        if not self._desp_cluster_queue:
            return
        ddx, ddy, cls, img = self._desp_cluster_queue.pop(0)
        px, py = player.x + 16, player.y + 16
        sx = px + ddx * 650
        sy = py + ddy * 650
        dist = math.hypot(px - sx, py - sy) or 1
        vx = (px - sx) / dist * self.SKY_ARROW_SPEED
        vy = (py - sy) / dist * self.SKY_ARROW_SPEED
        self.bullets.append(cls(sx, sy, vx, vy, self.SKY_ARROW_DMG, image=img))

    def _find_outside_pos(self):
        wx = self._room_cx - ROOM_W // 2
        wy = self._room_cy - ROOM_H // 2
        gx, gy = self._room_grid_x, self._room_grid_y
        options = []
        if (gx, gy - 1) not in self._room_connections:
            options.append((wx + ROOM_W // 2 - self.SIZE // 2, wy + WALL_T + 8))
        if (gx, gy + 1) not in self._room_connections:
            options.append((wx + ROOM_W // 2 - self.SIZE // 2, wy + ROOM_H - WALL_T - self.SIZE - 8))
        if (gx - 1, gy) not in self._room_connections:
            options.append((wx + WALL_T + 8, wy + ROOM_H // 2 - self.SIZE // 2))
        if (gx + 1, gy) not in self._room_connections:
            options.append((wx + ROOM_W - WALL_T - self.SIZE - 8, wy + ROOM_H // 2 - self.SIZE // 2))
        if not options:
            options.append((wx + ROOM_W // 2 - self.SIZE // 2, wy + WALL_T + 8))
        return random.choice(options)

    def take_flame_hit(self):
        self.flash_timer      = 0.4
        self._desp_flame_hits += 1
        sound.play('hit_weaken')
        if self._desp_flame_hits >= self.FLAME_HITS_KILL:
            self.invulnerable = False
            self.alive        = False
            stats.recorder.log_kill()

    def _update_desperate(self, player, dt, walls):
        self.desp_timer  += dt
        self.flash_timer  = max(0.0, self.flash_timer - dt)

        # Pillar contact damage
        if self._touch_pillar_cd > 0:
            self._touch_pillar_cd -= dt
        if self._touch_pillar_cd <= 0:
            for p in self._desp_pillars:
                if p.stuck and p.rect.colliderect(player.rect) and player.invulnerable_timer <= 0:
                    dealt = max(1, self.PILLAR_DAMAGE - getattr(player, 'defense', 0))
                    player.hp -= dealt
                    player.invulnerable_timer = 0.5
                    ui.spawn(player.x + 16, player.y - 8, dealt, ui.PLAYER_HIT_COLOR)
                    self._touch_pillar_cd = 0.6
                    break

        if self.desp_state == 'intro':
            if self.desp_timer >= self.DESP_INTRO_DUR:
                bx, by = self._find_outside_pos()
                self.x = float(bx);  self.y = float(by)
                self._sync_rect()
                self._aim_angle    = -math.pi / 2
                self._facing_right = True
                self.desp_state    = 'ring_charge'
                self.desp_timer    = 0.0

        elif self.desp_state == 'ring_charge':
            if self.desp_timer >= self.DESP_RING_CHARGE_DUR:
                self._fire_ring(self._desp_ring)
                sound.play('arrow_shot')
                self.desp_state = 'ring_fall'
                self.desp_timer = 0.0

        elif self.desp_state == 'ring_fall':
            for p in self._desp_pillars:
                p.update(dt)
            if all(p.stuck for p in self._desp_pillars) or self.desp_timer >= 2.0:
                self._desp_ring -= 1
                self.desp_state  = 'cluster_charge' if self._desp_ring <= 0 else 'ring_charge'
                self.desp_timer  = 0.0

        elif self.desp_state == 'cluster_charge':
            if self.desp_timer >= self.DESP_CLUSTER_CHARGE_DUR:
                self._prepare_cluster()
                self._fire_next_cluster_arrow(player)
                self.desp_state = 'cluster_resolve'
                self.desp_timer = 0.0

        elif self.desp_state == 'cluster_resolve':
            if self.desp_timer >= self.DESP_CLUSTER_FIRE_INTERVAL:
                self.desp_timer = 0.0
                if self._desp_cluster_queue:
                    self._fire_next_cluster_arrow(player)
                else:
                    self.desp_state = 'cluster_wait'
                    self.desp_timer = 0.0

        elif self.desp_state == 'cluster_wait':
            if self.desp_timer >= self.DESP_WAIT_DUR:
                self.desp_state = 'cluster_charge'
                self.desp_timer = 0.0

        for b in self.bullets:
            b.update(dt, walls)
        self.bullets = [b for b in self.bullets if b.alive]

    def _trigger_jump(self):
        if self._jump_phase is not None:
            return
        self._jump_phase = 'rise'
        self._jump_timer = 0.0

    def _wall_touched(self, ix, iy):
        return math.hypot(self.x - ix, self.y - iy) > 3.0

    def update(self, player, dt, walls):
        if not self.alive:
            return
        self._apply_status(dt)
        if not self.alive:
            return

        # ── Jump animation (wall-touch escape) ───────────────────────────────
        if self._jump_phase is not None:
            self._jump_timer += dt
            if self._jump_phase == 'rise':
                self.air_offset = -_BJUMP_HEIGHT * min(self._jump_timer / _BJUMP_RISE_DUR, 1.0)
                if self._jump_timer >= _BJUMP_RISE_DUR:
                    self.x = self._room_cx - self.SIZE // 2
                    self.y = self._room_cy - self.SIZE // 2
                    self._sync_rect()
                    self._jump_phase = 'hang'
                    self._jump_timer = 0.0
            elif self._jump_phase == 'hang':
                if self._jump_timer >= _BJUMP_HANG_DUR:
                    self._jump_phase = 'fall'
                    self._jump_timer = 0.0
            elif self._jump_phase == 'fall':
                self.air_offset = -_BJUMP_HEIGHT * max(0.0, 1.0 - self._jump_timer / _BJUMP_FALL_DUR)
                if self._jump_timer >= _BJUMP_FALL_DUR:
                    self.air_offset  = 0.0
                    self._jump_phase = None
                    self.state       = 'still'
                    self.state_timer = self.STILL_DUR
            for b in self.bullets:
                b.update(dt, walls)
            self.bullets = [b for b in self.bullets if b.alive]
            return

        if self.stun_timer > 0:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.parry_vulnerable = False
            for b in self.bullets:
                b.update(dt, walls)
            self.bullets = [b for b in self.bullets if b.alive]
            return

        if not self.desperate and self.hp / self.max_hp <= self.DESPERATE_PCT:
            self._enter_desperate()
        if self.desperate:
            self._update_desperate(player, dt, walls)
            return

        ex = self.x + self.SIZE // 2
        ey = self.y + self.SIZE // 2
        px = player.x + 16
        py = player.y + 16
        dx, dy = px - ex, py - ey
        dist   = math.hypot(dx, dy)
        spd    = self.speed * (0.5 if self.slow_timer > 0 else 1.0)

        self._facing_right = dx > 0
        self._aim_angle    = math.atan2(dy, dx)

        if self.state == 'chase':
            self._set_anim('walk')
            if dist > 0:
                ix = self.x + dx / dist * spd * dt
                iy = self.y + dy / dist * spd * dt
                self.x, self.y = ix, iy
                self._sync_rect()
                self._push_out_of_walls(walls)
                if self._wall_touched(ix, iy):
                    self._trigger_jump()
            if dist <= self.MAX_SHOOT_DIST:
                self.state       = 'still'
                self.state_timer = self.STILL_DUR

        elif self.state == 'still':
            self._set_anim('idle')
            self.state_timer -= dt
            if self.state_timer <= 0:
                if random.random() < self.DASH_CHANCE:
                    dir_x, dir_y  = random.choice(self._DASH_DIRS)
                    self._dash_vx = dir_x * self.DASH_SPEED_BOSS
                    self._dash_vy = dir_y * self.DASH_SPEED_BOSS
                    if dir_x != 0:
                        self._facing_right = dir_x > 0
                else:
                    self._dash_vx = 0.0
                    self._dash_vy = 0.0
                self._charge_is_ice = random.random() < 0.25
                self.state       = 'charge'
                self.state_timer = self.CHARGE_DUR

        elif self.state == 'charge':
            self._set_anim('idle')
            self.state_timer -= dt
            if self.state_timer <= 0:
                if dist > 0:
                    bspd   = self.BULLET_SPEED + self.floor_number * 15
                    spread = math.radians(30)
                    base   = math.atan2(dy, dx)
                    cls    = IceBullet if self._charge_is_ice else Bullet
                    for i in range(5):
                        t = i / 4
                        a = base - spread / 2 + spread * t
                        self.bullets.append(
                            cls(ex, ey, math.cos(a) * bspd, math.sin(a) * bspd,
                                self.BULLET_DAMAGE, image=self._arrow))
                    sound.play('arrow_shot')
                self.state       = 'shoot'
                self.state_timer = self.SHOOT_DUR

        elif self.state == 'shoot':
            self._set_anim('idle')
            self.state_timer -= dt
            if self.state_timer <= 0:
                if self._dash_vx != 0 or self._dash_vy != 0:
                    self.state       = 'dash'
                    self.state_timer = self.DASH_DUR
                else:
                    self.state       = 'retreat'
                    self.state_timer = self.RETREAT_DUR

        elif self.state == 'dash':
            self._set_anim('walk')
            ix = self.x + self._dash_vx * dt
            iy = self.y + self._dash_vy * dt
            self.x, self.y = ix, iy
            self._sync_rect()
            self._push_out_of_walls(walls)
            self.state_timer -= dt
            if self._wall_touched(ix, iy):
                self._trigger_jump()
            elif self.state_timer <= 0:
                self.state       = 'still'
                self.state_timer = self.STILL_DUR

        elif self.state == 'retreat':
            self._set_anim('walk')
            if dist > 0:
                ix = self.x - dx / dist * spd * dt
                iy = self.y - dy / dist * spd * dt
                self.x, self.y = ix, iy
                self._sync_rect()
                self._push_out_of_walls(walls)
                if self._wall_touched(ix, iy):
                    self._trigger_jump()
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state       = 'still'
                self.state_timer = self.STILL_DUR

        # Tick animation
        self._anim_timer += dt
        walk_frames, idle_frames = _get_rboss_frames()
        frames = walk_frames if self._anim_state == 'walk' else idle_frames
        if self._anim_timer >= 1.0 / _RBOSS_ANIM_FPS:
            self._anim_timer -= 1.0 / _RBOSS_ANIM_FPS
            self._anim_frame  = (self._anim_frame + 1) % len(frames)
        self._anim_frame = min(self._anim_frame, len(frames) - 1)

        # Passive contact damage
        if self.touch_timer > 0:
            self.touch_timer -= dt
        if (self.rect.colliderect(player.rect) and self.touch_timer <= 0
                and player.invulnerable_timer <= 0):
            dealt = max(1, self.TOUCH_DAMAGE - getattr(player, 'defense', 0))
            player.hp        -= dealt
            self.touch_timer  = self.TOUCH_INTERVAL
            ui.spawn(player.x + 16, player.y - 8, dealt, ui.PLAYER_HIT_COLOR)

        for b in self.bullets:
            b.update(dt, walls)
        self.bullets = [b for b in self.bullets if b.alive]

    # ── Draw ──────────────────────────────────────────────────────────────────

    def _draw_dash_indicator(self, screen, cam_x, cam_y):
        if self.desperate or self.state != 'charge' or (self._dash_vx == 0 and self._dash_vy == 0):
            return
        ticks    = pygame.time.get_ticks()
        progress = 1.0 - self.state_timer / self.CHARGE_DUR
        blink_ms = 100 if progress > 0.6 else 220
        if (ticks // blink_ms) % 2 == 0:
            return
        sx  = int(self.x - cam_x)
        sy  = int(self.y - cam_y) + int(self.air_offset)
        cx  = sx + self.SIZE // 2
        cy  = sy + self.SIZE // 2
        spd = math.hypot(self._dash_vx, self._dash_vy) or 1
        dx  = self._dash_vx / spd
        dy  = self._dash_vy / spd
        tip_x = cx + int(dx * 38)
        tip_y = cy + int(dy * 38)
        col   = (255, 210, 30)
        pygame.draw.line(screen, col, (cx, cy), (tip_x, tip_y), 3)
        perp_x, perp_y = -dy, dx
        head  = 12
        ah_x  = tip_x - int(dx * head)
        ah_y  = tip_y - int(dy * head)
        pygame.draw.polygon(screen, col, [
            (tip_x, tip_y),
            (ah_x + int(perp_x * head * 0.5), ah_y + int(perp_y * head * 0.5)),
            (ah_x - int(perp_x * head * 0.5), ah_y - int(perp_y * head * 0.5)),
        ])

    def _draw_bow_desperate(self, screen, cam_x, cam_y):
        if self.desp_state not in ('ring_charge', 'cluster_charge'):
            return
        if self.desp_state == 'ring_charge':
            progress = min(1.0, self.desp_timer / self.DESP_RING_CHARGE_DUR)
        else:
            progress = min(1.0, self.desp_timer / self.DESP_CLUSTER_CHARGE_DUR)
        frame_idx = min(len(self._bow) - 1, int(progress * len(self._bow)))
        aim = -math.pi / 2
        cx  = int(self.x + self.SIZE // 2 - cam_x)
        cy  = int(self.y + self.SIZE // 2 - cam_y)
        bx  = cx + int(math.cos(aim) * 12)
        by  = cy + int(math.sin(aim) * 12)
        bow_rot = pygame.transform.rotate(self._bow[frame_idx], -math.degrees(aim))
        screen.blit(bow_rot, bow_rot.get_rect(center=(bx, by)))
        pull_back = 6 * progress
        fwd       = self._arrow.get_width() // 2 - pull_back
        arrow_rot = pygame.transform.rotate(self._arrow, -math.degrees(aim))
        screen.blit(arrow_rot, arrow_rot.get_rect(
            center=(bx + int(math.cos(aim) * fwd), by + int(math.sin(aim) * fwd))))

    def _draw_bow(self, screen, cam_x, cam_y):
        if self.desperate:
            self._draw_bow_desperate(screen, cam_x, cam_y)
            return
        if self.state in ('chase', 'retreat', 'dash'):
            return

        if self.state == 'still':
            frame_idx = 0
        elif self.state == 'charge':
            progress  = 1.0 - (self.state_timer / self.CHARGE_DUR)
            frame_idx = min(len(self._bow) - 1, int(progress * len(self._bow)))
        else:  # shoot — fully drawn for brief freeze
            frame_idx = len(self._bow) - 1

        cx = int(self.x + self.SIZE // 2 - cam_x)
        cy = int(self.y + self.SIZE // 2 - cam_y)
        hold_dist = 12
        bx = cx + int(math.cos(self._aim_angle) * hold_dist)
        by = cy + int(math.sin(self._aim_angle) * hold_dist)

        bow_rot = pygame.transform.rotate(self._bow[frame_idx],
                                          -math.degrees(self._aim_angle))
        screen.blit(bow_rot, bow_rot.get_rect(center=(bx, by)))

        if self.state in ('still', 'charge'):
            progress  = (1.0 - self.state_timer / self.CHARGE_DUR) if self.state == 'charge' else 0.0
            pull_back = 6 * progress
            half_len  = self._arrow.get_width() // 2
            fwd       = half_len - pull_back
            arrow_cx  = bx + int(math.cos(self._aim_angle) * fwd)
            arrow_cy  = by + int(math.sin(self._aim_angle) * fwd)
            arrow_rot = pygame.transform.rotate(self._arrow,
                                                -math.degrees(self._aim_angle))
            screen.blit(arrow_rot, arrow_rot.get_rect(center=(arrow_cx, arrow_cy)))
            if self._charge_is_ice:
                frames = _get_frost_frames()
                if frames:
                    idx  = (pygame.time.get_ticks() // (1000 // _FROST_FPS)) % len(frames)
                    half = _FROST_PARTICLE_SIZE // 2
                    f    = frames[idx].copy()
                    f.set_alpha(210)
                    screen.blit(f, (arrow_cx - half, arrow_cy - half))

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx  = int(self.x - cam_x)
        sy  = int(self.y - cam_y)
        asy = sy + int(self.air_offset)

        if self.air_offset < 0:
            shadow_alpha = max(40, 160 + int(self.air_offset * 1.5))
            shadow = pygame.Surface((self.SIZE, 12), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, shadow_alpha))
            screen.blit(shadow, (sx, sy + self.SIZE - 6))

        walk_frames, idle_frames = _get_rboss_frames()
        frames = walk_frames if self._anim_state == 'walk' else idle_frames
        frame  = frames[self._anim_frame % len(frames)]

        if not self._facing_right:
            frame = pygame.transform.flip(frame, True, False)

        if self.stun_timer > 0:
            frame = frame.copy()
            frame.fill((180, 80, 255, 100), special_flags=pygame.BLEND_RGBA_ADD)

        screen.blit(frame, (sx, asy))
        self._draw_bow(screen, cam_x, cam_y)
        self._draw_dash_indicator(screen, cam_x, cam_y)

        if self.parry_vulnerable:
            pygame.draw.rect(screen, (180, 80, 255),
                             (sx - 3, sy - 3, self.SIZE + 6, self.SIZE + 6),
                             3, border_radius=14)

        self._draw_flame(screen, cam_x, cam_y)
        self._draw_frost(screen, cam_x, cam_y)
        self._draw_hp_bar(screen, cam_x, cam_y)

        for p in self._desp_pillars:
            p.draw(screen, cam_x, cam_y)

        for b in self.bullets:
            b.draw(screen, cam_x, cam_y)
