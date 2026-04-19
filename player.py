import pygame

class Player:
    def __init__(self, x, y, speed = 200):
        self.x = x
        self.y = y
        self.hp = 100
        self.speed = speed  # pixels per second
        self.parry_active = False
        self.parry_timer = 0
        self.parry_window = 0.15  # 150ms window
        self.facing = 'U'
        self.rect = pygame.Rect(x, y, 32, 32)

    def handle_input(self, keys, dt):
        if keys[pygame.K_w]:
            self.y -= self.speed * dt
            self.facing = 'U'
        if keys[pygame.K_s]:
            self.y += self.speed * dt
            self.facing = 'D'
        if keys[pygame.K_a]:
            self.x -= self.speed * dt
            self.facing = 'L'
        if keys[pygame.K_d]:
            self.x += self.speed * dt
            self.facing = 'R'
        self.rect.topleft = (self.x, self.y)

    def perform_parry(self):
        self.parry_active = True
        self.parry_timer = self.parry_window

    def update(self, dt):
        if self.parry_active:
            self.parry_timer -= dt
            if self.parry_timer <= 0:
                self.parry_active = False

    def draw(self, screen):
        pygame.draw.rect(screen, (0, 200, 0), self.rect)

        # Draw facing indicator
        cx, cy = self.rect.center
        length = 20

        if self.facing == 'U':
            end = (cx, cy - length)
        elif self.facing == 'D':
            end = (cx, cy + length)
        elif self.facing == 'L':
            end = (cx - length, cy)
        elif self.facing == 'R':
            end = (cx + length, cy)
        
        pygame.draw.line(screen, (255, 255, 0), (cx, cy), end, 3)

        # Parry arc
        if self.parry_active:
            import math
            radius = 40
            arc_rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)

            if self.facing == 'U':
                start = math.radians(45)
                end = math.radians(135)
            elif self.facing == 'D':
                start = math.radians(225)
                end = math.radians(315)
            elif self.facing == 'L':
                start = math.radians(135)
                end = math.radians(225)
            elif self.facing == 'R':
                start = math.radians(-45)
                end = math.radians(45)

            pygame.draw.arc(screen, (0, 100, 255), arc_rect, start, end, 3)