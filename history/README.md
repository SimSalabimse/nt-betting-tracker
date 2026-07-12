# History (preserved, not control-plane)

| Path | Contents |
|------|----------|
| `archives/` | All bet_log / bankroll CSV snapshots, including pre-restart eras and the live log before v3 |
| `rounds/` | Every historical round / deep-dive markdown |
| `legacy_docs/` | Old playbooks, skills text, performance essays, edges essays |
| `legacy_scripts/` | Previous Python helpers |
| `legacy_nt_betting_system/` | Incomplete SQLite automation attempt |

**Active ledger** is only `../data/bets.csv` (era archive rows + post-archive rows).
Do not re-import pre-restart CSVs into equity unless you intentionally change the baseline era.
