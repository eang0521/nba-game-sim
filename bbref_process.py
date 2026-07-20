"""
bbref_process.py

Reads bbref_stats.csv, selects the top 15 players per team per season
by a minutes-based importance metric, and writes bbref_roster.csv.

Metric: MPG * (MP / 1000)

Team-seasons with fewer than 15 players (caused by traded players being
assigned to their final team, or genuinely small lockout-era rosters)
are padded with [Filler] rows carrying zero stats. Fillers rank dead
last in any rating calculation and serve only to satisfy the simulator's
requirement of exactly 15 players per team.
"""

import io
import shutil
import sys

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Config ────────────────────────────────────────────────────────────────────
SOURCE = 'bbref_stats.csv'
WORK   = 'bbref_work.csv'
OUTPUT = 'bbref_roster.csv'
TOP_N  = 15

# ── 1. Copy source ────────────────────────────────────────────────────────────
shutil.copy(SOURCE, WORK)
print(f'Copied {SOURCE} -> {WORK}\n')

# ── 2. Load and compute metric ────────────────────────────────────────────────
df = pd.read_csv(WORK, encoding='utf-8-sig')
df['metric'] = df['MPG'] * (df['MP'] / 1000)
print(f'Loaded {len(df)} player-seasons\n')

# ── 3. Pad deficient team-seasons with filler rows ───────────────────────────
counts = df.groupby(['Year', 'Team']).size().reset_index(name='n')
short  = counts[counts['n'] < TOP_N]

if short.empty:
    print('All team-seasons have 15+ players. No padding needed.\n')
else:
    print(f'Padding {len(short)} team-season(s) with filler rows:')
    filler_rows = []

    for _, row in short.iterrows():
        year   = int(row['Year'])
        team   = row['Team']
        n_need = TOP_N - int(row['n'])
        season = f'{year - 1}-{str(year)[2:]}'

        for i in range(n_need):
            filler_rows.append({
                'Season': season, 'Year': year,
                'Player': f'[Filler {i + 1}]',
                'Pos': None, 'Age': None, 'Team': team,
                'GP': 0, 'MPG': 0.0, 'MP': 0.0,
                'FGM': 0, 'FGA': 0, '2PM': 0, '2PA': 0,
                '3PM': 0, '3PA': 0,
                'TRB': 0.0, 'AST': 0.0, 'STL': 0.0, 'BLK': 0.0,
                'TRB%': None, 'BPM': None, 'WS/48': None, 'VORP': None,
                'metric': 0.0,
            })

        print(f'  {team} {year}: added {n_need} filler row(s)')

    df = pd.concat([df, pd.DataFrame(filler_rows)], ignore_index=True)
    print(f'\nTotal after padding: {len(df)} rows\n')

# ── 4. Filter to top 15 per team per season ───────────────────────────────────
roster = (
    df
    .sort_values('metric', ascending=False)
    .groupby(['Year', 'Team'], group_keys=False)
    .head(TOP_N)
    .sort_values(['Year', 'Team', 'metric'], ascending=[True, True, False])
    .reset_index(drop=True)
)

# ── 5. Audit ──────────────────────────────────────────────────────────────────
counts_after = roster.groupby(['Year', 'Team']).size().reset_index(name='n')
still_short  = counts_after[counts_after['n'] < TOP_N]
filler_count = roster['Player'].str.startswith('[Filler').sum()

print(f'Final roster:')
print(f'  Total rows      : {len(roster)}')
expected = int(roster.groupby('Year')['Team'].nunique().mul(TOP_N).sum())
print(f'  Expected        : {expected}')
print(f'  Still under 15  : {len(still_short)}')
print(f'  Filler rows     : {filler_count}')

# ── 6. Save ───────────────────────────────────────────────────────────────────
roster.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
print(f'\nSaved {len(roster)} rows to {OUTPUT}')
