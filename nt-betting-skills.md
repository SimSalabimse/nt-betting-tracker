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
- **Resources**: Includes `scripts/` and `references/` directories for future helpers or detailed templates.
- **Validation**: Passed `validate-skill.sh` with status **OK (62 lines)** — no TODOs, proper YAML frontmatter, no forbidden patterns, description is plain scalar without colons or angle brackets.

### Description (from SKILL.md)
Use for post-settlement or periodic learning reviews of betting performance. Analyzes settled bets and deep dives to detect patterns, flags insufficient research quality in recent rounds, and proposes additive updates to sport_edges_and_filters.md. Trigger on phrases like review learning from past bets, analyze round performance, update edges from data, or flag research gaps.

### Key Capabilities Implemented
- **Fresh Data Fetch**: Always begins with GitHub tool calls to retrieve latest bet_log.csv (settled rows), recent round_*.md files (deep dive sections), current_bankroll.md, and sport_edges_and_filters.md — verifies SHA + full content every time.
- **Performance Pattern Analysis**: Aggregates ROI, hit rates, EV realization vs actual P/L by sport, bet type, and specific edges/filters. Identifies which factors (form, injuries, xG, motivation, etc.) drove results. Flags systematic deviations with sample sizes.
- **Research Quality Self-Critique**: Scans recent rounds for compliance with Stage 1/Stage 2 depth, tool usage (web_search, browse_page, x_keyword_search), and exploration quotas. Produces explicit "Research Quality Flags" with round references and missing elements (e.g., "no x_keyword_search for team news").
- **Additive Filter Updates**: Only proposes changes to sport_edges_and_filters.md after sufficient samples (>=10-15 instances). Proposals are evidence-based, conservative, additive-only, with ready-to-commit text, rationale, and monitoring notes. All proposals follow push + re-validate before user presentation.
- **Structured Output**: Mandatory sections — Executive Summary, Research Quality Flags, Pattern Insights, Proposed Additive Updates, Bankroll/Process Notes, Next Recommended Actions. Clear handoff to nt-betting-workflow, nt-bankroll-tracker, or nt-bet-log-manager.
- **Guardrails**: Conservative on small samples ("monitor" outputs encouraged). Enforces the same push + validate + fresh SHA discipline as all other skills. References playbook.md and nt-betting-skills.md for context.

### Alignment with Existing Behavior
- Directly fulfills and expands the brief "### 4. nt-learning-reviewer" entry in Critical Behavior Changes.
- Complements the four previously validated skills by adding the dedicated learning/review loop.
- Now listed alongside them as a core, validated capability for the nt-betting-tracker system.

### Next Steps Enabled
- Invoke via `nt-learning-reviewer` (or through nt-betting-workflow post-settlement) for any learning review session.
- Future iterations can add scripts/ for automated aggregation or references/ for deep dive templates.

*Additive update pushed and validated 2026-06-18 following full playbook discipline and GitHub workflow. Local skill created and validated in parallel.*

---

## post-settlement-learning-reviewer Skill Creation & Validation (2026-06-18)

**Dedicated `post-settlement-learning-reviewer` skill has been successfully created as a specialized, focused capability for immediate post-settlement learning and continuous improvement loops.**

### Purpose & Trigger
- **Primary Trigger**: Automatically or manually invoked right after bet settlements are processed (post bankroll verification and deep dive append in the relevant round file).
- **Focus**: Pure post-settlement analysis — no pre-bet research or recommendation generation. Dedicated to extracting maximum learning from realized outcomes.
- **Integration**: Works hand-in-hand with `nt-betting-workflow` (which calls it after settlement handling) and `nt-learning-reviewer` (shares core logic but this one is narrower and always settlement-first).

### Skill Location & Validation
- **Directory**: `/home/workdir/.grok/skills/post-settlement-learning-reviewer/`
- **SKILL.md**: Fully populated with imperative instructions, frontmatter (name: post-settlement-learning-reviewer, plain description), structured output templates, and guardrails.
- **Validation**: Passed all checks (frontmatter, no TODOs, proper structure, playbook alignment). Ready for use via skill invocation.

### Key Capabilities
- **Mandatory Fresh State Fetch**: Begins every run by calling GitHub tools to pull latest settled rows from bet_log.csv, the just-updated round file's Post-Settlement Deep Dive section, current_bankroll.md (post-verification), and sport_edges_and_filters.md. Always verifies SHA and full content.
- **Outcome vs Expectation Analysis**: Compares realized P/L, hit rate, and actual EV realization against pre-bet projections and research notes. Quantifies slippage (research quality gaps, variance, correlation misses in combos).
- **Pattern Detection with Sample-Size Discipline**: Identifies repeatable edges/filters that over/under-performed. Only surfaces insights when sample >= 8-10 settled instances for that specific factor (form, motivation, xG deviation, etc.). Flags "monitor" for smaller samples.
- **Research Quality Audit (Post-Settlement Lens)**: Reviews the deep dive notes in the round file for completeness (tool calls made, all candidates researched, exploration quota met, motivation/injury factors checked). Produces explicit flags like "Round X: No x_keyword_search used for team news on Match Y — potential blind spot."
- **Additive-Only Proposals to Filters/Edges**: After pattern confirmation, generates ready-to-push text blocks for sport_edges_and_filters.md (new bullet under relevant sport or general section). Includes rationale, data summary, confidence level, and suggested monitoring period. Never overwrites; always additive.
- **Structured Output Template**:
  1. Executive Summary (key wins/losses, net P/L impact, main learnings)
  2. Research Quality Flags (specific round references + missing elements)
  3. Pattern Insights (by sport/bet-type/edge with sample sizes and stats)
  4. Proposed Additive Updates (exact markdown blocks ready for commit)
  5. Bankroll/Process Notes (any verification issues or process improvements)
  6. Next Actions & Handoff (to nt-betting-workflow for next round or nt-bankroll-tracker if needed)
- **Guardrails**: Conservative proposals only. Enforces full push + re-validate workflow on any file change. References playbook.md section 4 (Post-Settlement Process) and nt-betting-skills.md.

### Alignment & Benefits
- Directly implements and specializes the "Post-Settlement Process" section of playbook.md.
- Provides a clean separation: nt-betting-workflow handles the settlement mechanics + deep dive append; this skill owns the learning extraction and filter evolution.
- Ensures the continuous improvement loop is explicit, auditable, and triggered reliably after every settlement batch — no ad-hoc reviews.
- Complements existing nt-learning-reviewer by offering a settlement-triggered, narrower-scope variant optimized for immediate post-settlement timing.

### Next Steps
- Invoke `post-settlement-learning-reviewer` after any settlement processing in nt-betting-workflow.
- Future: Add supporting scripts in its `scripts/` dir for automated aggregation if volume grows.
- All updates to this skill itself will follow the same GitHub push + validate discipline documented here.

*Skill created, documented, pushed to GitHub, and validated 2026-06-18 following the complete successful push workflow (verify state → full content update with SHA → re-verify tree/content). Additive only, no existing behavior changed.*