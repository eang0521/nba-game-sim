#!/usr/bin/env python3
"""
Web interface for the NBA Game Simulator.

Install Flask first:  pip install flask
Then run:             python web_sim.py
Open:                 http://localhost:5000
"""

import html
import json
import os
import sys

try:
    from flask import Flask, render_template_string, request
except ImportError:
    sys.exit("Flask is required. Install it with:  pip install flask")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nba26_game_sim import Team, Game

app = Flask(__name__)
TEAMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nba_rosters26_v3.json")


def load_teams():
    with open(TEAMS_FILE) as f:
        return json.load(f)


def run_game(t1_abbr, t2_abbr):
    """Run a full simulation and return the completed Game object and per-quarter play logs."""
    teams_data = load_teams()
    t1 = Team(t1_abbr, teams_data[t1_abbr])
    t2 = Team(t2_abbr, teams_data[t2_abbr])
    game = Game(t1, t2)
    quarter_logs = {}

    # Patch at the instance level — no class-level side effects, no cleanup needed.
    def _log(message):
        score_str = (
            f" [{game.t1.abbr} {game.t1.score} – {game.t2.abbr} {game.t2.score}]"
            if any(w in message for w in ("makes", "scores"))
            else ""
        )
        quarter_logs.setdefault(game.quarter, []).append(
            f"{game.format_time()} {message}{score_str}".strip()
        )

    game.log = _log
    game.display_lineups = lambda: None

    for q in range(1, 5):
        game.quarter = q
        game.play_quarter(12)

    ot = 1
    while t1.score == t2.score:
        game.quarter = 4 + ot
        game.play_quarter(5)
        ot += 1

    return game, quarter_logs


def period_label(q):
    return f"Q{q}" if q <= 4 else f"OT{q - 4}"


def render_log_line(line):
    """Wrap a play-by-play line in a styled <span> based on event type."""
    safe = html.escape(line)
    lower = line.lower()
    if "makes" in lower or "and-1" in lower:
        css = "ev-make"
    elif "misses" in lower:
        css = "ev-miss"
    elif "steal" in lower:
        css = "ev-steal"
    elif "block" in lower:
        css = "ev-block"
    elif "foul" in lower or "free throw" in lower:
        css = "ev-foul"
    elif "rebound" in lower:
        css = "ev-reb"
    elif "sub:" in lower or "jumpball" in lower or "wins the" in lower:
        css = "ev-misc"
    else:
        css = "ev-neutral"
    return f'<span class="{css}">{safe}</span>'


TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NBA Game Simulator{% if game %} — {{ game.t1.abbr }} vs {{ game.t2.abbr }}{% endif %}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0f1117;
      color: #e2e8f0;
      min-height: 100vh;
    }

    /* ── Header ──────────────────────────────────────── */
    header {
      background: #141929;
      border-bottom: 3px solid #3b5bdb;
      padding: 1.1rem 2rem;
      display: flex;
      align-items: center;
      gap: 0.9rem;
    }
    header h1 { font-size: 1.3rem; font-weight: 800; letter-spacing: 0.04em; color: #fff; }
    header .badge {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #748ffc;
      background: #1e2d5a;
      padding: 0.25rem 0.6rem;
      border-radius: 999px;
    }

    .container { max-width: 1080px; margin: 0 auto; padding: 2rem 1.5rem; }

    /* ── Form card ───────────────────────────────────── */
    .form-card {
      background: #141929;
      border: 1px solid #1e2d5a;
      border-radius: 10px;
      padding: 1.25rem 1.75rem;
      margin-bottom: 2rem;
    }
    .form-card h2 {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #748ffc;
      margin-bottom: 1rem;
    }
    .form-row { display: flex; gap: 0.9rem; align-items: flex-end; flex-wrap: wrap; }
    .form-group { display: flex; flex-direction: column; gap: 0.3rem; }
    .form-group label {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #64748b;
    }
    select {
      background: #0f1117;
      color: #e2e8f0;
      border: 1px solid #2d3f6e;
      border-radius: 6px;
      padding: 0.5rem 0.75rem;
      font-size: 0.88rem;
      min-width: 130px;
      cursor: pointer;
    }
    select:focus { outline: 2px solid #748ffc; outline-offset: 1px; }
    .btn {
      background: #3b5bdb;
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 0.55rem 1.5rem;
      font-size: 0.88rem;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.15s;
      letter-spacing: 0.03em;
    }
    .btn:hover { background: #4c6ef5; }
    .btn:active { background: #2f4ac0; }

    .error {
      color: #fca5a5;
      background: #2d1616;
      border: 1px solid #7f1d1d;
      border-radius: 6px;
      padding: 0.75rem 1rem;
      margin-bottom: 1.5rem;
      font-size: 0.88rem;
    }

    /* ── Scoreboard ──────────────────────────────────── */
    .scoreboard {
      background: #141929;
      border: 1px solid #1e2d5a;
      border-radius: 10px;
      padding: 2rem 1.5rem 1.5rem;
      margin-bottom: 1.5rem;
      text-align: center;
    }
    .score-teams {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 2.5rem;
      margin-bottom: 0.5rem;
    }
    .score-team { display: flex; flex-direction: column; align-items: center; gap: 0.2rem; }
    .team-abbr { font-size: 1.35rem; font-weight: 800; letter-spacing: 0.12em; color: #c5d0fc; }
    .team-score { font-size: 4.5rem; font-weight: 900; line-height: 1.05; color: #fff; }
    .team-score.winner { color: #69db7c; }
    .score-sep { font-size: 2.5rem; color: #2d3a5c; padding-top: 1rem; }
    .final-label {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #64748b;
      margin-bottom: 1.5rem;
    }

    /* ── Linescore ───────────────────────────────────── */
    .linescore-wrap { overflow-x: auto; }
    .linescore { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .linescore th, .linescore td {
      padding: 0.45rem 0.8rem;
      text-align: center;
      border: 1px solid #1e2d5a;
    }
    .linescore th {
      background: #0f1117;
      color: #748ffc;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }
    .linescore td:first-child { text-align: left; font-weight: 700; color: #fff; }
    .linescore .total { font-weight: 800; font-size: 1rem; color: #fff; }

    /* ── Section headings ────────────────────────────── */
    section { margin-bottom: 2.25rem; }
    section > h2 {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #748ffc;
      margin-bottom: 0.75rem;
      padding-bottom: 0.4rem;
      border-bottom: 1px solid #1e2d5a;
    }

    /* ── Play-by-play ────────────────────────────────── */
    .pbp-list { display: flex; flex-direction: column; gap: 0.4rem; }
    details {
      background: #141929;
      border: 1px solid #1e2d5a;
      border-radius: 8px;
      overflow: hidden;
    }
    details[open] { border-color: #3b5bdb; }
    summary {
      padding: 0.7rem 1rem;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.88rem;
      color: #c5d0fc;
      user-select: none;
      list-style: none;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    summary::-webkit-details-marker { display: none; }
    summary::after { content: '▸'; color: #748ffc; font-size: 0.75rem; }
    details[open] summary::after { content: '▾'; }
    .play-count { color: #475569; font-size: 0.72rem; font-weight: 400; }
    .pbp-log {
      padding: 0.6rem 1rem 0.8rem;
      border-top: 1px solid #1e2d5a;
      font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
      font-size: 0.76rem;
      line-height: 1.85;
      max-height: 400px;
      overflow-y: auto;
    }
    .pbp-log span { display: block; }

    .ev-make    { color: #69db7c; }
    .ev-miss    { color: #4b5e7a; }
    .ev-foul    { color: #ffa94d; }
    .ev-steal   { color: #4dabf7; }
    .ev-block   { color: #da77f2; }
    .ev-reb     { color: #38d9a9; }
    .ev-misc    { color: #748ffc; font-style: italic; }
    .ev-neutral { color: #94a3b8; }

    /* ── Box score ───────────────────────────────────── */
    .box-team { margin-bottom: 1.75rem; }
    .box-team h3 {
      font-size: 0.8rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #c5d0fc;
      margin-bottom: 0.5rem;
    }
    .box-wrap { overflow-x: auto; border: 1px solid #1e2d5a; border-radius: 8px; }
    .box-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
      min-width: 680px;
    }
    .box-table th, .box-table td {
      padding: 0.45rem 0.7rem;
      text-align: center;
      border-bottom: 1px solid #1a2235;
      white-space: nowrap;
    }
    .box-table th {
      background: #0f1117;
      color: #748ffc;
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .box-table td:first-child { text-align: left; color: #e2e8f0; padding-left: 1rem; }
    .box-table tbody tr:hover td { background: #172035; }
    .box-table .totals-row td {
      background: #111827;
      border-top: 2px solid #3b5bdb;
      border-bottom: none;
      font-weight: 700;
      color: #fff;
    }
    .box-table .totals-row td:first-child { color: #748ffc; }
    .pos-tag { color: #475569; font-size: 0.68rem; margin-left: 0.3rem; }
    .pm-pos { color: #69db7c; font-weight: 700; }
    .pm-neg { color: #f87171; font-weight: 700; }
  </style>
</head>
<body>

<header>
  <h1>NBA Game Simulator</h1>
  <span class="badge">2026 Season</span>
</header>

<div class="container">

  <!-- Sim form -->
  <div class="form-card">
    <h2>Simulate a Game</h2>
    <form method="post" action="/">
      <div class="form-row">
        <div class="form-group">
          <label>Home Team</label>
          <select name="t1" required>
            {% for abbr in teams %}
              <option value="{{ abbr }}"{% if abbr == selected_t1 %} selected{% endif %}>{{ abbr }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="form-group">
          <label>Away Team</label>
          <select name="t2" required>
            {% for abbr in teams %}
              <option value="{{ abbr }}"{% if abbr == selected_t2 %} selected{% endif %}>{{ abbr }}</option>
            {% endfor %}
          </select>
        </div>
        <button class="btn" type="submit">Simulate</button>
      </div>
    </form>
  </div>

  {% if error %}
    <div class="error">{{ error }}</div>
  {% endif %}

  {% if game %}
    {% set t1_wins = game.t1.score > game.t2.score %}
    {% set num_periods = game.t1_q_scores | length %}

    <!-- Scoreboard + Linescore -->
    <div class="scoreboard">
      <div class="score-teams">
        <div class="score-team">
          <div class="team-abbr">{{ game.t1.abbr }}</div>
          <div class="team-score{% if t1_wins %} winner{% endif %}">{{ game.t1.score }}</div>
        </div>
        <div class="score-sep">–</div>
        <div class="score-team">
          <div class="team-abbr">{{ game.t2.abbr }}</div>
          <div class="team-score{% if not t1_wins %} winner{% endif %}">{{ game.t2.score }}</div>
        </div>
      </div>
      <div class="final-label">
        Final{% if num_periods > 4 %} / {{ num_periods - 4 }}OT{% endif %}
      </div>

      <div class="linescore-wrap">
        <table class="linescore">
          <thead>
            <tr>
              <th>Team</th>
              {% for i in range(num_periods) %}<th>{{ period_label(i + 1) }}</th>{% endfor %}
              <th>T</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ game.t1.abbr }}</td>
              {% for s in game.t1_q_scores %}<td>{{ s }}</td>{% endfor %}
              <td class="total">{{ game.t1.score }}</td>
            </tr>
            <tr>
              <td>{{ game.t2.abbr }}</td>
              {% for s in game.t2_q_scores %}<td>{{ s }}</td>{% endfor %}
              <td class="total">{{ game.t2.score }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Play-by-play -->
    <section>
      <h2>Play-by-Play</h2>
      <div class="pbp-list">
        {% for q in quarter_logs | sort %}
          <details{% if loop.last %} open{% endif %}>
            <summary>
              {{ period_label(q) }}
              <span class="play-count">{{ quarter_logs[q] | length }} plays</span>
            </summary>
            <div class="pbp-log">
              {% for line in quarter_logs[q] %}
                {{ render_log_line(line) | safe }}
              {% endfor %}
            </div>
          </details>
        {% endfor %}
      </div>
    </section>

    <!-- Box Score -->
    <section>
      <h2>Box Score</h2>
      {% for team in [game.t1, game.t2] %}
        <div class="box-team">
          <h3>{{ team.abbr }}</h3>
          <div class="box-wrap">
            <table class="box-table">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>MIN</th><th>PTS</th><th>FG</th><th>3PT</th><th>FT</th>
                  <th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>PF</th><th>+/-</th>
                </tr>
              </thead>
              <tbody>
                {# Accumulate totals via namespace so they persist across the loop #}
                {% set t = namespace(min=0, pts=0, fgm=0, fga=0, tpm=0, tpa=0, ftm=0, fta=0, reb=0, ast=0, stl=0, blk=0, pf=0, pm=0) %}
                {% for p in team.players | sort(attribute='seconds_played', reverse=True) %}
                  {% if p.seconds_played > 0 %}
                    {% set mp = (p.seconds_played / 60) | round | int %}
                    {% set pm_str = ('+' if p.plus_minus > 0 else '') + (p.plus_minus | string) %}
                    {% set t.min = t.min + mp %}
                    {% set t.pts = t.pts + p.points %}
                    {% set t.fgm = t.fgm + p.fg_made %}
                    {% set t.fga = t.fga + p.fg_attempted %}
                    {% set t.tpm = t.tpm + p.tpt_made %}
                    {% set t.tpa = t.tpa + p.tpt_attempted %}
                    {% set t.ftm = t.ftm + p.ft_made %}
                    {% set t.fta = t.fta + p.ft_attempted %}
                    {% set t.reb = t.reb + p.rebounds %}
                    {% set t.ast = t.ast + p.assists %}
                    {% set t.stl = t.stl + p.steals %}
                    {% set t.blk = t.blk + p.blocks %}
                    {% set t.pf  = t.pf  + p.fouls %}
                    {% set t.pm  = t.pm  + p.plus_minus %}
                    <tr>
                      <td>{{ p.name }}<span class="pos-tag">({{ p.get_primary_position_name() }})</span></td>
                      <td>{{ mp }}</td>
                      <td>{{ p.points }}</td>
                      <td>{{ p.fg_made }}-{{ p.fg_attempted }}</td>
                      <td>{{ p.tpt_made }}-{{ p.tpt_attempted }}</td>
                      <td>{{ p.ft_made }}-{{ p.ft_attempted }}</td>
                      <td>{{ p.rebounds }}</td>
                      <td>{{ p.assists }}</td>
                      <td>{{ p.steals }}</td>
                      <td>{{ p.blocks }}</td>
                      <td>{{ p.fouls }}</td>
                      <td class="{{ 'pm-pos' if p.plus_minus > 0 else ('pm-neg' if p.plus_minus < 0 else '') }}">{{ pm_str }}</td>
                    </tr>
                  {% endif %}
                {% endfor %}
                {% set t_pm_str = ('+' if t.pm > 0 else '') + (t.pm | string) %}
                <tr class="totals-row">
                  <td>TOTALS</td>
                  <td>{{ t.min }}</td>
                  <td>{{ t.pts }}</td>
                  <td>{{ t.fgm }}-{{ t.fga }}</td>
                  <td>{{ t.tpm }}-{{ t.tpa }}</td>
                  <td>{{ t.ftm }}-{{ t.fta }}</td>
                  <td>{{ t.reb }}</td>
                  <td>{{ t.ast }}</td>
                  <td>{{ t.stl }}</td>
                  <td>{{ t.blk }}</td>
                  <td>{{ t.pf }}</td>
                  <td>{{ t_pm_str }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      {% endfor %}
    </section>

  {% endif %}

</div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    teams = sorted(load_teams().keys())
    game = None
    quarter_logs = {}
    error = None
    selected_t1 = teams[0]
    selected_t2 = teams[1] if len(teams) > 1 else teams[0]

    if request.method == "POST":
        t1 = request.form.get("t1", "").strip().upper()
        t2 = request.form.get("t2", "").strip().upper()
        selected_t1, selected_t2 = t1, t2

        if t1 == t2:
            error = "Please select two different teams."
        elif t1 not in teams or t2 not in teams:
            error = "Invalid team selection."
        else:
            game, quarter_logs = run_game(t1, t2)

    return render_template_string(
        TEMPLATE,
        teams=teams,
        game=game,
        quarter_logs=quarter_logs,
        selected_t1=selected_t1,
        selected_t2=selected_t2,
        error=error,
        period_label=period_label,
        render_log_line=render_log_line,
    )


if __name__ == "__main__":
    print("NBA Game Simulator — web server starting")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True)
