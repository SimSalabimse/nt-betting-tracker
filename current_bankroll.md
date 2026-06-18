# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 20:11 CEST (nt-bankroll-tracker + nt-bet-log-manager after settling 6 pending bets: 3x Tsjekkia losses, OConnor loss, Pitea BTTS loss, Bouzkova -5.5 win)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -120.80 NOK (previous -50.40 + net delta -70.40 from 6 settlements: -25-20-15-10-10 +9.60)
- **Bankroll (Equity)**: **379.20 NOK**
- **Pending at Risk**: **0.00 NOK** (all previous pending settled this round)
- **Liquid Available**: **379.20 NOK**

## Verification (nt-bankroll-tracker skill + strict formula)
- Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed.
- All 6 pending bets settled per user report. bet_log.csv updated with Result/P_L_NOK + settlement notes only (no deletions, proper quoting).
- New realized P/L: Tsjekkia Win -25, Over 2.5 -20, Schick Anytime -15, OConnor -10, Eskilstuna/Pitea BTTS -10, Bouzkova +9.60.
- Pending at Risk reduced from 92.00 → 0.00. Equity and Liquid updated accordingly.
- nt-bet-log-manager protocol followed exactly (fresh SHA, append-only for new, targeted updates for settlements).
- Git push + re-validation (content + SHA) completed before this reply.
- Post-settlement deep dives / learning notes can be added to round file if needed.

**All settlements processed, bankroll recalculated, and files pushed/validated per strict playbook rules. nt-betting-workflow + nt-bet-log-manager + nt-bankroll-tracker followed.**

*Updated via GitHub connected tools with full content + SHA validation on every push.*