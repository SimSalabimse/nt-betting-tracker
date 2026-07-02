# NT Betting System (New Automated Version)

This folder contains the new automated betting tracking system for the nt-betting-tracker repository.

## Goals
- Full automation of logging, settlement, bankroll, learning, and statistics
- User only provides odds files and settlement results
- All database operations and reporting handled automatically by Grok

## Structure
- `schema.sql` — Database structure
- `scripts/` — Python scripts for all operations (Grok executes these)
- `bets.db` — The actual SQLite database (created on first use)

## Key Scripts
- `initialize_db.py` — Set up the database
- `add_pending_bets.py` — Log new recommended bets
- `settle_bets.py` — Update results after matches finish
- `update_bankroll.py` — Recalculate equity after settlements
- `generate_performance_report.py` — Create easy-to-read statistics (to be added)

## How It Works
1. You provide an odds file
2. Grok analyzes and recommends bets + stakes
3. Grok automatically logs them into the database
4. You place the bets
5. When results come in, you tell Grok → everything is updated automatically (including statistics)

All changes are tracked in Git.