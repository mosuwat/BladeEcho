import pygame
import math
import random
import os
import tilemap as tilemap_mod
import ui
import sound
import stats

_ENEMY_IMG_DIR   = os.path.join(os.path.dirname(__file__), 'images', 'Enemy')
_SLIME_FRAMES    = None
_SKELETON_FRAMES = None   # {'idle': [...], 'run': [...]}
_BOW_FRAMES      = None   # [undrawn, mid-draw, full-draw]
_ARROW_SURF      = None   # single nocked-arrow sprite
_FLAME_FRAMES    = None   # pre-scaled animated flame overlay frames
_FROST_FRAMES    = None   # pre-scaled frost sparkle frames (particle size)

_FLAME_FPS       = 10
_FLAME_CELL      = 16
_FROST_FPS           = 10
_FROST_CELL          = 64
_FROST_PARTICLE_SIZE = 16
_FROST_SPAWN_RATE    = 8    # particles per second
_FROST_LIFE          = 0.8  # seconds per particle


def _get_flame_frames(size):
    global _FLAME_FRAMES
    if _FLAME_FRAMES is None:
        path  = os.path.join(os.path.dirname(__file__), 'images', 'Debuff', 'flamme.png')
        sheet = pygame.image.load(path).convert_alpha()
        cols  = sheet.get_width() // _FLAME_CELL
        raw   = [sheet.subsurface(_FLAME_CELL * i, 0, _FLAME_CELL, _FLAME_CELL)
                 for i in range(cols)]
        _FLAME_FRAMES = [pygame.transform.scale(f, (size, size)) for f in raw]
    return _FLAME_FRAMES


def _get_frost_frames():
    global _FROST_FRAMES
    if _FROST_FRAMES is None:
        path  = os.path.join(os.path.dirname(__file__), 'images', 'Debuff', 'frost.png')
        sheet = pygame.image.load(path).convert_alpha()
        cols  = sheet.get_width()  // _FROST_CELL
        rows  = sheet.get_height() // _FROST_CELL
        raw   = [sheet.subsurface(_FROST_CELL * c, _FROST_CELL * r, _FROST_CELL, _FROST_CELL)
                 for r in range(rows) for c in range(cols)]
        _FROST_FRAMES = [pygame.transform.scale(f, (_FROST_PARTICLE_SIZE, _FROST_PARTICLE_SIZE))
                         for f in raw]
    return _FROST_FRAMES


def _get_slime_frames():
    global _SLIME_FRAMES
    if _SLIME_FRAMES is None:
        tmx = tilemap_mod.load(os.path.join(_ENEMY_IMG_DIR, 'Slime', 'idle.tmx'))
        raw = tmx.get_frames(frame_tile_w=1)
        _SLIME_FRAMES = [pygame.transform.scale(f, (f.get_width() * 2, f.get_height() * 2))
                         for f in raw]
    return _SLIME_FRAMES


def _sheet_frames(path, frame_w, frame_h):
    sheet = pygame.image.load(path).convert_alpha()
    cols  = sheet.get_width()  // frame_w
    rows  = sheet.get_height() // frame_h
    return [sheet.subsurface(c * frame_w, r * frame_h, frame_w, frame_h)
            for r in range(rows) for c in range(cols)]


def _get_skeleton_frames():
    global _SKELETON_FRAMES
    if _SKELETON_FRAMES is None:
        base = os.path.join(_ENEMY_IMG_DIR, 'Skeleton - Base')
        idle = [pygame.transform.scale(f, (48, 48))
                for f in _sheet_frames(os.path.join(base, 'Idle', 'Idle-Sheet.png'), 32, 32)]
        run  = [pygame.transform.scale(f, (96, 96))
                for f in _sheet_frames(os.path.join(base, 'Run',  'Run-Sheet.png'),  64, 64)]
        _SKELETON_FRAMES = {'idle': idle, 'run': run}
    return _SKELETON_FRAMES


