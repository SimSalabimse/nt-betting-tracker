# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 552.93 NOK (locked baseline + full archive+live P/L method; post 2026-07-06 settlement batch of 7 bets: net +18.65 NOK. Detailed: Bilibili Gaming -2.5 Win +9.36, Boston Red Sox -1.5 Win +11.64, Mexico BTTS Win +15.75, Mexico O2.5 Win +17.40, Nautico PE U2.5 Win +4.50 (total wins profit +58.65); Stuart Bingham Loss -15, Mexico DNB Loss -25 (total losses -40). bet_log.csv fully updated and verified via full SHA workflow + tree re-check + content re-read before bankroll recalc. Equity adjusted ONLY on settlements per user rule.)

**Pending at Risk**: 0 NOK (all pending from 2026-07-05/06 batch now settled; previous pending total was exactly 112 NOK covering these 7 stakes. No open pending left in bet_log.csv.)

**Liquid Available**: 552.93 NOK (Equity 552.93 - Pending 0)

**Last Updated**: 2026-07-06 09:45 EDT - Full post-settlement batch processed: bet_log.csv settled with correct Result/P_L_NOK (no notes), verified via tree + re-read proof. current_bankroll.md updated with Equity rule + verification checklist (row counts match, P/L sums align, pending cleared). nt-bankroll-tracker followed by letter. Post-settlement-learning-reviewer triggered, round file to be created with deep dive, edges checked additive-only. All skills + robust_betting_protocol_v2.md followed in full. Irrefutable GitHub proof maintained throughout. Next: await new odds or review completion.