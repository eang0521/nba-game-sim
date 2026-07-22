"""
college_calibration.py

Tests whether last-season college stats predict year-1 NBA ratings
(2PS, 3PS, DEF, REB, OVR) from bbref_ratings.csv.

Steps:
  1. Load bbref_ratings.csv; identify each player's rookie year
  2. Scrape BBRef draft pages to get each player's profile URL
  3. Scrape each player's BBRef page for their last college season
  4. Merge with year-1 NBA ratings
  5. Save calibration_data.csv
  6. Print correlation table + OLS regression for each rating

Caches intermediate results so you can re-run without re-scraping:
  draft_links_cache.json   — {draft_year: {player_name: /players/...}}
  college_stats_cache.json — {player_name: {col: value, ...} | null}

Rate limit: 4 s per request (same as bbref_scraper.py).
"""

import io, sys, json, time, unicodedata, os, re
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup, Comment
from io import StringIO

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Config ────────────────────────────────────────────────────────────────────
DELAY   = 4
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}
BASE = 'https://www.basketball-reference.com'

RATINGS_FILE  = 'bbref_ratings.csv'
OUTPUT_FILE   = 'calibration_data.csv'
DRAFT_CACHE   = 'draft_links_cache.json'
COLLEGE_CACHE = 'college_stats_cache.json'

# Players with first year == 2002 might be mid-career entries (data starts 2002),
# so we only treat players whose first year >= 2003 as true rookies.
MIN_ROOKIE_YEAR = 2003

# ── Helpers ───────────────────────────────────────────────────────────────────

def norm_name(n: str) -> str:
    """Lowercase ASCII fold for fuzzy name matching."""
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
    """Find a BBRef table by id, including tables hidden inside HTML comments."""
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


# ── 1. Identify rookies ───────────────────────────────────────────────────────
ratings = pd.read_csv(RATINGS_FILE, encoding='utf-8-sig')
ratings = ratings[~ratings['Player'].str.startswith('[Filler')].copy()
print(f'Loaded {len(ratings)} real player-seasons from {RATINGS_FILE}')

first_year = (
    ratings.groupby('Player')['Year']
    .min()
    .reset_index()
    .rename(columns={'Year': 'RookieYear'})
)

# Restrict to players whose first NBA year is clearly within our data window
first_year = first_year[first_year['RookieYear'] >= MIN_ROOKIE_YEAR]

# Pull year-1 ratings for each rookie
rookie_ratings = pd.merge(
    first_year, ratings,
    left_on=['Player', 'RookieYear'],
    right_on=['Player', 'Year']
).drop(columns=['Year'])

# Only keep non-zero OVR (filters out players with essentially no stats)
rookie_ratings = rookie_ratings[rookie_ratings['OVR'] > 0].reset_index(drop=True)
print(f'Rookie player-seasons (OVR > 0): {len(rookie_ratings)}')

# Draft year = NBA rookie year - 1 (player was drafted the summer before)
draft_years_needed = sorted((rookie_ratings['RookieYear'] - 1).unique().tolist())
print(f'Draft classes to cover: {draft_years_needed[0]}–{draft_years_needed[-1]}')

# ── 2. Scrape BBRef draft pages for player profile URLs ───────────────────────
draft_cache: dict = load_json(DRAFT_CACHE)
cached_classes = [y for y in draft_years_needed if str(y) in draft_cache]
print(f'\nDraft cache: {len(cached_classes)}/{len(draft_years_needed)} classes already loaded')

for draft_year in draft_years_needed:
    key = str(draft_year)
    if key in draft_cache:
        continue

    url = f'{BASE}/draft/NBA_{draft_year}.html'
    print(f'Scraping {draft_year} draft... ({url})')
    html = fetch_html(url)
    if not html:
        draft_cache[key] = {}
        continue

    table = find_table(html, 'stats')
    if table is None:
        print(f'  No "stats" table found for {draft_year}')
        draft_cache[key] = {}
        continue

    players = {}
    for row in table.find_all('tr'):
        td = row.find('td', {'data-stat': 'player'})
        if td:
            a = td.find('a')
            if a and a.get('href'):
                name = a.get_text(strip=True)
                href = a['href']   # e.g. /players/j/jamesle01.html
                if name:
                    players[name] = href

    print(f'  {len(players)} players found')
    draft_cache[key] = players

