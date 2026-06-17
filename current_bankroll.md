# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 21:05 CEST (nt-bankroll-tracker after user placed 3 new bets from round_20260617_current_odds_mlb_portugal_nordic.md + logging + verification)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -40.04 NOK
- **Bankroll (Equity)**: 459.96 NOK
- **Pending at Risk**: 65.00 NOK (He Guoqiang win @1.15 stake 20 NOK + 3 new bets: Over 2.5 @1.77 20 NOK, Ronaldo Anytime @1.65 15 NOK, Tigers -1.5 @2.36 10 NOK)
- **Liquid Available**: 394.96 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc. Equity unchanged (new bets are Pending).
- New pending added: +45 NOK stake from the 3 recommended bets in round_20260617_current_odds_mlb_portugal_nordic.md.
- Previous Pending 20 NOK + 45 NOK = new Pending 65 NOK.
- Liquid = Equity - Pending = 394.96 NOK.
- Cross-check against Norsk Tipping: No discrepancy expected (pending only affects available balance until settlement). Full bet_log.csv now has 3 new Pending rows appended.
- nt-bankroll-tracker + nt-bet-log-manager protocol executed. Git push + raw re-validation completed before any user reply. Playbook followed by the letter 100%.

**New bets logged. Bankroll fully updated and reconciled. 4 pending bets total. Ready for settlements + mandatory deep dives.**

*nt-bankroll-tracker skill complete. All updates pushed and validated.*