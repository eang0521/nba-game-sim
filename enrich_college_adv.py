"""
enrich_college_adv.py

Fetches college advanced stats from CBB Reference (sports-reference.com/cbb)
for all players in calibration_data.csv, then adds new columns to the CSV.

New columns added:
  c_TSp    – True Shooting %
  c_USGp   – Usage rate
  c_STLp   – Steal %
  c_BLKp   – Block %
  c_ASTp   – Assist %
  c_TOVp   – Turnover %
  c_ORBp   – Offensive rebound %
  c_DRBp   – Defensive rebound %
  c_BPM    – Box Plus/Minus
  c_OBPM   – Offensive BPM
  c_DBPM   – Defensive BPM
  c_3PAr   – 3-point attempt rate (3PA/FGA) — also derivable but more accurate here
  c_FTr    – Free-throw attempt rate (FTA/FGA)

Run with: py enrich_college_adv.py
First run: ~90-120 min (network). Subsequent runs: instant (cached).
Progress saved every 10 new scrapes so you can interrupt and resume.
"""

import io, sys, json, time, os, re, unicodedata
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup, Comment
from io import StringIO

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DELAY   = 4
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}
CBB_BASE   = 'https://www.sports-reference.com/cbb/players'
CAL_FILE   = 'calibration_data.csv'
ADV_CACHE  = 'college_adv_cache.json'

# Columns to extract from players_advanced table
ADV_COLS = {
    'c_TSp':  'TS%',
    'c_USGp': 'USG%',
    'c_STLp': 'STL%',
    'c_BLKp': 'BLK%',
    'c_ASTp': 'AST%',
    'c_TOVp': 'TOV%',
    'c_ORBp': 'ORB%',
    'c_DRBp': 'DRB%',
    'c_BPM':  'BPM',
    'c_OBPM': 'OBPM',
    'c_DBPM': 'DBPM',
    'c_3PAr': '3PAr',
    'c_FTr':  'FTr',
}


def cbb_urls(full_name: str) -> list[str]:
    """Generate CBB Reference URL variants. CBB keeps 'jr'/'sr' in URLs."""
    s = unicodedata.normalize('NFD', full_name).encode('ascii', 'ignore').decode().lower()
    has_jr = bool(re.search(r'\bjr\.?\b', s))
    has_sr = bool(re.search(r'\bsr\.?\b', s))
    base = re.sub(r'\b(jr\.?|sr\.?|ii|iii|iv)\b', '', s)
    base = re.sub(r"[^a-z\s]", '', base)
    base = re.sub(r'\s+', '-', base.strip()).strip('-')
    urls = []
    for n in range(1, 3):
        if has_jr:
            urls.append(f'{CBB_BASE}/{base}-jr-{n}.html')
        if has_sr:
            urls.append(f'{CBB_BASE}/{base}-sr-{n}.html')
        urls.append(f'{CBB_BASE}/{base}-{n}.html')
    return urls


def fetch_html(url: str) -> str | None:
    time.sleep(DELAY)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f'    ERROR: {e}')
        return None


def safe_float(val) -> float | None:
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (ValueError, TypeError):
        return None


def load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(path: str, data: dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_adv_table(html: str) -> dict:
    """Find players_advanced table in comments, extract last valid season row."""
    soup = BeautifulSoup(html, 'html.parser')
    table = None
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        cs = BeautifulSoup(comment, 'html.parser')
        table = cs.find('table', id='players_advanced')
        if table:
            break
    if table is None:
        return {}

    try:
        df = pd.read_html(StringIO(str(table)))[0]
    except Exception:
        return {}

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            str(l1) if 'Unnamed' in str(l0) else f'{l0}_{l1}'
            for l0, l1 in df.columns
        ]
    else:
        df.columns = [str(c) for c in df.columns]

    df['Season'] = df['Season'].astype(str)
    df = df[df['Season'].str.match(r'^\d{4}-\d{2}$', na=False)]
    if df.empty:
        return {}

    last = df.iloc[-1]
    result = {}
    for dest, src in ADV_COLS.items():
        val = safe_float(last.get(src))
        if val is not None:
            result[dest] = val
    return result


def fetch_adv_stats(full_name: str) -> dict:
    """Try CBB Reference URL variants until we find one with an advanced table."""
    for url in cbb_urls(full_name):
        html = fetch_html(url)
        if html is None:
            continue
        result = parse_adv_table(html)
        if result:
            print(f'    → found ({len(result)} stats)')
            return result
        # Page exists but no advanced data — might be wrong player, keep trying
    return {}


# ── Main ─────────────────────────────────────────────────────────────────────

cal = pd.read_csv(CAL_FILE, encoding='utf-8-sig')
print(f'Calibration data: {len(cal)} players  ({cal["RookieYear"].min()}–{cal["RookieYear"].max()})')

adv_cache = load_json(ADV_CACHE)
already_cached = sum(1 for n in cal['Player'] if n in adv_cache)
todo = [row['Player'] for _, row in cal.iterrows() if row['Player'] not in adv_cache]
print(f'Already cached: {already_cached}/{len(cal)}  |  Remaining: {len(todo)}')

if todo:
    print(f'\nEstimated time: ~{len(todo)*DELAY//60} min\n')

new_scrapes = 0
for name in todo:
    print(f'  {name}')
    adv_cache[name] = fetch_adv_stats(name)
    new_scrapes += 1

    if new_scrapes % 10 == 0:
        save_json(ADV_CACHE, adv_cache)
        print(f'\n  [checkpoint: {new_scrapes} new scrapes]\n')

save_json(ADV_CACHE, adv_cache)
print(f'\nDone. {new_scrapes} new entries scraped.')

# ── Enrich calibration_data.csv ───────────────────────────────────────────────
all_dest_cols = list(ADV_COLS.keys())
for col in all_dest_cols:
    if col not in cal.columns:
        cal[col] = np.nan

rows_enriched = 0
for i, row in cal.iterrows():
    entry = adv_cache.get(row['Player'], {})
    if not entry:
        continue
    for col in all_dest_cols:
        if col in entry:
            cal.at[i, col] = entry[col]
    rows_enriched += 1

print(f'Enriched {rows_enriched} rows.')
print('\nCoverage per column:')
for col in all_dest_cols:
    n = cal[col].notna().sum()
    pct = 100 * n / len(cal)
    print(f'  {col:<10} {n:>3}/{len(cal)}  ({pct:.0f}%)')

cal.to_csv(CAL_FILE, index=False, encoding='utf-8-sig')
print(f'\nSaved updated {CAL_FILE}')
print('Next: re-run predict_rookies.py to retrain with new features.')
