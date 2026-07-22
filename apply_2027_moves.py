"""
apply_2027_moves.py
Apply all 2026 offseason trades, FA signings, retirements, and draft picks
to the base 2026-27 progression file (nba_rosters27_base.json).
"""

import io, sys, json, re, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def norm(s):
    n = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()

with open('nba_rosters27_base.json', encoding='utf-8') as f:
    rosters = json.load(f)

with open('rookie_predictions_2026.json', encoding='utf-8') as f:
    rookies_list = json.load(f)

ALL_TEAMS = ['ATL','BOS','BRK','CHI','CHO','CLE','DAL','DEN','DET','GSW',
             'HOU','IND','LAC','LAL','MEM','MIA','MIL','MIN','NOP','NYK',
             'OKC','ORL','PHI','PHO','POR','SAC','SAS','TOR','UTA','WAS']
for t in ALL_TEAMS:
    rosters.setdefault(t, [])

warnings = []

def find_and_remove(name, preferred_team=None):
    n = norm(name)
    search_order = ([preferred_team] + [t for t in ALL_TEAMS if t != preferred_team]
                    if preferred_team else list(ALL_TEAMS))
    for team in search_order:
        for i, p in enumerate(rosters.get(team, [])):
            if norm(p['name']) == n:
                return rosters[team].pop(i), team
    warnings.append(f"NOT FOUND: {name}")
    return None, None

def move(name, from_team=None, to_team=None):
    p, actual_from = find_and_remove(name, from_team)
    if p and to_team:
        rosters[to_team].append(p)
        if from_team and actual_from and actual_from != from_team:
            print(f"  NOTE: {name} was on {actual_from} (expected {from_team})")
    return p

def remove_player(name, from_team=None):
    p, actual = find_and_remove(name, from_team)
    if p:
        print(f"  Removed: {name} (was on {actual})")
    return p

def add_rookie(pick_num, to_team):
    for r in rookies_list:
        if r['pick'] == pick_num:
            rosters[to_team].append({
                'name':  r['name'],
                't_2pt': r['t_2pt'],
                't_3pt': r['t_3pt'],
                't_def': r['t_def'],
                't_reb': r['t_reb'],
            })
            return r['name']
    warnings.append(f"Draft pick #{pick_num} not found in rookie file")
    return None

# ── Summer Trades ──────────────────────────────────────────────────────────
print("Applying summer trades...")

# Giannis + Portis MIL→MIA; Herro, Jaquez, Ware, Jakucionis MIA→MIL
move('Giannis Antetokounmpo', 'MIL', 'MIA')
move('Bobby Portis', 'MIL', 'MIA')
move('Tyler Herro', 'MIA', 'MIL')
move('Jaime Jaquez Jr.', 'MIA', 'MIL')
move("Kel'el Ware", 'MIA', 'MIL')
move('Kasparas Jakučionis', 'MIA', 'MIL')

# Jaylen Brown BOS→PHI; Paul George PHI→BOS
move('Jaylen Brown', 'BOS', 'PHI')
move('Paul George', 'PHI', 'BOS')

# Ja Morant MEM→POR; Grant+Murray POR→MEM
move('Ja Morant', 'MEM', 'POR')
move('Jerami Grant', 'POR', 'MEM')
move('Kris Murray', 'POR', 'MEM')

# LaMelo CHO→MIN; Naz Reid MIN→CHO
move('LaMelo Ball', 'CHO', 'MIN')
move('Naz Reid', 'MIN', 'CHO')

# Kawhi LAC→TOR; Ingram+Dick TOR→LAC
move('Kawhi Leonard', 'LAC', 'TOR')
move('Brandon Ingram', 'TOR', 'LAC')
move('Gradey Dick', 'TOR', 'LAC')

# Walker Kessler UTA→LAL (sign-and-trade)
move('Walker Kessler', 'UTA', 'LAL')

# ── Free Agent Signings ─────────────────────────────────────────────────────
print("Applying FA signings...")

# Mitchell Robinson NYK→BOS
move('Mitchell Robinson', 'NYK', 'BOS')

# Jordan Clarkson UTA→NYK
move('Jordan Clarkson', 'UTA', 'NYK')

# Collin Sexton UTA→LAL
move('Collin Sexton', 'UTA', 'LAL')

# Moritz Wagner ORL→BRK
move('Moritz Wagner', None, 'BRK')

# Larry Nance Jr. → IND
move('Larry Nance Jr.', None, 'IND')

# Sandro Mamukelashvili → LAL
move('Sandro Mamukelashvili', None, 'LAL')

# Quentin Grimes → LAL
move('Quentin Grimes', None, 'LAL')

# Anfernee Simons CHI→PHI (Simons traded to CHI at deadline, signed PHI in summer)
move('Anfernee Simons', 'CHI', 'PHI')

