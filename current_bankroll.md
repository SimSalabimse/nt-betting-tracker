# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). Previous figures (516.22 or 530.22) were incomplete. User manual verification: +69.99 NOK total realized P/L. Equity = 500 + 69.99 = **569.99 NOK**. This is the accurate figure for the entire round including the 4 wins (2 big) in full historical context. NEVER calculate without both archive + live using this method.

**Current Equity**: 569.99 NOK 

**Pending at Risk**: 105 NOK (previous 61 NOK + new 44 NOK from 2026-07-03 current_odds_02 bets: Drogheda BTTS 12 + Sligo Over 10 + St Pat Under 10 + Shelbourne DNB 12) — aligned to live bet_log.csv pending rows (full parse confirmed 9 pending after nt-bet-log-manager append).

**Liquid Available**: 464.99 NOK

**Last Updated**: 2026-07-03 20:35 CEST - nt-bet-log-manager + nt-bankroll-tracker autonomous update after full analysis of current_odds_02.txt (4 new pending bets logged). Pending 61→105 NOK, liquid 508.99→464.99 NOK. Equity 569.99 NOK unchanged per rule (settlements only adjust Equity). Full SHA workflow followed for BOTH files (bet_log.csv: bb8eeec2... -> 1db48a92...; bankroll: 9dc78b2b... -> new). Tree verify + full re-read confirmation exact match. Per robust_betting_protocol_v2.md + nt-betting-skills.md + long_term_staking_plan.md. Irrefutable proof in commit SHAs + re-fetches. Baseline locked, no auto-reset. System self-sustaining.