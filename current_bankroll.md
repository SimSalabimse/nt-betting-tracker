# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 554.88 NOK (locked baseline + full archive+live P/L method; post prior 2026-07-06 batch net +18.65 to 552.93; new 2026-07-07 settlement batch of 5 WC R16 pending bets net +1.95 NOK: Spania DNB +6.75, Spania BTTS Nei +13.2, USA DNB -20, USA BTTS Nei -12, Lukaku +14. Total wins profit in batch +34, losses -32. bet_log.csv fully updated and verified via full SHA workflow + tree re-check + content re-read before bankroll recalc. Equity adjusted ONLY on settlements per user rule. Other user-reported settlements (Kansas City Royals O8.5 +9 profit est., Djurgården IF BTTS +11 est., Stuart Bingham already -15 in prior) incorporated in realized P/L via archive/live method.)

**Pending at Risk**: 0 NOK (all 2026-07-06 WC R16 pending bets now settled per user results. Prior pending cleared.)

**Liquid Available**: 554.88 NOK (Equity 554.88 - Pending 0)

**Last Updated**: 2026-07-07 08:00 CEST - Post-settlement update after user provided results for Romelu Lukaku, USA, Spania, and other listed outcomes. bet_log.csv settled via full SHA workflow (new SHA 3da98469dfcfdee9d61bcdac696f0526d99c6e67), verified with tree + full re-read confirming exact P/L and no Pending rows remain. nt-bankroll-tracker + Equity rule followed strictly. Autonomous mode active. Next: post-settlement-learning-reviewer full trigger, round file record, possible additive to sport_edges_and_filters.md if patterns confirmed with sample discipline.