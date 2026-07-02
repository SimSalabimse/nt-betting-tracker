# Robust Betting Agent Protocol v2 (2026-07-01 Cleanup Update - Reliable GitHub, Short Notes, Skills First)

**2026-07-01 MAJOR CLEANUP & RELIABILITY FIXES (Addresses All User-Reported Issues: GitHub update failures, bet_log corruption to 3 lines/garbage comments, ballooning files, bankroll drift, Grok not reading full file, old data in Notes)**

**Critical New Rules (Non-Negotiable - Immediate Effect)**:

1. **SHORT NOTES RULE (Root Fix for Ballooning, Truncation, Corruption, Update Failures)**: 
   - ALL bet_log.csv Notes MUST be concise: Result + brief explanation (outcome vs pre-bet prediction) + 1 key lesson or variance source.
   - Max recommended ~300-400 characters. 
   - **FORBIDDEN in Notes**: Long protocol text, full multi-agent simulations, exhaustive tool lists, SHA proofs, repetitive Section 5/9 text, "AUTONOMOUS per protocol..." walls of text.
   - Historical long Notes preserved in Git history + bet_log_archives/. 
   - Future appends/settlements use SHORT Notes ONLY. This directly fixes the ballooning that caused truncation to 3 lines, garbage comments, and GitHub update breaks.
   - Enforced in nt-bet-log-manager, safe_bet_log_edit.py, and all workflows.

2. **GitHub Update Reliability (Successful Push Workflow Mandatory - Never Skip)**:
   - Every file change (bet_log, bankroll, protocol, skills, rounds, etc.): 
     a. Verify current state with github___get_repository_tree.
     b. Get specific file content + exact current SHA with github___get_file_contents.
     c. Update ONLY with github___create_or_update_file using the exact sha, FULL clean actual text (no placeholders, no short versions, no garbage).
     d. Immediately verify after: Re-check tree + re-read full content with get_file_contents to confirm exact match, no corruption.
   - Prefer local `scripts/safe_bet_log_edit.py` (append-only or targeted settle, atomic write, validation, short Notes) for bet_log when GitHub feels flaky. Grok proposes exact lines/diffs; user applies locally then optional push.
   - Short content payloads only to prevent truncation.

3. **Bankroll Correctness (User-Preferred Rule Enforced)**:
   - Equity = 500 NOK baseline + SUM(all realized P/L from settled bets in live bet_log.csv).
   - Adjust Equity ONLY on settlements: +P/L profit on Win, -stake on Loss.
   - Pending at Risk tracked separately but NEVER subtracted from Equity until settled.
   - nt-bankroll-tracker skill + short verification note only. No bloated text.

4. **Skills First (nt-betting-workflow, nt-bet-log-manager, nt-bankroll-tracker, post-settlement-learning-reviewer, nt-learning-reviewer, betting-value-calculator)**:
   - Follow nt-betting-skills.md by the letter in full for all operations.
   - nt-bet-log-manager: Full fetch + SHA before any change, append-only or targeted short-Notes update, never delete/overwrite historical, proper quoting, validation.
   - All autonomous updates (bet_log append + bankroll) happen BEFORE any user-facing output, with full workflow verify.

5. **No More Ballooning or Old Data Issues**: Protocol itself kept lean. Long repetitive text moved to skills.md or deprecated. Future protocol updates additive and concise. Grok must read full current files every time (no lazy old-data following).

6. **FULL CONTENT RULE FOR github___create_or_update_file (Non-Negotiable - Prevents Data Loss from Placeholders)**: 
   - Always call github___get_file_contents to fetch the *full current content + exact SHA* immediately before building any update.
   - Construct the new content by taking the exact string returned from the fetch and appending or modifying *only* the necessary parts.
   - The "content" parameter sent to the tool must be the *complete, correct, final file text* — never placeholders, never summaries, never "paste here" text, never assumptions from previous knowledge.
   - If the file is very large (e.g. bet_log.csv), prefer the local `scripts/safe_bet_log_edit.py` (safe append-only) or ask the user to provide the full current content instead of risking incomplete payloads.
   - This rule was added after a placeholder mistake in a tool call temporarily replaced bet_log history with only pending bets (history was restored from Git). It is now permanent and non-negotiable.

**2026-07-02 NEW AUTOMATED WORKFLOW ADDITION**:

