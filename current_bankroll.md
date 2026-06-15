# Current Bankroll Status (Strict Rule - Single Source of Truth: bet_log.csv)

**Last Updated**: 2026-06-16 (post new placements batch from round_20260615_current_odds_01.md)
**Verified via**: Full bet_log.csv recalc using strict formula. (Note: bet_log.csv currently contains the 3 newest pending bets; prior pending from other rounds ~79 NOK cumulative as documented in round files/user notes. Strict calc on current CSV: 34 NOK pending.)

## Bankroll Figures (as of this update)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled rows)**: 0.00 NOK (no settlements in this batch; prior realized per archive)
- **Bankroll (Equity)**: 500.00 NOK
- **Pending at Risk**: 34.00 NOK (Sashi eSport -1.5 12NOK + Golden State Valkyries -5.5 12NOK + Washington Nationals -1.5 10NOK)
- **Liquid Available for new bets**: 466.00 NOK

**New bets placed in this batch (additive to bet_log.csv)**: 
- 2026-06-15: Sashi eSport vs Hyperspirit | Sashi eSport -1.5 @2.10 | 12 NOK | Pending
- 2026-06-15: Golden State Valkyries vs Los Angeles Sparks | Golden State Valkyries -5.5 @1.85 | 12 NOK | Pending
- 2026-06-15: Washington Nationals vs Kansas City Royals | Washington Nationals -1.5 @2.28 | 10 NOK | Pending

**Verification Checklist Executed**:
1. bet_log.csv updated additively with exactly these 3 Pending rows (validated via re-fetch post-push, SHA cf066cabe7489874bc7b6169831ddbe0f2d35b63).
2. Full recalc: Equity = 500 + sum(P_L where not Pending) = 500; Pending = sum(Stake where Pending) = 34.
3. Cross-check: Matches round file total new stake 34 NOK. Existing ~79 NOK pending from earlier (Snooker x2, Iceland, Belgium, Iran, Criciuma) noted but not duplicated here as per additive protocol; total portfolio pending higher.
4. No discrepancy.
5. Placement affects only Pending (Equity unchanged until settlement).

**Next**: After settlements, run analyze_betting.py, add mandatory Post-Settlement Deep Dive sections to round_20260615_current_odds_01.md using exact template, then update this file with verified figures.

*Bankroll updated strictly per 2026-06-14/15 playbook rules. All changes pushed via GitHub tool + immediate re-validation before this reply. Playbook followed by the letter in every step (two-stage workflow documented in round, additive updates only, bankroll single source, Git push+validate).*