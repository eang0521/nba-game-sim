import json
import random
import os

def roll_d(sides, num=1):
    return sum(random.randint(1, sides) for _ in range(num))

class Player:
    def __init__(self, name, t_2pt, t_3pt, t_def, t_reb):
        self.name = name
        self.t_2pt = t_2pt
        self.t_3pt = t_3pt
        self.t_def = t_def
        self.t_reb = t_reb
        
        self.ovr = t_2pt + t_3pt + t_def + t_reb
        self.pv = t_reb - t_3pt + (0.01 * t_2pt) + (0.0001 * t_def)
        self.off = t_2pt + t_3pt + (0.01 * self.ovr)
        
        # FT Calculation: 50 + 0.4*2PS + 1*3PS, capped at 90, floored at 1
        self.ft_chance = max(1, min(90, round(50 + (t_2pt * 0.4) + (t_3pt * 1.0))))
        
        # Stats
        self.seconds_played = 0
        self.points = 0
        self.fg_made = 0
        self.fg_attempted = 0
        self.tpt_made = 0
        self.tpt_attempted = 0
        self.ft_made = 0
        self.ft_attempted = 0
        self.rebounds = 0
        self.assists = 0
        self.steals = 0
        self.blocks = 0
        self.fouls = 0
        self.plus_minus = 0
        
        # State
        self.on_court = False
        self.fouled_out = False
        self.positions_played = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        self.current_position = None

    def get_primary_position_name(self):
        if sum(self.positions_played.values()) == 0:
            return "BN"
        best_pos = max(self.positions_played, key=self.positions_played.get)
        return {1: "PG", 2: "SG", 3: "SF", 4: "PF", 5: "C"}[best_pos]

class Team:
    def __init__(self, abbr, player_data):
        self.abbr = abbr
        self.players = [Player(p['name'], p['t_2pt'], p['t_3pt'], p['t_def'], p['t_reb']) for p in player_data]
        self.score = 0
        self.court = []
        self.defensive_fouls_qtr = 0
        self.foul_in_last_2_mins = False
        
    def get_court_sorted_by_pv(self):
        # Lowest PV is 1 (PG), Highest is 5 (C)
        sorted_court = sorted(self.court, key=lambda x: x.pv)
        for i, p in enumerate(sorted_court):
            p.current_position = i + 1
        return sorted_court

    def get_court_sorted_by_off(self):
        # Highest OFF first
        return sorted(self.court, key=lambda x: x.off, reverse=True)

