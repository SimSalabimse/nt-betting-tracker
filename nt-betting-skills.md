# NT Betting Skills

## Core Principle (Updated 2026-06-18)

**Option A is now the active standard**: When the user confirms bets have been placed (or when Grok proposes and user accepts), Grok **directly appends** the pending bets to the GitHub `bet_log.csv` mirror using full-content fetch + append (never blind overwrite). The local `safe_bet_log_edit.py` remains available for the user if they prefer manual control, but the default agentic flow is direct update by Grok.

This removes friction and makes the workflow decisive.

## nt-betting-workflow
Primary orchestrator. When bets are decided and confirmed placed:
- Immediately calls nt-bet-log-manager to append to GitHub bet_log.csv (full content + SHA fetch first).
- Updates current_bankroll.md with new pending risk.
- Updates the relevant round file.
- Pushes + validates everything before replying to user.
- Does **not** ask user to run local scripts for routine bet adding.

## nt-bet-log-manager
Handles all bet_log.csv mutations on the GitHub side:
- Always fetches current full file + SHA before any change.
- Appends new pending rows at the bottom only.
- For settlements: updates only the matching row + appends to Notes.
- Never deletes or truncates historical rows.
- Validates header, row count, and quoting after every push.

## betting-value-calculator
Calculates EV, Kelly guidance, and portfolio blending for proposed bets.

## nt-bankroll-tracker
Maintains current_bankroll.md in sync with bet_log.csv (equity, pending risk, liquid available).

All changes are pushed via GitHub tools and re-validated before any user-facing reply.