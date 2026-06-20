# NT Betting Skills

## Core Principle (Updated 2026-06-18)

**Option A is now the active standard**: When the user confirms bets have been placed (or when Grok proposes and user accepts), Grok **directly appends** the pending bets to the GitHub `bet_log.csv` mirror. Always fetch the full current file content + current SHA first, then append cleanly. Never perform blind or partial overwrites of historical data. The local `scripts/safe_bet_log_edit.py` remains available as a manual fallback for the user, but the default agentic flow is direct, decisive updates by Grok on the GitHub side.

This removes unnecessary back-and-forth while maintaining strong data integrity safeguards.

## nt-betting-workflow (Main Orchestrator Skill)
The primary skill for the entire betting process.

Responsibilities:
- Orchestrates the full two-stage research workflow (rough EV scan across all lines → deep research on high-EV candidates).
- Enforces **diversification rule** (max 2 per category, >=2 sports/types per portfolio) and **hard min 10 NOK stake filter** before any recommendation (2026-06-20 update).
- When bets are decided and user confirms placement: immediately triggers nt-bet-log-manager to append to GitHub bet_log.csv (full fetch first).
- Updates current_bankroll.md with new pending risk and recalculated liquid available.
- Updates the relevant round file with exact placed bets and notes.
- Ensures all changes are pushed via GitHub tools and re-validated (raw fetch + tree) before any reply to the user.
- Enforces playbook rules: EV discipline, bankroll limits, diversification, post-settlement deep dives, and additive-only updates to learning files.
- Triggers **post-settlement-learning-reviewer** after settlements and **nt-learning-reviewer** for exploration tracking/promotion.
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
- Used before any bet is proposed or added to the log. Now includes min-stake adjustment logic.

## nt-bankroll-tracker
Keeps `current_bankroll.md` perfectly synchronized with bet_log.csv.

Formulas:
- Equity = starting bankroll + SUM(all realized P/L from bet_log.csv)
- Pending at Risk = SUM(stakes of all rows where Result = "Pending")
- Liquid Available = Equity − Pending at Risk

After every addition or settlement, it recalculates and updates the md file with an explicit verification note ("Verified via full bet_log.csv recalculation").

## post-settlement-learning-reviewer (NEW 2026-06-20 Skill)
**Purpose**: Execute comprehensive deep dive review immediately after any settlement batch is reported. Ensures continuous learning from the now 98+ bet dataset.

**Key Responsibilities**:
- Parse recent settlements from bet_log.csv (or round file notes).
- Perform category-level analysis (win rate, ROI, variance per sport/bet-type) using analyze_betting.py or direct calc.
- Identify patterns: what worked (e.g. tennis game HC validated, HUB BTTS reliable), what didn't (Over 2.5 variance in some HUB, large WNBA spreads, high-odds props variance, esports map adaptation).
- Trigger **nt-learning-reviewer** to update tracker and check promotion criteria.
- Add detailed Post-Settlement Deep Dive section to the relevant round_*.md file (template: result vs pre-bet hyp, key factors confirmed/missed, lesson for filters).
- Propose additive updates to sport_edges_and_filters.md (edge tweaks, new high-odds section, etc.).
- Verify bankroll recalc and update current_bankroll.md.
- Flag data collection priorities for future (e.g. more Athletics, stricter esports filters).
- Enforce fixes like duplicate bet prevention and min-stake in future workflows.

**Integration**: Called automatically by nt-betting-workflow after user reports settlements. Always push updates to GitHub + re-validate before any user reply. References playbook.md and sport_edges_and_filters.md.

## nt-learning-reviewer (NEW 2026-06-20 Skill)
**Purpose**: Maintain automated data sufficiency tracking and exploration bet promotion logic. Removes need for user to manually track/remember when exploration categories have enough data.

**Key Responsibilities**:
- Maintains tracker table/section in sport_edges_and_filters.md (or dedicated if grows large): per-category settled count, wins, ROI, variance summary, promotion status.
- After post-settlement-learning-reviewer trigger: update counts/ROI from latest settlements.
- **Automated Promotion Check** (runs on every settlement batch):
  - If category meets all: >=10-12 settled, ROI >+4%, low-moderate variance, >=3 consistent deep dive patterns validated → promote (move to core section in sport_edges_and_filters.md, update allocation rules in playbook, remove 'HIGH exploration' tag).
  - Flag in next round recs: 'Category X promoted to standard treatment based on data'.
- **Pause/Demotion**: If ROI <-5% after 8+ or high unexplained variance → pause category, tighten filters sharply, note in tracker.
- Current tracked (post 98-bet review): Athletics promising keep exp; Snooker/Esports tightened/paused; Darts selective; High-odds ultra-exploratory.
- Ensures exploration logic is followed consistently (was missed before user reminder - now automated).

**Integration**: Triggered by post-settlement-learning-reviewer or nt-betting-workflow. Updates are additive to sport_edges_and_filters.md. Pushed/validated via GitHub tools. Lives alongside other skills in nt-betting-workflow orchestration.

## How the Skills Work Together (Option A Flow)
1. User places bets locally or confirms Grok's proposed bets.
2. Grok runs final EV/staking calculations with betting-value-calculator (incl. diversification + min-stake checks).
3. Grok calls nt-bet-log-manager → fetches full bet_log.csv + SHA → appends the exact new pending rows.
4. Grok updates current_bankroll.md and the round file.
5. All changes pushed to GitHub and re-validated.
6. On settlements: post-settlement-learning-reviewer runs deep dive → triggers nt-learning-reviewer for tracker/promotion → updates learning files.
7. Grok replies to user with confirmation and updated status.

This is the decisive, low-friction workflow we are now using.

All skill and data changes continue to follow the strict discipline of full retrieval + GitHub push + re-validation before any user-facing reply.

**2026-06-20 Update**: Added post-settlement-learning-reviewer and nt-learning-reviewer skills to address 98-bet review findings (duplicate bets, exploration automation, high-odds, min stake). Skills now fully integrated into workflow.