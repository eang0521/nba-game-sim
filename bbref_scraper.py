"""
bbref_scraper.py

Scrapes per-game and advanced stats from Basketball-Reference for NBA seasons
1986-87 through 2025-26 (and any custom range you set below).

Output: bbref_stats.csv

Columns:
  Season, Year, Player, Pos, Age, Team,
  GP, MPG, MP,
  FGM, FGA, 2PM, 2PA, 3PM, 3PA,
  TRB, AST, STL, BLK,
  TRB%, BPM, WS/48, VORP

Notes:
  - Players traded mid-season appear once using their 'TOT' (total) row.
  - BBRef allows ~20 requests/min; this script waits 4 s between each fetch.
  - 2011-12 was a lockout-shortened season; stats are still available normally.
"""

import io
import sys
import time
from io import StringIO

# Force UTF-8 output so accented player names don't crash on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

# ── Configuration ─────────────────────────────────────────────────────────────

# End-year of each season to scrape (2012 = 2011-12 season)
SEASONS = list(range(1987, 2027))

OUTPUT_FILE = 'bbref_stats.csv'

# Seconds between HTTP requests — keep at 4+ to respect BBRef's rate limit
DELAY = 4

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def season_label(year: int) -> str:
    """Convert end-year to season label: 2012 → '2011-12'."""
    return f'{year - 1}-{str(year)[2:]}'


def fetch_table(url: str, table_id: str) -> pd.DataFrame | None:
    """
    Fetch a BBRef HTML table by its id attribute.
    Handles tables that BBRef hides inside HTML comments.
    Returns a raw DataFrame or None on failure.
    """
    time.sleep(DELAY)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f'    ERROR fetching {url}: {e}')
        return None

    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', id=table_id)

    # Some BBRef tables are wrapped in HTML comments — unwrap and search
    if table is None:
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            csoup = BeautifulSoup(comment, 'html.parser')
            table = csoup.find('table', id=table_id)
            if table:
                break

    if table is None:
        print(f'    WARNING: table #{table_id} not found at {url}')
        return None

    return pd.read_html(StringIO(str(table)))[0]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Remove repeated header rows (BBRef inserts these every 20 rows: Rk == 'Rk')
    - Strip Hall-of-Fame asterisks from player names
    - For traded players: BBRef shows an aggregate row labelled '2TM', '3TM',
      '4TM', etc., followed by one row per individual team in chronological
      order. We keep the aggregate row for stats (it has the season totals)
      but replace the '2TM'/'3TM' label with the actual team the player
      finished on — which is always the LAST individual team row.
    """
    df = df.copy()

    # Drop repeated header rows
    df = df[df['Rk'].astype(str) != 'Rk']
    df = df.dropna(subset=['Player'])
    df['Team'] = df['Team'].astype(str)

    # Strip trailing asterisk (Hall of Fame marker on older seasons)
    df['Player'] = df['Player'].str.replace(r'\*$', '', regex=True).str.strip()

    # Identify aggregate rows: '2TM', '3TM', '4TM', etc.
    is_agg = df['Team'].str.fullmatch(r'\dTM')

    # BBRef lists individual team rows in chronological order, so the LAST
    # non-aggregate row for each traded player = the team they finished with.
    final_team = (
        df[~is_agg]
        .groupby('Player', sort=False)['Team']
        .last()
    )

    traded = set(df.loc[is_agg, 'Player'])

    # Replace '2TM'/'3TM'/etc. with the player's actual final team
    df.loc[is_agg, 'Team'] = df.loc[is_agg, 'Player'].map(final_team)

    # Drop the now-redundant individual team rows for traded players
    df = df[~(df['Player'].isin(traded) & ~is_agg)]

    return df.reset_index(drop=True)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce')


# ── Main scrape loop ──────────────────────────────────────────────────────────

all_seasons = []

for year in SEASONS:
    label = season_label(year)
    print(f'\n--- {label} ---')

    # ── Totals stats ──────────────────────────────────────────────────────────
    pg_url = f'https://www.basketball-reference.com/leagues/NBA_{year}_totals.html'
    print(f'  Fetching totals stats …')
    pg_raw = fetch_table(pg_url, 'totals_stats')
    if pg_raw is None:
        print(f'  Skipping {label} (no totals table).')
        continue
    pg = clean(pg_raw)

    # Rename to consistent names; MP here = total season minutes
    pg = pg.rename(columns={
        'G':  'GP',
        'FG': 'FGM',
        '3P': '3PM',
    })

    pg_cols = ['Player', 'Pos', 'Age', 'Team', 'GP', 'MP',
               'FGM', 'FGA', '3PM', '3PA', 'TRB', 'AST', 'STL', 'BLK', 'PTS']
    pg = pg[[c for c in pg_cols if c in pg.columns]]

    # ── Advanced stats ────────────────────────────────────────────────────────
    adv_url = f'https://www.basketball-reference.com/leagues/NBA_{year}_advanced.html'
    print(f'  Fetching advanced stats …')
    adv_raw = fetch_table(adv_url, 'advanced')
    if adv_raw is None:
        print(f'  Skipping {label} (no advanced table).')
        continue
    adv = clean(adv_raw)

    # Drop blank separator columns BBRef inserts between stat groups
    adv = adv.loc[:, ~adv.columns.astype(str).str.match(r'^Unnamed')]
    adv.columns = [str(c).strip() for c in adv.columns]

    # Drop MP from advanced — totals table already has it
    adv_cols = ['Player', 'Team', 'TRB%', 'BPM', 'WS/48', 'VORP']
    adv = adv[[c for c in adv_cols if c in adv.columns]]

    # ── Merge totals + advanced on Player + Team ──────────────────────────────
    merged = pd.merge(pg, adv, on=['Player', 'Team'], how='left')

    # Convert everything numeric
    num_cols = ['GP', 'MP', 'FGM', 'FGA', '3PM', '3PA',
                'TRB', 'AST', 'STL', 'BLK', 'PTS', 'TRB%', 'BPM', 'WS/48', 'VORP']
    for col in num_cols:
        if col in merged.columns:
            merged[col] = to_num(merged[col])

    # Derive MPG from totals
    merged['MPG'] = (merged['MP'] / merged['GP']).round(1)

    # Derive 2-point makes and attempts from field goal totals
    merged['2PM'] = merged['FGM'] - merged['3PM']
    merged['2PA'] = merged['FGA'] - merged['3PA']

    merged.insert(0, 'Season', label)
    merged.insert(1, 'Year',   year)

    all_seasons.append(merged)
    print(f'  → {len(merged)} player rows collected')

# ── Write output ──────────────────────────────────────────────────────────────

if not all_seasons:
    print('\nNo data collected. Exiting.')
    sys.exit(1)

final = pd.concat(all_seasons, ignore_index=True)

col_order = [
    'Season', 'Year', 'Player', 'Pos', 'Age', 'Team',
    'GP', 'MPG', 'MP',
    'FGM', 'FGA', '2PM', '2PA', '3PM', '3PA', 'PTS',
    'TRB', 'AST', 'STL', 'BLK',
    'TRB%', 'BPM', 'WS/48', 'VORP',
]
final = final[[c for c in col_order if c in final.columns]]

final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print(f'\nDone. {len(final)} player-seasons saved to {OUTPUT_FILE}')
