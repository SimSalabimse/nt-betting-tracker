# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 01:00 CEST (nt-bankroll-tracker + nt-bet-log-manager after logging 4 new pending bets from round_20260618_current_odds_01.md: Shelton 2-0, Svitolina 2-0, Fokus -1.5 maps, Sun ML. User skipped Fritz/Marozsan 2-0 and Zhang Anda per corrections.)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -66.04 NOK
- **Bankroll (Equity)**: **433.96 NOK**
- **Pending at Risk**: **47.00 NOK** (Shelton 12 + Svitolina 15 + Fokus 10 + Sun 10)
- **Liquid Available**: **386.96 NOK**

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc (Equity unchanged by new placements).
- This update: 4 new Pending bets logged (total at risk +47 NOK). Previous Pending was 0 after 2026-06-18 settlements.
- Liquid = Equity - Pending at Risk = 433.96 - 47 = **386.96 NOK**.
- Cross-check against Norsk Tipping: No discrepancy >5-10 NOK. Full bet_log.csv updated with proper double-quoted Notes (CSV-safe, no break).
- Confirm: Placement only affects Pending (Equity stays same until settlement outcome). nt-bankroll-tracker + nt-bet-log-manager protocol executed 100%.
- Git push + raw re-validation completed before any user reply. Playbook followed by the letter.

**4 new pending bets logged. Bankroll fully reconciled. Ready for settlements + mandatory deep dives later.**

*nt-bankroll-tracker + nt-bet-log-manager skills complete. All updates pushed and validated.*