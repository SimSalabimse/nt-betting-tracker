# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 20:15 CEST (nt-bankroll-tracker + nt-bet-log-manager after appending 3 new pending bets for Switzerland vs Bosnia round; previous 6 settlements processed)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -120.80 NOK
- **Bankroll (Equity)**: **379.20 NOK**
- **Pending at Risk**: **47.00 NOK** (new: Embolo Anytime 15 + Switzerland Win 20 + Under 2.5 12)
- **Liquid Available**: **332.20 NOK**

## Verification (nt-bankroll-tracker skill + strict formula)
- Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed 379.20.
- New pending appended correctly to bet_log.csv (3 rows, Pending status, proper quoting in Notes).
- Pending at Risk increased from 0.00 → 47.00. Liquid updated.
- nt-bet-log-manager + nt-betting-workflow protocol followed exactly (full content push, SHA validated pre/post).
- Git push + re-validation (content + SHA) completed before this reply.
- Post-settlement: Will update realized P/L, equity, and add deep dive notes to round_20260618_current_odds_football_mlb.md after matches settle.

**New pending bets active for Switzerland vs Bosnia-Hercegovina WC match. All files pushed/validated per strict playbook and user GitHub workflow rules. nt-betting-workflow + nt-bet-log-manager + nt-bankroll-tracker followed.**

*Updated via GitHub connected tools with full content + SHA validation on every push.*