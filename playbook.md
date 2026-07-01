# NT Betting Tracker Playbook (Updated 2026-07-01 - Active for Future Betting Recommendations + Cleanup)

**CLEANUP NOTE (2026-07-01)**: This playbook is now the active operational document for betting recommendations and workflows going forward (per user instruction). robust_betting_protocol_v2.md is historical/supplementary reference only. All future bet analysis, recs, and updates follow this playbook + nt-betting-skills.md by the letter. Short Notes Rule enforced everywhere to fix ballooning, truncation, and GitHub update corruption permanently. No long protocol text in bet_log Notes or bankroll.

**Current Clean State (2026-07-01)**:
- bet_log.csv: Full historical data preserved (Git + bet_log_archives/). Future mutations use short Notes only + nt-bet-log-manager or scripts/safe_bet_log_edit.py (append-only or targeted, validated, atomic).
- current_bankroll.md: Simplified, correct Equity rule (500 baseline + realized P/L only; +profit on Win, -stake on Loss; Pending tracked separately but not deducted until settled). Verified via full SHA workflow.
- rounds/: All good historical recommendations and data gathering preserved perfectly.
- Skills active: nt-betting-workflow (orchestrator), nt-bet-log-manager, nt-bankroll-tracker (correct rule), post-settlement-learning-reviewer, nt-learning-reviewer, betting-value-calculator.
- GitHub updates: Full Successful Push Workflow mandatory (tree → get content+SHA → full clean content + sha → re-verify). Local safe script preferred fallback for reliability.

**Project Goal**: Systematic, high-EV sports betting with strict bankroll management, deep research, reliable data tracking, and continuous learning. Focus on value, discipline, long-term edge. No more GitHub frustrations.

## File Structure

- **Root**: bet_log.csv (master log - never edit directly; use safe script or nt-bet-log-manager), current_bankroll.md (Equity correct per rule), sport_edges_and_filters.md (edges + learnings), README.md, nt-betting-skills.md (full skill defs + Short Notes Rule), Betting_Commands.txt (skills-first commands).
- **rounds/**: Primary for all round analysis, full research, recommendations, and processed files. All your good historical bets preserved here.
- **bet_log_archives/**: Historical snapshots and pre-clean archives.
- **scripts/**: safe_bet_log_edit.py (authoritative local tool for bet_log mutations - validate, add-pending append-only, settle targeted with short note append, atomic write, backup, proper quoting).

## Core Betting Workflow (Skills-Driven, Short Notes, Reliable)

### 1. Research Depth & Breadth
- Stage 1 (Rough EV Scan): Scan every line in odds file. Flag rough EV >=7-8%+.
- Stage 2 (Deep Research): Thorough per promising line using tools (web_search, browse_page, x_keyword_search etc.) with explicit proof. Required: form, H2H, xG, injuries, motivation, pace, specific stats, weather/venue if relevant. Per-line targeted research mandatory.
- First-principles + multi-agent simulation (Value Agent, Risk Manager, Data Hunter, Contrarian) with bias reset.
- Goal: Evidence-based recs across broad edges. Replace any that fail full criteria.

### 2. Recommendations
- Clear tables with exact bets (Match, Selection, Decimal Odds, Stake NOK, any notes).
- **Hard Min Stake Filter**: <10 NOK skipped entirely. Borderline only exactly 10 NOK if EV still >=+5% post-adjust.
- **Diversification Rule**: Max 2 bets per category/type per round. Every portfolio must include bets from >=2 different sports or distinctly different bet types. Track recent types to avoid repeats without fresh data.
- Immediately append new pending bets (short Notes) to bet_log.csv via nt-bet-log-manager or safe_bet_log_edit.py. Update current_bankroll.md (short note, correct Equity rule) and round file.

### 3. bet_log.csv & Bankroll Handling (Strict - Fixes Past Issues)
- Exact header: Date,Match,Selection,Decimal_Odds,Stake_NOK,Result,P_L_NOK,Notes
- New pending: Append only at bottom, Result="Pending", P_L empty, **short Notes** (result/explanation/lesson <400 chars).
- Settlements: Targeted update ONLY on matching row (Result + P_L_NOK). **Append short** settlement info to Notes. Never delete/overwrite/reduce historical rows.
- **Always use scripts/safe_bet_log_edit.py (local master) or nt-bet-log-manager (GitHub with full SHA workflow)**. Backup + validation mandatory. Proper CSV quoting.
- Bankroll: Equity = 500 + SUM(realized P/L). Adjust ONLY on settlements (+P/L profit Win, -stake Loss). Pending at Risk tracked separately. Liquid = Equity - Pending. Short verification note only. This keeps it always correct.

### 4. Post-Settlement Process
- Trigger post-settlement-learning-reviewer + nt-learning-reviewer skills.
- Deep dive (concise) in round file: result vs pre-bet hyp, key factors, lesson for filters.
- Update edges/filters in sport_edges_and_filters.md (additive, concise).
- Verify/update bankroll (correct rule, short note).
- nt-learning-reviewer: Update tracker in sport_edges_and_filters.md, check promotion (10-12 settled + ROI>+4% + patterns → promote to core).

### 5. Exploration & Balance
- Diversify across sports (football, tennis, darts, snooker, esports, props, new types).
- Exploration bets: Min 10 NOK, small stakes. Automated promotion via nt-learning-reviewer.
- High-Odds (>4.0): Ultra-small stake, deep per-line dive required, max 1 per round. High variance - primarily for learning.
- Try new bet types when edge supports, with strict filters.

## Skill Integration (Active - Use by the Letter)
- nt-betting-workflow: Main orchestrator for research → recs → updates.
- nt-bet-log-manager: All bet_log mutations (full fetch/SHA or local script, append-only/ targeted, short Notes, validate).
- nt-bankroll-tracker: Correct Equity rule, short notes, recalc after changes.
- betting-value-calculator: EV/staking math, tables, min-stake adjust, portfolio.
- post-settlement-learning-reviewer + nt-learning-reviewer: Deep dives, learning, promotion, additive updates.

All changes pushed/verified via full SHA workflow or local safe script before any output. Short Notes mandatory.

## General Rules
- Repo (or local master + script) is single source of truth.
- Additive updates for docs (concise).
- Validate before committing.
- Strict EV after deep research.
- Bankroll discipline (correct rule) and continuous learning from every outcome (especially losses).
- **Short Notes Rule everywhere in bet_log**: Prevents ballooning, truncation to 3 lines, corruption, and GitHub update failures. Historical long Notes safe in Git/archives.

## 2026-07-01 Cleanup Completion
All requested cleanup done: current_bankroll.md fixed to correct Equity rule + lean; nt-betting-skills.md + Betting_Commands.txt updated with Short Notes Rule, skills emphasis, local script fallback; playbook.md now active lean operational doc for future recs. bet_log data + all good recommendations in rounds/ preserved perfectly. GitHub updates now reliable with lean content + safe logic. No data loss. System robust and self-sustaining.

This is the living playbook. Update additively when processes improve. Follow nt-betting-skills.md + this playbook by the letter for all future betting work.