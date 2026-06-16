# Current Bankroll Status Summary

**Last Updated**: 2026-06-16 23:59 CEST (nt-bankroll-tracker + nt-bet-log-manager after settling 4 pending bets: Aaron Hill, X5 Gaming, IFK Värnamo, Ricky Walden)

## Bankroll Figures (Verified via full bet_log.csv recalc)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -61.57 NOK
- **Bankroll (Equity)**: 438.43 NOK
- **Pending at Risk**: 0.00 NOK (all 4 pending settled in this batch)
- **Liquid Available**: 438.43 NOK

## Verification (nt-bankroll-tracker skill + analyze_betting.py)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') = 438.43 NOK
- Pending at Risk = SUM(Stake for Pending) = 0 (Aaron Hill Win payout 25.05, P/L +10.05; three Losses -15 each)
- Liquid = Equity - Pending = 438.43 NOK
- Cross-check: Matches full CSV recalc. No discrepancy.
- Settled in this batch: Aaron Hill (win, 25.05 NOK payout), X5 Gaming +1.5 (loss), IFK Värnamo (loss), Ricky Walden -2.5 (loss). CSV quoting fixed (no value after quoted field on line 2+). nt-bet-log-manager protocol followed exactly.
- Git push + raw validation completed before reply.
- Playbook followed by the letter. Ready for next round.

*Bankroll updated post-settlement. All pending cleared. Deep dives added to round files per mandatory protocol.*