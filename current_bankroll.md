# Current Bankroll Status Summary

**Last Updated**: 2026-06-16 23:45 CEST (nt-bet-log-manager + nt-bankroll-tracker after user placement of 2 new snooker bets from round_20260616_current_odds_01_snooker_football.md)

## Bankroll Figures (Verified)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (settled)**: -1.78 NOK
- **Bankroll (Equity)**: 498.22 NOK
- **Pending at Risk**: 123.00 NOK (previous pending + 2 new 15 NOK bets: Aaron Hill -2.5 @1.67 + Ricky Walden -2.5 @1.95)
- **Liquid Available**: 375.22 NOK

## Verification (nt-bankroll-tracker + nt-bet-log-manager)
- bet_log.csv append validated: +2 new Pending rows appended correctly. Header intact. All Notes use ; separators and avoid commas per protocol. Pointers to round_20260616_current_odds_01_snooker_football.md included.
- Strict formula recalc confirmed: Equity unchanged at 498.22 NOK until settlement. New Pending = 93 + 30 = 123.00 NOK. Liquid = 498.22 - 123 = 375.22 NOK.
- Git push via push_files + immediate raw re-validation completed successfully. No data loss. Additive only.
- Playbook followed exactly (Two-Stage workflow already documented in round file; now logged per nt-bet-log-manager).
- Ready for future settlements. Post-Settlement Deep Dives will be added to the round file after outcomes.

*Updated after safe logging of the 2 recommended snooker exploration bets. Bankroll protected. All per playbook.md mandatory checklist.*