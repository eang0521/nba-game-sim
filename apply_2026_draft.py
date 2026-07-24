"""
apply_2026_draft.py

1. Updates all 2026 rookies in the 2027 roster files with new model predictions.
2. Adds LeBron James (OVR=81, PHI) to all three roster files.

Run with: py apply_2026_draft.py
"""
import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FLAT_FILES = ['nba_rosters27_v2.json', 'nba_rosters27_final.json']
ALL_FILE   = 'nba_rosters_all.json'
ALL_YEAR   = '2027'

# LeBron's properly progressed 2026-27 stats (from nba_rosters27_base.json)
LEBRON = {
    'name': 'LeBron James',
    't_2pt': 26, 't_3pt': 17, 't_def': 20, 't_reb': 18,
}
LEBRON_TEAM = 'PHI'

# Load rookie predictions
with open('rookie_predictions_2026.json', encoding='utf-8') as f:
    predictions = json.load(f)

# Build name → stat dict
rookie_stats = {
    r['name']: {
        't_2pt': r['t_2pt'], 't_3pt': r['t_3pt'],
        't_def': r['t_def'], 't_reb': r['t_reb'],
    }
    for r in predictions
}

def update_roster(roster: dict) -> tuple[int, list]:
    """Update rookies in-place, return (count_updated, change_log)."""
    updated = 0
    log = []
    for team, players in roster.items():
        for p in players:
            name = p['name']
            if name in rookie_stats:
                new = rookie_stats[name]
                old_ovr = p['t_2pt'] + p['t_3pt'] + p['t_def'] + p['t_reb']
                new_ovr = new['t_2pt'] + new['t_3pt'] + new['t_def'] + new['t_reb']
                changed = any(p.get(k) != new[k] for k in new)
                if changed:
                    log.append(f'  {team} {name}: OVR {old_ovr} -> {new_ovr}  '
                                f'[{p["t_2pt"]}/{p["t_3pt"]}/{p["t_def"]}/{p["t_reb"]}]'
                                f' -> [{new["t_2pt"]}/{new["t_3pt"]}/{new["t_def"]}/{new["t_reb"]}]')
                    p.update(new)
                    updated += 1
    return updated, log

def add_lebron(roster: dict) -> bool:
    """Add LeBron to LEBRON_TEAM if not already there."""
    team_players = roster.get(LEBRON_TEAM, [])
    if any(p['name'] == LEBRON['name'] for p in team_players):
        print(f'  LeBron already on {LEBRON_TEAM} — skipping')
        return False
    team_players.append(dict(LEBRON))
    roster[LEBRON_TEAM] = team_players
    print(f'  Added LeBron James to {LEBRON_TEAM}  OVR={sum(LEBRON[k] for k in ["t_2pt","t_3pt","t_def","t_reb"])}')
    return True

# ── Flat files ─────────────────────────────────────────────────────────────
for fname in FLAT_FILES:
    print(f'\n{fname}')
    with open(fname, encoding='utf-8') as f:
        data = json.load(f)

    n, log = update_roster(data)
    for line in log:
        print(line)
    print(f'  {n} rookies updated')
    add_lebron(data)

    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'  Saved {fname}')

# ── nba_rosters_all.json ───────────────────────────────────────────────────
print(f'\n{ALL_FILE} [{ALL_YEAR}]')
with open(ALL_FILE, encoding='utf-8') as f:
    all_data = json.load(f)

roster_2027 = all_data.get(ALL_YEAR, {})
n, log = update_roster(roster_2027)
for line in log:
    print(line)
print(f'  {n} rookies updated')
add_lebron(roster_2027)

all_data[ALL_YEAR] = roster_2027
with open(ALL_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False)
print(f'  Saved {ALL_FILE}')

print('\nDone.')
