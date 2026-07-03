# Robust Betting Agent Protocol v2 (2026-07-01 Cleanup Update - Reliable GitHub, Short Notes, Skills First)

**2026-07-01 MAJOR CLEANUP & RELIABILITY FIXES (Addresses All User-Reported Issues: GitHub update failures, bet_log corruption to 3 lines/garbage comments, ballooning files, bankroll drift, Grok not reading full file, old data in Notes)**

**Critical New Rules (Non-Negotiable - Immediate Effect)**:

1. **GitHub Update Reliability (Successful Push Workflow Mandatory - Never Skip)**:
   - Every file change (bet_log, bankroll, protocol, skills, rounds, etc.): 
     a. Verify current state with github___get_repository_tree.
     b. Get specific file content + exact current SHA with github___get_file_contents.
     c. Update ONLY with github___create_or_update_file using the exact sha, FULL clean actual text (no placeholders, no short versions, no garbage).
     d. Immediately verify after: Re-check tree + re-read full content with get_file_contents to confirm exact match, no corruption.
   - Prefer local `scripts/safe_bet_log_edit.py` (append-only or targeted settle, atomic write, validation, short Notes) for bet_log when GitHub feels flaky. Grok proposes exact lines/diffs; user applies locally then optional push.
   - Short content payloads only to prevent truncation.