class Game:
    def __init__(self, team1, team2):
        self.t1 = team1
        self.t2 = team2
        self.quarter = 0
        self.clock = 0
        self.possession = None
        self.jumpball_winner = None
        self.subs_waiting = False
        
        # Track scoring by quarter
        self.t1_q_scores = []
        self.t2_q_scores = []
        self.t1_last_q_score = 0
        self.t2_last_q_score = 0
        
    def format_time(self):
        mins = self.clock // 60
        secs = self.clock % 60
        return f"{mins:02}:{secs:02}"

    def log(self, message):
        score_str = f"[{self.t1.abbr} {self.t1.score} - {self.t2.abbr} {self.t2.score}]" if "makes" in message or "scores" in message else ""
        print(f"{self.format_time()} {message} {score_str}".strip())

    def update_plus_minus(self, scoring_team, points):
        other_team = self.t2 if scoring_team == self.t1 else self.t1
        for p in scoring_team.court:
            p.plus_minus += points
        for p in other_team.court:
            p.plus_minus -= points

    def start_quarter_lineups(self):
        for team in [self.t1, self.t2]:
            team.court = []
            for p in team.players:
                p.on_court = False
                
            for _ in range(5):
                bench = sorted([p for p in team.players if not p.on_court and not p.fouled_out], key=lambda x: x.ovr, reverse=True)
                if not bench: break
                
                roll = roll_d(20)
                if roll <= 6: idx = 0
                elif roll <= 11: idx = min(1, len(bench)-1)
                elif roll <= 15: idx = min(2, len(bench)-1)
                elif roll <= 18: idx = min(3, len(bench)-1)
                else: idx = min(4, len(bench)-1)
                
                selected = bench[idx]
                selected.on_court = True
                team.court.append(selected)

    def display_lineups(self):
        t1_sorted = self.t1.get_court_sorted_by_pv()
        t2_sorted = self.t2.get_court_sorted_by_pv()
        
        print("\nCURRENT LINEUPS:")
        print(f"{self.t1.abbr:<28} | {self.t2.abbr:<28}")
        print("-" * 59)
        
        positions = ["PG", "SG", "SF", "PF", "C"]
        for i, (p1, p2) in enumerate(zip(t1_sorted, t2_sorted)):
            pos = positions[i]
            p1_str = f"{pos}: {p1.name}"
            p2_str = f"{pos}: {p2.name}"
            print(f"{p1_str:<28} | {p2_str:<28}")
        print()

    def get_threshold_index(self, roll, pool_size):
        if pool_size >= 5: thresholds = [6, 11, 15, 18, 20]
        elif pool_size == 4: thresholds = [8, 14, 18, 20]
        elif pool_size == 3: thresholds = [9, 16, 20]
        elif pool_size == 2: thresholds = [13, 20]
        else: thresholds = [20]
        
        for i, t in enumerate(thresholds):
            if roll <= t: return i
        return len(thresholds) - 1

    def handle_substitutions(self, ft_shooter=None, forced_sub_players=None):
        if forced_sub_players is None: forced_sub_players = []
        
        subs_made_this_stoppage = False
        
        for team in [self.t1, self.t2]:
            forced_team = [p for p in forced_sub_players if p in team.players and p.on_court]
            if not self.subs_waiting and not forced_team: continue
            
            num_subs = 1 if forced_team and not self.subs_waiting else min(5, self.get_threshold_index(roll_d(20), 5) + 1)
            num_subs = max(num_subs, len(forced_team))
            
            court_pool = sorted(team.court, key=lambda x: x.ovr)
            available_bench_total = [p for p in team.players if not p.on_court and not p.fouled_out]
            
            out_players = []
            in_players = []
            
            for i in range(min(num_subs, len(court_pool), len(available_bench_total))):
                if i < len(forced_team):
                    out_p = forced_team[i]
                else:
                    valid_out = [p for p in court_pool if p not in out_players and p != ft_shooter]
                    if not valid_out: break
                    roll_out = roll_d(20)
                    idx_out = self.get_threshold_index(roll_out, len(valid_out))
                    out_p = valid_out[idx_out]
                
                valid_in_all = sorted([p for p in team.players if not p.on_court and not p.fouled_out and p not in in_players], key=lambda x: x.ovr, reverse=True)
                valid_in = valid_in_all[:5]
                
                if not valid_in: break
                
                roll_in = roll_d(20)
                idx_in = self.get_threshold_index(roll_in, 5)
                idx_in = min(idx_in, len(valid_in) - 1)
                in_p = valid_in[idx_in]
                
                out_players.append(out_p)
                in_players.append(in_p)
                
            for op, ip in zip(out_players, in_players):
                op.on_court = False
                team.court.remove(op)
                ip.on_court = True
                team.court.append(ip)
                self.log(f"SUB: {ip.name} in for {op.name}")
                subs_made_this_stoppage = True
                
        self.subs_waiting = False
        self.t1.get_court_sorted_by_pv()
        self.t2.get_court_sorted_by_pv()
        
        if subs_made_this_stoppage:
            self.display_lineups()

    def advance_time(self, dice_count):
        time_taken = roll_d(6, dice_count)
        self.clock -= time_taken
        if self.clock < 0: self.clock = 0
        
        for team in [self.t1, self.t2]:
            for p in team.court:
                p.seconds_played += time_taken
                p.positions_played[p.current_position] += time_taken
                
        return self.clock > 0

    def get_bonus_status(self, defense_team):
        if defense_team.defensive_fouls_qtr >= 4:
            return True
        if self.clock <= 120 and defense_team.foul_in_last_2_mins:
            return True
        return False

    def record_foul(self, player, defense_team):
        player.fouls += 1
        forced_sub = []
        if player.fouls >= 6:
            player.fouled_out = True
            forced_sub.append(player)
            self.log(f"{player.name} fouled out!")
        elif player.fouls >= (self.quarter + 2):
            forced_sub.append(player)
            self.log(f"{player.name} is in foul trouble ({player.fouls} fouls) and must sub out.")
        return forced_sub

    def shoot_fts(self, shooter, num_fts):
        if num_fts == 0: return True
        made_last = False
        for i in range(num_fts):
            shooter.ft_attempted += 1
            if roll_d(100) <= shooter.ft_chance:
                shooter.points += 1
                shooter.ft_made += 1
                shooter.team_ref.score += 1
                self.update_plus_minus(shooter.team_ref, 1)
                self.log(f"{shooter.name} makes free throw {i+1}/{num_fts}")
                if i == num_fts - 1:
                    made_last = True
            else:
                self.log(f"{shooter.name} misses free throw {i+1}/{num_fts}")
                if i == num_fts - 1:
                    made_last = False
        return made_last

    def play_possession(self, dice_count=4):
        if self.clock <= 0: return
        if not self.advance_time(dice_count): return

        off_team = self.possession
        def_team = self.t2 if off_team == self.t1 else self.t1
        
        for p in off_team.court: p.team_ref = off_team
        for p in def_team.court: p.team_ref = def_team

        event = roll_d(6)
        off_court_pv = off_team.get_court_sorted_by_pv()
        def_court_pv = def_team.get_court_sorted_by_pv()

        if event == 1:
            for i in range(5):
                defender = def_court_pv[i]
                safe_def = max(1, defender.t_def) # Minimum of 1 for steal calc
                if roll_d(100) <= safe_def:
                    defender.steals += 1
                    self.log(f"{defender.name} Steal")
                    self.possession = def_team
                    return
            event = random.randint(3, 6)

        if event == 2:
            foul_type = roll_d(10)
            foul_pos_roll = roll_d(10)
            foul_pos = (foul_pos_roll - 1) // 2
            
            if foul_type == 1:
                fouler = off_court_pv[foul_pos]
                forced = self.record_foul(fouler, def_team)
                self.log(f"{fouler.name} offensive foul")
                
                if self.get_bonus_status(off_team):
                    shooter = random.choice(def_team.court)
                    self.handle_substitutions(ft_shooter=shooter, forced_sub_players=forced)
                    made_last = self.shoot_fts(shooter, 2)
                    if not made_last: self.do_rebound_cycle(def_team, off_team, skipped_shooter=shooter)
                    else: self.possession = off_team
                else:
                    self.handle_substitutions(forced_sub_players=forced)
                    self.possession = def_team
            else:
                fouler = def_court_pv[foul_pos]
                forced = self.record_foul(fouler, def_team)
                def_team.defensive_fouls_qtr += 1
                if self.clock <= 120: def_team.foul_in_last_2_mins = True
                
                if foul_type <= 6:
                    self.log(f"{fouler.name} defensive foul")
                    if self.get_bonus_status(def_team):
                        shooter = random.choice(off_team.court)
                        self.handle_substitutions(ft_shooter=shooter, forced_sub_players=forced)
                        made_last = self.shoot_fts(shooter, 2)
                        if not made_last: self.do_rebound_cycle(off_team, def_team, skipped_shooter=shooter)
                        else: self.possession = def_team
                    else:
                        self.handle_substitutions(forced_sub_players=forced)
                        self.play_possession(dice_count=2)
                else:
                    self.log(f"{fouler.name} shooting foul")
                    off_court_off = off_team.get_court_sorted_by_off()
                    shooter = off_court_off[self.get_threshold_index(roll_d(20), 5)]
                    
                    # Minimum of 1 for 2PS and 3PS ratio calculation
                    safe_2pt = max(1, shooter.t_2pt)
                    safe_3pt = max(1, shooter.t_3pt)
                    shot_ratio = round((safe_2pt * 3) / ((safe_2pt * 3) + (safe_3pt * 2)) * 100)
                    
                    is_2pt = roll_d(100) <= shot_ratio
                    if not is_2pt and roll_d(6) <= 4: is_2pt = True
                    
                    pts = 2 if is_2pt else 3
                    defender = def_court_pv[shooter.current_position - 1]
                    
                    # Core stats can remain negative for the difference calc
                    diff = (shooter.t_2pt if is_2pt else shooter.t_3pt) - defender.t_def
                    mult = (2/3) if is_2pt else (1/2)
                    base = 54 if is_2pt else 36
                    target = round(diff * mult) + base
                    
                    made1 = roll_d(100) <= target
                    made2 = roll_d(100) <= target
                    
                    if made1 and made2:
                        shooter.fg_attempted += 1
                        shooter.fg_made += 1
                        if not is_2pt:
                            shooter.tpt_attempted += 1
                            shooter.tpt_made += 1
                            
                        shooter.points += pts
                        off_team.score += pts
                        self.update_plus_minus(off_team, pts)
                        
                        assist_roll = roll_d(100)
                        assister = None
                        ast_idx = -1
                        if assist_roll <= 24: ast_idx = 0
                        elif assist_roll <= 42: ast_idx = 1
                        elif assist_roll <= 54: ast_idx = 2
                        elif assist_roll <= 60: ast_idx = 3
                        
                        if ast_idx != -1:
                            teammates = [p for p in off_court_pv if p != shooter]
                            if ast_idx < len(teammates):
                                assister = teammates[ast_idx]
                                assister.assists += 1
                        
                        ast_str = f" ({assister.name} Assist)" if assister else ""
                        self.log(f"{shooter.name} makes {pts} (And-1!){ast_str}")
                        
                        if roll_d(10) <= pts: self.subs_waiting = True
                        
                        self.handle_substitutions(ft_shooter=shooter, forced_sub_players=forced)
                        
                        made_last = self.shoot_fts(shooter, 1)
                        if not made_last: self.do_rebound_cycle(off_team, def_team, skipped_shooter=shooter)
                        else: self.possession = def_team
                    else:
                        self.log(f"{shooter.name} misses {pts} on foul")
                        self.handle_substitutions(ft_shooter=shooter, forced_sub_players=forced)
                        
                        made_last = self.shoot_fts(shooter, pts)
                        if not made_last: self.do_rebound_cycle(off_team, def_team, skipped_shooter=shooter)
                        else: self.possession = def_team
            return

        if event >= 3:
            off_court_off = off_team.get_court_sorted_by_off()
            shooter = off_court_off[self.get_threshold_index(roll_d(20), 5)]
            
            # Minimum of 1 for 2PS and 3PS ratio calculation
            safe_2pt = max(1, shooter.t_2pt)
            safe_3pt = max(1, shooter.t_3pt)
            shot_ratio = round((safe_2pt * 3) / ((safe_2pt * 3) + (safe_3pt * 2)) * 100)
            
            is_2pt = roll_d(100) <= shot_ratio
            pts = 2 if is_2pt else 3
            
            defender = def_court_pv[shooter.current_position - 1]
            diff = (shooter.t_2pt if is_2pt else shooter.t_3pt) - defender.t_def
            target = round(diff * ((2/3) if is_2pt else (1/2))) + (54 if is_2pt else 36)
            
            shooter.fg_attempted += 1
            if not is_2pt:
                shooter.tpt_attempted += 1
            
            if roll_d(100) <= target:
                shooter.fg_made += 1
                if not is_2pt:
                    shooter.tpt_made += 1
                
                shooter.points += pts
                off_team.score += pts
                self.update_plus_minus(off_team, pts)
                
                assist_roll = roll_d(100)
                assister = None
                ast_idx = -1
                if assist_roll <= 24: ast_idx = 0
                elif assist_roll <= 42: ast_idx = 1
                elif assist_roll <= 54: ast_idx = 2
                elif assist_roll <= 60: ast_idx = 3
                
                if ast_idx != -1:
                    teammates = [p for p in off_court_pv if p != shooter]
                    if ast_idx < len(teammates):
                        assister = teammates[ast_idx]
                        assister.assists += 1
                
                ast_str = f" ({assister.name} Assist)" if assister else ""
                self.log(f"{shooter.name} makes {pts}{ast_str}")
                
                if roll_d(10) <= pts: self.subs_waiting = True
                
                self.possession = def_team
            else:
                blocked = False
                safe_def = max(1, defender.t_def) # Minimum of 1 for block calc
                if roll_d(100) <= safe_def:
                    if roll_d(6) <= defender.current_position + 1:
                        blocked = True
                        defender.blocks += 1
                        self.log(f"{shooter.name} misses {pts} (Blocked by {defender.name}!)")
                
                if not blocked:
                    self.log(f"{shooter.name} misses {pts}")
                    
                self.do_rebound_cycle(off_team, def_team, skipped_shooter=shooter)

    def do_rebound_cycle(self, off_team, def_team, skipped_shooter):
        off_pv = off_team.get_court_sorted_by_pv()
        def_pv = def_team.get_court_sorted_by_pv()
        
        cycle_num = 1
        while self.clock > 0:
            order = list(reversed(def_pv)) + list(reversed(off_pv))
            for reb_player in order:
                if cycle_num == 1 and reb_player == skipped_shooter: continue
                
                safe_reb = max(1, reb_player.t_reb) # Minimum of 1 for rebound calc
                reb_rating = safe_reb + (3 if cycle_num == 1 and reb_player in def_pv else 0)
                
                if roll_d(100) <= reb_rating:
                    reb_player.rebounds += 1
                    self.log(f"{reb_player.name} Rebound")
                    if reb_player in def_pv:
                        self.possession = def_team
                    else:
                        self.possession = off_team
                        self.play_possession(dice_count=2)
                    return
            
            self.clock -= 1
            cycle_num += 1

    def play_quarter(self, mins):
        self.subs_waiting = False
        self.clock = mins * 60
        self.t1.defensive_fouls_qtr = 0
        self.t2.defensive_fouls_qtr = 0
        self.t1.foul_in_last_2_mins = False
        self.t2.foul_in_last_2_mins = False
        
        self.start_quarter_lineups()
        self.display_lineups()
        
        if self.quarter == 1 or mins == 5:
            c1, c2 = self.t1.get_court_sorted_by_pv()[4], self.t2.get_court_sorted_by_pv()[4]
            # Minimum of 1 for jumpball calculation to avoid crash
            safe_c1_reb = max(1, c1.t_reb)
            safe_c2_reb = max(1, c2.t_reb)
            total_reb = safe_c1_reb + safe_c2_reb
            
            if roll_d(total_reb) <= safe_c1_reb:
                self.possession = self.t1
                if self.quarter == 1: self.jumpball_winner = self.t1
                self.log(f"{c1.name} wins the jumpball for {self.t1.abbr}")
            else:
                self.possession = self.t2
                if self.quarter == 1: self.jumpball_winner = self.t2
                self.log(f"{c2.name} wins the jumpball for {self.t2.abbr}")
        elif self.quarter in [2, 3]:
            self.possession = self.t2 if self.jumpball_winner == self.t1 else self.t1
        else:
            self.possession = self.jumpball_winner

        while self.clock > 0:
            self.play_possession()
            
        # Update quarter scores
        self.t1_q_scores.append(self.t1.score - self.t1_last_q_score)
        self.t2_q_scores.append(self.t2.score - self.t2_last_q_score)
        self.t1_last_q_score = self.t1.score
        self.t2_last_q_score = self.t2.score

    def print_box_score(self):
        print(f"\nFINAL SCORE: {self.t1.abbr} {self.t1.score} - {self.t2.abbr} {self.t2.score}")
        
        # --- Linescore Section ---
        headers = ["Team"] + [f"Q{i+1}" for i in range(4)]
        if len(self.t1_q_scores) > 4:
            headers += [f"OT{i-3}" for i in range(4, len(self.t1_q_scores))]
        headers.append("T")
        
        header_row = f"{headers[0]:<5}| " + " | ".join(f"{h:>3}" for h in headers[1:])
        print("\n" + header_row)
        
        def print_linescore(team, scores):
            row_str = f"{team.abbr:<5}| " + " | ".join(f"{s:>3}" for s in scores) + f" | {team.score:>3}"
            print(row_str)
            
        print_linescore(self.t1, self.t1_q_scores)
        print_linescore(self.t2, self.t2_q_scores)
        
        # --- Player Stats Section ---
        print(f"\n{'Player':<28} | {'MIN':>3} | {'PTS':>3} | {'FG':>5} | {'3PT':>5} | {'FT':>5} | {'REB':>3} | {'AST':>3} | {'STL':>3} | {'BLK':>3} | {'PF':>2} | {'+/-':>4} |")
        print("-" * 102)
        
        for team in [self.t1, self.t2]:
            print(f"--- {team.abbr} ---")
            
            t_min = t_pts = t_fgm = t_fga = t_tptm = t_tpta = t_ftm = t_fta = t_reb = t_ast = t_stl = t_blk = t_pf = 0
            t_pm_val = 0
            
            for p in sorted(team.players, key=lambda x: x.seconds_played, reverse=True):
                if p.seconds_played > 0:
                    mp = round(p.seconds_played / 60)
                    pos = p.get_primary_position_name()
                    plus_minus = f"+{p.plus_minus}" if p.plus_minus > 0 else f"{p.plus_minus}"
                    
                    name_pos = f"{p.name} ({pos})"
                    fg_str = f"{p.fg_made}-{p.fg_attempted}"
                    tpt_str = f"{p.tpt_made}-{p.tpt_attempted}"
                    ft_str = f"{p.ft_made}-{p.ft_attempted}"
                    
                    print(f"{name_pos:<28} | {mp:>3} | {p.points:>3} | {fg_str:>5} | {tpt_str:>5} | {ft_str:>5} | {p.rebounds:>3} | {p.assists:>3} | {p.steals:>3} | {p.blocks:>3} | {p.fouls:>2} | {plus_minus:>4} |")
                    
                    t_min += mp
                    t_pts += p.points
                    t_fgm += p.fg_made
                    t_fga += p.fg_attempted
                    t_tptm += p.tpt_made
                    t_tpta += p.tpt_attempted
                    t_ftm += p.ft_made
                    t_fta += p.ft_attempted
                    t_reb += p.rebounds
                    t_ast += p.assists
                    t_stl += p.steals
                    t_blk += p.blocks
                    t_pf += p.fouls
                    t_pm_val += p.plus_minus
            
            print("-" * 102)
            t_fg_str = f"{t_fgm}-{t_fga}"
            t_tpt_str = f"{t_tptm}-{t_tpta}"
            t_ft_str = f"{t_ftm}-{t_fta}"
            t_pm = f"+{t_pm_val}" if t_pm_val > 0 else f"{t_pm_val}"
            
            print(f"{'TOTALS':<28} | {t_min:>3} | {t_pts:>3} | {t_fg_str:>5} | {t_tpt_str:>5} | {t_ft_str:>5} | {t_reb:>3} | {t_ast:>3} | {t_stl:>3} | {t_blk:>3} | {t_pf:>2} | {t_pm:>4} |\n")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'nba_rosters26_v3.json')
    
    if not os.path.exists(json_file):
        print(f"Error: Could not find the given json at {json_file}")
        print("Please make sure the JSON file is in the exact same folder as this Python script.")
        return

    with open(json_file, 'r') as f:
        teams_data = json.load(f)

    while True:
        t1_abbr = input("Enter the first team abbreviation (e.g., GSW): ").strip().upper()
        if t1_abbr not in teams_data:
            print("Team not found in the JSON file.")
            continue
            
        t2_abbr = input("Enter the second team abbreviation: ").strip().upper()
        if t2_abbr not in teams_data or t1_abbr == t2_abbr:
            print("Team not found or same as first team.")
            continue
            
        t1 = Team(t1_abbr, teams_data[t1_abbr])
        t2 = Team(t2_abbr, teams_data[t2_abbr])
        
        game = Game(t1, t2)
        
        for q in range(1, 5):
            game.quarter = q
            print(f"\n--- START OF QUARTER {q} ---")
            game.play_quarter(12)
            
        ot = 1
        while t1.score == t2.score:
            print(f"\n--- START OF OVERTIME {ot} ---")
            game.quarter = 4 + ot
            game.play_quarter(5)
            ot += 1
            
        game.print_box_score()
        
        again = input("\nSimulate another game? (y/n): ").strip().lower()
        if again != 'y':
            break

if __name__ == "__main__":
    main()