# Current Bankroll Status Summary

**Last Updated**: 2026-06-17 03:01 CEST (nt-bankroll-tracker after settlement of 4 pending bets from round_20260616_current_odds_02.md)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -75.82 NOK
- **Bankroll (Equity)**: 424.18 NOK
- **Pending at Risk**: 0.00 NOK
- **Liquid Available**: 424.18 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') = 424.18 NOK
- Pending at Risk = SUM(Stake_NOK for Result == 'Pending') = 0.00 NOK
- Liquid Available = Bankroll - Pending at Risk = 424.18 NOK
- Settled in this batch: 
  - Irak vs Norge, Begge lag scorer Nei @1.50 12 NOK (Loss, P/L -12.00)
  - Irak vs Norge, Erling Haaland scorer @1.45 15 NOK (Win, P/L +6.75)
  - Irak vs Norge, Norge win @1.20 15 NOK (Win, P/L +3.00)
  - Irak vs Norge, Norge holder nullen Ja @1.58 12 NOK (Loss, P/L -12.00)
- Cross-check: Exact payouts provided by user (18 NOK and 21.75 NOK total returns). No discrepancy. Git push + raw validation completed before reply.
- Playbook followed by the letter. Ready for Post-Settlement Deep Dives + new round analysis.

*Bankroll updated post-settlement. All rules followed.*