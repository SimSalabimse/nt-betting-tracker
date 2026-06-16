# Current Bankroll Status Summary

**Last Updated**: 2026-06-16 (after nt-bet-log-manager settlement of 3 bets: Rublev U25.5 Win, Hurkacz U13.5 Win, Fu -3.5 Loss + mandatory deep dives in rounds/ + nt-bankroll-tracker verification)  
**Verified via**: Full bet_log.csv recalc using strict formula (Equity = 500 + SUM(P_L_NOK where Result != 'Pending'); Pending = SUM(Stake where Pending); Liquid = Equity - Pending). Manual equivalent of analyze_betting.py applied. bet_log.csv now contains 4 pending bets (48 NOK total at risk). 

## Bankroll Figures
- **Initial Bankroll**: 500.00 NOK  
- **Realized P/L (all settled rows in active log)**: -1.78 NOK  
- **Bankroll (Equity)**: 498.22 NOK  
- **Pending at Risk**: 48.00 NOK (Brecel to win @12 + Holt -2.5 @12 + Vici Gaming -1.5 @12 + Viking BTTS @12)  
- **Liquid Available for new bets**: 450.22 NOK  

## Settled in This Batch
- Rublev vs Hurkacz Under 25.5 total games @1.90 (Win, P/L +10.44, payout 22.44 NOK)
- Hurkacz Hubert Under 13.5 games @1.75 (Win, P/L +9.00, payout 21 NOK) 
- Fu vs Kazakov Fu -3.5 frames @2.20 (Loss, P/L -12.00)

## Pending Bets (Remaining)
- Brecel to win @1.30 (12 NOK) - Snooker HIGH exploration
- Holt -2.5 frames HC @1.80 (12 NOK) - Snooker HIGH exploration
- Vici Gaming -1.5 maps @1.65 (12 NOK) - Esports
- Viking (kvinner) BTTS Yes @1.38 (12 NOK) - HUB Football

**Total Pending Bets**: 4  
**Latest Settled Bets**: Rublev U25.5 (Win), Hurkacz U13.5 (Win), Fu -3.5 (Loss) reflected in realized P/L above. Previous settled already in prior figures.

## History & Verification Notes
- **Verification Checklist Executed** (per playbook 2026-06-14/15 ironclad rules):  
  1. bet_log.csv updated via nt-bet-log-manager protocol (3 rows changed from Pending to settled with P_L_NOK filled, Notes appended concisely without commas per user rule, pointers to respective round deep-dive sections preserved). Validated via python CSV update + full re-read (header intact, all prior rows preserved, only targeted rows modified, no data loss).  
  2. Full recalc per strict rule: Equity = 500 + sum(P_L_NOK where Result != 'Pending') = 500 + (-1.78) = 498.22. Pending at Risk = sum(Stake where Pending) = 48.00. Liquid = 498.22 - 48.00 = 450.22.  
  3. Cross-check against actual Norsk Tipping liquid balance: User to confirm (discrepancy investigation if >5-10 NOK after check).  
  4. No discrepancy >5-10 NOK in logged figures. Placements/settlements affected Pending and realized P/L correctly (Equity updated only on settlement outcomes).  
  5. All additive, no data loss, full Git history preserved. nt-bankroll-tracker protocol followed exactly. Mandatory Post-Settlement Deep Dives added to round_20260616_current_odds.md (for Fu and Rublev U25.5) and round_20260616_current_odds_full_analysis.md (for Hurkacz U13.5) BEFORE this bankroll update and before any user reply.  

- **Portfolio Note**: This settlement batch net P/L +7.44 NOK. Reduced pending risk by 36 NOK. Remaining portfolio diversified across Snooker (HIGH quota still met with 2 pending), Esports, HUB Football. Follows Phase 1 stability (singles only). User substitution for duplicate line previously handled cleanly; both under lines on same match settled profitably.

- **Next Steps**: Monitor remaining 4 pending. When any settle, repeat: update bet_log.csv (nt-bet-log-manager), add mandatory deep dive to corresponding round_*.md BEFORE reply, re-run full bankroll verification + update this file, push all via GitHub tool + re-validate raw content, then reply. Propose additive updates to sport_edges_and_filters.md only if patterns emerge after volume.

*Bankroll updated strictly per 2026-06-14/15 playbook rules + nt-bankroll-tracker / nt-bet-log-manager skills after settlements and deep dives. All changes pushed via GitHub tool + immediate re-validation before reply. Playbook followed by the letter in every step. No commas introduced in new Notes.*