save_json(DRAFT_CACHE, draft_cache)
print(f'Draft cache saved → {DRAFT_CACHE}')

# Build normalized-name → (canonical_name, url_path) lookup
# Also build name → pick number (dict insertion order = draft board order)
name_to_url: dict[str, tuple[str, str]] = {}
name_to_pick: dict[str, int] = {}
for draft_year_str, players in draft_cache.items():
    for pick_num, (name, url_path) in enumerate(players.items(), 1):
        key = norm_name(name)
        if key not in name_to_url:
            name_to_url[key] = (name, url_path)
        if key not in name_to_pick:
            name_to_pick[key] = pick_num

# ── 3. Scrape college stats for each rookie ───────────────────────────────────
college_cache: dict = load_json(COLLEGE_CACHE)
cached_players = sum(1 for v in college_cache.values() if v is not None)
print(f'\nCollege cache: {len(college_cache)} players loaded '
      f'({cached_players} with data, {len(college_cache)-cached_players} no college)')

all_rookie_names = rookie_ratings['Player'].tolist()
new_scrapes = 0

for player_name in all_rookie_names:
    if player_name in college_cache:
        continue

    nname = norm_name(player_name)
    match = name_to_url.get(nname)

    if match is None:
        # Try stripping suffixes like Jr., Sr., III
        alt = re.sub(r'\s+(jr\.?|sr\.?|ii+|iv|v)$', '', nname)
        match = name_to_url.get(alt)

    if match is None:
        print(f'  [no draft match] {player_name}')
        college_cache[player_name] = None
        continue

    _, url_path = match
    url = BASE + url_path
    print(f'  Fetching {player_name} → {url}')
    html = fetch_html(url)
    if not html:
        college_cache[player_name] = None
        continue

    table = find_table(html, 'all_college_stats')
    if table is None:
        # No college stats on this page (international/HS player)
        college_cache[player_name] = None
        print(f'    → no college_stats table')
        continue

    try:
        df = pd.read_html(StringIO(str(table)))[0]
    except Exception as e:
        print(f'    → parse error: {e}')
        college_cache[player_name] = None
        continue

    # all_college_stats has multi-level columns:
    #   Level 0 groups: (unnamed), Totals, Shooting, Per Game
    #   Level 1 stat:   Season/Age/College/G/MP, FG/FGA/…, FG%/3P%/FT%, MP/PTS/TRB/AST
    if isinstance(df.columns, pd.MultiIndex):
        flat = []
        for level0, level1 in df.columns:
            if 'Unnamed' in str(level0):
                flat.append(str(level1))          # Season, Age, College, G, MP(total)
            else:
                flat.append(f'{level0}_{level1}') # Totals_FG, Shooting_FG%, Per Game_MP
        df.columns = flat
    else:
        df.columns = [str(c) for c in df.columns]

    # Keep only rows with a real season label (drop Career, Did Not Play, etc.)
    df['Season'] = df['Season'].astype(str)
    df = df[df['Season'].str.match(r'^\d{4}-\d{2}$', na=False)]

    if df.empty:
        college_cache[player_name] = None
        print(f'    → no valid season rows')
        continue

    # Last row = final college season
    last = df.iloc[-1]

    def safe_float(val):
        if val is None:
            return None
        try:
            f = float(val)
            return None if pd.isna(f) else f
        except (ValueError, TypeError):
            return None

    g = safe_float(last.get('G'))
    row = {'G': g}

    # Totals columns → divide by G to get per-game
    for col in ['FG', 'FGA', '3P', '3PA', 'FT', 'FTA',
                'ORB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']:
        val = safe_float(last.get(f'Totals_{col}'))
        row[col] = (val / g) if (val is not None and g and g > 0) else None

    # Shooting percentages (already per-game ratios)
    for short, key in [('FG%', 'Shooting_FG%'), ('3P%', 'Shooting_3P%'), ('FT%', 'Shooting_FT%')]:
        row[short] = safe_float(last.get(key))

    # Per-game minutes
    row['MP'] = safe_float(last.get('Per Game_MP'))

    college_cache[player_name] = row
    new_scrapes += 1
    print(f'    → stats captured ({new_scrapes} new this run)')

    # Checkpoint every 20 scrapes
    if new_scrapes % 20 == 0:
        save_json(COLLEGE_CACHE, college_cache)
        print(f'    [checkpoint saved]')

