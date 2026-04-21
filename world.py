from constants import ROOM_W, ROOM_H, DOOR_SIZE, HALLWAY_LEN


def build_hallways(rooms, tmx_h, tmx_v):
    """Return (hallways, hall_walls).
    hallways  — list of (x, y, tmx, door_rooms) for drawing
                door_rooms: dict of layer_name → room whose lock state controls it
    hall_walls — collision rects from each TMX Walls layer
    """
    hallways, hall_walls = [], []
    seen = set()
    room_at = {(r.grid_x, r.grid_y): r for r in rooms}
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
                hx, hy = room.wx + ROOM_W, my - d
                hallways.append((hx, hy, tmx_h, {}))
                hall_walls += tmx_h.tile_rects('Walls', hx, hy, HALLWAY_LEN, DOOR_SIZE)
            elif ny == room.grid_y + 1 and nx == room.grid_x:
                seen.add(pair)
                hx, hy = mx - d, room.wy + ROOM_H
                other = room_at.get((nx, ny))
                door_rooms = {'DoorsTop': room, 'DoorsBottom': other}
                hallways.append((hx, hy, tmx_v, door_rooms))
                hall_walls += tmx_v.tile_rects('Walls', hx, hy, DOOR_SIZE, HALLWAY_LEN)
    return hallways, hall_walls


def finalize_map(rooms, tmx_h, tmx_v):
    hallways, hall_walls = build_hallways(rooms, tmx_h, tmx_v)
    all_walls = [w for r in rooms for w in r.walls] + hall_walls
    return hallways, hall_walls, all_walls


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
