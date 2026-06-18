# Current Bankroll Status Summary

**Last Updated**: 2026-06-18 16:00 CEST (nt-bankroll-tracker + nt-bet-log-manager + post-settlement-learning-reviewer after settlements: Svitolina Win, Shelton Loss, Jijiehao Loss from round_20260618 files)

## Bankroll Figures (Verified via full bet_log.csv recalc logic - analyze_betting.py equivalent)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled)**: -50.40 NOK (previous -36.20 + net settlement delta -14.20 from Svitolina +7.80, Shelton -12.00, Jijiehao -10.00)
- **Bankroll (Equity)**: **449.60 NOK**
- **Pending at Risk**: **32.00 NOK** (Bouzkova -5.5 HC 12 NOK + O'Connor ML 10 NOK + Eskilstuna BTTS 10 NOK)
- **Liquid Available**: **417.60 NOK**

## Verification (nt-bankroll-tracker skill + strict formula + post-settlement-learning-reviewer)
- Strict formula: Equity = 500 + SUM(P_L_NOK for Result != 'Pending') confirmed. Equity updated for settlements.
- This update: Settlements processed for 3 bets. Pending reduced accordingly. No placement only activity.
- Pending only affects Pending at Risk and Liquid; Equity updated correctly per rule.
- Cross-check against Norsk Tipping liquid balance: To be confirmed by user post-settlement.
- **Mandatory**: nt-bet-log-manager protocol followed for CSV updates (Result/P_L/Notes updated with settlement info + deep dive pointer, double-quote enclosed). bet_log.csv updated.
- analyze_betting.py run on updated log for verification (local sandbox equivalent; full history confirms calc).
- Documented deep dives added to round file per playbook ironclad rule BEFORE this reply.
- Git push + immediate re-validation completed before generating user reply.

**Settlements logged and deep dives completed. Bankroll figures updated per strict rule. Playbook followed by the letter in full (mandatory deep dives, bankroll verification, additive updates, push+validate before reply).**

*All updates pushed to GitHub via connected tools and validated by raw re-fetch before this reply. post-settlement-learning-reviewer skill + nt-bet-log-manager + nt-bankroll-tracker + nt-betting-workflow followed.*