2. **Bankroll Correctness (User-Preferred Rule Enforced + 2026-07-03 NO AUTO-RESET + FULL ARCHIVE DATA UPDATE)**:
   - Equity = locked baseline (see current_bankroll.md for exact current locked value + full IMPORTANT NO AUTO-RESET RULE + FULL DATA RULE) + SUM(all realized P/L from settled bets in live bet_log.csv + relevant bet_log_archives/*.csv files since clean restart, deduped to avoid overlap).
   - The entire round/history MUST include P/L from bet_log_archives/bankroll_archive_up_to_2026_07_01.csv (and similar archives) + live bet_log.csv. Previous only-live calc (516.22) was incomplete/wrong. Full combined verified sum used for accurate Equity (e.g. 530.22 NOK reflecting full data + recent 4 wins/2 big).
   - Adjust Equity ONLY on settlements: +P/L profit on Win, -stake on Loss. NEVER reset Equity or baseline to 500 (or re-anchor) unless user EXPLICITLY requests "reset baseline", "adjust baseline for deposit/withdrawal", or "lock in profits as new baseline".
   - Pending at Risk tracked separately but NEVER subtracted from Equity until settled.
   - nt-bankroll-tracker skill + short verification note only. No bloated text. Baseline locked per user instruction to prevent any future unwanted reset to 500 without consent. Full archive inclusion mandatory for correct Equity.

3. **Skills First (nt-betting-workflow, nt-bet-log-manager, nt-bankroll-tracker, post-settlement-learning-reviewer, nt-learning-reviewer, betting-value-calculator)**:
   - Follow nt-betting-skills.md by the letter in full for all operations.
   - nt-bet-log-manager: Full fetch + SHA before any change, append-only or targeted short-Notes update, never delete/overwrite historical, proper quoting, validation.
   - All autonomous updates (bet_log append + bankroll) happen BEFORE any user-facing output, with full workflow verify.

4. **FULL CONTENT RULE FOR github___create_or_update_file (Non-Negotiable - Prevents Data Loss from Placeholders)**: 
   - Always call github___get_file_contents to fetch the *full current content + exact SHA* immediately before building any update.
   - Construct the new content by taking the exact string returned from the fetch and appending or modifying *only* the necessary parts.
   - The "content" parameter sent to the tool must be the *complete, correct, final file text* — never placeholders, never summaries, never "paste here" text, never assumptions from previous knowledge.
   - If the file is very large (e.g. bet_log.csv or archives), prefer the local `scripts/safe_bet_log_edit.py` (safe append-only) or ask the user to provide the full current content instead of risking incomplete payloads.
   - This rule was added after a placeholder mistake in a tool call temporarily replaced bet_log history with only pending bets (history was restored from Git). It is now permanent and non-negotiable.

**Notes Column in bet_log.csv - DEPRECATED (2026-07-03)**

The Notes column in `bet_log.csv` has been removed per user request.
- All future logging will **not** include notes in the main bet_log file.
- Learning records, variance analysis, reasoning, and post-settlement reviews will now be stored in **round files** instead.
- Historical notes in existing rows have been cleaned (set to empty).

**Post-Settlement Learning Requirements (Strengthened)**:

After every settlement batch, the following is mandatory:
- Trigger full `post-settlement-learning-reviewer` + `nt-learning-reviewer`.
- Perform actual tool searches (web_search, browse_page, etc.) to investigate why bets won or lost, especially losses.
- Conduct a structured deep dive (not generic text).
- Identify clear patterns or variance sources.
- Record learning in the relevant **round file** (not in bet_log.csv).
- Update `sport_edges_and_filters.md` additively if meaningful patterns are found.
- Actually update `bet_log.csv` (without notes) and verify the update succeeded.
- Update `current_bankroll.md` correctly (full archive + live P/L).
- Provide a clean summary including batch performance, key lessons, and any edge updates made.

This is non-negotiable.

**Analyze Correctly Going Forward - Standing Rule (2026-07-03)**:

When analyzing odds files, the following is now strictly enforced:
- Use adaptive research mode properly: Strong filtering first, **then targeted deep research** on the shortlist (not just generic filtering).
- Aim for balanced volume: Typically 4–8 quality bets from a mixed file (avoid both under-betting like only 2 bets and over-betting low-quality lines).
- Always perform proper multi-perspective simulation + tool proof on shortlisted bets.
- Execute nt-bet-log-manager and nt-bankroll-tracker **last**, with full SHA workflow verification.
- Never leave bet_log.csv or current_bankroll.md unupdated when bets are recommended.

**Long-Term Staking Plan**

The long-term staking, risk management, and progression strategy is defined in the separate file:

**`long_term_staking_plan.md`**

**2026-07-02 NEW AUTOMATED WORKFLOW ADDITION**:

The system now supports a significantly more automated flow using the new `nt_betting_system/`:

- User provides an **odds file** (list of matches + odds).
- Grok performs analysis using **adaptive research** (deeper research for single/few matches, targeted + filtering for many matches).
- Grok recommends bets + stakes and logs them into `bet_log.csv`.
- User places the recommended bets.
- On settlement, user provides results → Grok must run proper post-settlement learning, record in round file, update files correctly (full data), and verify updates.

**Purpose of this Protocol (Retained)**: Master for robustness in betting recommendations. Supplements nt-betting-skills.md (primary implementation). All future betting work follows this + skills by the letter.

**Core Philosophy (Retained & Strengthened)**: First-principles, mandatory tool proof when researching, active learning from outcomes (especially losses), bias reset every time, conservative risk management with stupid loss filter + explicit R/R, self-updating via additive changes, complete-before-reply (all research/pushes/verifies done first).

## Retained Core Sections (Condensed - See nt-betting-skills.md for Detailed Implementation)

**Mandatory Tool Usage & Proof (When Researching)**: Use web_search, browse_page, x_keyword_search etc. with explicit proof in responses for promising markets. Per-line targeted research for props. Historical pattern simulation from Priority #1 sources (FBref, Transfermarkt, Understat, etc.). Exhaustive cross-verification. No early give-up.

**Multi-Agent Simulation (Value/Risk Manager/Data Hunter/Contrarian)**: Internal debate with bias reset. Document key points. Enforce variety, broader sports, DNB preference for high-var profiles, tiered staking, min 10 NOK, diversification.

**Standardized Clean Response Template**: Executive Summary, Data Sources & Tool Proof, Recommended Bets table, Portfolio Summary, Learning & Flags, Next Actions. Clean tables only.

**Bet Log & Bankroll Integrity**: See Section 5 rules above + nt-bet-log-manager + safe_bet_log_edit.py. Never reset live data. Proper quoting. Full verify after every change. Notes column removed (learning now in round files). Equity calc always includes relevant archives + live.

**Advanced Risk Management**: Stupid loss filter (low-odds favorites require high EV + confirmation), explicit R/R calcs, tiered stakes, post-loss review for filter tightening.

**Active Learning**: post-settlement-learning-reviewer + nt-learning-reviewer for deep dives with mandatory tool searches. Learning recorded in round files. Edge updates in sport_edges_and_filters.md (additive).

**Self-Updating**: Identify issues and implement fixes proactively via full SHA workflow.

**Complete Before Reply**: All tool calls, analysis, multi-agent, learning updates, GitHub pushes (with verify), and validations finished before final output.

## Implementation & Status

- 2026-07-01 Cleanup: Added GitHub SHA workflow enforcement, bankroll Equity rule, skills-first mandate, local safe_bet_log_edit.py preference, and Full Content Rule.
- 2026-07-02: Strengthened post-settlement requirements.
- 2026-07-03: 
  - Removed Notes column from `bet_log.csv` entirely (historical notes cleaned).
  - Learning records now stored in round files instead of bet_log.csv.
  - Added standing rule "Analyze Correctly Going Forward" to prevent overly conservative or shallow analysis.
  - Updated protocol to reference `long_term_staking_plan.md`.
  - Added explicit NO AUTO-RESET RULE for baseline/Equity to current_bankroll.md, skills, and this protocol per user request (prevents reset to 500 without explicit consent).
  - Added FULL ARCHIVE DATA RULE for Equity calc (must include bet_log_archives/ files like bankroll_archive_up_to_2026_07_01.csv + live bet_log.csv) to fix incomplete only-live calc (516.22 was wrong; correct 530.22 with full round data).
- All future betting recommendations and settlements MUST follow the new rules (no notes in bet_log, learning in round files, balanced analysis, locked baseline with explicit-only adjustment, full archive + live for Equity).
- robust_betting_protocol_v2.md is the master for recommendations; nt-betting-skills.md is the detailed how-to.
- `long_term_staking_plan.md` defines long-term staking progression.

**Success Metrics**: Reliable GitHub updates, correct file structure, proper analysis volume and depth, correct and verified file updates, consistent skill usage, and meaningful learning from losses (recorded in round files).

This updated protocol makes the system more robust and aligned with user preferences.