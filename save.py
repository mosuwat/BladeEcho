import os
import json
from constants import STEP_X, STEP_Y, ROOM_W, ROOM_H, WALL_T, DOOR_SIZE
from map_generator import MAP_ROWS, MAP_COLS
from room import Room
from enemy import RangedEnemy, MeleeEnemy
from world_objects import Coin
from player import Player
from world import finalize_map
from shop import Shop

SAVE_PATH = os.path.join(os.path.dirname(__file__), 'save.json')


def save_exists():
    return os.path.exists(SAVE_PATH)


def serialize_enemy(e):
    base = {'type': type(e).__name__, 'x': e.x, 'y': e.y,
            'hp': e.hp, 'floor_number': e.floor_number}
    if isinstance(e, MeleeEnemy):
        base.update({'state': e.state, 'dash_cd': e.dash_cd,
                     'stun_timer': e.stun_timer})
    elif isinstance(e, RangedEnemy):
        base['state'] = e.state
    return base


def write_save(player, rooms, floor_num, sublevel):
    room_data = []
    for room in rooms:
        room_data.append({
            'grid_x':      room.grid_x,
            'grid_y':      room.grid_y,
            'event_type':  room.event_type,
            'is_boss':     room.is_boss,
            'is_start':    room.is_start,
            'is_locked':   room.is_locked,
            'is_cleared':  room.is_cleared,
            'connections': [list(c) for c in room.connections],
            'enemies':     [serialize_enemy(e) for e in room.enemies],
            'floor_coins': [{'x': c.x, 'y': c.y} for c in room.floor_coins],
            'has_gate':    room.gate is not None,
        })
    data = {
        'player':    {
            'x': player.x, 'y': player.y,
            'hp': player.hp, 'max_hp': player.max_hp, 'coins': player.coins,
            'parry_window':          player.parry_window,
            'parry_dmg_mult':        player.parry_dmg_mult,
            'parry_speed_boost_dur': player.parry_speed_boost_dur,
            'parry_heal_pct':        player.parry_heal_pct,
            'parry_instakill':       player.parry_instakill,
            'sword_damage':          player.sword.damage,
            'sword_reach':           player.sword.reach,
            'sword_parry_pad':       player.sword.parry_pad,
            'sword_flame':           player.sword.flame,
            'sword_slow':            player.sword.slow,
            'sword_execute_pct':     player.sword.execute_pct,
        },
        'floor_num': floor_num,
        'sublevel':  sublevel,
        'rooms':     room_data,
    }
    with open(SAVE_PATH, 'w') as f:
        json.dump(data, f)


def read_save():
    with open(SAVE_PATH) as f:
        return json.load(f)


def load_game():
    """Return (rooms, start_room, grid, floor_num, sublevel, player,
               hallway_floors, hall_walls, all_walls)."""
    data  = read_save()
    grid  = [[None] * MAP_COLS for _ in range(MAP_ROWS)]
    rooms = []

    for rd in data['rooms']:
        room = Room(grid_x=rd['grid_x'], grid_y=rd['grid_y'],
                    event_type=rd['event_type'],
                    is_boss=rd['is_boss'], is_start=rd['is_start'])
        room.is_locked   = rd['is_locked']
        room.is_cleared  = rd['is_cleared']
        room.connections = {tuple(c) for c in rd['connections']}
        wx = room.grid_x * STEP_X
        wy = room.grid_y * STEP_Y
        room.setup_geometry(wx, wy, ROOM_W, ROOM_H, WALL_T, DOOR_SIZE)
        grid[rd['grid_y']][rd['grid_x']] = room
        rooms.append(room)

    for room, rd in zip(rooms, data['rooms']):
        for ed in rd['enemies']:
            if ed['type'] == 'RangedEnemy':
                e = RangedEnemy(ed['x'], ed['y'], ed['floor_number'])
                e.hp    = ed['hp']
                e.state = ed.get('state', 'chase')
            else:
                e = MeleeEnemy(ed['x'], ed['y'], ed['floor_number'])
                e.hp         = ed['hp']
                e.state      = ed.get('state', 'chase')
                e.dash_cd    = ed.get('dash_cd', 0.0)
                e.stun_timer = ed.get('stun_timer', 0.0)
            room.enemies.append(e)
        for cd in rd['floor_coins']:
            room.floor_coins.append(Coin(cd['x'], cd['y']))

    start_room = next(r for r in rooms if r.is_start)
    hallway_floors, hall_walls, all_walls = finalize_map(rooms)

    floor_num = data.get('floor_num', 1)
    sublevel  = data.get('sublevel',  1)
    for room, rd in zip(rooms, data['rooms']):
        if rd.get('has_gate'):
            room.place_gate()
        if room.event_type == 'shop':
            room.shop = Shop(floor_num)

    pd = data['player']
    player = Player(pd['x'], pd['y'], speed=300)
    player.hp     = pd['hp']
    player.max_hp = pd.get('max_hp', 100)
    player.coins  = pd['coins']
    player.parry_window          = pd.get('parry_window',          0.15)
    player.parry_dmg_mult        = pd.get('parry_dmg_mult',        1.5)
    player.parry_speed_boost_dur = pd.get('parry_speed_boost_dur', 0.0)
    player.parry_heal_pct        = pd.get('parry_heal_pct',        0.0)
    player.parry_instakill       = pd.get('parry_instakill',       False)
    player.sword.damage      = pd.get('sword_damage',      20)
    player.sword.reach       = pd.get('sword_reach',       70)
    player.sword.parry_pad   = pd.get('sword_parry_pad',   7)
    player.sword.flame       = pd.get('sword_flame',       False)
    player.sword.slow        = pd.get('sword_slow',        False)
    player.sword.execute_pct = pd.get('sword_execute_pct', 0.0)

    return rooms, start_room, grid, floor_num, sublevel, player, \
           hallway_floors, hall_walls, all_walls
