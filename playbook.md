# NT Betting Tracker Playbook

**⚠️ CLEAN RESTART 2026-06-28 NOTE (HIGHEST PRIORITY)**: 
**robust_betting_protocol_v2.md is now the MASTER protocol for ALL betting-related work.** 
Follow it by the letter in full — no skipping, no shortcuts. This playbook is historical/supplementary reference only. Do not follow playbook.md for current operations (per explicit user instruction in clean restart process). All rules, workflows, autonomous mode, per-sport checklists, variety enforcement, tiered staking/DNB, per-line research, doubles logic, force commands, and data integrity are in robust_betting_protocol_v2.md Sections 1-10 + 2026-06-28 additive. 

**Current Clean State (2026-06-28)**:
- Root: Active files only (bet_log.csv = header-only for fresh start, current_bankroll.md = 500 NOK baseline, robust_betting_protocol_v2.md, README.md, nt-*.md files, Betting_Commands.txt with force commands, sport_edges_and_filters.md, meta_review_log.md).
- `rounds/`: All round analysis/recommendation files.
- `bet_log_archives/`: All historical bet_log archives + full pre-clean-restart snapshots of bet_log.csv and current_bankroll.md.
- `scripts/`: Automation.

All previous structure references updated. Autonomous mode active (bet_log/bankroll updates before any output). Master Protocol followed exactly.

---

**Project Goal**: Systematic, high-EV sports betting with strict bankroll management, deep research, and reliable data tracking. Focus on value, discipline, and long-term edge.

## File Structure (Current Clean State)

- **Root level**:
  - `bet_log.csv` — Master log of all bets (pending + settled). **Never edit directly** — always use the safe script or nt-bet-log-manager skill (autonomous updates enforced).
  - `current_bankroll.md` — Current equity, pending risk, liquid available (reset to 500 NOK clean baseline 2026-06-28).
  - `sport_edges_and_filters.md` — Evolving edges, filters, and learnings.
  - `README.md`, `grok_skill_integration.md`, `nt-betting-skills.md`, `robust_betting_protocol_v2.md` (MASTER)

- **`rounds/` folder** (primary location for all round-related files):
  - All detailed round files, full research notes, recommendations, and processed analysis are now consolidated here.

- **`bet_log_archives/`**:
  - All historical bet_log archives + clean restart snapshots.

- **`scripts/`**:
  - `safe_bet_log_edit.py` — The single authoritative tool for all bet_log.csv modifications.

**Note**: The structure has been cleaned up for 2026-06-28 clean restart. All round files in `rounds/`. All bet_log archives in `bet_log_archives/`. bet_log.csv trimmed to header for fresh start. current_bankroll.md reset to 500 NOK. Autonomous mode active.

## Core Betting Workflow

### 1. Research Depth & Breadth (Mandatory)
- **Stage 1 (Rough EV Scan)**: Scan **every single line** in the provided odds file. Flag all lines meeting rough EV threshold (min 7-8%+ depending on sport).
- **Stage 2 (Deep Research Phase)**: 
  - Do **not** limit to 1-2 matches.
  - Research **every good edge opportunity** thoroughly using tools (web_search, browse_page, x_keyword_search, etc.).
  - Required data points: Recent form (last 5-10 matches), H2H, xG/underlying metrics, injuries/suspensions/team news, motivation (must-win, derby, rest), pace/defensive strength, specific bet-type stats (BTTS, Over/Under, handicap margins), weather/venue if relevant.
  - Only after thorough multi-candidate research do you prioritize and select the best ones.
- Goal: High-quality, evidence-based recommendations across a broad set of edges. Replace any match that fails criteria after full research.

### 2. Recommendations (Updated 2026-06-20 with Diversification & Min Stake)
- Use clear tables with **exact** bets (stake, odds, selection). No vague "third option".
- **Hard Min Stake Filter**: Calculated stake <10 NOK is skipped entirely (user hard limit). If borderline, only recommend exactly 10 NOK if post-adjust EV still >= +5%. All future proposals enforce this before any bet is added to log.
- **Diversification Rule (fixes repeat same bets issue)**: 
  - Max **2 bets per bet category/type** per round (e.g. no more than 2 Over 2.5, 2 BTTS, 2 Game HC, 2 ML fav in one portfolio).
  - Every portfolio **must include bets from at least 2 different sports or distinctly different bet types** (e.g. one football BTTS + one tennis game HC).
  - Track recent bet types from last 2-3 rounds in round file notes; avoid repeating the exact same edge profile (same odds band + same selection type) on multiple matches without fresh differentiating data.
  - This addresses the statistical improbability of identical edge/odds profiles across unrelated matches occurring repeatedly. Enforced in nt-betting-workflow before final selection.
