import random
from collections import deque
from room import Room, EVENT_WEIGHTS

MAP_ROWS = 8
MAP_COLS = 11
ROOMS_MIN = 8
ROOMS_MAX = 10

DR = [-1, 1, 0, 0]
DC = [0, 0, -1, 1]

def generate_map(is_boss_sublevel=True):
    target = random.randint(ROOMS_MIN, ROOMS_MAX)
    grid = [[None] * MAP_COLS for _ in range(MAP_ROWS)]

    # Start is pinned to the absolute bottom-center cell.
    # Because start_r == MAP_ROWS - 1, the boundary check (0 <= r+DR < MAP_ROWS)
    # already prevents any room from generating south of it.
    start_r = MAP_ROWS - 1
    start_c = MAP_COLS // 2

    stack = [(start_r, start_c)]
    placed = []

    while len(placed) < target and stack:
        r, c = stack.pop(random.randint(0, len(stack) - 1))

        if grid[r][c] is not None:
            continue

        neighbor_count = sum(
            1 for i in range(4)
            if 0 <= r + DR[i] < MAP_ROWS and 0 <= c + DC[i] < MAP_COLS
            and grid[r + DR[i]][c + DC[i]] is not None
        )

        # Always place the first room (start).
        # Place normally if only 1 neighbor (tree branch).
        # Occasionally allow 2 neighbors (30% chance) to create extra branches.
        can_place = (
            not placed
            or neighbor_count == 1
            or (neighbor_count == 2 and random.random() < 0.3)
        )

        if can_place:
            is_start = (r == start_r and c == start_c)
            room = Room(grid_x=c, grid_y=r, is_start=is_start)
            grid[r][c] = room
            placed.append(room)

            if is_start:
                # Start room only ever opens northward
                stack.append((r - 1, c))
            else:
                dirs = list(range(4))
                random.shuffle(dirs)
                for i in dirs:
                    nr, nc = r + DR[i], c + DC[i]
                    if 0 <= nr < MAP_ROWS and 0 <= nc < MAP_COLS and grid[nr][nc] is None:
                        stack.append((nr, nc))

    # Connect all adjacent placed rooms.
    # Start room is restricted to its north neighbour only.
    for room in placed:
        r, c = room.grid_y, room.grid_x
        for i in range(4):
            nr, nc = r + DR[i], c + DC[i]
            if room.is_start and not (nr == r - 1 and nc == c):
                continue
            if 0 <= nr < MAP_ROWS and 0 <= nc < MAP_COLS and grid[nr][nc] is not None:
                other = grid[nr][nc]
                if (other.grid_x, other.grid_y) not in room.connections:
                    room.connect(other)

    start_room = grid[start_r][start_c]

    # BFS from start to find farthest room → assign as boss
    dist = {start_room: 0}
    q = deque([start_room])
    while q:
        cur = q.popleft()
        for nx, ny in cur.connections:
            nb = grid[ny][nx]
            if nb not in dist:
                dist[nb] = dist[cur] + 1
                q.append(nb)

    exit_room = max((r for r in placed if not r.is_start), key=lambda r: dist.get(r, 0))
    if is_boss_sublevel:
        exit_room.is_boss    = True
        exit_room.event_type = 'boss'
    else:
        exit_room.event_type = 'exit'

    # Assign event types to remaining rooms, capping shop ≤ 2 and special ≤ 2
    regular = [r for r in placed if not r.is_start and r is not exit_room]
    random.shuffle(regular)
    shop_count    = 0
    special_count = 0
    item_count    = 0
    for room in regular:
        weights = dict(EVENT_WEIGHTS)
        if shop_count    >= 2: weights.pop('shop',    None)
        if special_count >= 2: weights.pop('special', None)
        if item_count    >= 2: weights.pop('item',    None)
        event = random.choices(list(weights), weights=weights.values(), k=1)[0]
        room.event_type = event
        if event == 'shop':    shop_count    += 1
        if event == 'special': special_count += 1
        if event == 'item':    item_count    += 1

    return placed, start_room, grid
