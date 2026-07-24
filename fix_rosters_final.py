"""
fix_rosters_final.py

1. Fetches team assignments for all 60 picks in the 2026 NBA draft.
2. Updates every 2026 rookie's stats in nba_rosters27_v2.json,
   nba_rosters27_final.json, nba_rosters_all.json, and nba_rosters27_extras.json
   with predictions from rookie_predictions_2026.json.
3. Adds any rookies not yet in any file to their drafting team's extras.
4. For every team, merges main + extras, sorts by OVR desc, keeps top 15
   in the main roster and puts the rest back in extras.
5. Saves all four files and reports changes.

Run with: py fix_rosters_final.py
"""
import io, sys, json, time, re
import requests
from bs4 import BeautifulSoup, Comment
from io import StringIO
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FLAT_FILES   = ['nba_rosters27_v2.json', 'nba_rosters27_final.json']
ALL_FILE     = 'nba_rosters_all.json'
ALL_YEAR     = '2027'
EXTRAS_FILE  = 'nba_rosters27_extras.json'
PREDS_FILE   = 'rookie_predictions_2026.json'
DRAFT_CACHE  = 'draft_links_cache.json'
ROSTER_SIZE  = 15
DELAY        = 4
HEADERS      = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}
BASE = 'https://www.basketball-reference.com'

# ── Load predictions ──────────────────────────────────────────────────────────
with open(PREDS_FILE, encoding='utf-8') as f:
    preds = json.load(f)

rookie_stats = {
    r['name']: {'t_2pt': r['t_2pt'], 't_3pt': r['t_3pt'],
                't_def': r['t_def'], 't_reb': r['t_reb']}
    for r in preds
}
rookie_ovr = {
    r['name']: r['t_2pt'] + r['t_3pt'] + r['t_def'] + r['t_reb']
    for r in preds
}
all_rookie_names = set(rookie_stats.keys())

# ── Fetch 2026 draft team assignments ────────────────────────────────────────
print('Fetching 2026 draft team assignments from BBRef...')
time.sleep(DELAY)
draft_url = f'{BASE}/draft/NBA_2026.html'
r = requests.get(draft_url, headers=HEADERS, timeout=30)
r.raise_for_status()
soup = BeautifulSoup(r.text, 'html.parser')

# Table may be in a comment
table = soup.find('table', id='stats')
if table is None:
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        cs = BeautifulSoup(comment, 'html.parser')
        table = cs.find('table', id='stats')
        if table:
            break

# Build pick → (player_name, team_abbr) mapping
pick_team: dict[str, str] = {}   # player_name → team abbr
if table:
    for row in table.find_all('tr'):
        pk_td   = row.find('td', {'data-stat': 'pick_overall'})
        pl_td   = row.find('td', {'data-stat': 'player'})
        tm_td   = row.find('td', {'data-stat': 'team_id'})
        if pk_td and pl_td and tm_td:
            name = pl_td.get_text(strip=True)
            team = tm_td.get_text(strip=True)
            if name and team:
                pick_team[name] = team
    print(f'  {len(pick_team)} picks with team assignments')
else:
    print('  WARNING: draft table not found; team assignments unavailable')

# Normalise team abbreviations to match our roster keys
TEAM_NORM = {
    'PHO': 'PHO', 'PHX': 'PHO',
    'BRK': 'BRK', 'BKN': 'BRK',
    'NOP': 'NOP', 'NOH': 'NOP',
    'CHA': 'CHO', 'CHO': 'CHO',
    'SAS': 'SAS',
    'GSW': 'GSW', 'GOS': 'GSW',
    'UTA': 'UTA',
    'MEM': 'MEM',
    'ORL': 'ORL',
    'WAS': 'WAS',
    'CHI': 'CHI',
    'DET': 'DET',
}
def norm_team(t: str) -> str:
    return TEAM_NORM.get(t, t)

# Build rookie → team map from draft page
rookie_team: dict[str, str] = {
    name: norm_team(team)
    for name, team in pick_team.items()
    if name in all_rookie_names
}
print(f'  Matched {len(rookie_team)} rookies to teams')

# ── Helper: ovr of a player dict ─────────────────────────────────────────────
def ovr(p: dict) -> int:
    return p['t_2pt'] + p['t_3pt'] + p['t_def'] + p['t_reb']

# ── Helper: apply rookie stats update to one player dict ─────────────────────
def update_player(p: dict) -> dict:
    name = p['name']
    if name in rookie_stats:
        new = rookie_stats[name]
        p = dict(p)
        p.update(new)
    return p

