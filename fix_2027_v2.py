"""
fix_2027_v2.py
Apply all remaining offseason moves found in the NBA.com/ESPN tracker:
  - Additional trades (Wiggins, Dort, Risacher, Ayton, Stewart, LeVert, Collins,
    Middleton, Sasser, Russell, Santi Aldama, Devin Carter, Nembhard, Gueye, etc.)
  - FA signings crossing teams (Powell, Hachimura, Kennard, Thybulle, Ziaire,
    Hayes, Post, Anderson, Vucevic, Oubre, Harris, Hukporti, Drummond,
    Finney-Smith, Bogdanovic, Conley)
  - Draft pick corrections (Karaban SAC, Braden Smith IND, Ryan Conwell MIA)
Input:  nba_rosters27_fixed.json
Output: nba_rosters27_v2.json
"""

import io, sys, json, re, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAT_KEYS = ['t_2pt', 't_3pt', 't_def', 't_reb']

def norm(s):
    n = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()

with open('nba_rosters27_fixed.json', encoding='utf-8') as f:
    rosters = json.load(f)

with open('rookie_predictions_2026.json', encoding='utf-8') as f:
    rookies_list = json.load(f)

ALL_TEAMS = sorted(rosters.keys())
warns = []

def find_and_remove(name, preferred=None):
    n = norm(name)
    order = ([preferred] + [t for t in ALL_TEAMS if t != preferred]
             if preferred else list(ALL_TEAMS))
    for team in order:
        for i, p in enumerate(rosters.get(team, [])):
            if norm(p['name']) == n:
                return rosters[team].pop(i), team
    warns.append(f'NOT FOUND: {name}')
    return None, None

def move(name, frm=None, to=None):
    p, actual = find_and_remove(name, frm)
    if p and to:
        rosters.setdefault(to, []).append(p)
        if frm and actual and actual != frm:
            print(f'  NOTE: {name} found on {actual}, expected {frm}')
    return p

def add_pick(pick_num, team):
    for r in rookies_list:
        if r['pick'] == pick_num:
            rosters.setdefault(team, []).append(
                {k: r[k] for k in ['name','t_2pt','t_3pt','t_def','t_reb']})
            return r['name']
    warns.append(f'Pick #{pick_num} not found')
    return None

# ── TRADES ─────────────────────────────────────────────────────────────────
print('=== TRADES ===')

# Aaron Wiggins: OKC → ATL (June 21)
move('Aaron Wiggins', 'OKC', 'ATL')

# Mouhamed Gueye: ATL → MIN (part of Randle deal — MIN receives Gueye + #33)
move('Mouhamed Gueye', 'ATL', 'MIN')

# Devin Carter: SAC → ATL (June 29)
move('Devin Carter', 'SAC', 'ATL')

# Santi Aldama: MEM → DAL (July 1, confirmed via July 7 6-team routing)
move('Santi Aldama', 'MEM', 'DAL')

# 6-team deal (July 7): LeVert DET→MIL; Prince+Harris MIL→DET;
#   Claxton already done; Collins LAC→DET; Sasser DET→DAL;
#   D'Angelo Russell →MEM; Middleton DAL→WAS
move('Caris LeVert', 'DET', 'MIL')
move('Taurean Prince', 'MIL', 'DET')
move('Gary Harris', 'MIL', 'DET')
move('John Collins', 'LAC', 'DET')        # sign-and-trade 3yr/$51M
move('Marcus Sasser', 'DET', 'DAL')
move("D'Angelo Russell", None, 'MEM')     # search all (base data has him on DAL)
move('Khris Middleton', 'DAL', 'WAS')

# Isaiah Stewart: DET → MEM (July 7 6-team, officially completes June 24 move)
move('Isaiah Stewart', 'DET', 'MEM')

# July 19: Dort + Nembhard OKC → ATL; ATL sends Risacher to DAL
move('Luguentz Dort', 'OKC', 'ATL')
move('Ryan Nembhard', None, 'ATL')        # search all — may be on DAL
move('Zaccharie Risacher', 'ATL', 'DAL')

# July 3: Ayton LAL → WAS; Hardy WAS → LAL
move('Deandre Ayton', 'LAL', 'WAS')
move('Jaden Hardy', 'WAS', 'LAL')

# Alex Karaban: SAS → SAC (draft night — corrected destination)
move('Alex Karaban', 'SAS', 'SAC')

# ── FA SIGNINGS (team changes) ─────────────────────────────────────────────
print('\n=== FA SIGNINGS (cross-team) ===')

# Rui Hachimura: LAL → LAC (2yr/$28M)
move('Rui Hachimura', 'LAL', 'LAC')

