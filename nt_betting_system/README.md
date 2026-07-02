# NT Betting System (New Automated Version)

This folder contains the foundation for a more automated betting tracking system.

## Important Note on the Database

The actual database file (`bets.db`) is **not committed** to this repository. This is intentional because binary database files do not version well in Git.

**How to initialize the database locally:**

Run this command once after cloning the repository:

```bash
python3 nt_betting_system/scripts/initialize_db.py
```

This will create your local `bets.db` file using the schema.

## Goals
- Reduce manual work for logging, settlement, bankroll tracking, and statistics
- Grok handles script execution and file updates
- User only provides odds files and settlement results

## Current Structure

- `schema.sql` — Database structure
- `scripts/` — Python scripts that Grok uses to manage the system
- `initialize_db.py` — Script to create the local database

## Key Scripts (Grok executes these)

- `process_odds_file.py` — Main entry point when you provide an odds file
- `recommend_from_odds_file.py` — Handles adaptive research (targeted vs deep mode)
- `add_pending_bets.py` — Logs recommended bets
- `full_settlement_flow.py` — Handles settlements + bankroll + stats refresh
- `generate_performance_report.py` — Creates `performance_report.md`
- `update_bankroll.py` — Updates equity after settlements

## How the System is Intended to Work

1. You provide an odds file
2. Grok analyzes it using adaptive research
3. Grok recommends bets + stakes
4. Grok logs the bets into your local SQLite database
5. You place the recommended bets
6. When you provide settlement results, Grok updates everything (results, bankroll, learning, and refreshes the performance report)

## Current Status (2026-07-02)

- Schema and core scripts are in place
- Adaptive research mode logic exists (targeted vs deep)
- Full end-to-end autonomous logging is still being improved
- `bets.db` must be created locally by running the initialize script

All changes to scripts and documentation are tracked in Git. The actual betting data lives in your local `bets.db`.