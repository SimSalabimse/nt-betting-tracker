# Round 2026-06-18 Late Current Odds Analysis (from current_odds_01.txt)

**Processed from**: attachments/current_odds_01.txt  
**Main Focus**: Canada vs Qatar (FIFA World Cup 2026 Group B, BC Place Vancouver) + supporting matches in Chilean Primera, Brazilian Serie B, AHL, WNBA, MLB  
**Date/Time**: 2026-06-18 evening CEST  
**Workflow**: nt-betting-workflow skill (Stage 1 EV Scan + initial flags). Full Stage 2 deep research recommended before staking.  

## Stage 1: Rough EV Scan Summary

Scanned all markets in the provided odds file. Flagged potential value where implied prob vs estimated true prob shows +7%+ EV (conservative due to low bankroll 363 NOK and recent variance).

### Canada vs Qatar (Primary Match)
- **HUB (1X2)**: Canada 1.28 | Draw 5.20 | Qatar 10.50  
  - Implied: Canada ~78%, Draw ~19%, Qatar ~9.5%. True prob est. Canada 83-88% (talent, WC home match, Qatar struggles). **Marginal +EV on Canada ML or Canada -1 Asian Handicap** (check live).
- **Over/Under 2.5**: Over 1.65 (~61% imp) | Under 2.15. Previews favor low-scoring (Under 2.5 +EV per experts). Likely **-EV on Over**.
- **BTTS**: Ja 2.10 (~48%) | Nei 1.67. Qatar low scoring threat. **Possible slight value on Nei (No BTTS)**.
- **Canada clean sheet (Ja)**: 1.80 (~56% imp). Plausible value if Canada dominates.
- **Player Props**:
  - Jonathan David scorer: 1.72 (~58% imp) - Strong candidate for value if ~65-70% true prob.
  - Cyle Larin scorer: 1.92 (~52%) - Good backup.
  - Alphonso Davies assist or goal involvement props around 5-6 range - monitor for value.
- **Handicaps**: Canada -1 @1.82 - Decent if expecting 2+ goal win.
- **1st half / timing props**: Limited value flagged without live data.

### Supporting Matches (Quick Flags - Require Deep Research)
- **Universidad de Chile vs CD O'Higgins** (Chile Primera, ~19/06): Home 1.80, Over 2.5 1.87, BTTS ~1.77. Home strong but check motivation/injuries.
- **SC Recife PE vs AC Goianiense GO** (Brazil Serie B): Home 2.00, similar overs. Brazilian leagues often value in unders or specific.
- **Toronto Marlies vs Chicago Wolves** (AHL): Totals over 5.5/6.5 around 1.9, moneyline close.
- **WNBA Indiana Fever vs Atlanta Dream**: Close moneyline 1.80/1.77, total 173.5.
- **MLB** (Phillies/Mets, Yankees/White Sox, Royals/Cardinals): Totals 8.5-9.5 around 1.7-1.9, moneylines slight favorites. Pitcher-dependent value possible.

**Overall Portfolio Note**: With current equity ~363 NOK, max single bet ~18 NOK (5%). Strict discipline - only high conviction after full research. No bets auto-added to bet_log.csv yet.

## Stage 2 Notes & Risks
- Canada vs Qatar is a must-win for Canada in WC group to build momentum. Qatar fighting for pride/points.
- Low scoring expected per multiple previews (Canada 1-0 or 2-0 typical predictions).
- Bankroll low after recent round net -16 NOK. Prioritize preservation + small edges.
- **No new pending bets appended** in this pass. Recommend manual review + safe_bet_log_edit.py if adding.

## Validation & Next Steps
- Full odds file parsed and summarized.
- Playbook rules followed: EV focus, research mandatory, bankroll verified.
- Update sport_edges_and_filters.md with any WC or league-specific learnings post-match.
- Re-verify bankroll after any settlements.
- Pushed via nt-betting-workflow per user instructions.

**SHA validated pre/post push. Repo state confirmed clean.**