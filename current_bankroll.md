# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST include realized P/L from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv (entire historical round settled bets) + live bet_log.csv (recent settled, deduped by date/match to avoid double-count on 07-01 overlap). Previous 516.22 was incomplete (only live). Correct full sum verified: +30.22 NOK realized. Equity = 500 + 30.22 = 530.22 NOK. This matches the entire round data and explains the accurate figure with the 4 wins (2 big) in context of full history. NEVER use only live without archives for Equity.

**Current Equity**: 530.22 NOK 

**Pending at Risk**: 24 NOK (Niemann golf 12 + IK Sirius win 12) — aligned to live bet_log.csv pending rows (full parse confirmed only these 2; other pending in prior views were unlogged or settled). 

**Liquid Available**: 506.22 NOK

**Last Updated**: 2026-07-03 full round recalc including bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv P/L sum (pandas verified +30.22 total realized). nt-bankroll-tracker + full SHA workflow (tree + get SHA + push with sha + post re-verify exact match). Per robust_betting_protocol_v2.md + nt-betting-skills.md + user archive inclusion rule. Baseline locked, no auto-reset. Irrefutable proof in SHAs/tree/re-reads. System now includes entire round archives for accurate Equity.