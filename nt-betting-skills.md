# NT Betting Skills

## Core Principle (Updated 2026-07-03)

**Option A is now the active standard**: When the user confirms bets have been placed (or when Grok proposes and user accepts), Grok **directly appends** the pending bets to the GitHub `bet_log.csv` mirror. Always fetch the full current file content + current SHA first, then append cleanly. Never perform blind or partial overwrites of historical data. The local `scripts/safe_bet_log_edit.py` remains available as a manual fallback for the user, but the default agentic flow is direct, decisive updates by Grok on the GitHub side.

This removes unnecessary back-and-forth while maintaining strong data integrity safeguards.

**Notes Column Removed (2026-07-03 Update)**: The Notes column has been removed from `bet_log.csv` entirely per user request. All historical notes have been cleaned. Future logging uses only core columns. All learning, variance analysis, reasoning, and post-settlement reviews are now recorded in **round files** instead of the main bet log.

## nt-betting-workflow (Main Orchestrator Skill)
The primary skill for the entire betting process.

Responsibilities:
- Orchestrates the full two-stage research workflow (rough EV scan across all lines → deep research on high-EV candidates).
- Enforces **diversification rule** (max 2 per category, >=2 sports/types per portfolio) and **hard min 10 NOK stake filter** before any recommendation.
- When bets are decided and user confirms placement: immediately triggers nt-bet-log-manager to append to GitHub bet_log.csv (full fetch first).
- Updates current_bankroll.md with new pending risk and recalculated liquid available.
- Updates the relevant round file with exact placed bets and detailed reasoning/learning.
- Ensures all changes are pushed via GitHub tools and re-validated (raw fetch + tree) before any reply to the user.
- Enforces playbook rules: EV discipline, bankroll limits, diversification, post-settlement deep dives, and additive-only updates to learning files.
- Triggers **post-settlement-learning-reviewer** after settlements and **nt-learning-reviewer** for exploration tracking/promotion.
- Does **not** require the user to run local scripts for routine bet additions.

**2026-06-28 CLEAN RESTART UPDATE (Autonomous Mode Enforcement)**: nt-betting-workflow now **immediately executes bet_log append (pending rows) + bankroll reserve using full SHA workflow + verifies BEFORE any user-facing output**. For settlements: auto deep-dive (post-settlement-learning-reviewer + nt-learning-reviewer), record learning in round file, auto meta if trigger, all pushes/verifies first, summary only after. User only needs to reply for changes or to report results.

## nt-bet-log-manager (Updated 2026-07-03)
Handles all mutations of bet_log.csv on the GitHub mirror with strict safety.

Key rules it enforces:
- **Always** fetch the complete current file content and its SHA before any change.
- New pending bets: Append **only** at the bottom. Set `Result=Pending`, leave `P_L_NOK` empty. **No Notes column** (deprecated).
- Settlements: Update only the exact matching row (change Result and P_L_NOK). No notes added to bet_log.csv.
- Strict post-change validation: header integrity, correct row count, proper CSV quoting, no malformation.
- Creates timestamped backup before modifications.
- Supports both singles and occasional combos when EV justifies it.

**Learning Record**: All detailed reasoning, variance sources, and lessons are now recorded in the relevant **round file**, not in bet_log.csv.

**2026-06-28 CLEAN RESTART UPDATE (Autonomous Mode Enforcement)**: nt-bet-log-manager now called **autonomously** by nt-betting-workflow (full fetch + SHA + append pending + post re-fetch verify + reserve stakes) **before any user-facing text**. Same for settlements (targeted updates). No skipped pushes.

The local `scripts/safe_bet_log_edit.py` is the equivalent tool for when the user wants to edit their local master copy manually.

## betting-value-calculator
Pure EV and staking math helper.

- Calculates single-bet EV = (estimated_true_probability × decimal_odds) − 1
- Provides portfolio-level blended EV, variance notes, and conservative Kelly/flat-stake suggestions
- Outputs clear tables with recommended stakes, EV ranges, and rationale
- Used before any bet is proposed or added to the log. Now includes min-stake adjustment logic.

## nt-bankroll-tracker
Keeps `current_bankroll.md` perfectly synchronized with bet_log.csv.

