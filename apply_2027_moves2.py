"""
apply_2027_moves2.py

Apply 2027 offseason moves (round 2):
  - DeMar DeRozan   SAC -> DEN
  - Klay Thompson   DAL -> MIA
  - Peyton Watson   DEN -> CLE
  - Max Strus       CLE -> LAL
  - Dennis Schroder CLE -> CHO
  - Tre Mann        CHO -> WAS (was in extras)

For every affected team, merge main + extras pool, sort by OVR desc,
keep top 15 in main, put the rest back in extras.

Updates: nba_rosters27_final.json, nba_rosters27_extras.json,
         nba_rosters_all.json['2027']
"""
import io, sys, json, re, unicodedata

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAT_KEYS = ['t_2pt', 't_3pt', 't_def', 't_reb']
MAIN_FILE = 'nba_rosters27_final.json'
EXTRAS_FILE = 'nba_rosters27_extras.json'
ALL_FILE = 'nba_rosters_all.json'
ALL_YEAR = '2027'
ROSTER_SIZE = 15

def norm(s):
    n = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()

def ovr(p):
    return p['t_2pt'] + p['t_3pt'] + p['t_def'] + p['t_reb']

with open(MAIN_FILE, encoding='utf-8') as f:
    main = json.load(f)
with open(EXTRAS_FILE, encoding='utf-8') as f:
    extras = json.load(f)

ALL_TEAMS = sorted(main.keys())

def find_and_remove(name, preferred=None):
    n = norm(name)
    order = ([preferred] + [t for t in ALL_TEAMS if t != preferred]
             if preferred else list(ALL_TEAMS))
    for team in order:
        for i, p in enumerate(main.get(team, [])):
            if norm(p['name']) == n:
                return main[team].pop(i), team, 'main'
        for i, p in enumerate(extras.get(team, [])):
            if norm(p['name']) == n:
                return extras[team].pop(i), team, 'extras'
    return None, None, None

def move(name, frm, to):
    p, actual_team, actual_pool = find_and_remove(name, frm)
    if p is None:
        print(f'  WARNING: {name} NOT FOUND')
        return
    main.setdefault(to, []).append(p)
    print(f'  {name}: {actual_team} ({actual_pool}) -> {to}')

print('=== MOVES ===')
move('DeMar DeRozan', 'SAC', 'DEN')
move('Klay Thompson', 'DAL', 'MIA')
move('Peyton Watson', 'DEN', 'CLE')
move('Max Strus', 'CLE', 'LAL')
move('Dennis Schröder', 'CLE', 'CHO')
move('Tre Mann', 'CHO', 'WAS')

affected = {'SAC', 'DEN', 'DAL', 'MIA', 'CLE', 'LAL', 'CHO', 'WAS'}

print('\n=== REBALANCING (top 15 to main, rest to extras) ===')
for team in sorted(affected):
    pool = main.get(team, []) + extras.get(team, [])
    # de-dupe by name just in case
    seen = set()
    dedup = []
    for p in pool:
        if p['name'] not in seen:
            dedup.append(p)
            seen.add(p['name'])
    dedup.sort(key=ovr, reverse=True)
    new_main = dedup[:ROSTER_SIZE]
    new_extras = dedup[ROSTER_SIZE:]
    main[team] = new_main
    if new_extras:
        extras[team] = new_extras
    elif team in extras:
        del extras[team]
    print(f'  {team}: main={len(new_main)} extras={len(new_extras)}')

# Clean empty extras teams
extras = {t: p for t, p in extras.items() if p}

with open(MAIN_FILE, 'w', encoding='utf-8') as f:
    json.dump(main, f, indent=2, ensure_ascii=False)
print(f'\nSaved {MAIN_FILE}')

with open(EXTRAS_FILE, 'w', encoding='utf-8') as f:
    json.dump(extras, f, indent=2, ensure_ascii=False)
print(f'Saved {EXTRAS_FILE}')

with open(ALL_FILE, encoding='utf-8') as f:
    all_data = json.load(f)
all_data[ALL_YEAR] = main
with open(ALL_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False)
print(f'Saved {ALL_FILE} [{ALL_YEAR}]')

print('\n=== FINAL ROSTER CHECK ===')
bad = [(t, len(p)) for t, p in main.items() if len(p) != ROSTER_SIZE]
if bad:
    print(f'  WARNING: teams not at {ROSTER_SIZE}: {bad}')
else:
    print(f'  All {len(main)} teams at exactly {ROSTER_SIZE} players')

print('\nDone.')
