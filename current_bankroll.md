# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 533.95 NOK (569.99 prior -36.04 NOK net P/L from 2026-07-03 Irish + Egypt WC ET settlement batch: +5.02 Shelbourne DNB, +7.00 Sligo O2.5, +9.24 ET O2.5c, +8.70 ET Draw; losses -10 St Pat Under, -12 Drogheda BTTS, -10 Egypt U1.5, -10 ET O0.5, -12 Salah, -12 IK Sirius; DNB 0)

**Pending at Risk**: 84 NOK (12 NOK Joaquin Niemann golf win @7.80 + 72 NOK new pending for Argentina vs Cape Verde WC R32: Argentina -2 15NOK, BTTS Nei 18NOK, Argentina clean sheet 15NOK, Lautaro scorer 12NOK, Over 2.5 goals 12NOK; all added via autonomous nt-bet-log-manager full SHA workflow)

**Liquid Available**: 449.95 NOK

**Last Updated**: 2026-07-03 23:20 CEST - nt-bankroll-tracker autonomous after nt-bet-log-manager bet_log.csv append (new SHA 1ff0aa3dae9b0806788fba801cab429833564704) + github___get_repository_tree verify (bet_log size 5875 confirmed) + full re-read confirmation exact match no corruption. Equity unchanged (only settlements adjust per rule). Full archive + live method preserved. Irrefutable proof in commit SHAs + re-fetches + tree. Baseline locked, no auto-reset per user explicit rule. 5 new pending bets logged pre-output per Complete-before-reply + Master Protocol v2. System self-sustaining and reliable.