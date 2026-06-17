# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 03:22 CEST (nt-bankroll-tracker after placement of 5 new pending bets from round_20260617_current_odds_01.md + user adjustments)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -75.82 NOK
- **Bankroll (Equity)**: 424.18 NOK
- **Pending at Risk**: 65.00 NOK
- **Liquid Available**: 359.18 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') = 424.18 NOK (unchanged - placements only affect Pending)
- Pending at Risk = SUM(Stake_NOK for Result == 'Pending') = 65.00 NOK (Østerrike win 15 + Over 2.5 Arg 20 + Fritz 10 + Nakashima 10 + KT Rolster 10)
- Liquid Available = Bankroll - Pending at Risk = 359.18 NOK
- New pending batch placed per user confirmation with adjustments (Nakashima stake to min 10 NOK; Argentina HUB win replaced by Over 2.5 @1.95 20 NOK as clearer value). All 5 logged to bet_log.csv with quoted Notes + round pointer.
- Cross-check: No discrepancy. Git push + raw validation completed before reply.
- Playbook followed by the letter. Ready for settlement + mandatory deep dives on these 5.

*Bankroll updated post-placement. All rules followed. nt-bankroll-tracker protocol executed.*