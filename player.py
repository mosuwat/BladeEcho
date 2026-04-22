import pygame
import math
import os
import tilemap as tilemap_mod
from enemy import Bullet
from sword import Sword
import sound

_PLAYER_DIR = os.path.join(os.path.dirname(__file__), 'images', 'player')
_SCALE      = 2   # 16×32 native → 32×64 display


def _load_anim(filename):
    tmx    = tilemap_mod.load(os.path.join(_PLAYER_DIR, filename))
    frames = tmx.get_frames(frame_tile_w=1)
    return [pygame.transform.scale(f, (f.get_width() * _SCALE,
                                       f.get_height() * _SCALE))
            for f in frames]


class Player:
    def __init__(self, x, y, speed = 200):
        self.x = x
        self.y = y
        self.max_hp = 100
        self.hp     = 100
        self.speed  = speed
        self.parry_active            = False
        self.parry_timer             = 0
        self.parry_window            = 0.15
        self.parry_cooldown          = 0
        self.parry_cooldown_duration = 2.0
        self.parry_dmg_mult          = 1.5   # damage multiplier applied to weakened enemies
        self.parry_speed_boost_dur   = 0.0   # seconds of speed boost after parry
        self.parry_speed_boost_timer = 0.0
        self.parry_heal_pct          = 0.0   # fraction of max_hp healed on parry
        self.parry_instakill         = False
        self.invulnerable_timer      = 0.0
        self.defense                 = 0
        self.facing_angle = 0.0
        self.rect  = pygame.Rect(x, y, 32, 32)
        self.coins = 0
        self.deflected_bullets = []
        self.sword = Sword(damage=20, reach=50)
        self._counter_swing = False
        self._parry_font = pygame.font.SysFont(None, 20)

        self._anims      = {'walk': _load_anim('Walk.tmx'), 'idle': _load_anim('Idle.tmx')}
        self._anim_state = 'idle'
        self._anim_frame = 0
        self._anim_timer = 0.0
        self._anim_fps   = 8
        self._moving     = False

    def handle_input(self, keys, dt, cam_x=0, cam_y=0):
        spd = self.speed * (1.5 if self.parry_speed_boost_timer > 0 else 1.0)
        if keys[pygame.K_w]:
            self.y -= spd * dt
        if keys[pygame.K_s]:
            self.y += spd * dt
        if keys[pygame.K_a]:
            self.x -= spd * dt
        if keys[pygame.K_d]:
            self.x += spd * dt
        self.rect.topleft = (int(self.x), int(self.y))
        self._moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]

        mx, my = pygame.mouse.get_pos()
        world_cx = self.x + 16
        world_cy = self.y + 16
        self.facing_angle = math.atan2((my + cam_y) - world_cy, (mx + cam_x) - world_cx)

    PARRY_FWD   = 18
    PARRY_RIGHT = 20
    PARRY_ANGLE_OFFSET = -math.pi / 3

    def get_parry_sword_hitbox(self):
        """Returns the sword's AABB during parry stance, or None when not parrying."""
        if not self.parry_active:
            return None
        right_angle  = self.facing_angle + math.pi / 2
        sword_angle  = self.facing_angle + self.PARRY_ANGLE_OFFSET
        hx = self.x + 16 + math.cos(self.facing_angle) * self.PARRY_FWD + math.cos(right_angle) * self.PARRY_RIGHT
        hy = self.y + 16 + math.sin(self.facing_angle) * self.PARRY_FWD + math.sin(right_angle) * self.PARRY_RIGHT
        return self.sword.get_parry_hitbox(hx, hy, sword_angle)

    def try_parry_bullet(self, bullet):
        if not self.parry_active or bullet.is_deflected:
            return False
        hitbox = self.get_parry_sword_hitbox()
        if hitbox is None or not hitbox.colliderect(bullet.rect):
            return False
        speed = math.hypot(bullet.vx, bullet.vy)
        pcx   = self.x + 16
        pcy   = self.y + 16
        dist  = math.hypot(bullet.x - pcx, bullet.y - pcy)
        bullet.alive = False   # destroy the incoming bullet
        new = Bullet(pcx + math.cos(self.facing_angle) * dist,
                     pcy + math.sin(self.facing_angle) * dist,
                     math.cos(self.facing_angle) * speed * 2,
                     math.sin(self.facing_angle) * speed * 2,
                     self.sword.damage * 3)
        new.is_deflected = True
        self.deflected_bullets.append(new)
        sound.play('parry_projectile')
        self._on_parry_success()
        return True

    def try_parry_dash(self, enemy):
        if not self.parry_active:
            return False
        is_dash = getattr(enemy, 'state', None) == 'dash'
        is_fall = getattr(enemy, 'desp_state', None) == 'impact'
        if not is_dash and not is_fall:
            return False
        hitbox = self.get_parry_sword_hitbox()
        if hitbox is None or not hitbox.colliderect(enemy.rect):
            return False
        if is_fall:
            if hasattr(enemy, 'parry_slam'):
                enemy.parry_slam()
            self.invulnerable_timer = 2.5
        else:
            enemy.stun(getattr(enemy, 'STUN_DURATION', 2.0), self.parry_dmg_mult)
            if self.parry_instakill and not getattr(enemy, 'is_boss', False):
                enemy.take_damage(enemy.hp)
        sound.play('parry_melee')
        self._on_parry_success()
        return True

    def _on_parry_success(self):
        self.parry_active   = False
        self.parry_timer    = 0
        self.parry_cooldown = 0
        self.sword.swing(self.facing_angle)
        self._counter_swing = True
        if self.parry_heal_pct > 0:
            self.hp = min(self.hp + int(self.max_hp * self.parry_heal_pct), self.max_hp)
        if self.parry_speed_boost_dur > 0:
            self.parry_speed_boost_timer = self.parry_speed_boost_dur

    def swing_sword(self):
        if self.parry_active:
            return
        if self._counter_swing:
            self._counter_swing = False
            self.sword.swing_active = False  # allow restart
        self.sword.swing(self.facing_angle)

    def perform_parry(self):
        if self.parry_cooldown > 0:
            return
        if self.sword.swing_active and not self._counter_swing:
            return
        self._counter_swing = False
        self.sword.swing_active = False
        self.parry_active = True
        self.parry_timer = self.parry_window
        self.parry_cooldown = self.parry_cooldown_duration

    def update(self, dt):
        if self.parry_active:
            self.parry_timer -= dt
            if self.parry_timer <= 0:
                self.parry_active = False
        if self.parry_cooldown > 0:
            self.parry_cooldown -= dt
        if self.parry_speed_boost_timer > 0:
            self.parry_speed_boost_timer -= dt
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
        self.sword.update(dt)

        state = 'walk' if self._moving else 'idle'
        if state != self._anim_state:
            self._anim_state = state
            self._anim_frame = 0
            self._anim_timer = 0.0
        self._anim_timer += dt
        if self._anim_timer >= 1.0 / self._anim_fps:
            self._anim_timer -= 1.0 / self._anim_fps
            frames = self._anims[self._anim_state]
            self._anim_frame = (self._anim_frame + 1) % len(frames)

    def draw(self, screen, cam_x=0, cam_y=0):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        frame = self._anims[self._anim_state][self._anim_frame]
        if abs(self.facing_angle) > math.pi / 2:
            frame = pygame.transform.flip(frame, True, False)
        fw, fh = frame.get_size()
        screen.blit(frame, (sx + 16 - fw // 2, sy + 32 - fh))

        cx = sx + 16
        cy = sy + 16
        length = 20
        end = (cx + math.cos(self.facing_angle) * length,
               cy + math.sin(self.facing_angle) * length)
        #pygame.draw.line(screen, (255, 255, 0), (cx, cy), end, 3)

        if self.parry_active:
            radius = 40
            arc_rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
            spread = math.radians(45)
            arc_start = -self.facing_angle - spread
            arc_end   = -self.facing_angle + spread
            #pygame.draw.arc(screen, (0, 100, 255), arc_rect, arc_start, arc_end, 3)

        if self.parry_active:
            right_angle = self.facing_angle + math.pi / 2
            hx = self.x + 16 + math.cos(self.facing_angle) * 18 + math.cos(right_angle) * 20
            hy = self.y + 16 + math.sin(self.facing_angle) * 18 + math.sin(right_angle) * 20
            self.sword.draw_at_angle(screen, hx, hy,
                                     cam_x, cam_y, self.facing_angle - math.pi / 3)
        else:
            self.sword.draw(screen, self.x + 16, self.y + 16, cam_x, cam_y)

        icon = self._parry_font.render("P", True, (100, 180, 255))
        icon.set_alpha(60 if self.parry_cooldown > 0 else 255)
        screen.blit(icon, (cx - icon.get_width() // 2, sy - 18))
