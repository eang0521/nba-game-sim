"""
predict_rookies.py

Fits OLS models on calibration_data.csv (college stats → year-1 NBA ratings)
then predicts 2PS, 3PS, DEF, REB, OVR for an incoming draft class.

Usage:
    py predict_rookies.py          # defaults to 2026 draft
    py predict_rookies.py 2025     # explicit draft year

Output:
    rookie_predictions_{year}.csv  — ranked predictions
    rookie_predictions_{year}.json — same data as JSON (for the N3BL app)
"""

import io, sys, json, time, unicodedata, os, re
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup, Comment
from io import StringIO
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Config ────────────────────────────────────────────────────────────────────
DRAFT_YEAR    = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
DELAY         = 4
HEADERS       = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}
BASE          = 'https://www.basketball-reference.com'
CAL_FILE      = 'calibration_data.csv'
DRAFT_CACHE   = 'draft_links_cache.json'
COLLEGE_CACHE = 'college_stats_cache.json'
OUT_CSV       = f'rookie_predictions_{DRAFT_YEAR}.csv'
OUT_JSON      = f'rookie_predictions_{DRAFT_YEAR}.json'
AGES_CACHE    = 'player_ages_cache.json'
SEASON_START  = '2026-10-01'   # age computed as of this date

STAT_MAP = {
    'G': 'c_G', 'MP': 'c_MP',
    'FG': 'c_FG', 'FGA': 'c_FGA', 'FG%': 'c_FGpct',
    '3P': 'c_3P', '3PA': 'c_3PA', '3P%': 'c_3Ppct',
    'FT': 'c_FT', 'FTA': 'c_FTA', 'FT%': 'c_FTpct',
    'ORB': 'c_ORB', 'TRB': 'c_TRB',
    'AST': 'c_AST', 'STL': 'c_STL', 'BLK': 'c_BLK',
    'TOV': 'c_TOV', 'PF': 'c_PF', 'PTS': 'c_PTS',
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def norm_name(n: str) -> str:
    n = unicodedata.normalize('NFD', n).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()


def fetch_html(url: str) -> str | None:
    time.sleep(DELAY)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f'  ERROR {url}: {e}')
        return None


def find_table(html: str, table_id: str):
    soup = BeautifulSoup(html, 'html.parser')
    t = soup.find('table', id=table_id)
    if t is None:
        for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
            cs = BeautifulSoup(comment, 'html.parser')
            t = cs.find('table', id=table_id)
            if t:
                break
    return t


