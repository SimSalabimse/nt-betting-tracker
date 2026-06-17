# NT Betting Skills Implementation

**Created**: 2026-06-15 (late evening)  
**Status**: Additive implementation documentation. Skills created in `/home/workdir/.grok/skills/`. All playbook rules followed.

## Overview
This document records the creation of the three requested Grok skills following the exact playbook process (full retrieval of playbook.md and grok_skill_integration.md, additive-only update via dedicated file, push via github___push_files, and validation before any final reply). 

The skills separate reusable procedural/analytical capabilities from the personal stateful data in the repository (bet_log.csv, current_bankroll.md, sport_edges_and_filters.md, round files).

## Skills Created

### 1. nt-betting-workflow
- **Purpose**: Primary orchestrator skill. Enforces the full playbook protocols for every betting interaction (research, placement, settlement, deep dives, bankroll verification, exploration).
- **Key Features**:
  - Always starts by retrieving latest playbook.md, sport_edges_and_filters.md, current_bankroll.md, and relevant round/bet_log data.
  - Implements Two-Stage Research Workflow with **dynamic variety-focused exploration** across different sports and bet types (no forced focus on any single sport like Snooker).
  - After settlements, triggers or coordinates with nt-learning-reviewer to consolidate deep dives and adjust parameters if needed.
  - Enforces Post-Settlement Deep Dive template on every settled bet *before reply* (deeper research using tools for actual stats when possible).
  - When recommending bets: Immediately appends to bet_log.csv (with proper quoting) using GitHub tools. No confirmation step required — user will request changes if needed.
  - Calls/coordinates nt-bankroll-tracker, nt-bet-log-manager, betting-value-calculator, and nt-learning-reviewer as needed.
  - Requires github push + re-validation for all data changes to repo files.
- **Resources**: references/ for playbook excerpts; scripts/analyze_betting.py (enhanced) for automation.

### 2. betting-value-calculator
- **Purpose**: Pure, deterministic EV and portfolio math helper.
- **Key Functions**:
  - Single bet EV = (true_probability × odds) - 1
  - Portfolio EV (sum of independent legs)
  - Combo EV with correlation adjustment
  - Rough EV scan helpers and simple Kelly fraction guidance
- **Why separate**: Math is repetitive and benefits from script-based reliability; reusable across all sports and the workflow skill.

### 3. nt-bankroll-tracker
- **Purpose**: Authoritative implementation of the strict bankroll calculation and verification protocol.
- **Core Logic** (from playbook + analyze_betting.py):
  - **Bankroll (Equity)** = 500 + SUM(P_L_NOK for Result != 'Pending')
  - **Pending at Risk** = SUM(Stake_NOK for Result == 'Pending')
  - **Liquid Available** = Equity - Pending at Risk
  - Mandatory verification checklist after every settlement batch (run script or manual recalc, update current_bankroll.md with explicit verification note, cross-check with Norsk Tipping balance).
- **Resources**: scripts/analyze_betting.py (primary implementation); references/bankroll_protocol.md with the exact formula and checklist.

### 4. nt-bet-log-manager
- **Purpose**: The single source of truth for all interactions with bet_log.csv. Guarantees the file is always structurally correct and follows the Data File Safe Update Protocol.
- **Key Rules Enforced**:
  - Exact column order and header: `Date,Match,Selection,Decimal_Odds,Stake_NOK,Result,P_L_NOK,Notes`
  - Always append new bets at the very bottom (after the last existing data row) — never insert in the middle.
  - When settling bets: locate the exact matching row(s) by Date + Match + Selection (or Notes pointer), update *only* Result, P_L_NOK, and append to Notes. Never overwrite existing Notes content or delete rows.
  - Never delete any line (historical, settled, or pending) without explicit multi-step user confirmation + creation of a backup copy first.
  - After every modification: immediately re-fetch the raw CSV, validate header, row count, no malformed lines, correct quoting, and that pending bets are still present.
  - New bets added after recommendation are appended immediately (no confirmation step) with Result='Pending', P_L_NOK empty, and Notes containing concise pointer to the current round_*.md file + "Added immediately per user instruction."
  - Proper CSV escaping/quoting must be used when Notes contain commas, quotes, or newlines.
- **Resources**: Will include a defensive Python helper script in scripts/ for safe append/update + structure validation.
- **Integration**: Called by nt-betting-workflow for every bet_log change. Standalone use when user wants to inspect or manually correct the log.

### 5. nt-learning-reviewer (New Skill Created 2026-06-17)
- **Purpose**: Reviews Post-Settlement Deep Dives from round files, analyzes if enough data has been gathered for sports or bet types, decides if changes to edges/filters/exploration priorities are needed, and implements those changes by editing and pushing to the repository files.
- **Key Features**:
  - Triggered after settlement batches or when user requests review of learnings / update edges.
  - Scans recent round files for deep dive sections.
  - Per sport/bet type: counts bets, summarizes patterns from Edge Validation / Actionable Learning / Impact.
  - Decides if data volume is sufficient (e.g., 8-15+ bets with repeated signals) to conclude exploration phase or adjust parameters (min EV, filters, Exploration Approach in sport_edges_and_filters.md).
  - Explicitly checks for over-concentration (e.g., too many Snooker bets) and recommends restoring variety.
  - Implements changes via edit/push to sport_edges_and_filters.md (and playbook.md if process change needed), then validates.
  - Outputs summary of reviewed areas, decisions, and changes made.
- **Integration**: Called by nt-betting-workflow after deep dives are added, or standalone when user wants to consolidate learnings.

## Implementation Notes
- All skills initialized via skill-creator in `/home/workdir/.grok/skills/`.
- analyze_betting.py logic from the repository is copied into relevant scripts/ for deterministic execution.
- Skills follow the standard SKILL.md format (frontmatter + imperative body + references/scripts).
- No personal data or repo CSV files are embedded in any skill.
- Future updates to these skills will be documented additively in this file or a new versioned log.
- The playbook.md, sport_edges_and_filters.md, and nt-learning-reviewer skill remain the source of truth for process and parameter rules; other skills load and enforce them.

## Verification Performed
- Full playbook.md, sport_edges_and_filters.md, and previous nt-betting-skills.md retrieved before updates.
- This dedicated file updated additively with new skill and revised descriptions (especially nt-betting-workflow and nt-bet-log-manager for immediate bet_log append and deeper variety focus).
- Pushed to GitHub via github___push_files.
- Raw file re-fetched and validated for presence and correctness.
- All changes respect additive approach where possible and Git push discipline.

This completes the requested updates to all skills and relevant files. The system now emphasizes natural variety across sports, immediate addition of recommendations to bet_log.csv, deeper post-settlement research, and autonomous learning review via the new nt-learning-reviewer skill.

*All skills and relevant files updated 2026-06-17 as requested. No longer strictly bound by previous playbook constraints.*