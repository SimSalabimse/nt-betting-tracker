# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 21:10 CEST (nt-bankroll-tracker after settlements of 3 new bets + He Guoqiang from round_20260617_current_odds_mlb_portugal_nordic.md + mandatory deep dives + full verification)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -72.04 NOK
- **Bankroll (Equity)**: **427.96 NOK**
- **Pending at Risk**: 10.00 NOK (Houston Astros vs Detroit Tigers - Detroit Tigers -1.5 @2.36 stake 10 NOK - still pending)
- **Liquid Available**: 417.96 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc.
- This batch settlements (3 of 4 pending):
  - He Guoqiang win @1.15 stake 20 → P/L **+3.00** NOK (payout 23 NOK)
  - Portugal Over 2.5 @1.77 stake 20 → P/L **-20.00** NOK (Loss, 1-1 final)
  - Ronaldo to Score Anytime @1.65 stake 15 → P/L **-15.00** NOK (Loss)
- Net this batch: +3 -20 -15 = **-32.00** NOK
- Previous Equity 459.96 -32.00 = new Equity **427.96** NOK. Pending reduced from 65 to 10 NOK (only Tigers -1.5 remains).
- Liquid = Equity - Pending = 417.96 NOK.
- Cross-check against Norsk Tipping: No discrepancy >5-10 NOK. Full bet_log.csv updated with settlement notes.
- **Mandatory Post-Settlement Deep Dives** added to round file before this reply. nt-bankroll-tracker + nt-bet-log-manager + nt-learning-reviewer protocol executed.
- Git push + raw re-validation completed before any user reply. Playbook followed by the letter 100%.

**Settlements processed. Bankroll fully reconciled. 1 pending remains (Tigers -1.5). Ready for final settlement + deep dive.**

*nt-bankroll-tracker skill complete. All updates pushed and validated.*