def load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(path: str, data: dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def safe_float(val):
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (ValueError, TypeError):
        return None


# ── 1. Load calibration data and fit OLS models ───────────────────────────────
print(f'Loading calibration data from {CAL_FILE}...')
cal = pd.read_csv(CAL_FILE, encoding='utf-8-sig')

features   = [c for c in cal.columns if c.startswith('c_')]
components = ['2PS', '3PS', 'DEF', 'REB']
all_cols   = components + ['OVR']

for col in features + all_cols:
    cal[col] = pd.to_numeric(cal[col], errors='coerce')

cal_clean = cal.dropna(subset=features + all_cols)
print(f'Training on {len(cal_clean)} complete cases  ({len(cal)} total)')

# Column means for imputing missing predictors on new players
feat_means = cal_clean[features].mean()

X_train = np.column_stack([np.ones(len(cal_clean)), cal_clean[features].values])

# Stage 1: predict OVR
components = ['2PS', '3PS', 'DEF', 'REB']
y_ovr = cal_clean['OVR'].values
ovr_beta, _, _, _ = np.linalg.lstsq(X_train, y_ovr, rcond=None)
y_hat = X_train @ ovr_beta
r2_ovr = 1 - np.sum((y_ovr - y_hat)**2) / np.sum((y_ovr - y_ovr.mean())**2)
print(f'  OVR: R² = {r2_ovr:.3f}')

# Stage 2: predict component shares (comp / OVR) — captures player archetype
share_betas = {}
mean_shares = {}
for comp in components:
    share = cal_clean[comp].values / cal_clean['OVR'].values
    beta, _, _, _ = np.linalg.lstsq(X_train, share, rcond=None)
    share_betas[comp] = beta
    mean_shares[comp] = float(share.mean())
    y_hat_s = X_train @ beta
    r2_s = 1 - np.sum((share - y_hat_s)**2) / np.sum((share - share.mean())**2)
    print(f'  {comp} share: R² = {r2_s:.3f}  (mean share = {share.mean():.3f})')

# Pick-only OVR model for international/HS players (no college stats to lean on)
# Uses 1/pick directly — avoids college-stat baseline swamping the pick signal
inv_pick_train = cal_clean['c_inv_pick'].values
X_pick_only = np.column_stack([np.ones(len(inv_pick_train)), inv_pick_train])
pick_only_beta, _, _, _ = np.linalg.lstsq(X_pick_only, y_ovr, rcond=None)
y_hat_po = X_pick_only @ pick_only_beta
r2_po = 1 - np.sum((y_ovr - y_hat_po)**2) / np.sum((y_ovr - y_ovr.mean())**2)
print(f'  Pick-only OVR (for intl/HS): R² = {r2_po:.3f}')

# ── 2. Get draft class player list ────────────────────────────────────────────
draft_cache = load_json(DRAFT_CACHE)
key = str(DRAFT_YEAR)

if key not in draft_cache:
    url = f'{BASE}/draft/NBA_{DRAFT_YEAR}.html'
    print(f'\nScraping {DRAFT_YEAR} draft: {url}')
    html = fetch_html(url)
    if not html:
        print('ERROR: Could not fetch draft page.')
        sys.exit(1)
    table = find_table(html, 'stats')
    if table is None:
        print(f'ERROR: No stats table found for {DRAFT_YEAR} draft.')
        sys.exit(1)
    players = {}
    for row in table.find_all('tr'):
        td = row.find('td', {'data-stat': 'player'})
        if td:
            a = td.find('a')
            if a and a.get('href') and a.get_text(strip=True):
                players[a.get_text(strip=True)] = a['href']
    print(f'  {len(players)} players found')
    draft_cache[key] = players
    save_json(DRAFT_CACHE, draft_cache)
else:
    print(f'\n{DRAFT_YEAR} draft already cached ({len(draft_cache[key])} players)')

draft_players = draft_cache[key]  # {name: /players/...}

# ── 3. Fetch college stats for each draftee ───────────────────────────────────
college_cache = load_json(COLLEGE_CACHE)
new_scrapes = 0

print(f'\nFetching college stats for {DRAFT_YEAR} draftees...')
for name, url_path in draft_players.items():
    if name in college_cache:
        continue

    url = BASE + url_path
    print(f'  Fetching {name} → {url}')
    html = fetch_html(url)
    if not html:
        college_cache[name] = None
        continue

    table = find_table(html, 'all_college_stats')
    if table is None:
        college_cache[name] = None
        print(f'    → no college stats (international/HS)')
        continue

    try:
        df = pd.read_html(StringIO(str(table)))[0]
    except Exception as e:
        print(f'    → parse error: {e}')
        college_cache[name] = None
        continue

    if isinstance(df.columns, pd.MultiIndex):
        flat = []
        for l0, l1 in df.columns:
            flat.append(str(l1) if 'Unnamed' in str(l0) else f'{l0}_{l1}')
        df.columns = flat
    else:
        df.columns = [str(c) for c in df.columns]

    df['Season'] = df['Season'].astype(str)
    df = df[df['Season'].str.match(r'^\d{4}-\d{2}$', na=False)]

    if df.empty:
        college_cache[name] = None
        print(f'    → no valid season rows')
        continue

    last = df.iloc[-1]
    g    = safe_float(last.get('G'))
    row  = {'G': g}

    for col in ['FG', 'FGA', '3P', '3PA', 'FT', 'FTA',
                'ORB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']:
        val = safe_float(last.get(f'Totals_{col}'))
        row[col] = (val / g) if (val is not None and g and g > 0) else None

    for short, key_col in [('FG%', 'Shooting_FG%'), ('3P%', 'Shooting_3P%'), ('FT%', 'Shooting_FT%')]:
        row[short] = safe_float(last.get(key_col))

    row['MP']  = safe_float(last.get('Per Game_MP'))
    row['Age'] = safe_float(last.get('Age'))

    college_cache[name] = row
    new_scrapes += 1
    print(f'    → stats captured ({new_scrapes} new this run)')

    if new_scrapes % 20 == 0:
        save_json(COLLEGE_CACHE, college_cache)
        print(f'    [checkpoint saved]')

save_json(COLLEGE_CACHE, college_cache)
print(f'College cache saved ({new_scrapes} new entries)')

# Load ages cache (populated by scrape_ages.py)
ages_cache = load_json(AGES_CACHE)
season_date = date.fromisoformat(SEASON_START)

def age_from_cache(name: str) -> int | None:
    entry = ages_cache.get(name)
    return entry['age'] if entry else None

# ── 4. Build feature vectors and predict ─────────────────────────────────────
print(f'\nPredicting ratings for {DRAFT_YEAR} draftees...')

ovr_lo = max(1,  int(cal_clean['OVR'].min()))
ovr_hi = min(150, int(cal_clean['OVR'].max()) + 10)

def _predict_row(name, pick, has_college, x_row, college_age=None):
    if not has_college:
        # Pick-only model: OVR purely from draft position, shares from training means
        ovr_raw = float(pick_only_beta[0] + pick_only_beta[1] * (1.0 / pick))
        ovr = max(ovr_lo, min(ovr_hi, ovr_raw))
        norm_shares = {k: v / sum(mean_shares.values()) for k, v in mean_shares.items()}
    else:
        # Stage 1: predict OVR from full feature set
        ovr_raw = float(x_row @ ovr_beta)
        ovr = max(ovr_lo, min(ovr_hi, ovr_raw))

        # Stage 2: predict shares, clip to >=0.01, normalize to sum=1
        raw_shares = {comp: float(x_row @ share_betas[comp]) for comp in components}
        raw_shares = {k: max(0.01, v) for k, v in raw_shares.items()}
        total = sum(raw_shares.values())
        norm_shares = {k: v / total for k, v in raw_shares.items()}

    # Distribute OVR by shares, fix rounding so components sum exactly to OVR
    comp_vals = {comp: norm_shares[comp] * ovr for comp in components}
    rounded   = {comp: int(comp_vals[comp]) for comp in components}
    remainder = int(round(ovr)) - sum(rounded.values())
    # Assign leftover to the component with the largest fractional part
    fracs = sorted(components, key=lambda c: comp_vals[c] - rounded[c], reverse=True)
    for i in range(abs(remainder)):
        rounded[fracs[i % len(fracs)]] += int(np.sign(remainder))

    # Age: prefer ages_cache (precise birthdate), fall back to college season age + 1
    age = age_from_cache(name)
    if age is None and college_age is not None:
        age = int(college_age) + 1  # college age → NBA rookie age

    return {
        'Player': name, 'Pick': pick, 'HasCollegeStats': has_college,
        'Age': age,
        'OVR': int(round(ovr)),
        **{comp: rounded[comp] for comp in components},
    }

# Assign pick numbers by draft board order (dict insertion order = BBRef table order)
draft_pick = {name: i for i, name in enumerate(draft_players.keys(), 1)}

predictions = []
for name, url_path in draft_players.items():
    cstats = college_cache.get(name)
    pick = draft_pick[name]
    if cstats is None:
        # No college stats — pick-only OVR model + mean shares (handled inside _predict_row)
        predictions.append(_predict_row(name, pick, False, None))
        continue

    # Build feature dict, derive c_2P / c_2PA / c_2Ppct
    feat = {}
    for raw_col, clean_col in STAT_MAP.items():
        val = cstats.get(raw_col)
        feat[clean_col] = float(val) if val is not None else np.nan

    fg  = feat.get('c_FG',  np.nan)
    tp  = feat.get('c_3P',  np.nan)
    fga = feat.get('c_FGA', np.nan)
    feat['c_2P']    = fg - tp if not (np.isnan(fg) or np.isnan(tp)) else np.nan
    feat['c_2PA']   = fga - feat.get('c_3PA', np.nan) if not np.isnan(fga) else np.nan
    feat['c_2Ppct'] = (feat['c_2P'] / feat['c_2PA']
                       if (not np.isnan(feat.get('c_2P', np.nan))
                           and feat.get('c_2PA', 0) and feat['c_2PA'] > 0)
                       else np.nan)
    feat['c_inv_pick'] = 1.0 / float(pick)

    # Fill any remaining NaN with training-set column means
    x_vec = np.array([feat.get(f, np.nan) for f in features])
    missing = np.isnan(x_vec)
    if missing.any():
        x_vec[missing] = feat_means[np.array(features)[missing]].values

    x_row = np.concatenate([[1.0], x_vec])
    college_age = safe_float(cstats.get('Age'))
    predictions.append(_predict_row(name, pick, True, x_row, college_age))

# ── 5. Sort and output ────────────────────────────────────────────────────────
df_out = pd.DataFrame(predictions).sort_values('Pick')

print(f'\n{"="*68}')
print(f'{DRAFT_YEAR} ROOKIE PREDICTIONS  (all {len(df_out)} picks, by draft order)')
print(f'{"="*68}')
print(f'{"Pk":<4} {"Player":<28} {"Age":>3} {"2PT":>4} {"3PT":>4} {"DEF":>4} {"REB":>4} {"OVR":>4}  {"Notes":<6}')
print('-' * 68)
for _, r in df_out.iterrows():
    note = '' if r['HasCollegeStats'] else '*'
    age_str = str(int(r['Age'])) if pd.notna(r.get('Age')) and r.get('Age') is not None else '?'
    print(f'{int(r["Pick"]):<4} {r["Player"]:<28} {age_str:>3} {r["2PS"]:>4} {r["3PS"]:>4} {r["DEF"]:>4} {r["REB"]:>4} {r["OVR"]:>4}  {note}')
print(f'\n* = no college stats; ratings estimated from pick position only')

# Save outputs
df_out.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
print(f'\nSaved → {OUT_CSV}')

json_out = [
    {
        'name': r['Player'],
        'draft_year': DRAFT_YEAR,
        'pick': r.get('Pick'),
        'age':  r.get('Age'),
        't_2pt': r.get('2PS'),
        't_3pt': r.get('3PS'),
        't_def': r.get('DEF'),
        't_reb': r.get('REB'),
        'ovr':   r.get('OVR'),
        'has_college_stats': r.get('HasCollegeStats', False),
    }
    for r in predictions
]
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(json_out, f, indent=2, ensure_ascii=False)
print(f'Saved → {OUT_JSON}')
