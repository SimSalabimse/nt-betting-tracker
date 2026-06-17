# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 18:47 CEST (nt-bankroll-tracker after settlement of 4 bets from round_20260617_current_odds_tennis_snooker_football.md + mandatory deep dives + full verification; 1 bet remains pending)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -40.04 NOK
- **Bankroll (Equity)**: 459.96 NOK
- **Pending at Risk**: 20.00 NOK (He Guoqiang win @1.15 stake 20 NOK - still pending)
- **Liquid Available**: 439.96 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc.
- This batch settlements (4 of 5): Auger win (+9.00), Lindorfitos -1.5 loss (-10.00), Ilves win (+6.84), Medvedev -3.5 win (+7.44) = net +13.28 NOK this batch.
- Previous Equity 446.68 +13.28 = new Equity 459.96 NOK. Pending reduced from 69 to 20 NOK (only He Guoqiang remains).
- Liquid = Equity - Pending = 439.96 NOK.
- Cross-check against Norsk Tipping: No discrepancy >5-10 NOK. Payouts matched user reported (Auger 24, Ilves 18.84, Medvedev 19.44; Lindorfitos loss 0).
- Mandatory Post-Settlement Deep Dives added to round file before this reply. nt-bankroll-tracker + nt-bet-log-manager protocol + full verification executed.
- Git push + raw re-validation completed before any user reply. Playbook followed by the letter 100%.

*Bankroll fully reconciled post-settlement batch. 1 pending remains (He Guoqiang). Ready for final settlement + deep dive. nt-bankroll-tracker skill complete.*