def _get_bow_frames():
    global _BOW_FRAMES
    if _BOW_FRAMES is None:
        path = os.path.join(os.path.dirname(__file__), 'images', 'Weapon', 'bow.tmx')
        raw  = tilemap_mod.load(path).get_frames(frame_tile_w=1)
        _BOW_FRAMES = [pygame.transform.scale(f, (f.get_width() * 1.75, f.get_height() * 1.75))
                       for f in raw]
    return _BOW_FRAMES


def _get_arrow_surf():
    global _ARROW_SURF
    if _ARROW_SURF is None:
        path = os.path.join(os.path.dirname(__file__), 'images', 'Weapon', 'arrow.tmx')
        raw  = tilemap_mod.load(path).get_frames(frame_tile_w=1)[0]
        _ARROW_SURF = pygame.transform.scale(raw, (raw.get_width() * 2, raw.get_height() * 2))
    return _ARROW_SURF


class Bullet:
    RADIUS = 5

    def __init__(self, x, y, vx, vy, damage, image=None):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.image = image
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
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        if self.image is not None:
            angle = math.atan2(self.vy, self.vx)
            rotated = pygame.transform.rotate(self.image, -math.degrees(angle))
            screen.blit(rotated, rotated.get_rect(center=(sx, sy)))
        else:
            color = (0, 200, 255) if self.is_deflected else (255, 210, 60)
            pygame.draw.circle(screen, color, (sx, sy), self.RADIUS)


