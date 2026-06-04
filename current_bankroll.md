# Current Bankroll Tracker - NT Betting Tracker

**Maintained by Grok for Simen Jacobsen | Started: 2026-06-04**

**Current Bankroll**: **500 NOK** (as of 2026-06-04)

**Status**: Transition round complete under moderate acceleration rules. All tracked bets pending settlement (no realized P/L yet). 30 NOK total at risk from placed singles. 2 Mexican bets reviewed at 0 stake (preserved for transparency).

## Bankroll History

| Date       | Action                                      | Change (NOK) | New Balance | Notes                                                                 | Linked to bet_log.csv rows |
|------------|---------------------------------------------|--------------|-------------|-----------------------------------------------------------------------|----------------------------|
| 2026-06-04 | Starting bankroll (reset for new phase)    | +500        | 500        | Per reset protocol in playbook for transition to moderate acceleration. Previous tracking reset. 3 placed bets (10 NOK each = 30 NOK at risk). 2 Mexican reviewed (0 stake, logged for history). | 1-5 (all pending/reviewed) |
| 2026-06-04 | Pending bets logged (no P/L yet)           | 0 (risk only)| 500        | Portfolio EV modest positive expected. Strict daily loss cap and review rules apply. See rounds/ for full analysis. | All rows                   |

## How This File is Updated (per playbook Fail-Proof Bankroll & Bet Tracking + File Management Rule)
- **Additive only**: After every settlement, append new row(s) to the History table with net P/L change from bet_log.csv (sum of settled P_L_NOK), updated balance, and reference to specific bet rows.
- **Auto-compute support**: Current Bankroll, ROI, drawdown, streaks derived from bet_log + this history. No destructive edits.
- **Validation**: Every update pushed via GitHub tools then immediately re-fetched/validated before confirmation.
- **Pending risk**: 30 NOK at risk (~6% of bankroll) - within conservative Phase 1 targets (max ~5-10% daily).

## Pending Bets Risk Summary (from bet_log.csv)
- **Placed & Pending (transition 10 NOK stakes)**: 
  - Zverev to win (Tennis) @1.25 - 10 NOK
  - Under 5.5 Total Goals (NHL) @~1.95 - 10 NOK
  - Lynx ML (WNBA) @Check - 10 NOK
- **Reviewed/Pending (0 stake, not placed this round)**: 2x Mexican Liga MX bets (reviewed per full playbook protocol: form/H2H/motivation/stats; held due to strict risk cap in transition/Phase 1 Protect & Validate).
- **Total at risk**: 30 NOK. Expected portfolio EV positive once settled.

## Alignment with Playbook & Moderate Acceleration
- Bankroll: 500 NOK start (as of 2026-06-04 in playbook and README).
- Phase 1: Protect & Validate until ~1000 NOK bankroll + solid positive ROI data over 20-40 bets.
- Future: Once settled and growing, scale to 15-25 NOK flat per high-conviction bet, allow 4-6 bets/round on good +EV opportunities. Daily risk target ~60-100 NOK.
- Strict rules: Daily/weekly review, reset protocol on significant drawdown, full transparency in logs.

## Notes
- This file provides **detailed narrative + table tracking** for bankroll (complements raw data in bet_log.csv and round post-mortems).
- All changes strictly additive per File Management Rule (no removal of history).
- GitHub version history provides full diffs/audit trail.
- Next: Post-settlement updates will append realized P/L rows and adjust balance.

*File created additively 2026-06-04 via GitHub tool + validation. Playbook followed by the letter.*

## Update 2026-06-05: 5 Pending Bets at 10 NOK Each (All Singles) - Non-CSV Detailed Tracker

**Per user clarification**: The bankroll tracking file should not be a CSV file. This current_bankroll.md is the primary **non-CSV detailed narrative tracker**. The bankroll_tracker.csv serves as structured data/CSV log (expanded with columns for liquid/pending/bet type details). Both are kept in sync additively per playbook rules. No files deleted.

**Current State**:
- **Liquid Bankroll**: 450 NOK (500 NOK base minus 50 NOK stakes placed for the 5 pending bets)
- **Pending Stakes**: 50 NOK
- **Pending Bet Count**: 5 (all Singles @10 NOK each)
- **Bet Type Breakdown**: All 5 are Singles pending settlement.
- **Total Bankroll Value** (liquid + pending stakes): 500 NOK
- **At Risk**: 50 NOK (~10% of bankroll, within conservative limits for transition)

**The 5 Pending Bets at 10 NOK Each**:
1. Tennis: Zverev to win vs Mensik (RG SF, clay) @1.25 - 10 NOK - Pending
2. NHL: Under 5.5 Total Goals (Hurricanes vs Golden Knights, SCF G2) @~1.95 - 10 NOK - Pending
3. WNBA: Lynx ML vs Golden State Valkyries - 10 NOK - Pending
4. Mexican Liga MX Bet 1 - 10 NOK - Pending (reviewed per full protocol, now pending per clarification)
5. Mexican Liga MX Bet 2 - 10 NOK - Pending (reviewed per full protocol, now pending per clarification)

**Notes**: bet_log.csv updated additively with corrected rows to match exact format and 5 pending @10 NOK each (Stake_NOK=10 for all). bankroll_tracker.csv already reflects this. This md provides the human-readable detailed tracking as requested (not CSV). All updates additive, history preserved, validated via re-fetch. Moderate acceleration active; Phase 1 Protect & Validate.