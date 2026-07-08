# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 579.83 NOK (locked baseline + full archive+live P/L method; post prior 2026-07-07 settlement batch net +19.35 to 574.23; then this 2026-07-08 settlement batch net +5.60 from 5 pending bets to 579.83; all pending cleared). bet_log.csv fully updated and verified via full SHA workflow + tree re-check + content re-read before bankroll recalc. Equity adjusted ONLY on settlements per user rule.

**Pending at Risk**: 27 NOK (new Phase 1B autonomous bets from 2026-07-08 current_odds_02.txt analysis: 15 NOK on TdF Pogacar Nei + 12 NOK on Brazil Over 2.5; total pending risk added after verification. bet_log.csv update verified with tree + full content re-read confirming exact pending rows with short notes in Match field, no garbage/placeholders/short versions.)

**Liquid Available**: 552.83 NOK (Equity 579.83 - Pending 27)

**Last Updated**: 2026-07-08 23:10 CEST - Post autonomous bet log update for current_odds_02.txt full analysis (Stage 1 rough EV scan + Stage 2 deep research with min 8-12 sources per shortlist, EV calc via betting-value-calculator rules, Phase 1B staking 12-20 NOK, max 1 double policy, diversification 2 sports, stupid loss filter applied, DNB preference where relevant). All GitHub pushes followed Successful Push Workflow with pre/post tree + content verification. Irrefutable proof recorded. User places every recommended bet. Next round will trigger post-settlement if applicable.