- Immediately append new pending bets to bet_log.csv (no confirmation step — user will flag changes if needed).

### 3. bet_log.csv Handling (Strict Rules)
- Exact header: Date,Match,Selection,Decimal_Odds,Stake_NOK,Result,P_L_NOK,Notes
- New pending bets: Append **only at the bottom**, Result="Pending", P_L_NOK empty.
- Settlements: Targeted update only on the matching row (Result + P_L_NOK). **Append** settlement info to existing Notes. Never overwrite/delete historical rows.
- Always use `scripts/safe_bet_log_edit.py` for any change.
- Mandatory backup + validation before/after every edit.
- Never reduce row count without explicit confirmation.

### 4. Post-Settlement Process (Enhanced with nt-learning-reviewer)
- After settlements reported: Run deep dive review on the round using **post-settlement-learning-reviewer skill**.
- **nt-learning-reviewer skill** automatically updates exploration tracker in sport_edges_and_filters.md, checks promotion criteria, and flags categories ready for standard treatment.
- Update edges/filters in sport_edges_and_filters.md when patterns emerge (additive).
- Verify bankroll (see below).
- Use older round files for learning when sufficient data exists.

### 5. Bankroll Management
- Formulas: Equity = 500 + SUM(realized P/L), Pending at Risk, Liquid Available = Equity - Pending at Risk.
- Mandatory verification checklist after every settlement before updating current_bankroll.md.
- Strict discipline on staking.

### 6. Exploration & Balance (Updated 2026-06-20)
- Diversify across sports (football, tennis, darts, snooker, esports, new props).
- Avoid over-weighting any single sport or bet type (enforced by diversification rule above).
- **Exploration bets**: Use small stakes (min 10 NOK). New automated promotion logic via nt-learning-reviewer (see sport_edges_and_filters.md for criteria: 10-12 settled + ROI>4% + patterns).
- **High-Odds (>4.0) bets**: New dedicated guidelines in sport_edges_and_filters.md. Ultra-small stake only, deep dive on specific odds line required, max 1 per round. High variance observed - use for learning/data collection primarily.
- Try new bet types/odds formats when edge supports it, but with strict filters.

## 2026-06-18 Safe bet_log.csv Editor Script

**Purpose**  
`scripts/safe_bet_log_edit.py` is the single authoritative tool for all modifications to `bet_log.csv`. This prevents truncation, row deletion, and quoting corruption.

**Location**  
`scripts/safe_bet_log_edit.py`

**Key Features & Rules Enforced**
- Exact header enforcement.
- Append-only for new pending bets (at bottom, Result=Pending, P_L empty).
- Targeted settlement updates only (modify Result + P_L_NOK and **append** to Notes — never overwrite or delete historical rows).
- Pre- and post-edit row count validation.
- Automatic timestamped backups before every write.
- Atomic writes using tempfile.
- Proper csv module with QUOTE_MINIMAL.
- Standalone validation command.

**Usage**
```bash
python scripts/safe_bet_log_edit.py validate bet_log.csv
python scripts/safe_bet_log_edit.py add-pending bet_log.csv "DATE,Match,Selection,Odds,Stake,Pending,,Notes"
python scripts/safe_bet_log_edit.py settle bet_log.csv "DATE,Match,Selection" "Win" "150.00"
```

**Integration**
All changes must go through this script (via nt-bet-log-manager skill or manually). Re-validate and run bankroll verification after edits.

**Best Practices**
- Always pull latest bet_log.csv first.
- Never edit directly with string methods.
- Keep historical rows untouched except for precise settlement updates.

## Skill Integration

