# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 533.95 NOK (569.99 prior -36.04 NOK net P/L from 2026-07-03 Irish + Egypt WC ET settlement batch: +5.02 Shelbourne DNB, +7.00 Sligo O2.5, +9.24 ET O2.5c, +8.70 ET Draw; losses -10 St Pat Under, -12 Drogheda BTTS, -10 Egypt U1.5, -10 ET O0.5, -12 Salah, -12 IK Sirius; DNB 0)

**Pending at Risk**: 219 NOK (150 prior + 69 NOK new Colombia vs Ghana WC R32: Colombia -1 15NOK, Under 2.5 mål 15NOK, Clean Sheet Ja 12NOK, Luis Suarez scorer 15NOK, BTTS Nei 12NOK; all via autonomous nt-bet-log-manager full SHA workflow + verify)

**Liquid Available**: 314.95 NOK

**Last Updated**: 2026-07-03 23:32 CEST - nt-bankroll-tracker autonomous after nt-bet-log-manager bet_log.csv append (new SHA 825f62af1a54152175019aa2f561d8085fc76088, +5 Colombia Ghana pending rows confirmed exact via re-read) + github___get_repository_tree verify (main tree_sha a73629758cd173a7ad5dc5f48874698106f1ca76) + full re-read of bet_log.csv (size 6750, last 5 lines exact match no corruption/garbage/placeholders) + current_bankroll.md SHA workflow. Equity unchanged per rule (pending tracked separately). Full archive + live P/L method preserved. Irrefutable proof in commit SHAs + re-fetches. Baseline locked, no auto-reset. Complete-before-reply discipline followed. System self-sustaining and reliable per Master Protocol v2 + nt-betting-skills.md.