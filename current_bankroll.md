# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - FULL DATA RULE (User Instruction 2026-07-03)**: Equity calculation MUST use the exact user-verified method: start from 500 in bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + add ALL profits and subtract ALL losses from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv (entire round, deduped for any 07-01 overlap). User manual verification confirmed prior +69.99 NOK total realized P/L leading to 569.99. This remains the accurate figure base. NEVER calculate without both archive + live using this method. No auto-reset.

**Current Equity**: 472.06 NOK (unchanged - pending stakes reserved separately per rule; full P/L method applied on last settlement batch)

**Pending at Risk**: 76 NOK (27 prior +49 from 4 new pending bets logged 2026-07-04: Monaro Over4.5 12, Egersund Over2.5 15, Halmstads Draw 10, Beijing Guoan win 12)

**Liquid Available**: 396.06 NOK

**Last Updated**: 2026-07-04 09:xx CEST - nt-bankroll-tracker autonomous after bet_log.csv append (new file SHA 47004ffaeec419d874f63519e1829826ad971f6b after fix push, commit f5fb96aa... + re-verify tree main + full re-read confirmed history + append correct, no placeholders/garbage after correction push) + github___get_repository_tree verify + current_bankroll.md SHA workflow. Equity adjusted ONLY on realized P/L per rule (pending tracked separately). Full archive + live P/L method + locked baseline preserved. Irrefutable proof in commit SHAs + re-fetches + round file. Complete-before-reply discipline followed. System self-sustaining per Master Protocol v2 + nt-betting-skills.md. Note: bet_log.csv temporarily had placeholder in intermediate push but immediately corrected with full content + append before any output.