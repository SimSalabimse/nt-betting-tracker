# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). Previous figures (516.22 or 530.22) were incomplete. User manual verification: +69.99 NOK total realized P/L. Equity = 500 + 69.99 = **569.99 NOK**. This is the accurate figure for the entire round including the 4 wins (2 big) in full historical context. NEVER calculate without both archive + live using this method.

**Current Equity**: 569.99 NOK 

**Pending at Risk**: 142 NOK (previous 105 NOK + new 37 NOK from 2026-07-03 ET bets on Australia vs Egypt current_odds_02.txt: Uavgjort ET 15 + Over 0.5 ET 10 + Over 2.5 Corners ET 12) — aligned to live bet_log.csv pending rows (full parse confirmed 12 pending after nt-bet-log-manager append of 3 ET bets). Full SHA workflow + re-verify completed.

**Liquid Available**: 427.99 NOK

**Last Updated**: 2026-07-03 22:15 CEST - nt-bet-log-manager + nt-bankroll-tracker autonomous update after full deep research analysis of attached current_odds_02.txt (ET markets). Added 3 quality ET bets (total new risk 37 NOK, tiered 10-15 NOK, stupid loss filter applied, DNB/ value focus). Pending 105→142 NOK, liquid 464.99→427.99 NOK. Equity 569.99 NOK unchanged per rule (settlements only). bet_log.csv SHA e1e373be... (verified append exact 3 rows). Tree + full re-read confirmation exact match, no corruption. Per robust_betting_protocol_v2.md + nt-betting-skills.md + long_term_staking_plan.md exactly. Irrefutable proof in commit SHAs + re-fetches. Baseline locked, no auto-reset. System self-sustaining and reliable.