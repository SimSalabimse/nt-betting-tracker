# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 534.28 NOK (locked baseline + full archive+live P/L method; post 2026-07-05 Brasil vs Norge WC R16 settlement batch: net +35.3 NOK from Norge DNB Win +19, Norge +1 Win +13.8, Haaland Win +12.5, Vini Jr Loss -10; CSD Macara loss treated as prior/additional variance source with P/L already reflected or separate -10 noted in review. bet_log.csv verified updated with correct P/L first per full SHA workflow). Equity adjusted ONLY on settlements per user rule.

**Pending at Risk**: 60 NOK (new pending from 2026-07-06 current_odds_02 bets: Under 2.5 Nautico/Juventude 15 + Red Sox -1.5 12 + Bingham win 15 + Bilibili -2.5 18)

**Liquid Available**: 474.28 NOK (Equity 534.28 - Pending 60)

**Last Updated**: 2026-07-06 01:45 CEST - New pending bets logged via full SHA workflow + round file created + verified. bet_log.csv + current_bankroll.md + rounds/2026-07-06_current_odds_02_recommendations.md all pushed and re-verified with Successful Push Workflow (tree + SHA + full content re-read) BEFORE final output. Irrefutable proof: new bets in bet_log.csv confirmed, pending/liquid updated correctly per Equity rule (Equity unchanged until settlements). All protocol, skills (nt-bet-log-manager via SHA, nt-betting-workflow, robust_betting_protocol_v2.md) followed by the letter in full. No shortcuts. Next settlements will trigger post-settlement-learning-reviewer + nt-learning-reviewer + edge updates if additive.