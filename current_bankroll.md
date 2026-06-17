# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 15:20 CEST (nt-bankroll-tracker after settlement of 5 bets from round_20260617_current_odds_01.md + mandatory deep dives + full verification)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -53.32 NOK
- **Bankroll (Equity)**: 446.68 NOK
- **Pending at Risk**: 0.00 NOK
- **Liquid Available**: 446.68 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc.
- Previous Equity 424.18 (realized -75.82) + this batch P/L (+6.00 Østerrike +21.00 Argentina O2.5 +2.50 Fritz +3.00 Nakashima -10.00 KT) = +22.50 → new realized -53.32, Equity 446.68 NOK.
- Pending at Risk = 0 (all 5 settled: Østerrike win, Argentina O2.5 win, Taylor Fritz win, Brandon Nakashima win, KT Rolster Challengers loss).
- Liquid Available = Bankroll - Pending = 446.68 NOK.
- Cross-check against Norsk Tipping: No discrepancy >5-10 NOK. All payouts matched user reported (rounded where noted).
- Settled in this batch: Brandon Nakashima win (payout 13), Taylor Fritz win (12.50), KT Rolster Challengers loss, Østerrike win (21), Argentina O2.5 win (41). nt-bankroll-tracker protocol + full verification executed.
- Git push + raw re-validation completed before any user reply. Playbook followed by the letter 100%.

*Bankroll fully reconciled post-settlement. Ready for next round. nt-bankroll-tracker skill complete.*