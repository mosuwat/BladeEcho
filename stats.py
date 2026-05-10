import csv
import os
import time

CSV_PATH = os.path.join(os.path.dirname(__file__), 'stats.csv')

_FIELDNAMES = [
    'run_number', 'survived_time', 'cleared',
    'parry_streak', 'missed_parries',
    'damage_dealt', 'enemies_killed',
    'money_healing', 'money_sword', 'money_parry', 'money_other',
    'parries_floor1', 'parries_floor2', 'parries_floor3',
    'misses_floor1',  'misses_floor2',  'misses_floor3',
]


class StatsRecorder:
    def __init__(self):
        self._run_data = {}
        self._run_start = 0.0
        self._streak = 0
        self._floor = 1

    @property
    def active(self):
        return bool(self._run_data)

    # ── Run lifecycle ──────────────────────────────────────────────────────────

    def start_run(self):
        self._run_start = time.time()
        self._streak = 0
        self._floor = 1
        self._run_data = {
            'run_number':     self._next_run_number(),
            'survived_time':  0.0,
            'cleared':        False,
            'parry_streak':   0,
            'missed_parries': 0,
            'damage_dealt':   0.0,
            'enemies_killed': 0,
            'money_healing':  0,
            'money_sword':    0,
            'money_parry':    0,
            'money_other':    0,
            'parries_floor1': 0,
            'parries_floor2': 0,
            'parries_floor3': 0,
            'misses_floor1':  0,
            'misses_floor2':  0,
            'misses_floor3':  0,
        }

    def set_floor(self, floor_num):
        self._floor = max(1, min(floor_num, 3))

    def end_run(self, cleared=False):
        if not self._run_data:
            return
        self._run_data['survived_time'] = round(time.time() - self._run_start, 2)
        self._run_data['cleared'] = cleared
        self._write_row(self._run_data)
        self._run_data = {}

    # ── Event loggers ──────────────────────────────────────────────────────────

    def log_parry_success(self):
        if not self._run_data:
            return
        self._streak += 1
        d = self._run_data
        if self._streak > d['parry_streak']:
            d['parry_streak'] = self._streak
        d[f'parries_floor{self._floor}'] += 1

    def log_parry_miss(self):
        if not self._run_data:
            return
        self._streak = 0
        self._run_data['missed_parries'] += 1
        self._run_data[f'misses_floor{self._floor}'] += 1

    def log_damage(self, amount):
        if self._run_data:
            self._run_data['damage_dealt'] += amount

    def log_kill(self):
        if self._run_data:
            self._run_data['enemies_killed'] += 1

    def log_purchase(self, category, amount):
        if not self._run_data:
            return
        key = f'money_{category}'
        if key in self._run_data:
            self._run_data[key] += amount

    # ── CSV helpers ────────────────────────────────────────────────────────────

    def _next_run_number(self):
        if not os.path.exists(CSV_PATH):
            return 1
        with open(CSV_PATH, 'r', newline='') as f:
            rows = list(csv.DictReader(f))
        return (int(rows[-1]['run_number']) + 1) if rows else 1

    def _write_row(self, data):
        exists = os.path.exists(CSV_PATH)
        with open(CSV_PATH, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
            if not exists:
                writer.writeheader()
            writer.writerow({k: data.get(k, '') for k in _FIELDNAMES})

    # ── Chart data for pygame rendering ────────────────────────────────────────

    def get_chart_data(self):
        """Return a dict of processed run data ready for draw_stats_screen()."""
        if not os.path.exists(CSV_PATH):
            return {'n_runs': 0}
        rows = []
        with open(CSV_PATH, newline='') as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return {'n_runs': 0}

        def _ints(key):
            return [int(float(r.get(key, 0) or 0)) for r in rows]

        def _floats(key):
            return [float(r.get(key, 0) or 0) for r in rows]

        run_nums = _ints('run_number')
        survived = _floats('survived_time')
        damage   = _floats('damage_dealt')
        kills    = _ints('enemies_killed')
        p_totals = [sum(_ints(f'parries_floor{i}')) for i in range(1, 4)]
        m_totals = [sum(_ints(f'misses_floor{i}'))  for i in range(1, 4)]
        money    = {k: sum(_ints(f'money_{k}'))
                    for k in ('healing', 'sword', 'parry', 'other')}
        n      = len(rows)
        clears = sum(1 for r in rows
                     if str(r.get('cleared', '')).lower() == 'true')
        return {
            'n_runs':      n,
            'n_clears':    clears,
            'clear_pct':   round(clears / n * 100, 1) if n else 0.0,
            'run_nums':    run_nums,
            'survived':    survived,
            'damage':      damage,
            'kills':       kills,
            'p_totals':    p_totals,
            'm_totals':    m_totals,
            'money_by_cat': money,
            'best_time':   max(survived) if survived else 0,
            'avg_time':    sum(survived) / n if n else 0,
            'best_damage': max(damage)   if damage  else 0,
            'avg_damage':  sum(damage)   / n if n else 0,
            'best_kills':  max(kills)    if kills   else 0,
            'avg_kills':   sum(kills)    / n if n else 0,
        }


recorder = StatsRecorder()
