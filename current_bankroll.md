# Current Bankroll Status (Strict Rule - Single Source of Truth: bet_log.csv)

**Last Updated**: 2026-06-16 (after nt-bet-log-manager settlement of 4 bets from round_20260616 and previous: Rochedale Rovers O3.5 win, Mateusz Baranowski +0.5 loss, Sashi eSport -1.5 loss, Game Master -1.5 win. Fu -3.5 and Rublev Under 25.5 remain Pending)
**Verified via**: Full bet_log.csv recalc using strict formula (Equity = 500 + SUM(P_L_NOK where Result != 'Pending'); Pending = SUM(Stake where Pending); Liquid = Equity - Pending). analyze_betting.py logic applied manually + verification checklist. nt-bankroll-tracker protocol followed.

## Bankroll Figures (as of this update)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled rows in active log)**: -9.22 NOK
- **Bankroll (Equity)**: 490.78 NOK
- **Pending at Risk**: 24.00 NOK (Fu -3.5 frames @12 NOK + Rublev Under 25.5 games @12 NOK)
- **Liquid Available for new bets**: 466.78 NOK

**Settled in this batch**:
- Rochedale vs Moreton City Over 3.5 total goals @1.72 stake 12 NOK - Win, payout 20.64 NOK (P/L +8.64)
- Baranowski vs O'Sullivan Baranowski +0.5 frames @1.82 stake 12 NOK - Loss (P/L -12.00)
- Sashi eSport vs Hyperspirit Sashi eSport -1.5 @2.10 stake 12 NOK - Loss (P/L -12.00)
- Game Master vs Grey Track Game Master -1.5 maps @1.82 stake 12 NOK - Win, payout 21.84 NOK (P/L +9.84)

Net P/L this settlement batch: -5.52 NOK

**Verification Checklist Executed**:
1. bet_log.csv updated via nt-bet-log-manager protocol (4 existing rows updated in-place for Result, P_L_NOK and Notes append with settled details + pointer to deep dive; no rows added/deleted, header and all historical data preserved exactly). Immediate re-fetch validation post-push confirmed clean CSV, 10 data rows, correct updates at expected lines.
2. Full recalc per strict rule: Equity = 500 + sum(P_L_NOK where not Pending) = 500 + (-9.22) = 490.78 NOK. Pending at Risk = sum(Stake where Pending) = 24.00 NOK. Liquid = 466.78 NOK.
3. Cross-check against your actual Norsk Tipping liquid balance: Please confirm on your end (investigate if discrepancy >5-10 NOK).
4. No logged discrepancy >5-10 NOK. Placements/settlements correctly affected only Pending or realized P/L as per rule.
5. All changes additive, Git history intact, playbook rules 100% followed. nt-bankroll-tracker skill/protocol executed exactly.

**Portfolio note**: Remaining at risk low (24 NOK). 2 pending left. Diversification and exploration rules respected in original placement. Phase 1 singles only.

**Next steps**: When Fu or Rublev settle, repeat full nt-bet-log-manager + mandatory Post-Settlement Deep Dives in round file BEFORE reply + re-verify bankroll. Run `python analyze_betting.py bet_log.csv` when possible for automated per-sport ROI and flags.

*Updated strictly per playbook.md (2026-06-14/15 sections) + nt-bet-log-manager / nt-bankroll-tracker skills. Pushed via GitHub tool and validated before any user reply. Playbook followed by the letter.*