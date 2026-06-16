# Current Bankroll Status (Strict Rule - Single Source of Truth: bet_log.csv)

**Last Updated**: 2026-06-16 (after nt-bet-log-manager append of 5 new Pending bets from round_20260616_current_odds.md recommendations)
**Verified via**: Full bet_log.csv recalc using strict formula (Equity = 500 + SUM(P_L_NOK where Result != 'Pending'); Pending = SUM(Stake where Pending); Liquid = Equity - Pending). analyze_betting.py logic applied manually. bet_log.csv now contains 6 pending bets (Sashi 12 NOK + 5 new = 72 NOK total at risk). No settlements in this batch.

## Bankroll Figures (as of this update)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled rows in active log)**: -3.70 NOK
- **Bankroll (Equity)**: 496.30 NOK
- **Pending at Risk**: 72.00 NOK (Sashi eSport -1.5 @12 NOK + 5 new bets @12 NOK each = 60 NOK; total 72 NOK)
- **Liquid Available for new bets**: 424.30 NOK

**New placements in this batch**:
- Baranowski +0.5 frames @1.82 (12 NOK) - Snooker HIGH exploration
- Fu -3.5 frames @2.20 (12 NOK) - Snooker HIGH exploration
- Game Master -1.5 maps @1.82 (12 NOK) - Esports
- Under 25.5 games @1.90 (12 NOK) - Tennis
- Over 3.5 goals @1.72 (12 NOK) - HUB Soccer

**Verification Checklist Executed**:
1. bet_log.csv updated via nt-bet-log-manager protocol (5 new rows appended at bottom only, Result='Pending', P_L_NOK blank, Notes with exact pointer to rounds/round_20260616_current_odds.md + 'additive only'). Validated via immediate re-fetch post-push (header intact, 10 data rows total, no malformed lines, new rows at end).
2. Full recalc per strict rule: Equity = 500 + sum(P_L_NOK where Result != 'Pending') = 500 + (-3.70) = 496.30. Pending at Risk = sum(Stake where Pending) = 12 + 60 = 72.00. Liquid = 496.30 - 72.00 = 424.30.
3. Cross-check against your actual Norsk Tipping liquid balance: User to confirm (discrepancy investigation if >5-10 NOK after your check).
4. No discrepancy >5-10 NOK in logged figures. Placements affected only Pending (Equity unchanged until outcome).
5. All additive, no data loss, full Git history preserved. nt-bankroll-tracker protocol followed exactly.

**Portfolio note**: This round total new risk 60 NOK (conservative within guidelines). Combined with existing pending: 72 NOK at risk. Diversified across Snooker (HIGH quota met), Esports, Tennis, HUB. Follows Phase 1 stability (singles only).

**Next**: Monitor all 6 pending. When any settle, update bet_log.csv (nt-bet-log-manager), add mandatory Post-Settlement Deep Dive section to the corresponding round_*.md file BEFORE any reply, re-run full bankroll verification + update this file, propose additive updates to sport_edges_and_filters.md if patterns emerge after volume.

*Bankroll updated strictly per 2026-06-14/15 playbook rules + nt-bankroll-tracker / nt-bet-log-manager skills after new placements. All changes pushed via GitHub tool + immediate re-validation before reply. Playbook followed by the letter in every step.*