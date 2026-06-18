# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 23:02 CEST (nt-bankroll-tracker + nt-bet-log-manager after settling 3 pending bets for Switzerland vs Bosnia round)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: **-136.80 NOK** (previous -120.80 + net -16.00 from 3 settlements: +11 -15 -12)
- **Bankroll (Equity)**: **363.20 NOK**
- **Pending at Risk**: **0.00 NOK** (all pending now settled)
- **Liquid Available**: **363.20 NOK**

## Verification (nt-bankroll-tracker skill + strict formula)
- Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed.
- All 3 pending bets settled: Embolo Loss (-15), Switzerland Win (+11 on 31 total payout), Under 2.5 Loss (-12). bet_log.csv updated with Result/P_L_NOK + appended settlement notes only (no deletions, proper quoting).
- Pending at Risk reduced from 47.00 → 0.00. Equity and Liquid updated accordingly.
- nt-bet-log-manager protocol followed exactly (fresh SHA, targeted settlement updates, full content push).
- Git push + re-validation (content + SHA) completed before this reply.
- Post-settlement deep dives / learning notes added to round_20260618_current_odds_football_mlb.md.

**Round net: -16 NOK. Switzerland win hit as expected; Embolo no goal + over 2.5 both missed. All files pushed/validated per strict playbook rules. nt-betting-workflow + nt-bet-log-manager + nt-bankroll-tracker followed.**

*Updated via GitHub connected tools with full content + SHA validation on every push.*