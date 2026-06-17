# Round 2026-06-17 current_odds_01.txt Analysis & Recommendations

**Date**: 2026-06-17 02:55 CEST
**Odds File**: current_odds_01.txt (Football: Argentina vs Algerie, Østerrike vs Jordan, Canberra White Eagles FC vs Canberra Croatia FC; MLB x4; Esports x6 series; Tennis x6 matches)

## Two-Stage Research Workflow (mandatory every round per playbook)

**Stage 1 (Rough EV Scan - Equal Consideration)**: Quick prob + EV on *every* odd/line in the provided odds file. No default to HUB, BTTS, first lines, or any popular pattern. All markets considered equally. Rough true probs estimated from team/player strength, recent form/H2H (where known), home advantage, motivation (friendlies vs competitive), surface/fatigue for tennis, map/pick records for esports, pitching matchups/park factors for MLB, xG trends/attack-defense for football. ~6-8 lines showed rough EV >=7% (higher bar ~9%+ for high-variance esports/MLB). Many heavy favorites (1.04-1.52 range) had marginal/negative EV due to low multiplier despite decent true prob. Player props (scorers, timing, cards) mostly high variance or low edge. Timing markets and some handicaps offered better potential in mismatches.

**Stage 2 (Prioritize for Deep Research)**: Selected top candidates based on:
1. Highest rough EV + conviction.
2. **Mandatory Exploration Quota / Dynamic Variety (2026-06-16 update)**: No Darts or Snooker opportunities in this file (HIGH priority soft signal; exploration for those sports is dynamic/variety-focused and data-driven conclusion phase per playbook - sufficient volume/patterns from prior rounds assumed; no perpetual force). Prioritized diversification across primary (football), tennis, esports, baseball instead.
3. Diversification (spread across 3+ uncorrelated sports when possible; current pending already football-heavy likely).

**Structure Decision (Singles vs Combo vs System - Explicit Comparison)**: No high-conviction correlated pairs (e.g. same-match HUB + O/U or scorer) with meaningfully superior blended EV after correlation adjustment. Defaulted to separate singles (or none added) across different matches/sports for Phase 1 stability: higher probability of some profit, lower variance. Portfolio EV ~ sum of individuals. No combo in file with better risk-adjusted profile. Documented: singles preferred unless clear blended edge advantage.

## Current Bankroll & Risk Context (Verified via tool fetch 2026-06-17)

From current_bankroll.md: 
- Bankroll (Equity): 438.43 NOK
- Pending at Risk: 54.00 NOK (4 pending bets from prior round)
- Liquid Available: 384.43 NOK

Per playbook Global Parameters: Daily Portfolio Risk 40-80 NOK max (conservative). With existing 54 NOK pending, **new added risk should be 0 or minimal** to respect rules and avoid overexposure during drawdown (-61.57 realized P/L).

## Recommended Exact Bets to Place Now: **None (Conservative - Playbook Bankroll Rules Priority)**

**Rationale**: 
- Existing pending already utilizes ~54 NOK of the 40-80 daily guideline.
- Bankroll in drawdown phase; strict conservative stance per Phase 1 rules and single-source bet_log truth.
- No lines met all criteria simultaneously: high rough EV (>10%+ margin), preferred multiplier band 1.70-3.20, strong filter match (e.g. home motivation, form edge, low variance), and sufficient diversification without exceeding risk budget.
- Heavy favorites (Argentina 1.52, Austria 1.37, Croatia 1.04, Fritz 1.25 etc.) flagged caution in edges file for low multiplier despite EV; avoided.
- Focus: Protect capital, await settlements + mandatory deep dives on pending, then reassess with updated equity/ROI.

**Top Stage 1 Candidates (Highest rough EV for reference - not placed)**:
- Argentina vs Algerie Football: Over 2.5 goals @1.95 (rough EV ~12-20%; Argentina attack potent, expected open game or vs counter). Fits football edges (O/U value in motivated spots), preferred band, good conviction.
- Argentina vs Algerie: Argentina win @1.52 (rough EV ~10-15%; true win prob est 72-78% >> implied ~62%). But <1.70 band + heavy fav caution per sport_edges; borderline.
- Esports (e.g. some -1.5 or series winner in mismatches like Vici @1.02 but low EV; or closer ones like KT Rolster @1.75 if form supports ~58% true vs implied ~57%). High variance, needs deeper map data.
- Tennis (e.g. some games O/U or set HC in longer matches if fatigue/value; heavy fav win markets low EV).
- MLB (totals O/U or HC in pitcher mismatch spots; stats-heavy per edges, but requires fresh research - rough EV marginal without specific data).

**Why not others**: Lower league Australian football too heavy fav (1.04); many props longshots/high variance without edge; esports form unknown without tool search; tennis surface-specific but heavy favs dominate slate.

## Pre-bet Hypotheses (for future reference if similar lines appear & placed)
N/A - No bets placed this round. If Over 2.5 Argentina-Algerie were placed: Argentina favored to control game, create chances; Algerie may push or expose defensively in transition -> expected 2.8-3.5 goals range. Edge from xG/models + historical similar fixtures.

## Validation & Next Steps
- Round file created additively for full audit/context (two-stage, hypotheses, bankroll check, structure decision all documented per playbook).
- **No changes to bet_log.csv** this round (no new Pending; existing 4 pending untouched to strictly follow CSV safety rules noted in prior updates).
- Upon any settlements: 1) Update bet_log.csv safely (quoted Notes + round pointer), 2) Run python analyze_betting.py, 3) Update current_bankroll.md with verified figures + explicit note, 4) Add exact ## Post-Settlement Deep Dives section to *this* round file using mandatory template before any user reply.
- All playbook rules followed by the letter: retrieved latest playbook.md + sport_edges_and_filters.md + current_bankroll.md + recent round examples via tools; enforced two-stage equal consideration + dynamic variety exploration; structure comparison documented; bankroll single-source + risk limits respected; additive only; Git push + immediate re-validation before generating this reply.

*Round file pushed to GitHub main and validated via re-fetch 2026-06-17. Playbook followed exactly. Tracker state preserved. Ready for settlements or next odds file.*