class Enemy:
    SIZE           = 32
    NAME           = ''
    is_boss        = False
    STUN_DURATION  = 2.0   # seconds stunned after a dash is parried

    def __init__(self, x, y, hp, speed):
        self.x = float(x)
        self.y = float(y)
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.alive = True
        self.rect = pygame.Rect(int(x), int(y), self.SIZE, self.SIZE)
        self.bullets    = []
        self.burn_timer  = 0.0   # seconds remaining of burn DoT
        self.burn_dps    = 0.0   # damage per second while burning
        self.slow_timer  = 0.0   # seconds remaining of slow debuff
        self._burn_accum    = 0.0   # damage accumulated since last tick display
        self._burn_tick     = 0.0   # countdown to next damage number
        self._frost_particles = []  # list of [x, y, vx, vy, life, anim_t]
        self._frost_spawn_acc = 0.0

    def take_damage(self, amount):
        actual = min(amount, max(0, self.hp))
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            if not self.is_boss:
                stats.recorder.log_kill()
        stats.recorder.log_damage(actual)
        return amount

    _BURN_TICK = 0.5

    def _apply_status(self, dt):
        """Call at the top of each subclass update(). Handles burn and slow timers."""
        if self.burn_timer > 0:
            self.burn_timer -= dt
            if not getattr(self, 'invulnerable', False):
                dmg               = self.burn_dps * dt
                self.hp          -= dmg
                self._burn_accum += dmg
                self._burn_tick  -= dt
                if self._burn_tick <= 0:
                    self._burn_tick = self._BURN_TICK
                    shown = int(self._burn_accum)
                    if shown > 0:
                        ui.spawn(self.x + 16, self.y - 8, shown, (255, 120, 0))
                    self._burn_accum = 0.0
                if self.hp <= 0:
                    self.hp = 0
                    self.alive = False
        if self.slow_timer > 0:
            self.slow_timer -= dt
            self._frost_spawn_acc += dt
            interval = 1.0 / _FROST_SPAWN_RATE
            while self._frost_spawn_acc >= interval:
                self._frost_spawn_acc -= interval
                px = self.x + random.uniform(0, self.SIZE)
                py = self.y + random.uniform(0, self.SIZE)
                vx = random.uniform(-25, 25)
                vy = random.uniform(-80, -35)
                self._frost_particles.append([px, py, vx, vy, _FROST_LIFE, 0.0])
        self._frost_particles = [
            [p[0] + p[2] * dt, p[1] + p[3] * dt, p[2], p[3], p[4] - dt, p[5] + dt]
            for p in self._frost_particles if p[4] - dt > 0
        ]

    @property
    def phase_label(self):
        return ''

    def update(self, player, dt, walls): pass

    def draw(self, screen, cam_x, cam_y): pass

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

    def _draw_flame(self, screen, cam_x, cam_y):
        if self.burn_timer <= 0:
            return
        frames = _get_flame_frames(self.SIZE)
        idx    = (pygame.time.get_ticks() // (1000 // _FLAME_FPS)) % len(frames)
        sx     = int(self.x - cam_x)
        sy     = int(self.y - cam_y)
        screen.blit(frames[idx], (sx, sy), special_flags=pygame.BLEND_ADD)

    def _draw_frost(self, screen, cam_x, cam_y):
        if not self._frost_particles:
            return
        frames = _get_frost_frames()
        half   = _FROST_PARTICLE_SIZE // 2
        for px, py, _, _, life, anim_t in self._frost_particles:
            idx   = int(anim_t * _FROST_FPS) % len(frames)
            frame = frames[idx].copy()
            frame.set_alpha(int(255 * (life / _FROST_LIFE)))
            screen.blit(frame, (int(px - cam_x) - half, int(py - cam_y) - half))

    def _draw_hp_bar(self, screen, cam_x, cam_y):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        bar_w = self.SIZE
        filled = int(bar_w * self.hp / self.max_hp)
        pygame.draw.rect(screen, (80, 0, 0),   (sx, sy - 8, bar_w, 5))
        pygame.draw.rect(screen, (220, 50, 50), (sx, sy - 8, filled, 5))


class RangedEnemy(Enemy):
    COLOR         = (180, 60, 60)
    BULLET_SPEED  = 300
    BULLET_DAMAGE = 1
    MAX_SHOOT_DIST = 650

    STILL_DUR   = 0.35   # pause before drawing bow
    CHARGE_DUR  = 0.75   # bow-draw hold
    SHOOT_DUR   = 0.20   # freeze after firing
    RETREAT_DUR = 0.70   # walk-away phase

    def __init__(self, x, y, floor_number=1):
        hp = 40 + floor_number * 15
        super().__init__(x, y, hp, speed=100)
        self.floor_number  = floor_number
        self.bullets       = []
        self.state         = 'chase'   # chase | still | charge | shoot | retreat
        self.state_timer   = 0.0
        self._sk           = _get_skeleton_frames()
        self._bow          = _get_bow_frames()
        self._arrow        = _get_arrow_surf()
        self._anim_state   = 'run'
        self._anim_frame   = 0
        self._anim_timer   = 0.0
        self._anim_fps     = 8
        self._facing_right  = True
        self._aim_angle     = 0.0   # radians toward player, kept for draw
        self._retreat_perp  = 0     # perpendicular strafe side when wall-stuck: -1, 0, or 1

    # ------------------------------------------------------------------ AI

    def _set_anim(self, state):
        if state != self._anim_state:
            self._anim_state = state
            self._anim_frame = 0
            self._anim_timer = 0.0

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
        dist   = math.hypot(dx, dy)
        spd    = self.speed * (0.5 if self.slow_timer > 0 else 1.0)

        self._facing_right = dx > 0
        self._aim_angle    = math.atan2(dy, dx)

        if self.state == 'chase':
            self._set_anim('run')
            if dist > 0:
                self.x += dx / dist * spd * dt
                self.y += dy / dist * spd * dt
                self._sync_rect()
                self._push_out_of_walls(walls)
            if dist <= self.MAX_SHOOT_DIST:
                self.state       = 'still'
                self.state_timer = self.STILL_DUR

        elif self.state == 'still':
            self._set_anim('idle')
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state       = 'charge'
                self.state_timer = self.CHARGE_DUR

        elif self.state == 'charge':
            self._set_anim('idle')
            self.state_timer -= dt
            if self.state_timer <= 0:
                bullet_spd = self.BULLET_SPEED + self.floor_number * 20
                if dist > 0:
                    self.bullets.append(
                        Bullet(ex, ey, dx / dist * bullet_spd, dy / dist * bullet_spd,
                               self.BULLET_DAMAGE, image=self._arrow))
                    sound.play('arrow_shot')
                self.state       = 'shoot'
                self.state_timer = self.SHOOT_DUR

        elif self.state == 'shoot':
            self._set_anim('idle')
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state       = 'retreat'
                self.state_timer = self.RETREAT_DUR

        elif self.state == 'retreat':
            self._set_anim('run')
            if dist > 0:
                self.x -= dx / dist * spd * dt
                self.y -= dy / dist * spd * dt
                self._sync_rect()
                self._push_out_of_walls(walls)
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state       = 'still'
                self.state_timer = self.STILL_DUR

        self._anim_timer += dt
        if self._anim_timer >= 1.0 / self._anim_fps:
            self._anim_timer -= 1.0 / self._anim_fps
            frames = self._sk[self._anim_state]
            self._anim_frame = (self._anim_frame + 1) % len(frames)
        self._anim_frame = min(self._anim_frame, len(self._sk[self._anim_state]) - 1)

        for b in self.bullets:
            b.update(dt, walls)
        self.bullets = [b for b in self.bullets if b.alive]

    # ---------------------------------------------------------------- Draw

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        cx = sx + self.SIZE // 2
        frame = self._sk[self._anim_state][self._anim_frame]
        if not self._facing_right:
            frame = pygame.transform.flip(frame, True, False)
        fw, fh = frame.get_size()
        screen.blit(frame, (cx - fw // 2, sy + self.SIZE - fh))
        self._draw_bow(screen, cam_x, cam_y)
        self._draw_flame(screen, cam_x, cam_y)
        self._draw_frost(screen, cam_x, cam_y)
        self._draw_hp_bar(screen, cam_x, cam_y)
        for b in self.bullets:
            b.draw(screen, cam_x, cam_y)

    def _draw_bow(self, screen, cam_x, cam_y):
        if self.state in ('chase', 'retreat'):
            return

        if self.state == 'still':
            frame_idx = 0
        elif self.state == 'charge':
            progress  = 1.0 - (self.state_timer / self.CHARGE_DUR)
            frame_idx = min(len(self._bow) - 1, int(progress * len(self._bow)))
        else:  # shoot — fully drawn for the brief freeze, then arrow is gone
            frame_idx = len(self._bow) - 1

        cx = int(self.x + 16 - cam_x)
        cy = int(self.y + 16 - cam_y)
        hold_dist = 10
        bx = cx + int(math.cos(self._aim_angle) * hold_dist)
        by = cy + int(math.sin(self._aim_angle) * hold_dist)

        # Bow: sprite baseline points up; add 90° CCW so frame 0 faces right at aim_angle=0
        bow_rot = pygame.transform.rotate(self._bow[frame_idx],
                                          -math.degrees(self._aim_angle))
        screen.blit(bow_rot, bow_rot.get_rect(center=(bx, by)))

        # Arrow nocked while drawing, hidden once shot fires.
        # Nock sits on the string; as the bow is drawn the string pulls back.
        if self.state in ('still', 'charge'):
            progress  = (1.0 - self.state_timer / self.CHARGE_DUR) if self.state == 'charge' else 0.0
            pull_back = 6 * progress          # max 6 px rearward along aim axis
            half_len  = self._arrow.get_width() // 2
            # nock position retreats opposite to aim; arrow center is half_len ahead of nock
            fwd = half_len - pull_back
            arrow_cx  = bx + int(math.cos(self._aim_angle) * fwd)
            arrow_cy  = by + int(math.sin(self._aim_angle) * fwd)
            arrow_rot = pygame.transform.rotate(self._arrow,
                                                -math.degrees(self._aim_angle))
            screen.blit(arrow_rot, arrow_rot.get_rect(center=(arrow_cx, arrow_cy)))


class MeleeEnemy(Enemy):
    COLOR          = (160, 80, 200)   # purple
    CHASE_SPEED    = 110
    DASH_SPEED     = 650
    DASH_RANGE     = 260    # start wind-up within this distance
    WINDUP_DUR     = 0.45   # pause before dash
    DASH_DUR       = 0.22   # duration of dash burst
    DASH_COOLDOWN  = 2.2
    DASH_DAMAGE    = 1
    TOUCH_DAMAGE   = 1
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
        self._frames      = _get_slime_frames()
        self._anim_frame  = 0
        self._anim_timer  = 0.0
        self._anim_fps    = 8
        self._windup_time = 0.0
        self._alert_font  = pygame.font.SysFont(None, 28)

    def stun(self, duration, dmg_mult=1.5):
        self.state            = 'chase'
        self.state_timer      = 0.0
        self.dash_vx          = 0.0
        self.dash_vy          = 0.0
        self.stun_timer       = duration
        self.dash_cd          = self.DASH_COOLDOWN
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
            self._windup_time = 0.0
            self._anim_timer += dt
            if self._anim_timer >= 1.0 / self._anim_fps:
                self._anim_timer -= 1.0 / self._anim_fps
                self._anim_frame  = (self._anim_frame + 1) % len(self._frames)
            self._move_toward(px, py, ex, ey, dist, dt, walls)
            self.dash_cd -= dt
            if dist < self.DASH_RANGE and self.dash_cd <= 0:
                self.state       = 'windup'
                self.state_timer = self.WINDUP_DUR
            self._passive_contact(player)

        elif self.state == 'windup':
            self._windup_time += dt
            self._anim_timer  += dt
            if self._anim_timer >= 1.0 / self._anim_fps:
                self._anim_timer -= 1.0 / self._anim_fps
                self._anim_frame  = (self._anim_frame + 1) % len(self._frames)
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
                self.touch_timer = self.TOUCH_INTERVAL
                if player.invulnerable_timer <= 0:
                    dealt = max(1, self.DASH_DAMAGE - getattr(player, 'defense', 0))
                    player.hp -= dealt
                    ui.spawn(player.x + 16, player.y - 8,
                                     dealt, ui.PLAYER_HIT_COLOR)
            if self.state_timer <= 0:
                self.state  = 'cooldown'
                self.dash_cd = self.DASH_COOLDOWN

        elif self.state == 'cooldown':
            self._windup_time = 0.0
            self._anim_timer += dt
            if self._anim_timer >= 1.0 / self._anim_fps:
                self._anim_timer -= 1.0 / self._anim_fps
                self._anim_frame  = (self._anim_frame + 1) % len(self._frames)
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
            dealt = max(1, self.TOUCH_DAMAGE - getattr(player, 'defense', 0))
            player.hp       -= dealt
            self.touch_timer = self.TOUCH_INTERVAL
            ui.spawn(player.x + 16, player.y - 8,
                     dealt, ui.PLAYER_HIT_COLOR)

    # ---------------------------------------------------------------- Draw

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        cx = sx + self.SIZE // 2
        cy = sy + self.SIZE // 2

        if self.state == 'dash':
            frame = self._frames[min(2, len(self._frames) - 1)]
            fw, fh = frame.get_size()
            screen.blit(frame, (cx - fw // 2, cy - fh // 2))
        elif self.state == 'windup':
            scale = 1.0 + 0.15 * math.sin(self._windup_time * 15)
            frame = self._frames[self._anim_frame]
            fw = max(1, int(frame.get_width()  * scale))
            fh = max(1, int(frame.get_height() * scale))
            scaled = pygame.transform.scale(frame, (fw, fh))
            ox = random.randint(-3, 3)
            oy = random.randint(-3, 3)
            screen.blit(scaled, (cx - fw // 2 + ox, cy - fh // 2 + oy))
            alert = self._alert_font.render("!", True, (255, 60, 60))
            screen.blit(alert, (cx - alert.get_width() // 2, sy - fh // 2 - alert.get_height() - 2))
        else:
            frame = self._frames[self._anim_frame]
            fw, fh = frame.get_size()
            screen.blit(frame, (cx - fw // 2, cy - fh // 2))

        self._draw_flame(screen, cam_x, cam_y)
        self._draw_frost(screen, cam_x, cam_y)
        self._draw_hp_bar(screen, cam_x, cam_y)