save_json(COLLEGE_CACHE, college_cache)
print(f'College cache saved → {COLLEGE_CACHE}  ({new_scrapes} new entries)')

# ── 4. Build calibration dataset ──────────────────────────────────────────────
# Map BBRef college stat column names to clean names
# BBRef uses: G, MP, FG, FGA, FG%, 3P, 3PA, 3P%, FT, FTA, FT%,
#             ORB, DRB, TRB, AST, STL, BLK, TOV, PF, PTS
STAT_MAP = {
    'G': 'c_G', 'MP': 'c_MP',
    'FG': 'c_FG', 'FGA': 'c_FGA', 'FG%': 'c_FGpct',
    '3P': 'c_3P', '3PA': 'c_3PA', '3P%': 'c_3Ppct',
    'FT': 'c_FT', 'FTA': 'c_FTA', 'FT%': 'c_FTpct',
    'ORB': 'c_ORB', 'TRB': 'c_TRB',
    'AST': 'c_AST', 'STL': 'c_STL', 'BLK': 'c_BLK',
    'TOV': 'c_TOV', 'PF': 'c_PF', 'PTS': 'c_PTS',
}

rows = []
no_college = 0

for _, rrow in rookie_ratings.iterrows():
    player = rrow['Player']
    cstats = college_cache.get(player)

    if cstats is None:
        no_college += 1
        continue

    record = {
        'Player':      player,
        'RookieYear':  rrow['RookieYear'],
        'Team':        rrow['Team'],
        '2PS':         rrow['2PS'],
        '3PS':         rrow['3PS'],
        'DEF':         rrow['DEF'],
        'REB':         rrow['REB'],
        'OVR':         rrow['OVR'],
    }

    for raw_col, clean_col in STAT_MAP.items():
        val = cstats.get(raw_col)
        record[clean_col] = float(val) if val is not None else np.nan

    # Derived college features
    try:
        fg  = record.get('c_FG',  np.nan)
        tp  = record.get('c_3P',  np.nan)
        fga = record.get('c_FGA', np.nan)
        record['c_2P']    = fg - tp if not (np.isnan(fg) or np.isnan(tp)) else np.nan
        record['c_2PA']   = fga - record.get('c_3PA', np.nan) if not np.isnan(fga) else np.nan
        record['c_2Ppct'] = record['c_2P'] / record['c_2PA'] if (
            not np.isnan(record['c_2P']) and record['c_2PA'] and record['c_2PA'] > 0
        ) else np.nan
    except Exception:
        record['c_2P'] = record['c_2PA'] = record['c_2Ppct'] = np.nan

    # Draft pick position — use 1/pick so the value curve is nonlinear:
    # pick 1 → 1.0, pick 5 → 0.2, pick 30 → 0.033 (matches real draft value drop-off)
    nname = norm_name(player)
    pick = name_to_pick.get(nname)
    if pick is None:
        alt = re.sub(r'\s+(jr\.?|sr\.?|ii+|iv|v)$', '', nname)
        pick = name_to_pick.get(alt)
    record['c_inv_pick'] = (1.0 / pick) if pick is not None else np.nan

    rows.append(record)

cal = pd.DataFrame(rows)
print(f'\nCalibration dataset: {len(cal)} rows '
      f'({no_college} rookies had no college stats and were excluded)')

cal.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print(f'Saved → {OUTPUT_FILE}')

if cal.empty:
    print('\nNo calibration rows — re-run after populating college_stats_cache.json.')
    sys.exit(0)

