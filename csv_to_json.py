"""
csv_to_json.py

Converts nba_11_26_ratings.csv to nba_rosters_all.json.

Output structure:
  { "2026": { "DEN": [{name, t_2pt, t_3pt, t_def, t_reb}, ...], ... }, ... }
"""

import io
import json
import sys

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SOURCE = 'bbref_ratings.csv'
OUTPUT = 'nba_rosters_all.json'

df = pd.read_csv(SOURCE, encoding='utf-8-sig')
print(f'Loaded {len(df)} rows from {SOURCE}')

def fix_name(s):
    """Reverse double-encoding: UTF-8 bytes misread as Latin-1 then re-encoded as UTF-8."""
    try:
        return s.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

all_data = {}

for year in sorted(df['Year'].unique()):
    year_df = df[df['Year'] == year]
    year_data = {}
    for team in sorted(year_df['Team'].unique()):
        team_df = year_df[year_df['Team'] == team]
        year_data[team] = [
            {
                'name':  fix_name(row['Player']),
                't_2pt': int(row['2PS']),
                't_3pt': int(row['3PS']),
                't_def': int(row['DEF']),
                't_reb': int(row['REB']),
            }
            for _, row in team_df.iterrows()
        ]
    all_data[str(year)] = year_data

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, separators=(',', ':'))

seasons = len(all_data)
teams   = len(next(iter(all_data.values())))
players = sum(len(p) for yr in all_data.values() for p in yr.values())
print(f'Done. {seasons} seasons × {teams} teams × 15 players = {players} player entries → {OUTPUT}')
