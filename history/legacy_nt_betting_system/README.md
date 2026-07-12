# NT Betting System (New Automated Version)

This folder contains prepared infrastructure for a more automated betting system.

## Current Status (Important)

**CSV logging is currently active.**

We are using the original `bet_log.csv` + `current_bankroll.md` system with `scripts/safe_bet_log_edit.py` for updates.

The new scripts in this folder (`nt_betting_system/scripts/`) are built and ready, but SQLite (`bets.db`) logging is currently on hold. We may return to it later.

## How Logging Currently Works

- Recommended bets are logged into `bet_log.csv` using short notes.
- Updates are done via `scripts/safe_bet_log_edit.py` (preferred) or full SHA workflow on GitHub.
- `current_bankroll.md` is updated with correct Equity rule after settlements.

## Prepared Scripts (For Future Use)

- `process_odds_file.py` — Main entry point
- `recommend_from_odds_file.py` — Adaptive research (targeted vs deep)
- `full_settlement_flow.py` — Full settlement + bankroll + stats
- `generate_performance_report.py` — Creates performance reports

## How to Initialize (If We Return to SQLite Later)

```bash
python3 nt_betting_system/scripts/initialize_db.py
```

## Summary

- Current active system: CSV (`bet_log.csv`)
- New scripts: Ready but not active yet
- SQLite: On hold for now

All script improvements and documentation are kept for future use.