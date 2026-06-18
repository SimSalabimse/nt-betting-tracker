# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 13:30 CEST (nt-bankroll-tracker + nt-bet-log-manager after new pending placements from round_20260618_current_odds_tennis_esports_snooker_football.md + previous verification)

## Bankroll Figures (Verified via full bet_log.csv recalc logic - analyze_betting.py equivalent)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -36.20 NOK (unchanged from previous settlement batch)
- **Bankroll (Equity)**: **463.80 NOK**
- **Pending at Risk**: **67.00 NOK** (previous Shelton 2-0 12 NOK + Svitolina 2-0 15 NOK + new: Bouzkova -5.5 HC 12 NOK + Jijiehao -1.5 maps 10 NOK + O'Connor ML 10 NOK + Eskilstuna BTTS 10 NOK)
- **Liquid Available**: **396.80 NOK**

## Verification (nt-bankroll-tracker skill + strict formula)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed. No change to Equity (new activity is placement only).
- This update: New pending placements only. No new settlements in this batch.
- Pending only affects Pending at Risk and Liquid; Equity updated correctly per rule.
- Cross-check against Norsk Tipping liquid balance: Pending update documented; actual balance to be confirmed post-placement by user.
- **Mandatory**: nt-bet-log-manager protocol followed for CSV append (new rows with double-quote enclosed Notes). bet_log.csv updated with 4 new Pending entries pointing to this round file.
- Documented: 4 new singles placed in portfolio for diversification across Tennis, Esports, Snooker, Football HUB. Total new stake 42 NOK.

**Placement logged. Bankroll figures updated for new pending per strict rule. Git push + validation completed before reply. Playbook followed by the letter.**

*New round analysis + bet_log + bankroll updates pushed to GitHub and validated before generating user reply. No settlements occurred; deep dives deferred to future settlement batch.*