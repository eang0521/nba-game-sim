"""
bbref_rate.py

Reads bbref_roster.csv and applies the 29-step rating formula to produce
2PS, 3PS, DEF, REB, and OVR for every player-season.

Filler players skip steps 1-24 and receive all-zero ratings.

Output: bbref_ratings.csv
  Columns: Season, Year, Player, Team, 2PS, 3PS, DEF, REB, OVR
"""

import io
import sys

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

INPUT  = 'bbref_roster.csv'
OUTPUT = 'bbref_ratings.csv'

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_csv(INPUT, encoding='utf-8-sig')
print(f'Loaded {len(df)} rows from {INPUT}')

is_filler = df['Player'].str.startswith('[Filler')
real = df[~is_filler].copy().reset_index(drop=True)
fill = df[is_filler].copy().reset_index(drop=True)
print(f'  Real players : {len(real)}')
print(f'  Filler rows  : {len(fill)}\n')

# Coerce all needed columns to numeric, filling NaN with 0
num_cols = ['GP', 'MP', '2PM', '2PA', '3PM', '3PA',
            'PTS', 'TRB', 'AST', 'STL', 'BLK', 'TRB%', 'BPM', 'VORP']
for col in num_cols:
    if col in real.columns:
        real[col] = pd.to_numeric(real[col], errors='coerce').fillna(0)
    else:
        real[col] = 0.0
        print(f'WARNING: column {col!r} missing — defaulting to 0')

def stdz(x, mean, stdev):
    return (x - mean) / stdev

# Safe denominators (replace 0 with NaN so division yields NaN → fillna(0))
gp  = real['GP'].replace(0, np.nan)
mp  = real['MP'].replace(0, np.nan)

# ── Steps 1-8: Raw overall rating ────────────────────────────────────────────

# 1. Standardize BPM
v1 = stdz(real['BPM'], -0.95, 3.15)

# 2. Standardize VORP/game
v2 = stdz(real['VORP'] / gp, 0.01, 0.02).fillna(0)

# 2b. Standardize total VORP
v2b = stdz(real['VORP'], 0.65, 1.3)

# 3. min(v1, v2, v2b)
v3 = np.minimum(np.minimum(v1, v2), v2b)

# 4. Counting stats per game / 25
v4 = ((real['PTS'] + real['TRB'] + real['AST'] + real['STL'] + real['BLK'])
      / gp / 25).fillna(0)

# 5. v3 + v4
v5 = v3 + v4

# 6. Standardize v5
v6 = stdz(v5, 0.45, 1.25)

# 7. Raw OVR
v7 = v6 * 16 + 60

# 8. Floor at 0
v7 = np.maximum(v7, 0)

# ── Steps 9-16: Skill metrics ─────────────────────────────────────────────────

# 9. 2PM × (2PM/2PA) × (2PM/MP)
twoPA = real['2PA'].replace(0, np.nan)
v9 = (real['2PM'] * (real['2PM'] / twoPA) * (real['2PM'] / mp)).fillna(0)

# 10. Standardize v9 + 1
v10 = stdz(v9, 11.75, 15.65) + 1

# 11. 3PM × (3PM/3PA) × (3PM/MP)
threePA = real['3PA'].replace(0, np.nan)
v11 = (real['3PM'] * (real['3PM'] / threePA) * (real['3PM'] / mp)).fillna(0)

# 12. Standardize v11 + 1
v12 = stdz(v11, 1.35, 2.05) + 1

# 13. Stocks × (Stocks/MP)
stocks = real['STL'] + real['BLK']
v13 = (stocks * (stocks / mp)).fillna(0)

# 14. Standardize v13 + 1
v14 = stdz(v13, 4.0, 4.3) + 1

# 15. TRB × (TRB/MP) × (TRB%/100)
v15 = (real['TRB'] * (real['TRB'] / mp) * (real['TRB%'] / 100)).fillna(0)

# 16. Standardize v15 + 1
v16 = stdz(v15, 7.1, 12.9) + 1

# ── Steps 17-24: Weights ──────────────────────────────────────────────────────

# 17-20. Raise to power 0.3 (clip negatives to 0 to keep real numbers)
v17 = np.maximum(v10, 0) ** 0.3
v18 = np.maximum(v12, 0) ** 0.3
v19 = np.maximum(v14, 0) ** 0.3
v20 = np.maximum(v16, 0) ** 0.3

# 21-24. Normalize — fall back to equal weights if all are 0
total_w = v17 + v18 + v19 + v20
safe_w  = total_w.copy()
safe_w[safe_w == 0] = 1.0          # prevents /0; v17-v20 also 0 → ratings = 0

v21 = v17 / safe_w   # 2PS weight
v22 = v18 / safe_w   # 3PS weight
v23 = v19 / safe_w   # DEF weight
v24 = v20 / safe_w   # REB weight

# ── Steps 25-29: Final ratings ────────────────────────────────────────────────

real['2PS'] = (v7 * v21).round().astype(int)
real['3PS'] = (v7 * v22).round().astype(int)
real['DEF'] = (v7 * v23).round().astype(int)
real['REB'] = (v7 * v24).round().astype(int)
real['OVR'] = real['2PS'] + real['3PS'] + real['DEF'] + real['REB']

# Filler players: all zeros
for col in ['2PS', '3PS', 'DEF', 'REB', 'OVR']:
    fill[col] = 0

# ── Combine & save ────────────────────────────────────────────────────────────
out_cols = ['Season', 'Year', 'Player', 'Team', '2PS', '3PS', 'DEF', 'REB', 'OVR']
result = (
    pd.concat([real, fill], ignore_index=True)
    [out_cols]
    .sort_values(['Year', 'Team', 'OVR'], ascending=[True, True, False])
    .reset_index(drop=True)
)

result.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
print(f'Saved {len(result)} rows to {OUTPUT}\n')

# ── 2025-26 top 15 sanity check ───────────────────────────────────────────────
top = (result[result['Year'] == 2026]
       .sort_values('OVR', ascending=False)
       .head(15))
print('2025-26 top 15 by OVR:')
print(top[['Player', 'Team', '2PS', '3PS', 'DEF', 'REB', 'OVR']].to_string(index=False))
