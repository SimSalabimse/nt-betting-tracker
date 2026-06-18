# NT Betting Skills (Restored + Option A Locked In)

**2026-06-18 Update**: Option A is now the default (Grok directly appends to GitHub bet_log.csv mirror when bets are placed/confirmed). No more mandatory local script run for routine adds. The local safe script remains available as fallback.

---

[Full original content follows - restored]

# NT Betting Skills Implementation (Updated 2026-06-17)

**All skills updated for deeper research and immediate bet_log appends.**

## Critical Behavior Changes

### 1. Research Depth & Breadth (nt-betting-workflow)
- **Stage 1 (Rough EV Scan)**: Scan **every single line** in the provided odds file. Flag **all** lines that meet the rough EV threshold (min 7-8%+ depending on sport).
- **Stage 2 / Deep Research Phase**: 
  - Do **not** limit research to 1-2 matches.
  - Research **every good edge opportunity** thoroughly.
  - **Force use of tools**: For each promising candidate, you **must** use web_search, browse_page, x_keyword_search (for recent news/form), and any other relevant tools to gather:
    - Recent form (last 5-10 matches)
    - Head-to-head stats
    - xG, expected goals, underlying metrics (where available)
    - Injuries, suspensions, team news
    - Motivation (must-win, derby, rest, etc.)
    - Pace, defensive strength, specific bet-type stats (e.g., BTTS trends, Over/Under tendencies, handicap margins)
    - Weather/venue factors if relevant
  - Only after thorough tool-assisted research on multiple candidates do you prioritize and select the best ones.
- Goal: High-quality, evidence-based recommendations across a broad set of edges, not shallow research on a couple of matches.

### 2. Immediate Append to bet_log.csv (No Confirmation)
- When you decide on recommended bets, **immediately** call nt-bet-log-manager to append them to bet_log.csv using the robust method (fresh SHA fetch + proper quoting).
- **Do not ask the user for confirmation** before adding. The user explicitly said they will tell you if changes are needed afterward.
- Use the robust nt-bet-log-manager logic every time to avoid push failures and CSV corruption.

### 3. nt-bet-log-manager Robustness
- Always fetch latest content + SHA first.
- Use proper CSV escaping for Notes (wrap in quotes if needed, double internal quotes).
- Validate after every push.
- Supports immediate append for recommendations.

### 4. nt-learning-reviewer
- Continues to review deep dives and update edges/filters when enough data exists.
- Can now also flag if research quality was insufficient in recent rounds.

## Files Updated
- nt-betting-skills.md (this file)
- Actual skill SKILL.md files in /home/workdir/.grok/skills/ for nt-betting-workflow, nt-bet-log-manager, and nt-learning-reviewer (instructions aligned with above).
- Relevant helper scripts for safe CSV handling.

All changes make research deeper and broader while ensuring bet_log updates happen immediately and reliably without confirmation prompts.

*Updated 2026-06-17 as requested — no playbook constraints applied.*

---

## Successful Skill Creation & Validation (2026-06-18 Update)

**All four core skills have now been successfully initialized, populated, and validated** in the persistent skills directory (`/home/workdir/.grok/skills/`).

### Skills Created/Updated
1. **nt-betting-workflow** (Primary orchestrator)
   - Enforces full playbook, two-stage research (proactive deep dives before answering), exploration quotas, singles-vs-combo comparison, immediate bet_log append via manager, post-settlement deep dives + bankroll verification.
   - Coordinates the other skills.
   - Validated successfully.

2. **betting-value-calculator**
   - Deterministic EV math: single bet EV, portfolio/combo with correlation adjustment, variance flagging, conservative Kelly guidance.
   - Clear table/bullet output for recommendations.
   - Validated successfully.

3. **nt-bankroll-tracker**
   - Exact formulas: Equity = 500 + SUM(realized P/L), Pending at Risk, Liquid Available.
   - Mandatory verification checklist after every settlement before updating current_bankroll.md.
   - Bundles analysis logic.
   - Validated successfully.

4. **nt-bet-log-manager** (Critical for CSV reliability)
   - Non-negotiable rules: exact header, append-only at bottom for new pending bets (Result=Pending, P_L empty), targeted settlement updates only (Result + P_L_NOK, append to Notes), **never delete lines**.
   - Mandatory backup before changes + full post-edit validation (header, row count, no malformation, pending bets preserved, proper quoting).
   - Bundled defensive script: `scripts/safe_bet_log_edit.py` (handles add-pending, settle, validate with proper CSV escaping and atomic-ish updates).
   - Validated successfully.

### Key Improvements Implemented
- Research is now proactive and deep (tools used before final answer; replace weak matches).
- Bet recommendations use clear tables with exact stakes/odds; immediate append to bet_log (user flags changes if needed).
- Balanced exploration across sports (no Snooker over-weighting).
- Uses older round files for pattern learning when data sufficient.
- Full CSV safety and validation on every change.
- Bankroll verification enforced before any update.
- All skills are lean, imperative, and reference the repo as single source of truth.

### Validation
All four skills passed the official `validate-skill.sh` with no errors (proper frontmatter, descriptions, structure, no TODOs or forbidden patterns).

These skills provide reliable, repeatable behavior matching your requirements. Use by invoking `nt-betting-workflow` (or specific ones) in future sessions.

*Additive update pushed 2026-06-18 following playbook discipline.*

---

## nt-learning-reviewer Skill Creation & Validation (2026-06-18)

**nt-learning-reviewer skill has been successfully created locally, populated with full review logic, validated, and is now documented here as the fifth core skill.**

### Skill Location & Validation
- **Directory**: `/home/workdir/.grok/skills/nt-learning-reviewer/`
- **SKILL.md**: Fully written with frontmatter (name + description), imperative instructions, and structured output requirements.