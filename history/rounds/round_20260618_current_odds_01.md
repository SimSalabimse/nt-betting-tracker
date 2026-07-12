# Round 2026-06-18 Current Odds Analysis & Recommendations

**Processed from:** attachments/current_odds_01.txt (full raw odds dump)
**Main Focus:** Tsjekkia (Czechia) vs Sør-Afrika (South Africa) - FIFA World Cup 2026 Group A
**Date/Time:** 2026-06-18 ~17:00 CEST kickoff (Mercedes-Benz Stadium, Atlanta)
**Workflow:** nt-betting-workflow (Stage 1 full scan + Stage 2 tool-assisted deep research on all flagged edges) + immediate bet_log append protocol

---

## Stage 1: Rough EV Scan - All Markets Flagged

Scanned **every single line** in the 32kB odds file. Only markets with rough EV potential >=7-8% (sport-dependent) advanced to Stage 2.

### Czechia vs South Africa - Key Flagged Markets (High Priority)
- **HUB (1X2)**: Tsjekkia 1.82 (implied prob ~54.9%) | Uavgjort 3.45 | Sør-Afrika 4.40
- **Over/Under 2.5**: Over 2.10 (implied ~47.6%) | Under 1.70
- **Both Teams Scorer (BTTS)**: Ja 1.92 | Nei 1.80
- **Player to Score**: Patrik Schick 2.20 | Tomas Chory 2.70 | Jan Kuchta 2.60 | Pavel Sulc 3.75 | Lyle Foster 3.60 | Iqraam Rayners 4.00
- **Anytime Goal + Assist Combos**: Several at 5.50-12.50 (e.g. Schick + Provod assist 5.50)
- **Clean Sheet**: Tsjekkia Ja 2.25 | Nei 1.58
- **Handicap 3-way 0:1**: Tsjekkia -1 3.35 | Uavgjort 3.40 | SA +1 1.97
- **1st Half Winner**: Tsjekkia 2.45 | Draw 2.10 | SA 4.80
- **Corners, Cards, Player Cards/Assists**: Many props (e.g. specific pairs getting card 8.35-18.00)
- **Combos at end**: Over 1.5 & Over 7.5 corners & Over 2.5 cards (Ja) @2.50 ; P. Schick scorer & Czechia win @2.70 etc.

### Other Matches in File (Lower Priority but Scanned)
- **Kristianstads DFF vs IK Uppsala (Damallsvenskan)**: Home 1.40, Over 2.5 1.42, BTTS Ja 1.57
- **BK Häcken vs FC Rosengård**: Home 1.20 heavy fav, Over 2.5 1.37
- **Tennis (Collignon/Bellucci, Eala/Rybakina, Medjedovic/Humbert)**: Fav MLs, game handicaps, total games overs/unders (e.g. Over 23.5/25.5)
- **Esports/Other**: Minor value in map handicaps

**Stage 1 Conclusion**: Strongest edges in Czechia win, Over 2.5, Schick anytime, and correlated combos. Swedish women's and tennis secondary.

---

## Stage 2: Deep Research Summary (Tool Calls: web_search + context)

### Czechia vs South Africa - Full Context
- **Tournament Situation**: Both teams on 0 points after Matchday 1 losses (Czechia 1-2 South Korea; South Africa 0-2 Mexico). Must-win to stay alive for knockout phase or better group standing.
- **Team News & Suspensions**: South Africa missing Sphephelo Sithole and vice-captain Themba Zwane (both sent off vs Mexico - major midfield loss, impacts control and creativity). Czechia squad fully available; no reported injuries affecting key players (Schick, Soucek, Kuchta, Provod, Sulc etc.).
- **Form & Quality Gap**: Czechia enter with better recent results and superior individual quality/experience (Premier League/Champions League level players). SA have shown fight but disciplinary issues and depth problems exposed.
- **Tactical Expectation**: Czechia favored to control possession (3-4-2-1 or similar), create high-quality chances via wings and Schick focal point. SA likely compact or counter-attacking but vulnerable to set-pieces and transitions. Expected total goals: 2.8-3.4 (open, motivated game).
- **Venue/Other**: Neutral venue (Atlanta) but European team likely more comfortable. Weather not extreme factor.

**Value Confirmation**:
- Czechia Win @1.82: True probability est. 62-67% (quality + motivation + SA absences) >> implied 54.9%. **EV +10-18%** (core allocation).
- Over 2.5 Goals @2.10: Expected 2.9-3.4 goals supports hit rate >52%. **EV +8-15%**.
- Patrik Schick Anytime @2.20: Primary goal threat, clinical vs weak SA defense. Est true prob 48-54%. **EV +6-15%**.
- Czechia Clean Sheet @2.25: Viable if dominance holds; correlates with win. Good secondary.
- Handicaps/1st Half: Tsjekkia -1 or strong 1st half control also positive but singles preferred for clarity.

**Risks Flagged**: SA high motivation (must-win), possible low-block resilience or set-piece luck. Variance in single WC match. No over-exposure to props.

### Secondary Matches Research Notes
- Swedish women's: Home teams strong favorites with goal volume; value in overs/home win if lines soft.
- Tennis: Standard grass/hard court fav edges and total games; lower EV than football but good for diversification (e.g. strong fav 2-0 or game HC).

---

## Final Recommendations (Bankroll Discipline Applied)

**Portfolio Construction**:
- Max 5% total risk this round.
- Flat stakes or conservative 1/2 Kelly sizing for flagged EV >8%.
- All **singles** (no parlays unless exceptional correlation at boosted odds).
- Immediate append to bet_log.csv via nt-bet-log-manager protocol (full SHA + proper quoting).

**Recommended Bets**:

1. **Tsjekkia Win @1.82** - Stake: 25 NOK (high conviction core bet)
   - Est EV: +10-18%
   - Notes: Quality + motivation edge vs depleted opponent. round_20260618_current_odds_01.md #1

2. **Over 2.5 Total Goals @2.10** - Stake: 20 NOK
   - Est EV: +8-15%
   - Notes: Open game expected, SA defensive issues. round_20260618_current_odds_01.md #2

3. **Patrik Schick Anytime Goalscorer @2.20** - Stake: 15 NOK
   - Est EV: +6-15%
   - Notes: Focal point in attack vs vulnerable defense. round_20260618_current_odds_01.md #3

**Optional/Secondary (if bankroll allows, lower stake)**:
- Czechia Clean Sheet Ja @2.25 - 10 NOK (correlates with win)
- Specific player props or Swedish home overs if deeper value confirmed.

**Expected Blended EV**: +9-14% on portfolio. Strict stop-loss and no chasing.

**Post-Settlement Plan**: Full deep dive + nt-learning-reviewer update after matches settle. Update current_bankroll.md only after verification checklist.

---

## Validation & Commit Notes
- Full content of current_odds_01.txt analyzed line-by-line per skill rules.
- All research tool-assisted (no shallow picks).
- bet_log.csv append executed immediately for the 3 core bets (see separate validation or included push).
- This file now contains complete actionable output replacing previous placeholder.
- Playbook followed: no confirmation asked before log append; user will correct if needed.

**Next**: Monitor live if needed, but pre-match analysis complete. Good luck!

*Updated and pushed via nt-betting-workflow + github tools per user instructions. SHA validated before/after.*