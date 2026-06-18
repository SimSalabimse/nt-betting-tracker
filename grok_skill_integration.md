# Grok Skill Integration for nt-betting-tracker

**Created: 2026-06-15**  
**Status**: Additive documentation only. No changes to data, betting logic, or core rules.

## Overview
This document captures the analysis and recommendation in response to the query: "Can you make this entire project into a skill? If not, which part can and should be skills?"

It follows the playbook philosophy established in the 2026-06-14 major update: lean core files, dedicated purpose-built files for new concerns, strict additive updates, full retrieval + GitHub push + re-validation before any user-facing reply, and preservation of bet_log.csv as single source of truth for all financial tracking.

## 1. Can the Entire Project Become One Skill?

**Answer: No.**

### Rationale
- **Stateful personal financial data**: The project contains your complete betting history (`bet_log.csv`, archive), current bankroll state (`current_bankroll.md`), pending risk, per-bet P/L in NOK, and specific Norsk Tipping market selections. A Grok skill is a reusable capability module. It must not contain or version personal financial records or tie the agent's behavior to one individual's private betting account.
- **Process vs. Capability**: The heart of the project is the *living process* codified in `playbook.md` (mandatory deep dives on every settlement, two-stage research workflow, exploration quotas for Darts/Snooker, bankroll verification formula and checklist, singles-vs-combo comparison, additive-only updates). These are instructions *to follow*, not code to embed. The playbook + GitHub workflow (push_files + validate) is already the control plane.
- **Scope and bloat**: Including dozens of round_*.md files, historical archives, and evolving config would make any skill impractically large and quickly stale. Skills use progressive disclosure and are meant to stay focused (<500 lines SKILL.md recommended).
- **Update friction**: Data changes (new bets, settlements, deep dives) must continue to use the github___push_files tool and immediate validation. A monolithic skill would create dual maintenance paths.
- **Privacy & separation**: Your bankroll, stakes (now accelerating to 15-25 NOK), and ROI are personal. Skills in /home/workdir/.grok/skills/ are for agent extension and persist across sessions but should remain general or organization-specific, not user-financial-log-specific.

The project is best viewed as **your personal audited betting system** with strong process guardrails. Grok assists by following the process, not by becoming the process.

## 2. Which Parts Can and Should Be Skills?

**Answer: The procedural workflow and analytical automation logic.**

These are exactly the kind of non-obvious, repeatable, high-value procedures that skills are designed to encode.

### Primary Recommendation: `nt-betting-workflow` Skill

**Directory**: `/home/workdir/.grok/skills/nt-betting-workflow/`

**Frontmatter Description** (example):
```
name: nt-betting-workflow
description: Use for all Norsk Tipping Oddsen betting rounds, settlements, bankroll reconciliations, post-settlement deep dives, EV analysis, and portfolio construction. Enforces the full playbook protocols including two-stage research, mandatory exploration quota, deep dive templates, and bankroll verification checklist.
```

**Key Body Content (Imperative Form)**:
- Always begin by fetching the latest versions of `playbook.md`, `sport_edges_and_filters.md`, `current_bankroll.md`, and the most recent round file + bet_log.csv summary using available GitHub tools or raw URLs.
- Execute the **Two-Stage Research Workflow** on every round without exception:
  - Stage 1: Equal consideration rough EV scan across *all* markets/lines in the odds file.
  - Stage 2: Prioritize using highest EV + conviction + **mandatory exploration quota** (at least 1-2 from HIGH priority sports in sport_edges_and_filters.md, e.g. Darts and Snooker).
- For every settlement batch, *before any user reply*:
  - Update bet_log.csv
  - Add the exact **Post-Settlement Deep Dive** section (template in playbook) to the relevant `rounds/` file.
  - Run bankroll verification (analyze_betting.py or manual full SUM formula).
  - Update `current_bankroll.md` with verified Equity / Pending at Risk / Liquid Available + explicit "Verified via full bet_log.csv recalc..." note.
- Enforce diversification and explicit singles-vs-combo EV/variance comparison in round files.
- After multiple deep dives reveal patterns, propose *additive only* updates to `sport_edges_and_filters.md`.
- All data-changing actions must be pushed via github___push_files and re-validated by raw fetch before the final reply to the user.

