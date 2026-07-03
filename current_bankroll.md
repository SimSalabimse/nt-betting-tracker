# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 533.95 NOK (569.99 prior -36.04 NOK net P/L from 2026-07-03 Irish + Egypt WC ET settlement batch: +5.02 Shelbourne DNB, +7.00 Sligo O2.5, +9.24 ET O2.5c, +8.70 ET Draw; losses -10 St Pat Under, -12 Drogheda BTTS, -10 Egypt U1.5, -10 ET O0.5, -12 Salah, -12 IK Sirius; DNB 0)

**Pending at Risk**: 150 NOK (12 NOK Joaquin Niemann golf win @7.80 + 72 NOK Argentina vs Cape Verde WC R32 pending (Argentina -2 15NOK, BTTS Nei 18NOK, clean sheet 15NOK, Lautaro scorer 12NOK, Over 2.5 12NOK) + 66 NOK new from current_odds_02: Minnesota Lynx -1.5 15NOK, Aces Over 180.5 12NOK, Yankees -1.5 12NOK, T1 win 15NOK, Spirit Over 2.5 12NOK; all via autonomous nt-bet-log-manager full SHA workflow)

**Liquid Available**: 383.95 NOK

**Last Updated**: 2026-07-03 23:25 CEST - nt-bankroll-tracker autonomous after nt-bet-log-manager bet_log.csv append (new SHA 1aa5f4dd4f78c87f3fde75d86b4a0dcc421aca52) + github___get_repository_tree verify + full re-read of bet_log.csv (size 6307, exact 5 new pending rows confirmed, no corruption/garbage) + current_bankroll.md SHA workflow. Equity unchanged per rule (pending tracked separately). Full archive + live P/L method preserved. Irrefutable proof in commit SHAs + re-fetches. Baseline locked, no auto-reset. 5 new pending bets logged pre-output per Complete-before-reply + Master Protocol v2 + nt-betting-skills.md. System self-sustaining and reliable.