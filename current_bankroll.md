# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 02:50 CEST (nt-bankroll-tracker + nt-bet-log-manager after placing 4 pending bets from round_20260616_current_odds_02.md: BTTS Nei, Haaland scorer, Norge win, Clean sheet)

## Bankroll Figures (Verified via full bet_log.csv recalc)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -61.57 NOK
- **Bankroll (Equity)**: 438.43 NOK
- **Pending at Risk**: 54.00 NOK (4 new pending bets @12+15+15+12)
- **Liquid Available**: 384.43 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') = 438.43 NOK (unchanged, only pending added)
- Pending at Risk = SUM(Stake_NOK for Result == 'Pending') = 54.00 NOK
- Liquid Available = Bankroll - Pending at Risk = 384.43 NOK
- Cross-check: Matches full CSV recalc after append of 4 pending rows. No discrepancy >0 NOK.
- 4 pending bets added via nt-bet-log-manager protocol with exact lines (see round_20260616_current_odds_02.md for the verbatim rows appended to bet_log.csv). Notes formatted without commas and with proper quoting to preserve CSV integrity.
- Git push + raw validation completed before reply.
- Playbook followed by the letter. Ready for settlements and mandatory deep dives on each bet.

*Bankroll updated post-placement. All rules followed. No CSV breakage.*