# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 20:06 CEST (nt-bankroll-tracker + nt-bet-log-manager after appending 3 new pending bets from Czechia vs South Africa WC analysis in round_20260618_current_odds_01.md)

## Bankroll Figures (Verified via full bet_log.csv recalc logic - analyze_betting.py equivalent)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -50.40 NOK
- **Bankroll (Equity)**: **449.60 NOK**
- **Pending at Risk**: **92.00 NOK** (previous 32.00 from Bouzkova/OConnor/Eskilstuna + new 60.00 from Czechia bets: 25+20+15)
- **Liquid Available**: **357.60 NOK**

## Verification (nt-bankroll-tracker skill + strict formula + post-settlement checks)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed unchanged (no new settlements).
- New pending added: +60 NOK at risk (Tsjekkia Win 25 + Over 2.5 20 + Schick Anytime 15). Pending at Risk updated from 32.00 → 92.00. Liquid adjusted accordingly.
- nt-bet-log-manager protocol followed for CSV append (fresh SHA fetch, proper quoting, append-only at bottom, no commas in unquoted fields).
- Cross-check: bet_log.csv now contains the 3 new Pending rows with correct Notes referencing round file and skills.
- No placement-only activity; all via robust manager.
- Git push + immediate re-validation (tree + content re-read) completed before generating this reply.
- nt-learning-reviewer / post-settlement notes carried forward from previous.

**New pending risk from WC football core bets added and bankroll figures recalculated per strict nt-bankroll-tracker rules. All playbook requirements met (deep research before bets, immediate log append, bankroll verification, push+validate before reply).**

*Updated via connected GitHub tools per user nt-bet-log-manager / nt-bankroll-tracker instructions. SHA validated before/after each push.*