Persistent skills available:
- `nt-betting-workflow` (main orchestrator)
- `betting-value-calculator`
- `nt-bankroll-tracker`
- `nt-bet-log-manager`
- `post-settlement-learning-reviewer` (new: handles deep dive after settlements, triggers nt-learning-reviewer)
- `nt-learning-reviewer` (new: maintains data sufficiency tracker, auto promotion of exploration categories, updates sport_edges_and_filters.md)

Use them for consistent rule enforcement. See nt-betting-skills.md for full definitions of new reviewer skills.

## General Rules
- Repo is single source of truth.
- Additive updates for documentation.
- Validate before committing.
- Strict EV filter after deep research.
- Bankroll discipline and continuous learning.
- **2026-06-20**: All recommendations now pass through diversification check, min-stake filter, and exploration status check before proposal.

## 2026-06-19 Role Update: Grok Autonomous Decision Maker

**Updated Authority Structure**:
- **Grok (AI) Role**: Makes **ALL** decisions autonomously. Performs research, EV analysis, bet selection, stake sizing, portfolio construction, and risk management. Provides ready-to-place bet instructions immediately.
- **User Role**: You are here **only to place the bets**. Receive clear instructions (exact Match, Selection, Decimal Odds, Stake in NOK, any special notes) and execute them on your betting platform (e.g. Norsk Tipping). Report back results or settlements. No research or decision-making required from you.

## 2026-06-20 Post-Settlement Learning Review Summary
- With 98 bets data: Core football stable; exploration needs tighter filters/automation (implemented); repeat bet types fixed via diversification rule; min 10 NOK enforced; high-odds >4 treated as ultra-exploratory with deep dive requirement.
- Changes pushed to sport_edges_and_filters.md and this playbook. nt-learning-reviewer and post-settlement-learning-reviewer skills now active in workflow.

## 2026-06-21 Robust Protocol v2 Integration

**Major Update**: Created and integrated `robust_betting_protocol_v2.md` as the master robustness layer. This protocol addresses all feedback points in detail (mandatory tool proof with explicit evidence in every response, active/automated learning from every outcome especially losses, bias reset + first-principles + multi-agent internal simulation for fresh evaluations and broader markets, standardized clean response template with bets table, bet log archiving protocol when file grows large, advanced risk management with stupid loss filter and explicit risk/reward calculations, skill reliability with exact references and pre-checks, self-updating proactive improvements, complete-before-reply discipline).

**How to Use**: All future workflows, nt-betting-workflow skill executions, round file updates, and user responses must align with robust_betting_protocol_v2.md by the letter in full. It takes precedence for addressing gaps and making the system "just work" with minimal corrections. Existing playbook rules (diversification, min stake, exploration automation, post-settlement processes, autonomous decisions) are foundational and now strengthened by the v2 protocol.

See robust_betting_protocol_v2.md for the complete detailed implementation. This update was performed following the Successful Push Workflow exactly: tree verified, full current content + SHA fetched, full new content provided (old + additive section), clear commit message, post-push verification planned.

## Data Pipeline & Risk Architecture (Integrated from Comprehensive Norsk Tipping Research - June 2026)

**Purpose**: Directly addresses the core problems identified in prior project iterations (inconsistent data gathering, insufficient historical depth, poor edge estimation, variance mismanagement, overexposure). This section incorporates the full recommended strategy from detailed analysis of Norsk Tipping offerings, odds types, and best data sources. It is designed for implementation in the GitHub repo to make the system robust, self-sustaining, and production-ready.

### Core Strategy for Data Pipeline (Build/Robustify)

**ETL Pipeline**:
- Scheduled scraping (or APIs where available) for NT odds (current + historical archive via repeated crawls of oddsen + event pages) + results.
- Use Playwright or undetected Selenium with stealth/rotating residential proxies, header randomization, and retry logic. Monitor with logging/alerts.
- Fallback to secondary sources (e.g., OddsPortal for historical).

**Storage**:
- PostgreSQL (or TimescaleDB/DuckDB for time-series) with tables for events, odds history (timestamped decimal odds + implied probs), results, and features.
- JSONB for flexible market structures (handles varying odds types per sport).

**Feature Engineering**:
- Per-sport modules: ELO/TrueSkill ratings, xG models for soccer, usage/matchup features for props, rest/travel/fatigue, head-to-head, form streaks.
- Build sport-specific feature extractors (e.g., player xG/xA for props, map-level for esports).

