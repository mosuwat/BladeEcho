import os

_cfg = {}
_path = os.path.join(os.path.dirname(__file__), 'constants.txt')
with open(_path) as _f:
    for _line in _f:
        _line = _line.strip()
        if not _line or '=' not in _line:
            continue
        _k, _v = _line.split('=', 1)
        _cfg[_k.strip()] = _v.strip()

def _int(k):  return int(_cfg[k])
def _rgb(k):  return tuple(int(x) for x in _cfg[k].split(','))

SCREEN_W    = _int('SCREEN_W')
SCREEN_H    = _int('SCREEN_H')
ROOM_W      = _int('ROOM_W')
ROOM_H      = _int('ROOM_H')
HALLWAY_LEN = _int('HALLWAY_LEN')
WALL_T      = _int('WALL_T')
DOOR_SIZE   = _int('DOOR_SIZE')
BG_COLOR    = _rgb('BG_COLOR')
FPS         = _int('FPS')

STEP_X = ROOM_W + HALLWAY_LEN
STEP_Y = ROOM_H + HALLWAY_LEN
