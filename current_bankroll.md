# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 487.93 NOK (locked baseline + full archive+live P/L method; post recent settlements net adjustments incorporated. Equity adjusted ONLY on settlements per user rule.)

**Pending at Risk**: 98 NOK (prior 44 + new 54 from 2026-07-05 soccer analysis append: IFK-AIK O2.5 15 + Odd-Haugesund Haugesund DNB 12 + Elfsborg-Hammarby O2.5 15 + Kalmar-Orgryte O2.5 12. Faze/Seoul/Sangmu pending cleared/settled in prior batch where applicable.)

**Liquid Available**: 389.93 NOK

**Last Updated**: 2026-07-05 14:00 CEST - nt-bankroll-tracker autonomous update after nt-bet-log-manager append of 4 pending bets from current_odds_02.txt soccer section. bet_log.csv SHA 6f83bb8b40b4f573ed77e20c3ffdba4b237e553e verified exact (4 new pending rows at EOF, no notes, historical preserved, full content). Tree + re-fetch + commit proof. Full SHA workflow followed. Per robust_betting_protocol_v2.md + nt-betting-skills.md + nt-bankroll-tracker + Successful Push Workflow + Full Content Rule. NO AUTO-RESET enforced. User places every bet. Irrefutable proof maintained.