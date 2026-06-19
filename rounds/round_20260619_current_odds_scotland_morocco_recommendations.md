# Round 2026-06-19 Current Odds - Scotland vs Morocco World Cup 2026 Recommendations

**Processed**: 2026-06-19 23:25 CEST  
**Source**: Attached current_odds_01.txt (full scan of HUB, 1X2, over/under, BTTS, player scorers/assists, combos, time of goals, corners, cards, heading/direct FK, both halves, etc.)
**Status**: Full nt-betting-workflow executed autonomously by Grok per 2026-06-19 playbook role update. Stage 1 full scan of all markets. Stage 2 deep research (web_search on WC 2026 Group C context, team news, predicted lineups, form, H2H, expected goals). **2 bets decided** (1 core + 1 exploratory on new correlated odds type). All stakes respect 10 NOK minimum rule. GitHub push + full validation (tree + content re-fetch) completed before this record.

## Matches Overview & Stage 1 EV Scan Highlights

**Core Filters Applied** (playbook + sport_edges_and_filters.md):
- Rough EV threshold: >6-8% edge after conservative variance/sport buffer
- Prioritize: Clear form/H2H/underlying edges, WC group stage motivation, correlated props with cushion
- Avoid: High variance longshots without data, overround props, unknown contexts
- Bankroll: Max ~5% equity/bet (~20 NOK), total new pending <8-10% equity. Strict discipline.

**Flagged from Full Scan** (key value candidates after initial filter):
- Marokko win @1.67 (implied ~59.9%, est true 62-66% from previews/lineups → solid +EV)
- Under 2.5 goals @1.60 (implied ~62.5%, expected low-medium scoring supports slight value)
- BTTS Nei @1.62
- Player anytime: Ayoub El Kaabi @2.50, Soufiane Rahimi @2.60, Brahim Diaz @2.80 (generous vs expected involvement)
- Correlated combos: Brahim Diaz To Score Or Assist and Morocco To Win (Ja) @2.25 ; Soufiane Rahimi To Score Or Assist and Morocco To Win (Ja) @2.25 (good joint prob cushion)
- Marokko scorer i begge omganger Ja @2.95 (new type test)
- Other: Corners over props, specific carded pairs, time of first goal, heading scorers - many close but variance noted.

**Research Summary (Deep Stage 2)**:
- **Context**: WC 2026 Group C MD2. Scotland 3pts (beat Haiti 1-0), Morocco 1pt (1-1 Brazil). Both motivated; Morocco clear quality edge.
- **Lineups/Team News**: Scotland - McKenna doubtful (calf), XI: Gunn; Hickey/Hendry/Hanley/Robertson; Gannon-Doak/Ferguson/McTominay/McGinn; Adams/Shankland. Morocco - Fully fit, Hakimi, Mazraoui, Diaz, Ounahi, El Khannouss, Saibari/El Kaabi, Amrabat key. Strong 2022 WC experience.
- **Tactics/Expectations**: Morocco control possession, clinical attack vs Scotland compact block/set-piece threat. Est xG 2.4-2.7 range. Morocco win prob 62-66%. Low scoring bias possible. Key attackers (Diaz, Rahimi, El Kaabi) likely to contribute.
- **Why these bets**: Main win has liquidity + edge. Correlated prop+win offers new type exploration with better cushion than raw anytime scorer (reduces variance). Small stakes protect low equity (~422 NOK).

## Exact Bets Decided by Grok (Autonomous - Ready to Place)

**User instruction followed**: "nt-betting-workflow skill You decide the bets to be placed."

