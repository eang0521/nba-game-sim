"""
scrape_ages.py

Fetches birthdate for every player in college_stats_cache.json (those with
a BBRef URL in draft_links_cache.json) and computes their age as of the
start of the target NBA season (default: 2026-10-01).

Output: player_ages_cache.json — {player_name: {birthdate, age}}

Re-run safely: skips players already in the cache.
"""

import io, sys, json, time, unicodedata, os, re
import requests
from bs4 import BeautifulSoup
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Config ────────────────────────────────────────────────────────────────────
SEASON_START  = date(2026, 10, 1)   # age as of this date
DELAY         = 4
HEADERS       = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}
BASE          = 'https://www.basketball-reference.com'
DRAFT_CACHE   = 'draft_links_cache.json'
COLLEGE_CACHE = 'college_stats_cache.json'
AGES_CACHE    = 'player_ages_cache.json'

# ── Helpers ───────────────────────────────────────────────────────────────────

def norm_name(n: str) -> str:
    n = unicodedata.normalize('NFD', n).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', n).lower().strip()

def load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(path: str, data: dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def compute_age(birthdate_str: str) -> int | None:
    try:
        bd = date.fromisoformat(birthdate_str)
        return (SEASON_START - bd).days // 365
    except Exception:
        return None

def fetch_birthdate(url: str) -> str | None:
    time.sleep(DELAY)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f'  ERROR {url}: {e}')
        return None
    soup = BeautifulSoup(r.text, 'html.parser')
    span = soup.find('span', id='necro-birth')
    if span and span.get('data-birth'):
        return span['data-birth']
    # Fallback: search for data-birth attribute anywhere
    tag = soup.find(attrs={'data-birth': True})
    return tag['data-birth'] if tag else None

# ── Load caches ───────────────────────────────────────────────────────────────
draft_cache   = load_json(DRAFT_CACHE)
college_cache = load_json(COLLEGE_CACHE)
ages_cache    = load_json(AGES_CACHE)

# Build normalized-name → url lookup from draft cache
name_to_url: dict[str, str] = {}
for players in draft_cache.values():
    for name, url_path in players.items():
        key = norm_name(name)
        if key not in name_to_url:
            name_to_url[key] = url_path

# Players to process: those with college data (not None) and a known URL
to_scrape = []
for player_name, cstats in college_cache.items():
    if player_name in ages_cache:
        continue                          # already have their age
    if cstats is None:
        continue                          # no college data, skip for now
    nname = norm_name(player_name)
    url_path = name_to_url.get(nname)
    if url_path is None:
        alt = re.sub(r'\s+(jr\.?|sr\.?|ii+|iv|v)$', '', nname)
        url_path = name_to_url.get(alt)
    if url_path:
        to_scrape.append((player_name, url_path))

print(f'Players with college data : {sum(1 for v in college_cache.values() if v)}')
print(f'Already in ages cache     : {len(ages_cache)}')
print(f'To scrape                 : {len(to_scrape)}')
print()

new_entries = 0
for i, (name, url_path) in enumerate(to_scrape, 1):
    url = BASE + url_path
    print(f'[{i}/{len(to_scrape)}] {name}')
    birthdate = fetch_birthdate(url)
    if birthdate:
        age = compute_age(birthdate)
        ages_cache[name] = {'birthdate': birthdate, 'age': age}
        print(f'  → {birthdate}  (age {age} on {SEASON_START})')
    else:
        ages_cache[name] = {'birthdate': None, 'age': None}
        print(f'  → birthdate not found')
    new_entries += 1

    if new_entries % 20 == 0:
        save_json(AGES_CACHE, ages_cache)
        print(f'  [checkpoint saved — {new_entries} new entries]')

save_json(AGES_CACHE, ages_cache)
print(f'\nDone. {new_entries} new entries added.')
print(f'Ages cache saved → {AGES_CACHE}  ({len(ages_cache)} total)')