**Modeling & Value Detection**:
- For each sport/market: Estimate true probability → compare to NT implied prob for +EV.
- Statistical baselines: Poisson/Negative Binomial for totals/scores; Bradley-Terry or logistic for winners.
- ML ensembles: XGBoost/LightGBM with careful time-series CV (avoid leakage).
- Rigorous backtesting: walk-forward, out-of-sample.
- Live & Odds Tracking: Poll or WebSocket for live scores/odds; archive NT lines frequently (they can be slow to move vs. sharp books).

**Risk Assessment Module** (Critical for fixing variance/overexposure issues):
- **EV Calculation**: EV = (p_model × decimal_odds) - 1.
- **Stake Sizing**: Kelly Criterion (f = edge / odds; use fractional Kelly 0.25–0.5 for safety) or fixed % of bankroll scaled by edge/confidence.
- **Portfolio Risk**: Monte Carlo simulations for drawdown/ruin probability and multi-bet portfolio (account for correlations, e.g., same-league matches).
- **Tracking & Analytics**: Log every bet (sport, market type, EV, stake, result, actual vs. expected). Analyze ROI, Sharpe-like metrics, variance per sport/market type.
- Set rules: max exposure per sport/market, stop after drawdowns, periodic reviews.
- Bankroll sims: Stress-test with historical variance.

**Tech Stack Recommendations**:
- Python (pandas, scikit-learn, statsmodels, requests/Playwright, SQLAlchemy).
- Docker for reproducibility.
- GitHub Actions or Prefect/Airflow for orchestration.
- Streamlit/Dash for monitoring dashboard.
- Version models and features.

**Edge Sources**:
- Compare NT odds to sharp lines (Pinnacle, Betfair SP) or closing odds for “market efficiency” signals.
- NT margins are higher (~7–8%+ implied), so value often in mispricings on less liquid markets or Norwegian-relevant events.

**Practical Tips**:
- Start narrow (e.g., focus on football 1X2 + over/under + key props; or esports maps).
- Paper trade or small stakes while validating.
- Factor NT limits (e.g., monthly loss caps).
- Responsible play: Set strict personal limits.

**Why this fixes prior issues**:
- Better data completeness/reliability reduces model error.
- Explicit risk sims (Monte Carlo, per-type variance tracking) prevent ruin from variance.
- Per-sport specialization exploits where edge exists.
- Directly supports the advanced edge calculation methods already in nt_sports_data_sources.md (xG props, bivariate Poisson, Monte Carlo for combos).

**Implementation Priority**:
- Extend scripts/analyze_betting.py and betting-value-calculator skill with Risk Assessment Module functions.
- Add ETL orchestration to nt-betting-workflow skill.
- Update nt_sports_data_sources.md references if new sources emerge.
- Track per-odds-type performance in bet_log analysis for continuous improvement.

**Implementation Status**: This section was added following the Successful Push Workflow exactly (tree verified, current SHA fetched, additive update with full content, clear message). It makes the entire system significantly more robust for data gathering and risk assessment.

**Next Actions**
- Implement pipeline components incrementally in scripts/.
- Validate with historical data.
- Continue using robust_betting_protocol_v2.md for all betting work.

This is the living playbook. Update additively when processes improve.

---
**CLEAN RESTART 2026-06-28 COMPLETION NOTE (ADDITIVE)**: 
All clean restart actions completed: bet_log.csv archived full then trimmed to header-only; current_bankroll.md archived then reset to 500 NOK baseline; all remaining root bet_log_archive_*.csv and backups moved to bet_log_archives/ and root versions deleted; robust_betting_protocol_v2.md, Betting_Commands.txt, README.md, nt_sports_data_sources.md updated with autonomous mode, per-sport checklists (soccer lineups/motivation/H2H/form/weather/ref/VAR/xG/historical priority + other sports), force commands, variety enforcement, tiered staking/DNB, per-line research, doubles logic. Multiple Successful Push Workflow verifies passed. Root perfectly clean. Autonomous mode active (bet_log/bankroll updates before any output). Master Protocol followed by the letter in full. System maximally robust and self-sustaining.