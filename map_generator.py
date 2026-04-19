import random

# Constants
MAP_SIZE_X = 7
MAP_SIZE_Y = 9
ROOMS_TARGET = random.randint(8, 10)

# Initialize map
game_map = [[False for _ in range(MAP_SIZE_Y)] for _ in range(MAP_SIZE_X)]
game_map[MAP_SIZE_X - 1][MAP_SIZE_Y // 2] = True

# Directions
dx = [-1, 1, 0, 0]
dy = [0, 0, -1, 1]

# Start in the middle
start_x, start_y = MAP_SIZE_X - 2, MAP_SIZE_Y // 2
stack = [(start_x, start_y)]
rooms_count = 0

while rooms_count < ROOMS_TARGET and stack:
    # Randomly picking from the list makes it more organic than just a Stack or Queue
    r, c = stack.pop(random.randint(0, len(stack) - 1))
    
    if game_map[r][c] or r == MAP_SIZE_X - 1:
        continue

    # Count existing neighbors to check for "clumping"
    neighbor_rooms = 0
    for i in range(4):
        nr, nc = r + dx[i], c + dy[i]
        if 0 <= nr < MAP_SIZE_X and 0 <= nc < MAP_SIZE_Y:
            if game_map[nr][nc]:
                neighbor_rooms += 1

    # Logic: Only place a room if it has 1 or fewer neighbors (prevents 2x2 blocks)
    # The first room (start) will have 0 neighbors.
    if neighbor_rooms <= 1 or (rooms_count == 0):
        game_map[r][c] = True
        rooms_count += 1

        # Add neighbors to the potential list
        directions = list(range(4))
        random.shuffle(directions) # Randomize direction priority
        
        for i in directions:
            nr, nc = r + dx[i], c + dy[i]
            if 0 <= nr < MAP_SIZE_X and 0 <= nc < MAP_SIZE_Y:
                if not game_map[nr][nc]:
                    stack.append((nr, nc))

# Final Print
print(f"Target: {ROOMS_TARGET} | Actual: {rooms_count}")
for row in game_map:
    print("".join(['.' if cell else 'X' for cell in row]))