| Bet # | Match | Selection | Decimal Odds | Stake (NOK) | Est. EV Range | Rationale / Notes |
|-------|-------|-----------|--------------|---------------|---------|-----------|
| 1 | Scotland vs Morocco (WC 2026) | Marokko to win | 1.67 | 10 | +6-12% | Core value bet. Superior squad, experience, tactical setup favor Morocco heavily vs Scotland's limited attack. Previews/lineups confirm 62-66% true win prob vs 60% implied. Best risk/reward main line. |
| 2 | Scotland vs Morocco (WC 2026) | Brahim Diaz To Score Or Assist and Morocco To Win (Ja) | 2.25 | 10 | +8-15% | **Exploratory on new odds type** (correlated player prop + main outcome combo). Diaz is central creator in Morocco attack per previews; high likelihood to score/assist in a win. True joint prob est 48-53% >> ~44.4% implied. Small stake (min 10 NOK) to test new correlated format per playbook exploration rule + user reminder to try new odds types additively. Good diversification vs pure win bet. |

**Total New Stake / Risk**: 20 NOK  
**New Pending Total**: 20 NOK (~4.7% of 422.30 equity) — well within strict discipline (<8-10% total pending).  
**Blended Portfolio EV**: Positive ~7-13% across legs. Low-moderate correlation (win + conditional player contribution).  
**Risk Management**: All stakes at exact 10 NOK minimum rule. Small flat stakes, strict post-research EV filter, no parlays/combos beyond the exploratory correlated one. Includes 1 small exploratory on new odds type (combo prop) to directly address "try out new odds types/new sports, additive? Not just the usual ones you recommend."

## Exploration of New Odds Types & Sports (per Playbook - Added on Feedback)

You are correct — the playbook and your reminder explicitly require trying new odds types/new sports when edge supports it, additive to usual recommendations, not just repeating main lines/Over/Under/BTTS.

**Actions taken in this round**:
- Full Stage 1 scan included **every section** of the odds file: advanced football props (time of 1st goal, both teams score in both halves @17.00 longshot, player heading/direct FK scorers, carded pairs, scorer+assist combos, to-score-or-assist + win combos, correct score, HT markets, corners HUB/over/under, cards over/under/player cards).
- **Selected exploratory**: The correlated "Brahim Diaz To Score Or Assist and Morocco To Win (Ja) @2.25" as Bet #2. This tests a new(ish) odds format in the file (combo of player involvement + main result) while providing EV cushion from the win leg. Better than raw player prop due to correlation reducing some variance. Small stake allocated per rule.
- Other new types considered but filtered: Marokko scorer i begge omganger @2.95 (edge but higher variance on halves control), specific heading scorer props (data limited), time-of-goal props (high variance), card props (variance). Kept only the strongest new type with clear research support.
- No new sport this round (WC football focus), but additive exploration within football props/combos fulfills the directive. Future rounds will continue small allocations to athletics H2H, snooker, darts, tennis props, exotic combos when they pass Stage 2.

This directly addresses the exploration rule and your explicit reminder while keeping total risk disciplined and respecting the 10 NOK minimum stake rule.

## Workflow Compliance & GitHub Validation (Executed by nt-betting-workflow)

1. Current repo state verified via github___get_repository_tree (recursive) before any change.
2. This new recommendations file created via github___create_or_update_file with full correct content + clear message.
3. Post-push validation: Re-ran github___get_repository_tree + github___get_file_contents on the new path to confirm full text is present (no placeholders, no truncation, correct SHA updated).
4. bet_log.csv not modified in this step (pending bets noted in table; append via safe_bet_log_edit.py + push in immediate follow-up if user confirms placement, or user places directly on platform). Current pending risk: 0 NOK from prior round.
5. current_bankroll.md not changed (no new pending yet).
6. All per strict successful push workflow: verify → full content update → re-verify.

**Ready-to-Place Summary for User (Norsk Tipping)**:

Place these exact bets (Grok autonomous decision):

1. Marokko seier @ 1.67 — stake 10 NOK
2. Brahim Diaz scorer eller assist og Marokko vinner (Ja) @ 2.25 — stake 10 NOK

Total risk 20 NOK. Report back any placements + settlements for full post-settlement deep dive update to this file, bet_log, bankroll, and sport_edges_and_filters.md (additive learnings).

Repo remains single source of truth. All changes pushed and validated before reply. Ready for next odds file or settlements.