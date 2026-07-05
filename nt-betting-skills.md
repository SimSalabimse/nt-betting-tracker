# NT Betting Skills (Updated 2026-07-05 - Research Depth Enforcement)

## Core Principle (Updated 2026-07-05)

**Option A is now the active standard**: When the user confirms bets have been placed (or when Grok proposes and user accepts), Grok **directly appends** the pending bets to the GitHub `bet_log.csv` mirror.

**Notes Column Removed**: All learning now goes to round files.

**Research Depth Rule (NEW - 2026-07-05)**: The system has been doing insufficient research. Minimum standards are now enforced:
- Every shortlisted bet requires **minimum 8-12 distinct tool calls / high-quality sources**.
- For high-variance bets (especially Over/Under in knockout games): **minimum 12-15 sources**.
- Must use multiple sources: FBref, Transfermarkt, Understat, FotMob, lineups, weather, H2H, motivation, xG models, etc.
- Shallow research is no longer acceptable. Depth is now mandatory.

## nt-betting-workflow (Main Orchestrator Skill)

Responsibilities:
- Orchestrates the full two-stage research workflow.
- Enforces diversification and min 10 NOK stake filter.
- **NEW**: Must enforce the Research Depth Rule. No bet should be recommended with shallow research (2-5 sources is no longer acceptable).
- Triggers nt-bet-log-manager and updates round files.

## nt-bet-log-manager (Updated 2026-07-03)

Handles mutations of bet_log.csv with strict safety. No Notes column. Learning goes to round files.

## betting-value-calculator

Pure EV and staking math helper.

## nt-bankroll-tracker

Keeps current_bankroll.md synchronized using full archive + live method.

## post-settlement-learning-reviewer (Updated 2026-07-05)

Executes deep dive after settlements.
- Must perform real tool searches on why bets won/lost.
- Pay special attention to recurring weak areas (e.g. recent Over/Under performance).
- Record structured learning in round files.
- Update sport_edges_and_filters.md when patterns appear.

## nt-learning-reviewer

Maintains data sufficiency tracking.

## How the Skills Work Together (Updated 2026-07-05)

1. User places bets or confirms recommendations.
2. Grok runs final EV/staking calculations.
3. Grok calls nt-bet-log-manager.
4. Updates current_bankroll.md and round file.
5. On settlements: post-settlement-learning-reviewer runs deep dive.

**Research Depth is now mandatory** at every stage of analysis.

**Over/Under Caution**: Due to recent poor performance, Over/Under bets (especially in knockout games) are heavily deprioritized unless supported by very strong multi-source evidence.