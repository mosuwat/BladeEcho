import pygame
from map_generator import MAP_COLS, MAP_ROWS

COLORS = {
    'start':   (50,  200,  50),
    'monster': (180,  60,  60),
    'boss':    (220, 100,  20),
    'shop':    (200, 180,  50),
    'special': (150,  80, 200),
    'item':    ( 60, 120, 200),
    'exit':    (  0, 180, 220),
}

CELL = 18
GAP  = 3
STEP = CELL + GAP


def draw(screen, rooms, cur_room, font):
    sw, sh = screen.get_size()
    ox = (sw - MAP_COLS * STEP) // 2
    oy = (sh - MAP_ROWS * STEP) // 2

    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    room_dict = {(r.grid_x, r.grid_y): r for r in rooms}

    def adjacent_visited(room):
        return any(
            room_dict.get((nx, ny)) and room_dict[(nx, ny)].visited
            for nx, ny in room.connections
        )

    for room in rooms:
        visited    = room.visited
        discovered = not visited and adjacent_visited(room)
        if not visited and not discovered:
            continue

        rx = ox + room.grid_x * STEP
        ry = oy + room.grid_y * STEP
        base  = COLORS.get(room.event_type, (80, 80, 80))
        color = base if visited else tuple(int(c * 0.4) for c in base)

        for nx, ny in room.connections:
            nb = room_dict.get((nx, ny))
            if nb and (nb.visited or adjacent_visited(nb)):
                pygame.draw.line(screen, (60, 60, 80),
                                 (rx + CELL // 2, ry + CELL // 2),
                                 (ox + nx * STEP + CELL // 2,
                                  oy + ny * STEP + CELL // 2), 2)

        pygame.draw.rect(screen, color, (rx, ry, CELL, CELL))

        if room is cur_room:
            pygame.draw.rect(screen, (255, 255, 255), (rx, ry, CELL, CELL), 2)
            pygame.draw.circle(screen, (255, 255, 255),
                               (rx + CELL // 2, ry + CELL // 2), 3)

    title = font.render("MAP  (M to close)", True, (180, 180, 200))
    screen.blit(title, title.get_rect(centerx=sw // 2, y=oy - 28))