**Bundled Resources**:
- `references/`: Key protocol excerpts or the full distilled playbook rules (playbook.md in the repo remains the authoritative source; we still read it in full for any edit).
- `scripts/analyze_betting.py`: Copy or enhanced version of the automation script. Provides deterministic bankroll recalc, per-sport ROI tables, exploration priority flags, and pattern detection helpers. Can be executed via bash or code tool without loading the entire CSV into context every time.

**Benefits**:
- Guarantees consistent, 100% playbook-compliant behavior across all future betting interactions.
- Frees token budget (rules are loaded on-demand via skill rather than repeated in every prompt).
- Maintains the strict "push + validate before reply" discipline while adding structure.
- Easy to iterate: update skill when playbook evolves (after push to repo).

### Secondary Recommendation: `betting-value-calculator` Skill (Future)

If EV calculations, combo adjustments for correlation, or rough probability estimation become frequent repetitive tasks, extract pure math helpers into a small dedicated skill.
- Scripts for EV = (p * o) - 1, portfolio EV, correlation-adjusted combo EV, simple Kelly suggestions.
- Keeps math reliable and token-efficient.

### What Should NOT Become Part of Any Skill
- `bet_log.csv`, `bet_log_archive_*.csv`, `current_bankroll.md`: These are the financial single source of truth. Updates only through playbook process + GitHub.
- `sport_edges_and_filters.md`: Config and data-driven edges. Updated only after sufficient settled bets + deep dive patterns (per 2026-06-14 rules).
- Individual `round_*.md` and `rounds/` contents: Historical narrative and learning artifacts. Stay in repo.
- `playbook.md` itself: Remains the process bible in the repo. The skill *references and loads from it* but does not replace the requirement to read the full current version before changes.

## 3. Implementation Notes & Alignment

- Creating the skill does **not** change any existing betting rule, bankroll formula, deep dive requirement, or file convention.
- The 2026-06-14 improvements (mandatory deep dives, exploration quota, two-stage workflow, analyze_betting.py) are fully preserved and will be encoded in the skill.
- This document (`grok_skill_integration.md`) + the short pointer section in `playbook.md` serve as the permanent record of the decision.
- If you approve, next step is to use the skill-creator to initialize `nt-betting-workflow` and populate it with the distilled protocols above.
- All future updates to the skill or playbook will still follow the additive + push + validate discipline.

## 4. Summary Table

| Component                  | Make into Skill? | Reason / Notes                                      |
|----------------------------|------------------|-----------------------------------------------------|
| Entire project + all data  | No              | Personal financial state + process, not general capability |
| Procedural rules (playbook core) | Yes (primary) | Exactly the repeatable non-obvious workflow skills target |
| analyze_betting.py logic   | Yes (bundled)   | Deterministic automation; move to skill scripts/   |
| sport_edges_and_filters.md | No (repo only)  | Data/config; update only after patterns from deep dives |
| bet_log.csv & bankroll     | No (repo only)  | Single source of truth for all P/L and equity      |
| round files                | No (repo only)  | Per-round history and post-mortems                 |
| EV math helpers            | Yes (secondary) | Pure functions; reusable across sports             |

This structure keeps the tracker lean, auditable, and fully under your control while giving Grok a powerful, compliant "muscle memory" for assisting with it.

*Document created additively 2026-06-15 following playbook by the letter. Pushed and validated together with playbook.md update.*

**2026-06-18 Note**: Option A (direct GitHub bet_log.csv appends by Grok when bets placed) is now the active standard. Local safe script is fallback only.

**2026-06-19 Update: nt-betting-workflow Skill Activated**

The primary `nt-betting-workflow` skill has been successfully created at `/home/workdir/.grok/skills/nt-betting-workflow/` using the skill-creator init script and populated with a comprehensive imperative SKILL.md (91 lines, validated).

It now serves as the main orchestrator for all betting workflow tasks and explicitly encodes:
- Mandatory GitHub state verification + full-content push + re-validation before every data-changing reply
- Two-stage research (Stage 1 rough EV scan of every line + Stage 2 deep research on flagged opportunities)
- Safe bet_log.csv handling rules (nt-bet-log-manager)
- Bankroll verification formulas + checklist (nt-bankroll-tracker)
- Support for EV/portfolio calculations (betting-value-calculator to be initialized on demand)

The skill references the authoritative playbook.md and round files in this repo. All future nt-betting interactions (including the current round_20260619_current_odds_01.md) will use this skill. Supporting skills can be created similarly if/when needed for finer granularity.

This update was pushed via github___create_or_update_file with full content and SHA validation immediately after skill creation and local validation. Workflow discipline maintained 100%.