# round_20260620_current_odds_01.md — Brazil vs Haiti + Turkey vs Paraguay (FIFA WC 2026)

**Date**: 2026-06-20 | **Source**: current_odds_01.txt | **Workflow**: nt-betting-workflow (full Stage 1 rough EV scan across ALL lines + Stage 2 deep research) + nt-bet-log-manager + nt-bankroll-tracker

## Summary of User Action
User placed all 4 recommended bets on Norsk Tipping with **one minor change**: Vinicius Junior outside-16m prop stake increased from planned 8 NOK to **minimum 10 NOK**. All other stakes and selections exact as recommended. Logged precisely via nt-bet-log-manager protocol.

**Bets placed (exact)**:
1. Brazil vs Haiti — Over 4.5 Total Goals @2.80 stake **12 NOK**
2. Brazil vs Haiti — Vinicius Junior scorer from outside 16-meter feltet (Ja) @6.40 stake **10 NOK** (min stake adjustment)
3. Brazil vs Haiti — Tidspunkt for 1. Brasil mål: 1-15 min @3.00 stake **10 NOK**
4. Turkey vs Paraguay — Arda Guler To Score Or Assist and Tyrkia To Win (Ja) @2.75 stake **12 NOK**

**Total stake placed**: 44 NOK | **New pending risk added**: 44 NOK

## Match 1: Brazil vs Haiti (WC 2026 Group C, Philadelphia)
**HUB**: Brasil 1.10 | Uavgjort 8.80 | Haiti 23.00
**Key research (Stage 2)**: Confirmed lineup (Alisson; Danilo, Marquinhos, Gabriel, Alex Sandro; Casemiro, Guimarães, Paqueta; Raphinha, Cunha, Vinicius). Endrick benched, Neymar out (calf). Haiti weak minnow, expected defensive/low threat. High scoring + early goals likely. Brazil dominance expected (true win prob 93-96%+).

**Stage 1 rough EV scan highlights (new types explored)**:
- Over 4.5 goals @2.80: Strong value (implied ~35.7%, true est 55-65%+ from mismatch stats) → **Selected**
- Vinicius outside 16m Ja @6.40: Exploratory prop (Vini long-range threat vs weak org) → **Selected** (stake to min 10 NOK)
- 1st Brazil goal 1-15 min @3.00: Timing prop exploration (early goal probable) → **Selected**
- Many other props (cards combos, heading, high handicaps, time windows) scanned; only these met strict post-research EV + new-type + bankroll filters.

**Selected bets rationale**: High-EV mismatch lines + deliberate exploration of new odds types (timing, outside-box scorer) per user reminder. Diversified from main HUB.

## Match 2: Turkey vs Paraguay (WC 2026 Group D)
**HUB**: Tyrkia 2.05 | Uavgjort 3.30 | Paraguay 3.60
**Key research**: Turkey slight edge with creative young talents (Guler, Yildiz, Kerem). Paraguay leaky post poor start. Volume in attack/corners expected.

**Stage 1 highlights + new types**:
- Correlated Arda Guler scorer/assist + Turkey win (Ja) @2.75: Good correlated value (Guler focal point) → **Selected**
- Other props (cards, corners totals, timing, heading) scanned; this met EV + exploration criteria.

## New Odds Types Exploration (Additive per user request)
This round deliberately tested:
- High goal totals (>4.5)
- Timing of first goal (1-15 min window)
- Scorer from outside 16m / heading props
- Correlated player prop + team win combos
These are additive to usual main lines/over/under/BTTS. Small stakes used for exploration. Will monitor hit rate in post-settlement deep dive.

## Bankroll Impact (post-placement)
Equity: 442 NOK | Pending at Risk: 44 NOK (these 4) + any prior | Liquid: ~398 NOK
Full sync via nt-bankroll-tracker after bet_log append.

**All updates pushed and re-validated via GitHub tools (full content + SHA checks) before this file was written.**

## Post-Settlement Deep Dive (nt-bet-log-manager + post-settlement-learning-reviewer executed 2026-06-20)
**Settlements reported**:
- Over 4.5 goals: Loss (Brazil 3-0 Haiti — only 3 goals, controlled performance). P/L -12.00. Confirmed via official reports.
- Vinicius outside 16m Ja: Loss (Vini scored but shot from inside/edge of box per highlights). P/L -10.00. Lesson on exact shot location sensitivity.
- 1st Brazil goal 1-15 min: Loss (first goal 23'). P/L -10.00. VAR/offside volatility noted.
- Turkey correlated (Guler score/assist + Turkey win): Loss (Turkey 0-1 Paraguay, 10-man, fastest WC goal). P/L -12.00. Guler had chances but no decisive contribution + team loss killed combo.

**Deep dive learnings (internet tools + reports used)**:
- High goal line props (O4.5) in heavy fav mismatches can underperform even in wins if game is controlled/low-threat (Brazil dominated but paced themselves). Tighten future filter: require stronger xG/pace data or avoid O4.5+ on short-odds favs.
- "Outside 16m scorer" props are ambiguous/volatile — require video confirmation; consider clearer player props (anytime, first half, etc.) for better settlement reliability.
- Timing props highly sensitive to VAR/disallowed goals.
- Correlated player+team win props: High sensitivity to team result variance. In WC mismatches, prefer standalone player props or reduce stake significantly. Paraguay resilience (even 10-man) shows underdog fight factor often underestimated.
- Overall round variance realized as expected for exploratory new types; small stakes protected bankroll. Good data for future new-type allocation rules.

**Additive update to sport_edges_and_filters.md completed** (darts 180s validation + 170 variance lesson + esports HC variance + correlated prop filter note).

**Next**: Continue monitoring remaining pending (de Decker darts props settled in parallel batch; new round_20260620_current_odds_02.md bets).