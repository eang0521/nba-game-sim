# N3BL NBA Game Simulator — Official Rulebook

A possession-by-possession NBA game simulation played with physical dice and a stat sheet. Two teams of 15 players compete across four 12-minute quarters, with 5-minute overtime periods as needed.

---

## Table of Contents

1. [Materials Needed](#1-materials-needed)
2. [Player Ratings](#2-player-ratings)
3. [Pre-Game: Calculating Derived Stats](#3-pre-game-calculating-derived-stats)
4. [Setting Lineups](#4-setting-lineups)
5. [Assigning Positions](#5-assigning-positions)
6. [Starting the Game: The Tip-Off](#6-starting-the-game-the-tip-off)
7. [The Game Clock](#7-the-game-clock)
8. [The Possession Loop](#8-the-possession-loop)
9. [Event 1 — Steal Attempt](#9-event-1--steal-attempt)
10. [Event 2 — Foul](#10-event-2--foul)
11. [Events 3–6 — Shot Attempt](#11-events-36--shot-attempt)
12. [Assists](#12-assists)
13. [Blocks](#13-blocks)
14. [Rebounds](#14-rebounds)
15. [Free Throws](#15-free-throws)
16. [Fouls and Foul Trouble](#16-fouls-and-foul-trouble)
17. [The Bonus](#17-the-bonus)
18. [Substitutions](#18-substitutions)
19. [Quarter and Overtime Rules](#19-quarter-and-overtime-rules)
20. [Tracking Stats](#20-tracking-stats)
21. [Quick Reference](#21-quick-reference)

---

## 1. Materials Needed

- **Dice:** d6, d10, d20, and d100 (two d10s used as percentile dice: tens digit + ones digit)
- **Two team rosters** with player ratings filled in (see Section 2)
- **Player cards** with derived stats pre-calculated (see Section 3)
- **Stat sheet** for recording points, rebounds, assists, etc. per player
- **Scratch paper** for tracking: game clock, possession arrow, quarterly foul counts, bonus status, and substitution flag

---

## 2. Player Ratings

Every player has four base ratings. Ratings are typically in the range of roughly −10 to 50, and can occasionally be negative for weak players.

| Rating | Abbreviation | What It Measures |
|--------|-------------|-----------------|
| 2-Point Skill | **2PT** | Inside scoring, mid-range shooting |
| 3-Point Skill | **3PT** | Perimeter shooting ability |
| Defense | **DEF** | Stealing, shot contesting, blocking |
| Rebounding | **REB** | Ability to grab missed shots |

---

## 3. Pre-Game: Calculating Derived Stats

Before tipoff, calculate the following for **every player on both rosters** and write them on player cards. These values stay constant throughout the game.

---

### OVR — Overall Rating

```
OVR = 2PT + 3PT + DEF + REB
```

Used to rank players for lineup selection and substitutions.

---

### PV — Position Value

```
PV = REB − 3PT + (2PT ÷ 100)
```

> The `÷ 100` term is a minor tiebreaker. For most purposes, sort primarily by `REB − 3PT`.

PV determines which position a player occupies on the court. **Lower PV → plays guard (PG). Higher PV → plays big (C).** Sort the five players on the court by PV and assign positions 1 through 5.

PV also determines **positional matchups**: when a player shoots, the defender matched against them is whichever defensive player is in the same PV-ranked slot.

---

### OFF — Offensive Rating

```
OFF = 2PT + 3PT + (OVR ÷ 100)
```

> The `÷ 100` term is a minor tiebreaker. For most purposes, sort by `2PT + 3PT`.

OFF determines shot priority — who gets the ball on offense. Higher OFF = more shot attempts.

---

### FT% — Free Throw Chance

```
FT% = 50 + (2PT × 0.4) + (3PT × 1.0)
Minimum: 1 | Maximum: 90
```

FT% is the target number you must roll **at or under** on a d100 to make a free throw.

**Example:** A player with 2PT 20 and 3PT 15 has FT% = 50 + 8 + 15 = **73**.

---

### Shot Ratio

```
Shot Ratio = round( (2PT × 3) ÷ ((2PT × 3) + (3PT × 2)) × 100 )
```

Shot Ratio is the d100 target for a **2-point attempt** vs. a **3-point attempt**. A higher Shot Ratio means the player favors 2-point shots.

> If a player has 0 or negative 3PT, treat their Shot Ratio as **100** (always shoots 2s). Likewise treat 0 or negative 2PT as **0** when calculating the formula; floor both values at 1 before dividing.

**Example:** 2PT 30, 3PT 15 → Shot Ratio = round((90) ÷ (90 + 30) × 100) = round(75) = **75**

---

### Make Chance — Pre-Calculate at Game Time

The Make Chance is calculated **during the game** based on the specific offensive player vs. their matched defender. However, you can speed up play by pre-filling a table on the stat sheet for common matchups.

| Shot Type | Formula |
|-----------|---------|
| **2PT** | `round((Shooter 2PT − Defender DEF) × 0.667) + 54` |
| **3PT** | `round((Shooter 3PT − Defender DEF) × 0.5) + 36` |

This is the number you must roll **at or under** on a d100 to make the shot.

> A league-average player shooting a 2-pointer against a league-average defender has roughly a **54% chance** to make it. For 3-pointers the baseline is **36%.**

---

## 4. Setting Lineups

Lineups are set at the **start of each quarter** and after certain stoppages (see Section 18). Each coach independently sets their team's five-man unit.

### Lineup Selection Procedure

1. List all available players (not fouled out, not currently on court) sorted by **OVR, highest first**.
2. Repeat the following **five times**, once per court slot:
   - Roll **d20** and consult the **D20 Selection Table** below.
   - The result gives you a rank index — pick the player at that rank from the remaining available list.
   - That player is now on the court and cannot be selected again for this lineup.

### D20 Selection Table

| d20 Roll | 5 Available | 4 Available | 3 Available | 2 Available |
|----------|-------------|-------------|-------------|-------------|
| 1–6 | Rank #1 (Best) | Rank #1 | Rank #1 | Rank #1 |
| 7–11 | Rank #2 | Rank #1 | Rank #1 | Rank #1 |
| 12–15 | Rank #3 | Rank #2 | Rank #2 | Rank #2 |
| 16–18 | Rank #4 | Rank #3 | Rank #3 | Rank #2 |
| 19–20 | Rank #5 | Rank #4 | Rank #3 | Rank #2 |

> If fewer than 5 eligible players remain, use the appropriate column. The result is always capped at the last available rank.

---

## 5. Assigning Positions

Once five players are on the court, sort them by **PV** from lowest to highest and assign:

| PV Rank | Position |
|---------|----------|
| 1 (Lowest PV) | **PG** — Point Guard |
| 2 | **SG** — Shooting Guard |
| 3 | **SF** — Small Forward |
| 4 | **PF** — Power Forward |
| 5 (Highest PV) | **C** — Center |

**Reassign positions every time the lineup changes.** A player's position slot is what determines their defensive matchup, shot initiation priority in the rebound cycle, and block probability.

---

## 6. Starting the Game: The Tip-Off

Only **Quarter 1** and each **overtime period** begin with a tip-off. The two centers (position 5) jump for the ball.

### Tip-Off Resolution

1. Add together both centers' **REB** values (treating negative REB as 1 minimum): `Total = max(1, C1_REB) + max(1, C2_REB)`
2. Roll **d100**. Calculate Team 1's tip threshold: `Tip Threshold = round(max(1, C1_REB) ÷ Total × 100)`
3. If d100 ≤ Tip Threshold → **Team 1 wins the tip**. Otherwise → **Team 2 wins the tip**.
4. Record who won the tip — you'll need it for Quarters 2, 3, and 4.

### Quarter Possession Arrow

| Quarter | First Possession |
|---------|-----------------|
| Q1 | Tip-off winner |
| Q2 | Tip-off **loser** |
| Q3 | Tip-off **loser** |
| Q4 | Tip-off **winner** |
| OT | New tip-off |

---

## 7. The Game Clock

Each quarter lasts **12 minutes (720 seconds)**. Overtime lasts **5 minutes (300 seconds)**.

Track the clock in **seconds** on your scratch paper. Every possession, **roll dice and subtract the result** from the clock.

| Situation | Clock Roll |
|-----------|-----------|
| Standard possession | **4d6** seconds |
| Quick possession (off. rebound put-back, foul continuation) | **2d6** seconds |

When the clock reaches **0**, the quarter ends immediately. If the clock would go below 0, set it to 0 — the quarter ends as normal.

> **Clock conversion tip:** 1 minute = 60 seconds. 2:00 warning = 120 seconds remaining.

---

## 8. The Possession Loop

Every possession follows this exact sequence:

```
1. Roll 4d6 → subtract from clock
2. If clock = 0 → quarter ends, stop
3. Roll d6 → possession event:
      1    = Steal Attempt    (→ Section 9)
      2    = Foul             (→ Section 10)
     3–6   = Shot Attempt     (→ Section 11)
```

Repeat from step 1 with each new possession until the clock runs out.

---

## 9. Event 1 — Steal Attempt

The defense tries to take the ball away. Check each defender **in PV order, PG first through C last**.

For each defender:
1. Roll **d100**.
2. If the result ≤ that defender's **DEF** (minimum 1) → **Steal!**
   - Record **+1 STL** for that defender.
   - Possession switches to the **defense**.
   - End this possession.
3. If no steal → move to the next defender.

If all **five defenders fail**, no steal occurs. Instead of rolling d6 again, randomly pick a result from 3–6 (roll d6, re-rolling 1s and 2s) and resolve as a **Shot Attempt**.

---

## 10. Event 2 — Foul

### Step 1 — Identify the Fouler's Position

Roll **d10** to determine which positional slot is involved in the foul:

| d10 Roll | Position Slot |
|----------|--------------|
| 1–2 | PG (slot 1) |
| 3–4 | SG (slot 2) |
| 5–6 | SF (slot 3) |
| 7–8 | PF (slot 4) |
| 9–10 | C (slot 5) |

### Step 2 — Foul Type

Roll **d10**:

| d10 Roll | Foul Type |
|----------|-----------|
| 1 | **Offensive Foul** |
| 2–6 | **Defensive Foul — Non-Shooting** |
| 7–10 | **Defensive Foul — Shooting** |

---

### Offensive Foul

The **offensive player** in the foul's position slot committed the foul.

1. Record **+1 PF** on that offensive player. Check foul trouble (Section 16).
2. Check if the **offense** is in the bonus (Section 17):
   - **In bonus:** Randomly choose any player from the **defense** to shoot **2 free throws** (roll to pick: any random method). After FTs, **offense** retains possession.
   - **Not in bonus:** Possession changes to the **defense**.
3. Resolve any forced substitutions (Section 18), then continue.

---

### Defensive Foul — Non-Shooting

The **defensive player** in the foul's position slot committed the foul.

1. Record **+1 PF** on that defensive player. Add **+1** to that team's quarter foul count. Check foul trouble (Section 16).
2. If the clock is at **120 seconds or less**, mark the **Late Foul Flag** for the defense (used for bonus tracking — see Section 17).
3. Check if the **defense** is in the bonus (Section 17):
   - **In bonus:** Randomly choose any player from the **offense** to shoot **2 free throws**. After FTs, possession goes to the **defense**.
   - **Not in bonus:** Possession stays with the **offense**. Handle substitutions, then immediately roll **2d6** for clock time and run a new possession for the same team.
4. Resolve any forced substitutions before the next action.

---

### Defensive Foul — Shooting

A foul occurred during a shot attempt. The offensive player was in the act of shooting.

**Step A — Select the Shooter**

Sort offensive players by **OFF, highest first**. Roll **d20** and use the D20 Selection Table (5-player column) to pick the shooter. Note their **position slot** (their PV rank).

**Step B — Determine Shot Type**

1. Roll **d100**: if result ≤ shooter's **Shot Ratio** → **2-point attempt**.
2. If the result was *above* Shot Ratio (possible 3-pointer): roll **d6**. If result ≤ 4 → it converts to a **2-point attempt**. If 5–6 → **3-point attempt**.

So a 3-pointer is only the result when **both** the d100 fails the Shot Ratio *and* the d6 shows 5 or 6.

**Step C — Resolve the And-1 Check**

Calculate the **Make Chance** (see Section 3) using the shooter's skill vs. the defender in the matching position slot.

Roll **d100 twice** — independently, both against the same Make Chance:

| Both rolls made (≤ Make Chance)? | Outcome |
|----------------------------------|---------|
| **Yes, both made** | **And-1!** The basket counts. Score the points. Shoot **1 bonus free throw**. |
| **Either roll missed** | **No basket.** Shoot **2 FTs** (for a 2PT foul) or **3 FTs** (for a 3PT foul). |

**Step D — After Free Throws**

- If the **last free throw is made**: possession goes to the **defense**.
- If the **last free throw is missed**: go to the **Rebound Cycle** (Section 14). The shooter cannot rebound their own last miss on the first cycle.

> For the And-1 basket: record the FG (and 3PT if applicable) on the shooter's stat line before shooting the 1 free throw. Also check for an assist (Section 12) and roll for the Subs Flag (Section 18).

---

## 11. Events 3–6 — Shot Attempt

### Step 1 — Select the Shooter

1. Sort offensive players by **OFF, highest first**.
2. Roll **d20** and use the **D20 Selection Table** (5-player column) to pick the shooter.
3. Note the shooter's **position slot** (their PV rank 1–5). The **matched defender** is the defensive player at the same PV rank.

### Step 2 — Determine Shot Type

1. Roll **d100**: if result ≤ shooter's **Shot Ratio** → **2-point attempt**. Done.
2. If result > Shot Ratio: roll **d6**. If ≤ 4 → **2-point attempt**. If 5–6 → **3-point attempt**.

> Record **+1 FGA** (and **+1 3PA** if 3-pointer) on the shooter now, regardless of outcome.

### Step 3 — Resolve the Shot

Calculate **Make Chance** using the shooter's skill vs. the matched defender's DEF.

Roll **d100**: if result ≤ Make Chance → **Made basket**.

---

### If Made

1. Add **2 or 3 points** to the offense's score and to the shooter's **PTS** total.
2. Record **+1 FGM** (and **+1 3PM** if 3-pointer).
3. Update **+/−** for all players on the court (Section 20).
4. Check for an **Assist** (Section 12).
5. Roll **d10**: if result ≤ points scored → set the **Subs Flag** (substitutions available at next dead ball).
   - After a 2-pointer: 20% chance (d10 rolls 1–2)
   - After a 3-pointer: 30% chance (d10 rolls 1–3)
6. Possession switches to the **defense**. Continue the loop.

### If Missed

1. Check for a **Block** (Section 13).
2. Go to the **Rebound Cycle** (Section 14).

---

## 12. Assists

After every made **field goal** (not free throws), roll **d100** to determine if an assist was recorded.

First, **remove the shooter from the list** and sort the remaining four teammates by **PV, lowest first**. This gives you four ranked teammates: the smallest (lowest PV), the second smallest, the third smallest, and the biggest (highest PV).

| d100 Roll | Assisting Teammate |
|-----------|-------------------|
| 1–24 | Teammate #1 — smallest remaining (lowest PV) |
| 25–42 | Teammate #2 — second smallest |
| 43–54 | Teammate #3 — third smallest |
| 55–60 | Teammate #4 — biggest remaining (highest PV) |
| 61–100 | No assist |

**Example:** If the PG shoots, the four teammates are SG (#1), SF (#2), PF (#3), and C (#4). A roll of 30 would credit the SG with an assist. If the SF shoots, teammates are PG (#1), SG (#2), PF (#3), and C (#4).

Record **+1 AST** for the credited teammate.

---

## 13. Blocks

On a **missed field goal attempt** (not free throws), before going to the Rebound Cycle, check if the matched defender blocked the shot.

1. Roll **d100**: if result ≤ defender's **DEF** (minimum 1) → possible block. Otherwise, no block.
2. If the first roll passes: roll **d6**. If result ≤ **(defender's position + 1)** → **Block confirmed!**

| Defender Position | d6 Threshold for Block |
|-------------------|----------------------|
| PG (slot 1) | ≤ 2 |
| SG (slot 2) | ≤ 3 |
| SF (slot 3) | ≤ 4 |
| PF (slot 4) | ≤ 5 |
| C (slot 5) | ≤ 6 (automatic if DEF check passed) |

Record **+1 BLK** for the defender. Then proceed to the Rebound Cycle regardless — a blocked shot still needs to be rebounded.

---

## 14. Rebounds

After a missed field goal or a missed final free throw, run the Rebound Cycle.

### Rebound Order (Always This Sequence)

Go through players in this fixed order each cycle:

1. C — **defense** (PV rank 5)
2. PF — defense (PV rank 4)
3. SF — defense (PV rank 3)
4. SG — defense (PV rank 2)
5. PG — defense (PV rank 1)
6. C — **offense** (PV rank 5)
7. PF — offense (PV rank 4)
8. SF — offense (PV rank 3)
9. SG — offense (PV rank 2)
10. PG — offense (PV rank 1)

> **Important:** On the **first cycle only**, skip the shooter (they cannot rebound their own miss immediately). The shooter re-enters eligibility in the second cycle.

### Rebound Roll

For each player in order, roll **d100**:

- **Rebound Rating** = player's **REB** (minimum 1) + **3** if the player is on *defense* and it is the *first cycle*
- If d100 ≤ Rebound Rating → **Rebound!**

Record **+1 REB** for that player.

- **Defense rebounds:** possession switches to the **defense**. End the cycle. Continue the possession loop.
- **Offense rebounds:** possession stays with the **offense**. Roll **2d6** for clock time and immediately resolve a new shot attempt (the offensive team gets the ball back with less time).

If **no one** rebounds in the full 10-player pass: subtract **1 second** from the clock and repeat the cycle from step 1 (without the +3 defensive bonus — that only applies on the first cycle). Keep cycling until someone rebounds or the clock hits 0.

---

## 15. Free Throws

For each free throw to be taken:

1. Roll **d100**.
2. If result ≤ shooter's **FT%** → **Made.** Record **+1 FTM, +1 FTA, +1 PTS**.
3. If result > FT% → **Missed.** Record **+1 FTA** only.

**After the last free throw in a set:**
- If **made**: possession goes to the **defense**. Continue the possession loop.
- If **missed**: go to the **Rebound Cycle** (Section 14). The shooter is ineligible to rebound their own miss on the first cycle.

> The free throw shooter may **not** be substituted out while shooting. All other substitutions that are waiting happen before the first FT is taken (see Section 18).

---

## 16. Fouls and Foul Trouble

### Recording Fouls

Any time a player commits a foul, add **+1 PF** to their stat line.

### Foul Trouble Thresholds

A player in foul trouble **must be substituted out immediately** after the current play is resolved:

| Quarter | Foul Limit (must sub out) |
|---------|--------------------------|
| Q1 | 3 or more fouls |
| Q2 | 4 or more fouls |
| Q3 | 5 or more fouls |
| Q4 / OT | 6 fouls (fouled out) |

### Fouling Out

When a player accumulates **6 personal fouls**, they are **permanently ejected** from the game. They cannot return under any circumstances. A replacement must enter immediately.

---

## 17. The Bonus

A team is **in the bonus** when their **opponents** must shoot free throws on all defensive fouls, regardless of whether it was a shooting foul.

A team is in the bonus if **either** condition is met:

1. The defense has committed **4 or more defensive fouls** this quarter.
2. The clock is at **120 seconds or fewer** (last 2:00 of a quarter) **and** the defense committed a foul during that last 2-minute window (Late Foul Flag is set).

> Defensive foul count resets to **0** at the start of every quarter. The Late Foul Flag also resets each quarter.

> Only **defensive** fouls count toward the quarter foul count. Offensive fouls do not.

---

## 18. Substitutions

### When Substitutions Are Allowed

Substitutions only happen at dead balls. There are two triggers:

1. **Subs Flag** — set randomly after made field goals (see Section 11). When set, both teams may make substitutions at the next dead ball.
2. **Forced Sub** — a player is in foul trouble or has fouled out. They must exit immediately when play stops.

### Substitution Procedure

When the Subs Flag is set **or** a forced sub is needed, perform this for **each team**:

**How many subs?**

- If the Subs Flag is set: roll **d20** and use the D20 Selection Table (5-player column). The result **index + 1** = number of subs (index 0 → 1 sub, index 4 → 5 subs).
- If only forced subs with no Subs Flag: 1 sub happens (plus any additional forced players).
- The total is always at least the number of forced-out players.

**Who comes out?**

1. Sort the five players currently on the court by **OVR, lowest first**.
2. For each sub slot:
   - If this slot is a forced sub (foul trouble/foul-out), that player automatically comes out.
   - Otherwise: roll **d20** and use the D20 Selection Table from the remaining court players (excluding the free throw shooter if FTs are pending, and anyone already selected to exit). Index 0 = lowest OVR player.
3. Mark each exiting player as on the bench.

**Who comes in?**

1. Sort all bench players (not fouled out) by **OVR, highest first**. Take the top 5 available.
2. For each sub slot: roll **d20** and use the D20 Selection Table from that top-5 pool. Index 0 = highest OVR bench player.
3. Mark each entering player as on the court.

**After substitutions:**
- Clear the Subs Flag.
- Re-sort both teams by PV and reassign positions 1–5.
- If substitutions were made, note the new lineups.

> The free throw shooter cannot be subbed out mid-sequence. Any substitutions involving them wait until after the free throws are complete.

---

## 19. Quarter and Overtime Rules

| Period | Clock | Tip-Off? | Starting Possession |
|--------|-------|----------|---------------------|
| Q1 | 12:00 | **Yes** | Tip-off winner |
| Q2 | 12:00 | No | Tip-off **loser** |
| Q3 | 12:00 | No | Tip-off **loser** |
| Q4 | 12:00 | No | Tip-off **winner** |
| OT1, OT2, … | 5:00 | **Yes** | New tip-off each OT |

### At the Start of Each Quarter

1. Set new lineups for both teams using the lineup selection procedure (Section 4).
2. Reset the clock to 720 seconds (or 300 for OT).
3. Reset both teams' **defensive foul count to 0**.
4. Clear both teams' **Late Foul Flags**.
5. Determine starting possession per the table above.

### Overtime

If the score is **tied at the end of Q4**, play a 5-minute overtime period with a new tip-off. Continue playing overtime periods until one team leads at the buzzer.

---

## 20. Tracking Stats

### Per-Player Stats to Record

| Stat | When to Record |
|------|---------------|
| **MIN** | Track seconds played; divide by 60 at game end |
| **PTS** | Add 2 or 3 on made FG; add 1 per made FT |
| **FGA** | +1 on every shot attempt (before outcome) |
| **FGM** | +1 only on made field goals |
| **3PA** | +1 on every 3-point attempt |
| **3PM** | +1 on made 3-pointers |
| **FTA** | +1 on every free throw attempted |
| **FTM** | +1 on made free throws |
| **REB** | +1 on each rebound grabbed |
| **AST** | +1 on assist rolls (Section 12) |
| **STL** | +1 when a steal is recorded (Section 9) |
| **BLK** | +1 when a block is confirmed (Section 13) |
| **PF** | +1 on every foul committed |
| **+/−** | See below |

### Plus/Minus

Every time **points are scored**, apply the following immediately:

- Add the points to every player **currently on the court** for the **scoring team**.
- Subtract the points from every player **currently on the court** for the **other team**.

### Linescore (Quarter-by-Quarter Score)

Track each team's score at the end of each quarter. Record the **points scored that quarter** (not the cumulative total) in each box.

```
Team  | Q1 | Q2 | Q3 | Q4 | T
------|----|----|----|----+---
      |    |    |    |    |
      |    |    |    |    |
```

### Box Score Format

```
Player (Pos)         | MIN | PTS |  FG  | 3PT  |  FT  | REB | AST | STL | BLK | PF | +/-
---------------------|-----|-----|------|------|------|-----|-----|-----|-----|----|----
                     |     |     |      |      |      |     |     |     |     |    |
TOTALS               |     |     |      |      |      |     |     |     |     |    |
```

---

## 21. Quick Reference

### Possession Event Summary

| d6 Roll | Event |
|---------|-------|
| 1 | Steal — each defender rolls d100 ≤ their DEF |
| 2 | Foul — roll d10 for type, d10 for position |
| 3–6 | Shot — select shooter (d20), determine type (d100 + d6), make check (d100) |

---

### D20 Selection Table

| d20 | 5 Options | 4 Options | 3 Options | 2 Options |
|-----|-----------|-----------|-----------|-----------|
| 1–6 | #1 | #1 | #1 | #1 |
| 7–11 | #2 | #1 | #1 | #1 |
| 12–15 | #3 | #2 | #2 | #2 |
| 16–18 | #4 | #3 | #3 | #2 |
| 19–20 | #5 | #4 | #3 | #2 |

*Index returned is (row − 1); e.g., "Rank #1" = Index 0, "Rank #2" = Index 1.*

---

### Foul Type Table (d10)

| d10 | Foul Type |
|-----|-----------|
| 1 | Offensive foul |
| 2–6 | Defensive non-shooting foul |
| 7–10 | Defensive shooting foul |

---

### Foul Position Table (d10)

| d10 | Position Involved |
|-----|------------------|
| 1–2 | PG slot |
| 3–4 | SG slot |
| 5–6 | SF slot |
| 7–8 | PF slot |
| 9–10 | C slot |

---

### Assist Table (d100)

Remove the shooter first, then sort the remaining four teammates by PV lowest-to-highest.

| d100 | Assisting Teammate |
|------|-------------------|
| 1–24 | Teammate #1 (smallest remaining) |
| 25–42 | Teammate #2 |
| 43–54 | Teammate #3 |
| 55–60 | Teammate #4 (biggest remaining) |
| 61–100 | No assist |

---

### Shot Make Chance Formulas

| Shot Type | Formula | Baseline (equal skills) |
|-----------|---------|------------------------|
| 2-pointer | `round((Shooter 2PT − Defender DEF) × 0.667) + 54` | 54% |
| 3-pointer | `round((Shooter 3PT − Defender DEF) × 0.5) + 36` | 36% |

---

### Block Check (After Missed Field Goal)

1. Roll d100 ≤ Defender DEF → possible block
2. Roll d6 ≤ (Defender position + 1) → confirmed block

| Defender | d6 Needed |
|----------|-----------|
| PG | ≤ 2 |
| SG | ≤ 3 |
| SF | ≤ 4 |
| PF | ≤ 5 |
| C | ≤ 6 (always) |

---

### Foul Trouble Thresholds

| Quarter | Foul Limit |
|---------|-----------|
| Q1 | 3+ |
| Q2 | 4+ |
| Q3 | 5+ |
| Q4 / OT | 6 (foul out) |

---

### Clock Reference

| Quarter | Total Seconds | 2:00 Warning |
|---------|--------------|-------------|
| Q1–Q4 | 720 | 120 |
| OT | 300 | 120 |

---

*N3BL NBA Game Simulator — 2026 Edition*