# ── Main transformation ───────────────────────────────────────────────────────
def process_rosters(main: dict, extras: dict) -> tuple[dict, dict, list]:
    """
    Given main roster dict and extras dict (both {team: [players]}):
    1. Update all rookie stats in both pools.
    2. Add missing rookies to their team's pool (extras side).
    3. For each team, sort combined pool by OVR desc, keep top 15 in main.
    Returns (new_main, new_extras, change_log).
    """
    log = []

    # Collect all teams from both sources
    all_teams = set(list(main.keys()) + list(extras.keys()) + list(rookie_team.values()))

    # Build per-team pools: {team: [all players]}
    pools: dict[str, list] = {}
    for team in all_teams:
        pool = []
        seen = set()
        for p in main.get(team, []):
            p = update_player(p)
            pool.append(p)
            seen.add(p['name'])
        for p in extras.get(team, []):
            p = update_player(p)
            if p['name'] not in seen:
                pool.append(p)
                seen.add(p['name'])
        pools[team] = pool

    # Add missing rookies to their team's pool
    in_any = {p['name'] for pool in pools.values() for p in pool}
    for name, team in rookie_team.items():
        if name not in in_any:
            stats = dict(rookie_stats[name])
            stats['name'] = name
            pools.setdefault(team, []).append(stats)
            log.append(f'  ADDED {name} (OVR={rookie_ovr[name]}) to {team} extras')

    # Sort each team's pool and split at 15
    new_main:   dict[str, list] = {}
    new_extras: dict[str, list] = {}
    for team, pool in pools.items():
        pool.sort(key=lambda p: ovr(p), reverse=True)
        new_main[team]   = pool[:ROSTER_SIZE]
        new_extras[team] = pool[ROSTER_SIZE:]

    # Build change log: compare new main vs old main
    for team in sorted(all_teams):
        old_names = {p['name'] for p in main.get(team, [])}
        new_names = {p['name'] for p in new_main.get(team, [])}
        added   = new_names - old_names
        removed = old_names - new_names
        if added or removed:
            for n in sorted(added):
                log.append(f'  {team} + {n}  OVR={ovr(next(p for p in new_main[team] if p["name"]==n))}')
            for n in sorted(removed):
                p = next((x for x in main.get(team,[]) if x['name']==n), None)
                if p:
                    log.append(f'  {team} - {n}  OVR={ovr(p)}')

    return new_main, new_extras, log

# ── Load files ────────────────────────────────────────────────────────────────
with open(EXTRAS_FILE, encoding='utf-8') as f:
    extras_data = json.load(f)

# Process each flat file independently (they may differ)
for fname in FLAT_FILES:
    print(f'\n=== {fname} ===')
    with open(fname, encoding='utf-8') as f:
        main_data = json.load(f)

    new_main, new_extras, log = process_rosters(main_data, extras_data)
    for line in log:
        print(line)

    # Verify all teams are 15
    oversized = [(t, len(p)) for t, p in new_main.items() if len(p) != ROSTER_SIZE]
    if oversized:
        print(f'  WARNING: teams not at {ROSTER_SIZE}: {oversized}')
    else:
        print(f'  All {len(new_main)} teams at exactly {ROSTER_SIZE} players')

    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(new_main, f, indent=2, ensure_ascii=False)
    print(f'  Saved {fname}')

    # Use the last file's extras as the canonical new_extras
    extras_out = new_extras

# ── nba_rosters_all.json ──────────────────────────────────────────────────────
print(f'\n=== {ALL_FILE} [{ALL_YEAR}] ===')
with open(ALL_FILE, encoding='utf-8') as f:
    all_data = json.load(f)

with open(FLAT_FILES[-1], encoding='utf-8') as f:
    final_main = json.load(f)   # re-read the just-saved final file

all_data[ALL_YEAR] = final_main
with open(ALL_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False)
print(f'  Updated 2027 key in {ALL_FILE}')
print(f'  Saved {ALL_FILE}')

# ── extras file ───────────────────────────────────────────────────────────────
print(f'\n=== {EXTRAS_FILE} ===')
# Remove teams with empty extras lists
extras_clean = {t: p for t, p in extras_out.items() if p}
with open(EXTRAS_FILE, 'w', encoding='utf-8') as f:
    json.dump(extras_clean, f, indent=2, ensure_ascii=False)
print(f'  Saved {EXTRAS_FILE}  ({len(extras_clean)} teams have extras)')
total_extras = sum(len(p) for p in extras_clean.values())
print(f'  Total extras players: {total_extras}')

print('\nDone.')
