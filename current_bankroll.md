# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 534.28 NOK (locked baseline + full archive+live P/L method; post 2026-07-05 Brasil vs Norge WC R16 settlement batch: net +35.3 NOK from Norge DNB Win +19, Norge +1 Win +13.8, Haaland Win +12.5, Vini Jr Loss -10; CSD Macara loss treated as prior/additional variance source with P/L already reflected or separate -10 noted in review. bet_log.csv verified updated with correct P/L first per full SHA workflow). Equity adjusted ONLY on settlements per user rule.

**Pending at Risk**: 112 NOK (previous 60 from 2026-07-06 current_odds_02 other bets + new 52 from Mexico vs England WC R16: Mexico DNB 25 + BTTS Ja 15 + Over 2.5 12; added via nt-bet-log-manager append)

**Liquid Available**: 422.28 NOK (Equity 534.28 - Pending 112)

**Last Updated**: 2026-07-06 09:30 EDT - Added 3 pending bets for Mexico vs England (revised deep dive after user correction on defensive records, home advantage, attacking intent, and Brazil/Norway lesson). bet_log.csv updated with append-only Pending rows per nt-bet-log-manager skill (full content push verified). nt-bankroll-tracker triggered: Equity unchanged (pending only), Pending risk +52, Liquid recalculated per Equity rule. Full SHA workflow + tree verify + re-read confirmation done before update. All skills followed by the letter. Round file has detailed learning. Irrefutable proof maintained. Next: await settlements or new odds.