Formulas:
- Equity = locked baseline (see current_bankroll.md for current locked value and full NO AUTO-RESET RULE) + SUM(all realized P/L from bet_log.csv)
- Pending at Risk = SUM(stakes of all rows where Result = "Pending")
- Liquid Available = Equity − Pending at Risk

**Update Rule (per user feedback for correctness)**: Equity adjusted ONLY on settlements — +P/L profit on Win, -stake on Loss. Pending stakes tracked but not deducted from Equity until settled. This keeps Equity always correct. NEVER reset Equity or baseline to 500 (or any anchor) unless user EXPLICITLY requests it. See current_bankroll.md IMPORTANT - NO AUTO-RESET RULE for details and enforcement.

After every addition or settlement, it recalculates and updates the md file with an explicit short verification note ("Verified via full bet_log.csv recalculation + SHA workflow").

**2026-06-28 CLEAN RESTART UPDATE (Autonomous Mode Enforcement)**: nt-bankroll-tracker now called **autonomously** (recalc + short verification note) immediately after any bet_log update, before any output. Baseline is LOCKED per user NO AUTO-RESET rule in current_bankroll.md — do not auto-enforce or reset without explicit user ask.

## post-settlement-learning-reviewer (Updated 2026-07-03)
**Purpose**: Execute comprehensive deep dive review immediately after any settlement batch is reported. Ensures continuous learning from outcomes.

**Key Responsibilities**:
- Parse recent settlements from bet_log.csv.
- Perform category-level analysis (win rate, ROI, variance per sport/bet-type).
- Identify patterns: what worked and what didn't.
- Record detailed Post-Settlement Deep Dive in the relevant **round_*.md** file (result vs pre-bet hypothesis, key factors confirmed/missed, lesson for filters). Keep concise.
- Propose additive updates to sport_edges_and_filters.md (edge tweaks, new sections, etc.).
- Verify bankroll recalc and update current_bankroll.md.
- Enforce fixes like duplicate bet prevention and min-stake in future workflows.

**Integration**: Called automatically by nt-betting-workflow after user reports settlements. Always push updates to GitHub + re-validate before any user reply.

## nt-learning-reviewer
**Purpose**: Maintain automated data sufficiency tracking and exploration bet promotion logic.

**Key Responsibilities**:
- Maintains tracker table/section in sport_edges_and_filters.md.
- After post-settlement-learning-reviewer trigger: update counts/ROI from latest settlements.
- **Automated Promotion Check** (runs on every settlement batch):
  - If category meets criteria (≥10-12 settled, ROI >+4%, low-moderate variance, ≥3 consistent patterns validated) → promote to core section.
  - Flag in next round recs.
- **Pause/Demotion**: If ROI <-5% after 8+ settled or high unexplained variance → pause category, tighten filters.

**Integration**: Triggered by post-settlement-learning-reviewer or nt-betting-workflow. Updates are additive to sport_edges_and_filters.md.

## How the Skills Work Together (Updated 2026-07-03)
1. User places bets locally or confirms Grok's proposed bets.
2. Grok runs final EV/staking calculations with betting-value-calculator (incl. diversification + min-stake checks).
3. Grok calls nt-bet-log-manager → fetches full bet_log.csv + SHA → appends the exact new pending rows (**no Notes**).
4. Grok updates current_bankroll.md and the relevant round file with detailed reasoning and learning.
5. All changes pushed to GitHub and re-validated (full SHA workflow).
6. On settlements: post-settlement-learning-reviewer runs deep dive → records learning in round file → triggers nt-learning-reviewer for tracker/promotion → updates learning files.
7. Grok replies to user with confirmation and updated status.

**2026-06-28 CLEAN RESTART UPDATE (Autonomous Mode Enforcement)**: Steps 3-4 now happen **immediately and autonomously** (full SHA workflow + verifies) **before any user-facing output**. User only replies for changes or results.

All skill and data changes continue to follow the strict discipline of full retrieval + GitHub push + re-validation before any user-facing reply.

**Analyze Correctly Going Forward (Standing Rule)**: When analyzing odds files, strong filtering must be followed by proper targeted deep research on the shortlist. Aim for balanced volume (typically 4–8 quality bets from mixed files). Overly conservative outputs (e.g. only 2 bets) or shallow analysis are not acceptable.

This is the decisive, low-friction workflow we are now using.