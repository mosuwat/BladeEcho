import pygame
from constants import ROOM_W, ROOM_H, HALLWAY_LEN, WALL_T, DOOR_SIZE


def build_hallways(rooms):
    floors, walls = [], []
    seen = set()
    for room in rooms:
        mx = room.wx + ROOM_W // 2
        my = room.wy + ROOM_H // 2
        d  = DOOR_SIZE // 2
        for nx, ny in room.connections:
            pair = tuple(sorted([(room.grid_x, room.grid_y), (nx, ny)]))
            if pair in seen:
                continue
            if nx == room.grid_x + 1 and ny == room.grid_y:
                seen.add(pair)
                hx = room.wx + ROOM_W
                floors.append(pygame.Rect(hx, my - d, HALLWAY_LEN, DOOR_SIZE))
                walls += [pygame.Rect(hx, my - d - WALL_T, HALLWAY_LEN, WALL_T),
                          pygame.Rect(hx, my + d,           HALLWAY_LEN, WALL_T)]
            elif ny == room.grid_y + 1 and nx == room.grid_x:
                seen.add(pair)
                hy = room.wy + ROOM_H
                floors.append(pygame.Rect(mx - d, hy, DOOR_SIZE, HALLWAY_LEN))
                walls += [pygame.Rect(mx - d - WALL_T, hy, WALL_T, HALLWAY_LEN),
                          pygame.Rect(mx + d,           hy, WALL_T, HALLWAY_LEN)]
    return floors, walls


def finalize_map(rooms):
    hallway_floors, hall_walls = build_hallways(rooms)
    all_walls = [w for r in rooms for w in r.walls] + hall_walls
    return hallway_floors, hall_walls, all_walls


def get_camera(player, screen_w, screen_h):
    return player.x + 16 - screen_w // 2, player.y + 16 - screen_h // 2


def current_room(player, rooms):
    px, py = player.x + 16, player.y + 16
    for room in rooms:
        if room.wx <= px < room.wx + ROOM_W and room.wy <= py < room.wy + ROOM_H:
            return room
    return None


def resolve_walls(player, walls):
    for wall in walls:
        if not player.rect.colliderect(wall):
            continue
        ol  = player.rect.right  - wall.left
        or_ = wall.right  - player.rect.left
        ot  = player.rect.bottom - wall.top
        ob  = wall.bottom - player.rect.top
        if min(ol, or_) < min(ot, ob):
            player.x -= ol if ol < or_ else -or_
        else:
            player.y -= ot if ot < ob else -ob
        player.rect.topleft = (int(player.x), int(player.y))
