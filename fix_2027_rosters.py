"""
fix_2027_rosters.py

Applies corrections to nba_rosters27_moves.json:
  1. Trade corrections (Randle MIN→BRK, Claxton BRK→CHI,
     Bridges CHO→PHO, Allen+O'Neale PHO→CHO)
  2. Injury-return players (Haliburton, Kessler, Kyrie, Lillard, VanVleet)
     using data from nba_rosters_all.json — two-step progression +
     one -4 penalty per missed season
"""

import io, sys, json, re, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAT_KEYS = ['t_2pt','t_3pt','t_def','t_reb']

def norm(s):
    n = unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()

def apply_delta(stats, delta):
    """Apply the distribution progression rule for one year."""
    if delta == 0:
        return dict(stats)
    sign = 1 if delta > 0 else -1
    abs_delta = abs(delta)
    base  = abs_delta // 4
    extra = abs_delta %  4
    ordered = sorted(STAT_KEYS, key=lambda k: stats[k], reverse=True)
    new = {}
    for i, k in enumerate(ordered):
        change = sign * (base + 1) if i < extra else sign * base
        new[k]  = max(0, stats[k] + change)
    return new

AGE_DELTA = {
    18: 6, 19: 4, 20: 3, 21: 2, 22: 1, 23: 0,
    24:-1, 25:-1, 26:-2, 27:-2, 28:-3, 29:-4, 30:-4,
    31:-5, 32:-5, 33:-6, 34:-6, 35:-7, 36:-7, 37:-8,
    38:-8, 39:-9, 40:-9, 41:-10,
}

# ── Load files ─────────────────────────────────────────────────────────────
with open('nba_rosters27_moves.json', encoding='utf-8') as f:
    rosters = json.load(f)

with open('nba_rosters_all.json', encoding='utf-8') as f:
    all_data = json.load(f)

ALL_TEAMS = sorted(rosters.keys())
warnings = []

def find_and_remove(name, preferred_team=None):
    n = norm(name)
    order = ([preferred_team] + [t for t in ALL_TEAMS if t != preferred_team]
             if preferred_team else list(ALL_TEAMS))
    for team in order:
        for i, p in enumerate(rosters.get(team, [])):
            if norm(p['name']) == n:
                return rosters[team].pop(i), team
    warnings.append(f"NOT FOUND: {name}")
    return None, None

def move(name, from_team=None, to_team=None):
    p, actual = find_and_remove(name, from_team)
    if p and to_team:
        rosters.setdefault(to_team, []).append(p)
        if from_team and actual and actual != from_team:
            print(f"  NOTE: {name} on {actual}, not {from_team}")
    return p

# ── 1. Trade Corrections ───────────────────────────────────────────────────
print("=== TRADE CORRECTIONS ===")

# Julius Randle MIN→BRK (trade on eve of 2026 draft, #28 pick already on BRK)
move('Julius Randle', 'MIN', 'BRK')
print("  Randle: MIN → BRK")

# Nic Claxton BRK→CHI (part of same multi-team deal)
move('Nic Claxton', 'BRK', 'CHI')
print("  Nic Claxton: BRK → CHI")

# Miles Bridges CHO→PHO (June 28 2026)
move('Miles Bridges', 'CHO', 'PHO')
print("  Miles Bridges: CHO → PHO")

# Grayson Allen PHO→CHO (same trade)
move('Grayson Allen', 'PHO', 'CHO')
print("  Grayson Allen: PHO → CHO")

# Royce O'Neale PHO→CHO (same trade)
move("Royce O'Neale", 'PHO', 'CHO')
print("  Royce O'Neale: PHO → CHO")

# ── 2. Injury-Return Players ───────────────────────────────────────────────
print("\n=== INJURY-RETURN PLAYERS ===")

def build_injury_player(name, last_year, year1_age, year2_age, team):
    """
    Reconstruct a 2026-27 rating for a player who missed 2025-26.
    last_year  = '2025' or '2024' (key in all_data)
    year1_age  = player's age in last_year's season (step 1 delta)
    year2_age  = player's age in missed season (step 2 delta)
    """
    # Find the player in historical data
    n = norm(name)
    record = None
    for team_code, players in all_data.get(str(last_year), {}).items():
        for p in players:
            if norm(p['name']) == n:
                record = {k: p[k] for k in STAT_KEYS}
                break
        if record:
            break
    if not record:
        warnings.append(f"Historical data NOT FOUND: {name} in {last_year}")
        return None

    ovr0 = sum(record[k] for k in STAT_KEYS)
    # Step 1: progress using year1_age
    d1 = AGE_DELTA.get(year1_age, -11)
    s1 = apply_delta(record, d1)
    # Step 2: progress using year2_age
    d2 = AGE_DELTA.get(year2_age, -11)
    s2 = apply_delta(s1, d2)
    # Injury penalty: -1 to each stat
    final = {k: max(0, s2[k] - 1) for k in STAT_KEYS}

    ovr_final = sum(final[k] for k in STAT_KEYS)
    print(f"  {name:<28} OVR {ovr0}→{ovr_final}  "
          f"[{final['t_2pt']}/{final['t_3pt']}/{final['t_def']}/{final['t_reb']}]  "
          f"(d1={d1}, d2={d2}, inj=-4)  → {team}")

    entry = {'name': name}
    entry.update(final)
    rosters.setdefault(team, []).append(entry)
    return entry

# Tyrese Haliburton — IND
# 2024-25: age 25  →  2025-26: age 26 (missed)
build_injury_player('Tyrese Haliburton', 2025, 25, 26, 'IND')

# Walker Kessler — LAL (UTA data from 2024-25; age 24→25; missed 2025-26)
build_injury_player('Walker Kessler', 2025, 24, 25, 'LAL')

# Kyrie Irving — DAL (2024-25: age 32; missed 2025-26: age 33)
build_injury_player('Kyrie Irving', 2025, 32, 33, 'DAL')

# Damian Lillard — POR (2024-25 MIL: age 34; missed 2025-26: age 35)
build_injury_player('Damian Lillard', 2025, 34, 35, 'POR')

# Fred VanVleet — HOU (2024-25: age 31; missed 2025-26: age 32)
build_injury_player('Fred VanVleet', 2025, 31, 32, 'HOU')

# ── 3. Save ────────────────────────────────────────────────────────────────
with open('nba_rosters27_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(rosters, f, ensure_ascii=False, indent=2)

# ── 4. Report ──────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print("2026-27 ROSTER STATE AFTER CORRECTIONS  (target = 15/team)")
print(f"{'='*65}")

total_players = 0
for team in sorted(rosters.keys()):
    players = rosters[team]
    cnt = len(players)
    total_players += cnt
    flag = f"  ← need {'+'if cnt<15 else ''}{15-cnt}" if cnt != 15 else ''
    print(f"\n{team} ({cnt}/15){flag}")
    for p in sorted(players, key=lambda x: -(x['t_2pt']+x['t_3pt']+x['t_def']+x['t_reb'])):
        ovr = p['t_2pt']+p['t_3pt']+p['t_def']+p['t_reb']
        print(f"  {p['name']:<32} {ovr:3}")

print(f"\nTotal players across 30 teams: {total_players}")

if warnings:
    print(f"\nWARNINGS:")
    for w in warnings:
        print(f"  {w}")

print("\nSaved → nba_rosters27_fixed.json")
