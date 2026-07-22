"""
make_2027_rosters.py

Step 1: Apply age-based progression to 2025-26 ratings to produce
        tentative 2026-27 base ratings (before any player movement).

Age→OVR delta table (age during 2025-26 season):
  18→+6  19→+4  20→+3  21→+2  22→+1  23→0
  24→-1  25→-1  26→-2  27→-2  28→-3  29→-4  30→-4
  31→-5  32→-5  33→-6  34→-6  35→-7  36→-7  37→-8
  38→-8  39→-9  40→-9  41→-10  42→-10  43→-11

Distribution rule (sort stats descending, abs_delta = |delta|):
  base  = abs_delta // 4
  extra = abs_delta % 4
  top `extra` stats change by sign*(base+1), rest by sign*base
"""

import io, sys, json, re, unicodedata
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Config ────────────────────────────────────────────────────────────────
ROSTERS_JSON = 'nba_rosters_all.json'
STATS_CSV    = 'bbref_stats.csv'
OUTPUT_JSON  = 'nba_rosters27_base.json'

AGE_DELTA = {
    18:  6, 19:  4, 20:  3, 21:  2, 22:  1, 23:  0,
    24: -1, 25: -1, 26: -2, 27: -2, 28: -3, 29: -4, 30: -4,
    31: -5, 32: -5, 33: -6, 34: -6, 35: -7, 36: -7, 37: -8,
    38: -8, 39: -9, 40: -9, 41: -10, 42: -10, 43: -11,
}

STAT_KEYS = ['t_2pt', 't_3pt', 't_def', 't_reb']

# ── Helpers ───────────────────────────────────────────────────────────────
def norm(name: str) -> str:
    n = unicodedata.normalize('NFD', str(name)).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()

def fix_enc(s: str) -> str:
    """Reverse double-encoding: UTF-8 bytes misread as Latin-1."""
    try:
        return s.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

def apply_progression(player: dict, delta: int) -> dict:
    stats = {k: player[k] for k in STAT_KEYS}
    if delta == 0:
        return dict(stats)
    sign      = 1 if delta > 0 else -1
    abs_delta = abs(delta)
    base      = abs_delta // 4
    extra     = abs_delta % 4
    # Sort by current value descending so largest stats absorb most change
    ordered   = sorted(STAT_KEYS, key=lambda k: stats[k], reverse=True)
    new_stats = {}
    for i, k in enumerate(ordered):
        change        = sign * (base + 1) if i < extra else sign * base
        new_stats[k]  = max(0, stats[k] + change)
    return new_stats

# ── Load data ─────────────────────────────────────────────────────────────
print('Loading data…')
with open(ROSTERS_JSON, encoding='utf-8') as f:
    all_data = json.load(f)

rosters_2026 = all_data['2026']

df = pd.read_csv(STATS_CSV, encoding='utf-8-sig')
df26 = df[df['Year'] == 2026].copy()
df26['Age'] = pd.to_numeric(df26['Age'], errors='coerce')

# Build normalised-name → age lookup (apply fix_enc to CSV names)
age_lookup: dict[str, int] = {}
for _, row in df26.iterrows():
    name = fix_enc(str(row['Player']))
    age  = row['Age']
    if pd.notna(age):
        age_lookup[norm(name)] = int(age)

print(f'  {len(age_lookup)} players in 2025-26 age lookup')

# ── Apply progression ─────────────────────────────────────────────────────
rosters_2027: dict[str, list] = {}
no_age_found: list[tuple[str,str]] = []
player_log: list[dict] = []  # for reporting

for team, players in rosters_2026.items():
    new_players = []
    for p in players:
        name = p['name']
        if name.startswith('[Filler'):
            continue

        nname = norm(name)
        age   = age_lookup.get(nname)

        # Fallback: try fix_enc on the stored name
        if age is None:
            age = age_lookup.get(norm(fix_enc(name)))

        if age is None:
            no_age_found.append((name, team))
            delta = 0
        else:
            delta = AGE_DELTA.get(age, (-11 if age > 43 else 0))

        new_s = apply_progression(p, delta)
        ovr_before = sum(p[k]     for k in STAT_KEYS)
        ovr_after  = sum(new_s[k] for k in STAT_KEYS)
        player_log.append({
            'team': team, 'name': name, 'age': age, 'delta': delta,
            'ovr_before': ovr_before, 'ovr_after': ovr_after,
        })
        new_players.append({
            'name':  name,
            't_2pt': new_s['t_2pt'],
            't_3pt': new_s['t_3pt'],
            't_def': new_s['t_def'],
            't_reb': new_s['t_reb'],
        })
    rosters_2027[team] = new_players

# ── Save ──────────────────────────────────────────────────────────────────
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(rosters_2027, f, ensure_ascii=False, indent=2)

print(f'\nSaved base 2026-27 ratings → {OUTPUT_JSON}')

# ── Report ────────────────────────────────────────────────────────────────
print(f'\n{"="*60}')
print('TOP 20 PLAYERS BY 2026-27 OVR')
print(f'{"="*60}')
top = sorted(player_log, key=lambda x: x['ovr_after'], reverse=True)[:20]
for r in top:
    arrow = f"+{r['delta']}" if r['delta'] >= 0 else str(r['delta'])
    print(f"  {r['name']:<30} {r['team']:3}  age {r['age'] or '?':2}  "
          f"{r['ovr_before']} → {r['ovr_after']} ({arrow})")

print(f'\n{"="*60}')
print('BIGGEST FALLERS (delta ≤ -5)')
print(f'{"="*60}')
fallers = sorted([r for r in player_log if r['delta'] <= -5],
                 key=lambda x: x['ovr_before'], reverse=True)
for r in fallers[:30]:
    print(f"  {r['name']:<30} {r['team']:3}  age {r['age'] or '?':2}  "
          f"{r['ovr_before']} → {r['ovr_after']}  (delta {r['delta']})")

if no_age_found:
    print(f'\nWARNING: {len(no_age_found)} players with no age data (delta=0 used):')
    for name, team in no_age_found:
        print(f'  {team}: {name}')

print('\nDone.')
