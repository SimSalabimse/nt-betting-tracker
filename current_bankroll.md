# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 00:27 CEST (nt-bankroll-tracker + nt-bet-log-manager after settlement of 4 pending bets: Harry Kane win, England win, Dodgers U7.5 loss, Detroit Tigers -1.5 loss + mandatory Post-Settlement Deep Dives + nt-learning-reviewer review + full verification)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -72.04 + 6.00 = **-66.04 NOK**
- **Bankroll (Equity)**: **433.96 NOK**
- **Pending at Risk**: **0.00 NOK** (all 4 pending bets settled in this batch)
- **Liquid Available**: **433.96 NOK**

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc.
- This batch settlements (4 bets):
  - Harry Kane Anytime @1.95 stake 15 → Win, P/L **+14.25** NOK (payout 29.25)
  - England to Win @1.67 stake 25 → Win, P/L **+16.75** NOK (payout 41.75)
  - Under 7.5 Runs Dodgers vs Rays @1.69 stake 15 → Loss, P/L **-15.00** NOK
  - Detroit Tigers -1.5 @2.36 stake 10 → Loss, P/L **-10.00** NOK
- Net this batch: +14.25 +16.75 -15 -10 = **+6.00** NOK
- Previous Equity 427.96 +6.00 = new Equity **433.96 NOK**. Pending reduced from 65 to **0 NOK**.
- Liquid = Equity - Pending = **433.96 NOK**.
- Cross-check against Norsk Tipping: No discrepancy >5-10 NOK. Full bet_log.csv updated with settlement notes and proper quoting.
- **Mandatory Post-Settlement Deep Dives** added to round_20260617_current_odds_01.md (and referenced for Tigers) using exact template before this reply. nt-bankroll-tracker + nt-bet-log-manager + nt-learning-reviewer protocol executed.
- Git push + raw re-validation completed before any user reply. Playbook followed by the letter 100%.

**All pending bets settled. Bankroll fully reconciled. nt-learning-reviewer flagged variance on MLB unders and run lines for future filter review (monitor after more data).**

*nt-bankroll-tracker + nt-bet-log-manager + nt-learning-reviewer skills complete. All updates pushed and validated.*