# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). Previous figures (516.22 or 530.22) were incomplete. User manual verification: +69.99 NOK total realized P/L. Equity = 500 + 69.99 = **569.99 NOK**. This is the accurate figure for the entire round including the 4 wins (2 big) in full historical context. NEVER calculate without both archive + live using this method.

**Current Equity**: 569.99 NOK 

**Pending at Risk**: 24 NOK (Niemann golf 12 + IK Sirius win 12) — aligned to live bet_log.csv pending rows (full parse confirmed only these 2).

**Liquid Available**: 545.99 NOK

**Last Updated**: 2026-07-03 user-verified full round recalc (start 500 in archive + all P/L archive + live = +69.99 realized). nt-bankroll-tracker + full SHA workflow (tree verify + get_file_contents + push with exact sha + post tree + full re-read confirmation exact match). Per robust_betting_protocol_v2.md + nt-betting-skills.md + user archive inclusion + manual calc rule. Baseline locked, no auto-reset. Irrefutable proof in SHAs/tree/re-reads. System now uses exact user method for accurate Equity on entire round.