# Mo Bamba → UTA
move('Mo Bamba', None, 'UTA')

# Charles Bassey → GSW
move('Charles Bassey', None, 'GSW')

# ── Retirements ─────────────────────────────────────────────────────────────
print("Removing retired players...")
remove_player('Chris Paul')
remove_player('Kyle Lowry')
remove_player('Danilo Gallinari')

# ── Key Unsigned Free Agents ────────────────────────────────────────────────
print("Extracting unsigned free agents...")
fa_pool = []

lebron, _ = find_and_remove('LeBron James', 'LAL')
if lebron:
    fa_pool.append({'name': 'LeBron James', 'record': lebron,
                    'status': 'Unsigned UFA — CLE/MIA/GSW/PHI all pursuing'})

beal, _ = find_and_remove('Bradley Beal', 'LAC')
if beal:
    fa_pool.append({'name': 'Bradley Beal', 'record': beal,
                    'status': 'Unsigned UFA — injury concerns; thin market'})

# Harden already on CLE (negotiating), Draymond expected GSW, Klay on DAL contract
# Leave them in their current spots

# ── 2026 Draft ─────────────────────────────────────────────────────────────
print("Adding 2026 draft picks...")
draft_final = {
    1:  'WAS',  # AJ Dybantsa
    2:  'UTA',  # Darryn Peterson
    3:  'MEM',  # Cameron Boozer
    4:  'CHI',  # Caleb Wilson
    5:  'LAC',  # Keaton Wagler
    6:  'BRK',  # Mikel Brown Jr.
    7:  'SAC',  # Darius Acuff Jr.
    8:  'ATL',  # Kingston Flemings
    9:  'DAL',  # Morez Johnson Jr.
    10: 'MIL',  # Brayden Burries
    11: 'GSW',  # Yaxel Lendeborg
    12: 'OKC',  # Aday Mara (from LAC)
    13: 'MIL',  # Nate Ament (MIA pick traded to MIL)
    14: 'CHO',  # Hannes Steinbach
    15: 'CHI',  # Dailyn Swain (from POR)
    16: 'OKC',  # Bennett Stirtz (traded to OKC)
    17: 'DET',  # Ebuka Okorie (OKC pick traded to DET)
    18: 'CHO',  # Christian Anderson Jr. (from ORL/PHX)
    19: 'TOR',  # Allen Graves
    20: 'SAS',  # Jayden Quaintance (ATL pick traded to SAS)
    21: 'MEM',  # Karim López (DET→MEM)
    22: 'PHI',  # Labaron Philon Jr.
    23: 'ATL',  # Zuby Ejiofor (from CLE)
    24: 'LAL',  # Cameron Carr (NYK→LAL)
    25: 'DAL',  # Sergio de Larrea (LAL→DAL via NYK)
    26: 'SAS',  # Tarris Reed Jr. (DEN→SAS)
    27: 'BOS',  # Chris Cenac Jr.
    28: 'BRK',  # Joshua Jefferson (MIN→BRK)
    29: 'SAS',  # Alex Karaban (CLE→SAS)
    30: 'PHO',  # Koa Peat (DAL→PHO)
}
for pick, team in sorted(draft_final.items()):
    add_rookie(pick, team)

# ── Save ────────────────────────────────────────────────────────────────────
with open('nba_rosters27_moves.json', 'w', encoding='utf-8') as f:
    json.dump(rosters, f, ensure_ascii=False, indent=2)

# ── Report ──────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print("2026-27 ROSTER STATE  (target = 15 per team)")
print(f"{'='*65}")

for team in ALL_TEAMS:
    players = rosters[team]
    cnt = len(players)
    flag = '  ***' if cnt != 15 else ''
    print(f"\n{team} ({cnt}/15){flag}")
    for p in sorted(players, key=lambda x: -(x['t_2pt']+x['t_3pt']+x['t_def']+x['t_reb'])):
        ovr = p['t_2pt']+p['t_3pt']+p['t_def']+p['t_reb']
        print(f"  {p['name']:<32} {ovr:3}")

if fa_pool:
    print(f"\n{'='*65}")
    print("PLAYERS NEEDING PLACEMENT (unsigned FAs):")
    for fa in fa_pool:
        r = fa['record']
        ovr = r['t_2pt']+r['t_3pt']+r['t_def']+r['t_reb']
        print(f"\n  {fa['name']:<30} OVR {ovr}  "
              f"[{r['t_2pt']}/{r['t_3pt']}/{r['t_def']}/{r['t_reb']}]")
        print(f"    {fa['status']}")

if warnings:
    print(f"\n{'='*65}")
    print("WARNINGS (players not found / picks missing):")
    for w in warnings:
        print(f"  {w}")

print("\nDone. Output: nba_rosters27_moves.json")