# Luke Kennard: LAL → PHO (2yr/~$13M)
move('Luke Kennard', 'LAL', 'PHO')

# Matisse Thybulle: POR → LAL (1yr/$3.3M)
move('Matisse Thybulle', 'POR', 'LAL')

# Ziaire Williams: BRK → LAL (1yr/$3M)
move('Ziaire Williams', 'BRK', 'LAL')

# Jaxson Hayes: LAL → UTA (2yr/$12M)
move('Jaxson Hayes', 'LAL', 'UTA')

# Quinten Post: GSW → MEM offer sheet, Warriors declined (3yr/$30M)
move('Quinten Post', 'GSW', 'MEM')

# Kyle Anderson: MIN → TOR (1yr/$3.9M)
move('Kyle Anderson', 'MIN', 'TOR')

# Nikola Vucevic: BOS → ORL (1yr/$3.9M — re-signed after being traded to BOS at deadline)
move('Nikola Vucevic', 'BOS', 'ORL')

# Norman Powell: MIA → CHI (2yr/$45M — signed after MIA allowed him to leave)
move('Norman Powell', 'MIA', 'CHI')

# Kelly Oubre Jr.: PHI → IND (2yr/~$17M)
move('Kelly Oubre Jr.', 'PHI', 'IND')

# Tobias Harris: DET → SAS (2yr/$31M)
move('Tobias Harris', 'DET', 'SAS')

# Ariel Hukporti: NYK → PHI (1yr/$3.4M)
move('Ariel Hukporti', 'NYK', 'PHI')

# Andre Drummond: PHI → NYK (1yr/$3.9M re-sign — was on PHI in 2025-26, moves to NYK)
move('Andre Drummond', 'PHI', 'NYK')

# Dorian Finney-Smith: HOU → CHO (trade: Rockets get trade exception)
move('Dorian Finney-Smith', 'HOU', 'CHO')

# Bogdan Bogdanovic: LAC → HOU (1yr re-sign — in base data shown on LAC)
move('Bogdan Bogdanovic', 'LAC', 'HOU')

# Mike Conley Jr.: MIN → BOS (1yr re-sign — joins Celtics)
move('Mike Conley', 'MIN', 'BOS')

# ── Braden Smith deal (CHI sends #38 to IND, IND sends Kam Jones to CHI) ──
print('\n=== BRADEN SMITH / KAM JONES DEAL ===')
move('Kam Jones', 'IND', 'CHI')           # IND → CHI
name = add_pick(38, 'IND')               # Braden Smith → IND
if name:
    print(f'  Added {name} (pick #38) to IND')

# ── Ryan Conwell deal (2nd-round pick #37 → MIA) ─────────────────────────
print('\n=== ADDITIONAL 2ND ROUND PICKS ===')
name = add_pick(37, 'MIA')
if name:
    print(f'  Added {name} (pick #37) to MIA')

# Bruce Thornton (pick #31) → HOU (NYK to HOU in draft-night deal)
name = add_pick(31, 'HOU')
if name:
    print(f'  Added {name} (pick #31) to HOU')

# Felix Okpara (pick #46) → WAS (ORL sends Okpara to WAS)
name = add_pick(46, 'WAS')
if name:
    print(f'  Added {name} (pick #46) to WAS')

# Izaiyah Nelson (pick #51) → ORL
name = add_pick(51, 'ORL')
if name:
    print(f'  Added {name} (pick #51) to ORL')

# ── Save ───────────────────────────────────────────────────────────────────
with open('nba_rosters27_v2.json', 'w', encoding='utf-8') as f:
    json.dump(rosters, f, ensure_ascii=False, indent=2)

# ── Report ──────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print('2026-27 ROSTERS v2  (target = 15/team)')
print(f"{'='*65}")

total = 0
for team in sorted(rosters.keys()):
    players = rosters[team]
    cnt = len(players)
    total += cnt
    delta = 15 - cnt
    flag = f'  ← {"need +" if delta>0 else "cut "}{abs(delta)}' if cnt != 15 else ''
    print(f'\n{team} ({cnt}/15){flag}')
    for p in sorted(players, key=lambda x: -(x['t_2pt']+x['t_3pt']+x['t_def']+x['t_reb'])):
        ovr = p['t_2pt']+p['t_3pt']+p['t_def']+p['t_reb']
        print(f'  {p["name"]:<32} {ovr:3}')

print(f'\nTotal: {total} players across 30 teams  (target 450)')

if warns:
    print(f'\nWARNINGS:')
    for w in warns:
        print(f'  {w}')

print('\nSaved → nba_rosters27_v2.json')
