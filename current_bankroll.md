# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). Previous figures (516.22 or 530.22) were incomplete. User manual verification: +69.99 NOK total realized P/L. Equity = 500 + 69.99 = **569.99 NOK**. This is the accurate figure for the entire round including the 4 wins (2 big) in full historical context. NEVER calculate without both archive + live using this method.

**Current Equity**: 569.99 NOK 

**Pending at Risk**: 61 NOK (Niemann golf 12 + IK Sirius win 12 + Egypt DNB 15 + Salah anytime 12 + Under 1.5 Goals 10) — aligned to live bet_log.csv pending rows (full parse confirmed 5 pending after nt-bet-log-manager append of Australia vs Egypt bets).

**Liquid Available**: 508.99 NOK

**Last Updated**: 2026-07-03 20:27 CEST - nt-bet-log-manager + nt-bankroll-tracker autonomous update: appended exactly 3 new pending bets for Australia vs Egypt (FIFA WC 2026 R32) per round file + user correction (Egypt DNB 15NOK, Salah anytime 12NOK, Under 1.5 Goals 10NOK min stake). Pending 24->61 NOK, liquid adjusted 545.99->508.99 NOK. Equity unchanged per rule (settlements only adjust Equity). Full SHA workflow followed for BOTH files (bet_log.csv: 65351269... -> bb8eeec2...; bankroll: ae9333e7... -> new). Tree verify + full re-read confirmation exact match + 3 rows at bottom present. Per robust_betting_protocol_v2.md + nt-betting-skills.md + long_term_staking_plan.md. Irrefutable proof in commit SHAs + re-fetches. Baseline locked, no auto-reset. System self-sustaining.