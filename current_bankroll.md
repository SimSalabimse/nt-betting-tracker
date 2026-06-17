# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 18:40 CEST (nt-bankroll-tracker after placement of all 5 recommended pending bets from round_20260617_current_odds_tennis_snooker_football.md + full verification)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -53.32 NOK
- **Bankroll (Equity)**: 446.68 NOK
- **Pending at Risk**: 69.00 NOK
- **Liquid Available**: 377.68 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc (no change to realized P/L).
- Placement of 5 singles (Auger win 15 NOK + Medvedev -3.5g 12 NOK + He Guoqiang win 20 NOK + Lindorfitos -1.5 maps 10 NOK + Ilves win 12 NOK = total 69 NOK stake) only affects Pending at Risk. Equity unchanged per ironclad rule.
- Previous: Equity 446.68 | Pending 0 | Liquid 446.68
- New: Equity 446.68 | Pending 69.00 | Liquid 377.68
- Cross-check against Norsk Tipping: No discrepancy >5-10 NOK. All pending stakes logged correctly.
- Git push + raw re-validation completed before any user reply. Playbook followed by the letter 100%.

*Bankroll updated post-placement. Pending bets now tracked. Ready for settlements + mandatory deep dives. nt-bankroll-tracker skill complete.*