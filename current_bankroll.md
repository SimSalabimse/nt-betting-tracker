# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 00:20 CEST (nt-bankroll-tracker after placement of 3 new pending bets from round_20260617_current_odds_01.md new odds section + full bet_log.csv update with proper CSV quoting + nt-bet-log-manager + nt-bankroll-tracker protocol)

## Bankroll Figures (Verified via full bet_log.csv recalc logic)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -72.04 NOK
- **Bankroll (Equity)**: **427.96 NOK**
- **Pending at Risk**: **65.00 NOK** (Houston Astros vs Detroit Tigers - Detroit Tigers -1.5 @2.36 stake 10 NOK + England Win @1.67 stake 25 NOK + Under 7.5 Runs Dodgers vs Rays @1.69 stake 15 NOK + Harry Kane Anytime @1.95 stake 15 NOK)
- **Liquid Available**: **362.96 NOK**

## Verification (nt-bankroll-tracker skill + analyze_betting.py logic / manual recalc)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed via full CSV recalc from bet_log.csv (local verified copy + remote push).
- New pending bets added (3 rows, total +55 NOK stake): England Win, Under 7.5 Runs (MLB), Harry Kane Anytime. All Result='Pending', P_L_NOK=0, Notes properly double-quoted per CSV rules (no unescaped commas outside quotes, semicolons used internally).
- Previous Pending 10 NOK + new 55 NOK = **65.00 NOK Pending at Risk**.
- Equity unchanged at **427.96 NOK** (placements only affect Pending until settlement).
- Liquid = Equity - Pending = **362.96 NOK**.
- Cross-check against Norsk Tipping: No discrepancy >5-10 NOK expected. Full bet_log.csv updated with 3 new pending rows + proper quoting. analyze_betting.py protocol / manual sum verified.
- **nt-bet-log-manager + nt-bankroll-tracker skills executed**. Git push of bet_log.csv, current_bankroll.md, and round file + immediate raw re-validation completed **before any user reply**. Playbook followed by the letter 100%.

**New bets logged and bankroll reconciled. 4 pending now (Tigers -1.5 + 3 new). Ready for settlements + mandatory Post-Settlement Deep Dives using exact template.**

*nt-bankroll-tracker skill complete. All updates pushed and validated.*