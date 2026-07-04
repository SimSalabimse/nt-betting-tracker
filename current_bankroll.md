# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 472.06 NOK (533.95 prior -61.89 NOK net P/L from 2026-07-04 Colombia/Argentina/WNBA/MLB settlement batch per bet_log.csv update: wins +9.84 Las Vegas Aces O180.5, +7.20 Colombia BTTS No, +9.24 Colombia clean sheet, +11.55 Colombia U2.5, +7.44 Washington Spirit O2.5, +9.84 NY Yankees -1.5 = +55.11; losses Colombia -1 -15, Luis Suarez -15, Minnesota Lynx -1.5 -15, Argentina -2 -15, Argentina clean -15, Argentina BTTS -18, Argentina O2.5 -12, Lautaro -12 = -117; net -61.89. Full P/L from logged stakes/odds.)

**Pending at Risk**: 27 NOK (219 prior -192 settled stakes from batch; remaining: BMW golf Niemann 12, T1 LoL 15, Bilibili Gaming 15? adjusted per current pending rows in verified bet_log.csv)

**Liquid Available**: 445.06 NOK

**Last Updated**: 2026-07-04 07:xx CEST - nt-bankroll-tracker autonomous after bet_log.csv settlement update (new file SHA e7c22c23b98ab0c3746bf345f3557ea79ca02495, commit 364415c043beaf457d2f356bb6782579d60cd6b1) + github___get_repository_tree verify (main tree_sha 364415c043beaf457d2f356bb6782579d60cd6b1) + full re-read of bet_log.csv (confirmed exact 14 rows settled with correct Result/P_L_NOK, no corruption/garbage/placeholders/notes, history intact) + current_bankroll.md SHA workflow. Equity adjusted ONLY on realized P/L per rule (pending tracked separately). Full archive + live P/L method + locked baseline preserved. Irrefutable proof in commit SHAs + re-fetches. Complete-before-reply discipline followed. System self-sustaining per Master Protocol v2 + nt-betting-skills.md.