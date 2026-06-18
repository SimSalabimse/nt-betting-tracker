## 2026-06-18 Safe bet_log.csv Editor Script

**Purpose**  
Introduce `scripts/safe_bet_log_edit.py` as the single authoritative tool for all modifications to `bet_log.csv`. This script prevents the truncation, row deletion, and quoting corruption issues seen in earlier commits by enforcing strict rules and using safe editing practices.

**Location**  
`scripts/safe_bet_log_edit.py` (placed alongside `analyze_betting.py` for consistency in the `scripts/` directory).

**Key Features & Rules Enforced**
- Exact header enforcement.
- Append-only for new pending bets (always added at the bottom with `Result=Pending` and empty `P_L_NOK`).
- Targeted settlement updates only (modify `Result` + `P_L_NOK` on the matching row and **append** to Notes — never overwrite or delete historical rows).
- Pre- and post-edit row count validation (warns or aborts on unexpected decreases).
- Automatic timestamped backups before every write.
- Atomic writes using `tempfile` for safety.
- Proper `csv` module handling with `QUOTE_MINIMAL` for complex Notes fields (commas, pipes, quotes, etc.).
- Standalone validation command.

**Usage**
```bash
# Validate current file
python scripts/safe_bet_log_edit.py validate bet_log.csv

# Add new pending bet(s)
python scripts/safe_bet_log_edit.py add-pending bet_log.csv "DATE,Match,Selection,Odds,Stake,Pending,,Notes"

# Settle existing bet(s)
python scripts/safe_bet_log_edit.py settle bet_log.csv "DATE,Match,Selection" "Win" "150.00"
```

**Integration with Workflow & nt-bet-log-manager Skill**
- All changes to `bet_log.csv` must go through this script (either via the `nt-bet-log-manager` Grok skill or manual execution).
- After any edit: re-validate the file, run bankroll verification if needed, then commit + push with clear message.
- The `nt-betting-workflow` skill coordinates this automatically.

**Best Practices**
- Always work from a fresh pull of the latest `bet_log.csv`.
- Never edit the CSV directly with string replacement, text editors, or methods that break quoting.
- Keep all historical rows untouched except for precise settlement updates.
- After settlements, follow the existing post-settlement deep dive + bankroll verification checklist.

*This section was added strictly additively following the established playbook pattern. Previous content restored from good commit history.*