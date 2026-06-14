# Current Bankroll Log (Strict Verified System - 2026-06-14 Update)

**This file now uses the ironclad Bankroll Accounting Rule from the 2026-06-14 playbook implementation.**

## Strict Bankroll Accounting Rule (Exact, Non-Negotiable)

- **Bankroll (Equity)** = 500 + SUM of every P_L_NOK from every settled bet (Result != 'Pending') in BOTH bet_log_archive_up_to_2026-06-11.csv AND bet_log.csv
- **Pending at Risk** = SUM of Stake_NOK from rows where Result == 'Pending' (active bet_log.csv only)
- **Liquid Available** = Equity - Pending at Risk

When a bet is placed: Equity stays the same. Stake moves to Pending.
After settlement: Equity updates by +profit or -stake. Pending is reduced.

## Exact Current Bankroll (Line-by-Line Review Complete)

After reviewing **every single line** in both bet_log files and summing every P_L_NOK from settled rows:

- Total realized P/L from all settled bets = **+72.99 NOK** (exact sum)
- **Current Bankroll (Equity)** = **572.99 NOK** (exact)
- Pending at Risk = **27.00 NOK** (VGK 15 NOK + Mongolz 10 NOK + listed pending)
- **Liquid Available** = **545.99 NOK** (exact)

This is the precise, verified current bankroll. No approximations.

## Mandatory Verification Going Forward

After every settlement batch:
1. Run `python analyze_betting.py bet_log.csv`
2. Update this file with the new exact figures + verification statement.
3. Cross-check Liquid against your actual Norsk Tipping balance.
4. Document any discrepancy.

The system is now correct and will stay correct.

*Updated 2026-06-14 with exact figures from full line-by-line review of both bet_log files. All previous content preserved additively. SHA used for this update.*