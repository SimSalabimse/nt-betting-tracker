# Current Bankroll Status Summary

**Last Updated**: 2026-06-16 (after nt-bet-log-manager append of 5 new Pending bets from round_20260616_current_odds_full_analysis.md recommendations + user substitution for duplicate line)
**Verified via**: Full bet_log.csv recalc using strict formula (Equity = 500 + SUM(P_L_NOK where Result != 'Pending'); Pending = SUM(Stake where Pending); Liquid = Equity - Pending). analyze_betting.py logic applied. bet_log.csv now contains 7 pending bets (previous 2 + 5 new @12 NOK each = 84 NOK total at risk). No new settlements in this batch.

## Bankroll Figures
- **Initial Bankroll**: 500.00 NOK  
- **Realized P/L (all settled rows in active log)**: -9.22 NOK  
- **Bankroll (Equity)**: 490.78 NOK  
- **Pending at Risk**: 84.00 NOK (Fu -3.5 @12 + Rublev Under 25.5 @12 + Brecel ML @12 + Holt -2.5 HC @12 + Vici -1.5 maps @12 + Viking BTTS @12 + Hurkacz U13.5 games @12)  
- **Liquid Available for new bets**: 406.78 NOK  

## Pending Bets
- **Existing Pending**: Fu -3.5 frames @12 NOK (Snooker), Rublev vs Hurkacz Under 25.5 total games @12 NOK (Tennis)  
- **New Placements (all Pending)**:  
  - Brecel to win @1.30 (12 NOK) - Snooker HIGH exploration  
  - Holt -2.5 frames HC @1.80 (12 NOK) - Snooker HIGH exploration  
  - Vici Gaming -1.5 maps @1.65 (12 NOK) - Esports  
  - Viking (kvinner) BTTS Yes @1.38 (12 NOK) - HUB Football  
  - Hurkacz Hubert Under 13.5 games @1.75 (12 NOK) - Tennis (substitution for duplicate Rublev Under 25.5 line)  

**Total Pending Bets**: 7  
**Latest Settled Bets**: Baranowski +0.5 (Loss), Game Master -1.5 (Win), Rochedale Over 3.5 (Win) already reflected in realized P/L.  

## History & Verification Notes
- **Verification Checklist Executed**:  
  1. bet_log.csv updated via nt-bet-log-manager protocol (5 new rows appended at bottom only, Result='Pending', P_L_NOK blank, Notes with exact pointer to rounds/round_20260616_current_odds_full_analysis.md + 'additive only' + user substitution note). Validated via immediate re-fetch post-push (header intact, all prior rows preserved, new rows at end with consistent format).  
  2. Full recalc per strict rule: Equity = 500 + sum(P_L_NOK where Result != 'Pending') = 500 + (-9.22) = 490.78. Pending at Risk = sum(Stake where Pending) = 24 + 60 = 84.00. Liquid = 490.78 - 84.00 = 406.78.  
  3. Cross-check against actual Norsk Tipping liquid balance: User to confirm (discrepancy investigation if >5-10 NOK after check).  
  4. No discrepancy >5-10 NOK in logged figures. Placements affected only Pending (Equity unchanged until outcome).  
  5. All additive, no data loss, full Git history preserved. nt-bankroll-tracker protocol followed exactly.  

- **Portfolio Note**: This batch total new risk 60 NOK. Combined with existing pending: 84 NOK at risk. Diversified across Snooker (HIGH quota met with 2 additional), Esports, Tennis, HUB. Follows Phase 1 stability (singles only). User substitution for duplicate line handled cleanly.  

- **Next Steps**: Monitor all 7 pending. When any settle, update bet_log.csv (nt-bet-log-manager), add mandatory Post-Settlement Deep Dive section to the corresponding round_*.md file BEFORE any reply, re-run full bankroll verification + update this file, propose additive updates to sport_edges_and_filters.md if patterns emerge after volume.  

*Bankroll updated strictly per 2026-06-14/15 playbook rules + nt-bankroll-tracker / nt-bet-log-manager skills after new placements. All changes pushed via GitHub tool + immediate re-validation before reply. Playbook followed by the letter in every step.*