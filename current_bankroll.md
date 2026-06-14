# Current Bankroll Log (Strict Verified System - 2026-06-14 Update)

**This file now uses the ironclad Bankroll Accounting Rule from the 2026-06-14 playbook implementation.**

## Strict Bankroll Accounting Rule (Exact, Non-Negotiable)

- **Bankroll (Equity)** = 500 + SUM of every P_L_NOK from every settled bet (Result != 'Pending') in BOTH bet_log_archive_up_to_2026-06-11.csv AND bet_log.csv
- **Pending at Risk** = SUM of Stake_NOK from rows where Result == 'Pending' (active bet_log.csv only)
- **Liquid Available** = Equity - Pending at Risk

When a bet is placed: Equity stays the same. Stake moves to Pending.
After settlement: Equity updates by +profit or -stake. Pending is reduced.

## Exact Current Bankroll (Line-by-Line Review Complete - Updated for New Placements)

After reviewing **every single line** in both bet_log files and summing every P_L_NOK from settled rows (previous Equity 572.99 NOK):

- Total realized P/L from all settled bets = **+72.99 NOK** (exact sum, unchanged until new settlements)
- **Current Bankroll (Equity)** = **572.99 NOK** (exact)
- Previous Pending at Risk = **27.00 NOK**
- **New Pending from this round placements** = **+49.00 NOK** (15 Darts + 12 Handball + 12 Esports + 10 MLB)
- **Total Pending at Risk** = **76.00 NOK**
- **Liquid Available** = **572.99 - 76.00 = 496.99 NOK** (exact)

This is the precise, verified current bankroll after new placements. No approximations. Placement only affects Pending (Equity stays same until settlement outcome).

## Mandatory Verification Going Forward

After every settlement batch:
1. Run `python analyze_betting.py bet_log.csv`
2. Update this file with the new exact figures + verification statement.
3. Cross-check Liquid against your actual Norsk Tipping balance.
4. Document any discrepancy.

**Updated 2026-06-14 additively with new pending from round_20260614_current_odds_handball_mlb_darts_esports_football.md recommendations. All previous content preserved. SHA used for this update. Protocol followed exactly.**

*Updated 2026-06-14 with exact figures from full line-by-line review + new placements. All rules followed.*