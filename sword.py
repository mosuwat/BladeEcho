import pygame
import math
import os
import tilemap as tilemap_mod

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
_SWORD_TMX  = os.path.join(BASE_DIR, 'images', 'weapon', 'sword.tmx')
_SCALE      = 2
_GRIP_DIST  = 8   # pixels from player center to sword grip (fixed)


class Sword:
    SWING_DURATION = 0.22   # seconds for one full swing
    SWING_COOLDOWN = 0.11   # extra dead time after swing before next swing (total gap = 0.33s)
    SWING_ARC      = math.radians(110)  # total arc swept

    def __init__(self, damage=20, reach=70):
        self.damage      = damage
        self.reach       = reach
        self._base_reach = reach
        self.scale       = 1.0
        self.flame       = False  # burn on hit
        self.slow        = False  # slow on hit
        self.execute_pct = 0.0    # instant-kill threshold (fraction of max_hp)

        self.swing_active      = False
        self.swing_timer       = 0.0
        self.swing_cd          = 0.0
        self.swing_start_angle = 0.0
        self.hit_this_swing    = set()   # enemy ids already hit in this swing

        frame = tilemap_mod.load(_SWORD_TMX).get_frames(frame_tile_w=1)[0]
        scaled = pygame.transform.scale(frame, (frame.get_width() * _SCALE,
                                                frame.get_height() * _SCALE))
        self.img_base = pygame.transform.flip(pygame.transform.rotate(scaled, 90), True, True)
        self.image    = self.img_base

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def swing(self, facing_angle):
        """Start a swing beginning half-arc behind the facing direction."""
        if self.swing_active or self.swing_cd > 0:
            return
        self.swing_active      = True
        self.swing_timer       = self.SWING_DURATION
        self.swing_start_angle = facing_angle - self.SWING_ARC / 2
        self.hit_this_swing.clear()

    def upgrade(self, damage_bonus=5, reach_bonus=0):
        self.damage += damage_bonus
        if reach_bonus:
            self.scale += 0.05
            self.reach  = int(self._base_reach * self.scale)
            w = int(self.img_base.get_width()  * self.scale)
            h = int(self.img_base.get_height() * self.scale)
            self.image = pygame.transform.scale(self.img_base, (w, h))

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt):
        if self.swing_active:
            self.swing_timer -= dt
            if self.swing_timer <= 0:
                self.swing_active = False
                self.swing_cd = self.SWING_COOLDOWN
        elif self.swing_cd > 0:
            self.swing_cd -= dt

    # ------------------------------------------------------------------
    # Hitbox
    # ------------------------------------------------------------------

    def current_angle(self):
        if not self.swing_active:
            return None
        progress = 1.0 - (self.swing_timer / self.SWING_DURATION)
        return self.swing_start_angle + self.SWING_ARC * progress

    def get_parry_hitbox(self, cx, cy, angle):
        """AABB covering the sword blade at a fixed angle (parry stance).
        (cx, cy) is the visual center of the sword image."""
        half  = self.reach / 2
        tip_x = cx + math.cos(angle) * half
        tip_y = cy + math.sin(angle) * half
        end_x = cx - math.cos(angle) * half
        end_y = cy - math.sin(angle) * half
        pad   = int(7 * self.scale)
        left  = min(tip_x, end_x) - pad
        top   = min(tip_y, end_y) - pad
        right = max(tip_x, end_x) + pad
        bot   = max(tip_y, end_y) + pad
        return pygame.Rect(left, top, right - left, bot - top)

    def draw_parry_centered(self, screen, cx, cy, cam_x, cam_y, angle):
        """Draw sword with its image center at (cx, cy)."""
        rotated = pygame.transform.rotate(self.image, -math.degrees(angle))
        screen.blit(rotated, rotated.get_rect(center=(cx - cam_x, cy - cam_y)))

    def get_hitbox(self, cx, cy):
        """Rect centred on the sword tip during a swing. None when not swinging."""
        angle = self.current_angle()
        if angle is None:
            return None
        tip_x = cx + math.cos(angle) * self.reach
        tip_y = cy + math.sin(angle) * self.reach
        size  = 24
        return pygame.Rect(tip_x - size // 2, tip_y - size // 2, size, size)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, cx, cy, cam_x, cam_y):
        """Draw sword at its current swing angle. No-op when not swinging."""
        angle = self.current_angle()
        if angle is None:
            return
        self._blit_at_angle(screen, cx, cy, cam_x, cam_y, angle)

    def draw_at_angle(self, screen, cx, cy, cam_x, cam_y, angle):
        """Draw sword held at a fixed angle (e.g. parry stance)."""
        self._blit_at_angle(screen, cx, cy, cam_x, cam_y, angle)

    def _blit_at_angle(self, screen, cx, cy, cam_x, cam_y, angle):
        rotated    = pygame.transform.rotate(self.image, -math.degrees(angle))
        sword_len  = max(self.image.get_width(), self.image.get_height())
        center_dist = _GRIP_DIST + sword_len // 2
        center_x   = (cx - cam_x) + math.cos(angle) * center_dist
        center_y   = (cy - cam_y) + math.sin(angle) * center_dist
        screen.blit(rotated, rotated.get_rect(center=(center_x, center_y)))
