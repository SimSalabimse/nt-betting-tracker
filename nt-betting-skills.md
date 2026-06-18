# NT Betting Skills

## Core Principle (Updated 2026-06-18)

**Option A is now the active standard**: When the user confirms bets have been placed (or when Grok proposes and user accepts), Grok **directly appends** the pending bets to the GitHub `bet_log.csv` mirror. Always fetch the full current file content + current SHA first, then append cleanly. Never perform blind or partial overwrites of historical data. The local `scripts/safe_bet_log_edit.py` remains available as a manual fallback for the user, but the default agentic flow is direct, decisive updates by Grok on the GitHub side.

This removes unnecessary back-and-forth while maintaining strong data integrity safeguards.

## nt-betting-workflow (Main Orchestrator Skill)
The primary skill for the entire betting process.

Responsibilities:
- Orchestrates the full two-stage research workflow (rough EV scan across all lines → deep research on high-EV candidates).
- When bets are decided and user confirms placement: immediately triggers nt-bet-log-manager to append to GitHub bet_log.csv (full fetch first).
- Updates current_bankroll.md with new pending risk and recalculated liquid available.
- Updates the relevant round file with exact placed bets and notes.
- Ensures all changes are pushed via GitHub tools and re-validated (raw fetch + tree) before any reply to the user.
- Enforces playbook rules: EV discipline, bankroll limits, diversification, post-settlement deep dives, and additive-only updates to learning files.
- Does **not** require the user to run local scripts for routine bet additions.

## nt-bet-log-manager
Handles all mutations of bet_log.csv on the GitHub mirror with strict safety.

Key rules it enforces:
- **Always** fetch the complete current file content and its SHA before any change.
- New pending bets: Append **only** at the bottom. Set `Result=Pending`, leave `P_L_NOK` empty.
- Settlements: Update only the exact matching row (change Result and P_L_NOK) and append details to the Notes field. Never delete or overwrite historical rows.
- Strict post-change validation: header integrity, correct row count, proper CSV quoting (especially Notes with commas/quotes), no malformation.
- Creates timestamped backup before modifications.
- Supports both singles and occasional combos when EV justifies it.

The local `safe_bet_log_edit.py` is the equivalent tool for when the user wants to edit their local master copy manually.

## betting-value-calculator
Pure EV and staking math helper.

- Calculates single-bet EV = (estimated_true_probability × decimal_odds) − 1
- Provides portfolio-level blended EV, variance notes, and conservative Kelly/flat-stake suggestions
- Outputs clear tables with recommended stakes, EV ranges, and rationale
- Used before any bet is proposed or added to the log

## nt-bankroll-tracker
Keeps `current_bankroll.md` perfectly synchronized with bet_log.csv.

Formulas:
- Equity = starting bankroll + SUM(all realized P/L from bet_log.csv)
- Pending at Risk = SUM(stakes of all rows where Result = "Pending")
- Liquid Available = Equity − Pending at Risk

After every addition or settlement, it recalculates and updates the md file with an explicit verification note ("Verified via full bet_log.csv recalculation").

## How the Skills Work Together (Option A Flow)
1. User places bets locally or confirms Grok's proposed bets.
2. Grok runs final EV/staking calculations with betting-value-calculator.
3. Grok calls nt-bet-log-manager → fetches full bet_log.csv + SHA → appends the exact new pending rows.
4. Grok updates current_bankroll.md and the round file.
5. All changes pushed to GitHub and re-validated.
6. Grok replies to user with confirmation and updated status.

This is the decisive, low-friction workflow we are now using.

All skill and data changes continue to follow the strict discipline of full retrieval + GitHub push + re-validation before any user-facing reply.