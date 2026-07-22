import io, sys, json, re, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def norm(s):
    n = unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()

with open('nba_rosters27_v2.json', encoding='utf-8') as f:
    rosters = json.load(f)

# Find and replace Tatum in BOS
n = norm('Jayson Tatum')
for i, p in enumerate(rosters['BOS']):
    if norm(p['name']) == n:
        old_ovr = p['t_2pt']+p['t_3pt']+p['t_def']+p['t_reb']
        # Injury-adjusted rating from 2024-25 base + 2-step progression + -4 penalty
        rosters['BOS'][i] = {
            'name':  'Jayson Tatum',
            't_2pt': 23,
            't_3pt': 27,
            't_def': 20,
            't_reb': 23,
        }
        new_ovr = 23+27+20+23
        print(f"Jayson Tatum BOS: OVR {old_ovr} → {new_ovr}  "
              f"[{rosters['BOS'][i]['t_2pt']}/{rosters['BOS'][i]['t_3pt']}/"
              f"{rosters['BOS'][i]['t_def']}/{rosters['BOS'][i]['t_reb']}]")
        break
else:
    print("Tatum NOT FOUND in BOS")

with open('nba_rosters27_v2.json', 'w', encoding='utf-8') as f:
    json.dump(rosters, f, ensure_ascii=False, indent=2)

print("Saved.")