# ── 5. Analysis ───────────────────────────────────────────────────────────────
targets  = ['2PS', '3PS', 'DEF', 'REB', 'OVR']
features = [c for c in cal.columns if c.startswith('c_')]

# Coerce all to numeric
for col in features + targets:
    cal[col] = pd.to_numeric(cal[col], errors='coerce')

cal_clean = cal.dropna(subset=features + targets)
print(f'Complete cases for regression: {len(cal_clean)} / {len(cal)}')

if len(cal_clean) < 10:
    print('\nToo few complete cases for meaningful analysis.')
    print('Tip: run with fewer features or fill missing college stats.')
    sys.exit(0)

# ── Correlations ──────────────────────────────────────────────────────────────
print('\n' + '='*65)
print('CORRELATIONS  (college stat → NBA year-1 rating)')
print('='*65)
corr = cal_clean[features + targets].corr()
for t in targets:
    col_corr = corr[t][features].dropna().sort_values(ascending=False)
    top = col_corr.head(6)
    bottom = col_corr.tail(3)
    print(f'\n  {t}:')
    for feat, r in top.items():
        bar = '█' * int(abs(r) * 20) + ('↑' if r >= 0 else '↓')
        print(f'    {feat:<14s}  r = {r:+.3f}  {bar}')
    print(f'    ...')
    for feat, r in bottom.items():
        bar = '█' * int(abs(r) * 20) + ('↑' if r >= 0 else '↓')
        print(f'    {feat:<14s}  r = {r:+.3f}  {bar}')

# ── OLS regression ────────────────────────────────────────────────────────────
components = ['2PS', '3PS', 'DEF', 'REB']

print('\n' + '='*65)
print('OLS REGRESSION — Stage 1: OVR')
print('='*65)

X_raw = cal_clean[features].values
X     = np.column_stack([np.ones(len(X_raw)), X_raw])

y = cal_clean['OVR'].values
beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
y_hat  = X @ beta
ss_res = np.sum((y - y_hat) ** 2)
ss_tot = np.sum((y - np.mean(y)) ** 2)
r2     = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
print(f'\n  OVR  (R² = {r2:.3f}, n = {len(y)}):')
coefs = pd.Series(beta[1:], index=features)
for feat in coefs.abs().sort_values(ascending=False).head(5).index:
    print(f'    {feat:<14s}  β = {coefs[feat]:+.4f}')
print(f'    intercept    β = {beta[0]:+.4f}')

print('\n' + '='*65)
print('OLS REGRESSION — Stage 2: Component shares (comp/OVR)')
print('='*65)

for comp in components:
    share_col = f'share_{comp}'
    cal_clean = cal_clean.copy()
    cal_clean[share_col] = cal_clean[comp] / cal_clean['OVR']
    y_s = cal_clean[share_col].values
    beta_s, _, _, _ = np.linalg.lstsq(X, y_s, rcond=None)
    y_hat_s  = X @ beta_s
    ss_res_s = np.sum((y_s - y_hat_s) ** 2)
    ss_tot_s = np.sum((y_s - np.mean(y_s)) ** 2)
    r2_s     = 1 - ss_res_s / ss_tot_s if ss_tot_s > 0 else 0.0
    print(f'\n  {comp} share  (R² = {r2_s:.3f}, mean share = {y_s.mean():.3f}):')
    coefs_s = pd.Series(beta_s[1:], index=features)
    for feat in coefs_s.abs().sort_values(ascending=False).head(5).index:
        print(f'    {feat:<14s}  β = {coefs_s[feat]:+.4f}')

# ── Summary ───────────────────────────────────────────────────────────────────
print('\n' + '='*65)
print('SUMMARY')
print('='*65)
print(f'  Rookies in dataset       : {len(rookie_ratings)}')
print(f'  With college stats found : {len(cal)}')
print(f'  Complete cases (all cols): {len(cal_clean)}')
print(f'  Calibration file         : {OUTPUT_FILE}')
print()
print('Next step: inspect calibration_data.csv to identify which college')
print('stats best predict each rating, then build a rating estimator for')
print('incoming 2026-27 rookies.')