The system now supports a significantly more automated flow using the new `nt_betting_system/`:

- User provides an **odds file** (list of matches + odds).
- Grok performs analysis using **adaptive research** (deeper research for single/few matches, targeted + filtering for many matches).
- Grok recommends bets + stakes and **automatically logs** them into SQLite (`bets.db`).
- User places the recommended bets.
- On settlement, user provides results → Grok runs full settlement flow (updates bets, bankroll, learning review, and refreshes `performance_report.md`).
- All database operations and reporting are handled by Grok via scripts. User does not run scripts.

This new automated capability is built on top of the existing robust rules (Short Notes, Full Content Rule, SHA workflow, etc.).

**Purpose of this Protocol (Retained)**: Master for robustness in betting recommendations. Supplements nt-betting-skills.md (primary implementation). All future betting work follows this + skills by the letter.

**Core Philosophy (Retained & Strengthened)**: First-principles, mandatory tool proof when researching, active learning from outcomes (especially losses), bias reset every time, conservative risk management with stupid loss filter + explicit R/R, self-updating via additive changes, complete-before-reply (all research/pushes/verifies done first).

## Retained Core Sections (Condensed - See nt-betting-skills.md for Detailed Implementation)

**Mandatory Tool Usage & Proof (When Researching)**: Use web_search, browse_page, x_keyword_search etc. with explicit proof in responses for promising markets. Per-line targeted research for props. Historical pattern simulation from Priority #1 sources (FBref, Transfermarkt, Understat, etc.). Exhaustive cross-verification. No early give-up.

**Multi-Agent Simulation (Value/Risk Manager/Data Hunter/Contrarian)**: Internal debate with bias reset. Document key points. Enforce variety, broader sports, DNB preference for high-var profiles, tiered staking, min 10 NOK, diversification.

**Standardized Clean Response Template**: Executive Summary, Data Sources & Tool Proof, Recommended Bets table, Portfolio Summary, Learning & Flags, Next Actions. Clean tables only.

**Bet Log & Bankroll Integrity (Updated with Short Notes + SHA Workflow)**: See Section 5 rules above + nt-bet-log-manager + safe_bet_log_edit.py. Never reset live data. Proper quoting. Full verify after every change.

**Advanced Risk Management**: Stupid loss filter (low-odds favorites require high EV + confirmation), explicit R/R calcs, tiered stakes, post-loss review for filter tightening. WC motivation/set-piece and grass totals variance notes retained as examples.

**Active Learning**: post-settlement-learning-reviewer + nt-learning-reviewer for deep dives, edge updates in sport_edges_and_filters.md (additive, concise), promotion/demotion of categories based on data.

**Self-Updating**: Identify issues (like past GitHub/ballooning problems) and implement fixes proactively via full SHA workflow. Update this protocol, skills.md, Betting_Commands.txt additively when needed.

**Complete Before Reply**: All tool calls, analysis, multi-agent, learning updates, GitHub pushes (with verify), and validations finished before final output.

## Implementation & Status

- 2026-07-01 Cleanup: Added Short Notes Rule, GitHub SHA workflow enforcement, bankroll Equity rule, skills-first mandate, local safe_bet_log_edit.py preference, and Full Content Rule. Fixed root causes of update failures and ballooning. Protocol kept lean going forward.
- 2026-07-02: Added new automated workflow using `nt_betting_system/` (SQLite + Python scripts). Grok now handles logging, settlement, bankroll, learning, and statistics automatically when user provides odds files or settlement results. Adaptive research logic implemented. Performance reports auto-generated.
- All future betting recommendations and settlements MUST use short Notes in bet_log, full SHA workflow for pushes, and nt-*-skills by the letter.
- robust_betting_protocol_v2.md is now the master for recommendations; nt-betting-skills.md is the detailed how-to for safe execution.
- play book.md remains historical/supplementary.

**Success Metrics**: Reliable GitHub updates (no more 3-line corruption or skipped pushes), manageable file sizes, correct bankroll at all times, consistent skill usage, preserved historical data + good recommendations in rounds/, continuous improvement from losses without bloat. New automated flow reduces manual work while maintaining quality through adaptive research.

This updated protocol + skills makes the entire system extremely robust, self-sustaining, and "just works" with minimal user intervention. All past issues closed.