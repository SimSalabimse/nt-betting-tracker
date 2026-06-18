# NT Betting Tracker Playbook

**Project Goal**: Systematic, high-EV sports betting with strict bankroll management, deep research, and reliable data tracking. Focus on value, discipline, and long-term edge.

## File Structure (Current Clean State)

- **Root level**:
  - `bet_log.csv` — Master log of all bets (pending + settled). **Never edit directly** — always use the safe script.
  - `bet_log_archive_up_to_2026-06-11.csv` — Historical archive.
  - `current_bankroll.md` — Current equity, pending risk, liquid available.
  - `sport_edges_and_filters.md` — Evolving edges, filters, and learnings.
  - `analyze_betting.py` — Analysis and backtesting script.
  - `README.md`, `grok_skill_integration.md`, `nt-betting-skills.md`

- **`rounds/` folder** (primary location for all round-related files):
  - All detailed round files, full research notes, recommendations, and processed analysis are now consolidated here.
  - Root-level `round_*.md` files have been moved into this folder for cleanliness (duplicates consolidated where they existed).

- **`scripts/`**:
  - `safe_bet_log_edit.py` — The single authoritative tool for all bet_log.csv modifications.
  - `analyze_betting.py` (symlink or copy at root for convenience if needed).

**Note**: The structure has been cleaned up. All round files are now in `rounds/`. Existing Notes references in bet_log.csv have been preserved by keeping historical file names consistent.

## Core Betting Workflow

### 1. Research Depth & Breadth (Mandatory)
- **Stage 1 (Rough EV Scan)**: Scan **every single line** in the provided odds file. Flag all lines meeting rough EV threshold (min 7-8%+ depending on sport).
- **Stage 2 (Deep Research Phase)**: 
  - Do **not** limit to 1-2 matches.
  - Research **every good edge opportunity** thoroughly using tools (web_search, browse_page, x_keyword_search, etc.).
  - Required data points: Recent form (last 5-10 matches), H2H, xG/underlying metrics, injuries/suspensions/team news, motivation (must-win, derby, rest), pace/defensive strength, specific bet-type stats (BTTS, Over/Under, handicap margins), weather/venue if relevant.
  - Only after thorough multi-candidate research do you prioritize and select the best ones.
- Goal: High-quality, evidence-based recommendations across a broad set of edges. Replace any match that fails criteria after full research.

### 2. Recommendations
- Use clear tables with **exact** bets (stake, odds, selection). No vague "third option".
- Immediately append new pending bets to bet_log.csv (no confirmation step — user will flag changes if needed).

### 3. bet_log.csv Handling (Strict Rules)
- Exact header: Date,Match,Selection,Decimal_Odds,Stake_NOK,Result,P_L_NOK,Notes
- New pending bets: Append **only at the bottom**, Result="Pending", P_L_NOK empty.
- Settlements: Targeted update only on the matching row (Result + P_L_NOK). **Append** settlement info to existing Notes. Never overwrite/delete historical rows.
- Always use `scripts/safe_bet_log_edit.py` for any change.
- Mandatory backup + validation before/after every edit.
- Never reduce row count without explicit confirmation.

### 4. Post-Settlement Process
- After settlements reported: Run deep dive review on the round.
- Update edges/filters in sport_edges_and_filters.md when patterns emerge.
- Verify bankroll (see below).
- Use older round files for learning when sufficient data exists.

### 5. Bankroll Management
- Formulas: Equity = 500 + SUM(realized P/L), Pending at Risk, Liquid Available = Equity - Pending at Risk.
- Mandatory verification checklist after every settlement before updating current_bankroll.md.
- Strict discipline on staking.

### 6. Exploration & Balance
- Diversify across sports (football, tennis, darts, snooker, etc.).
- Avoid over-weighting any single sport.
- Try new bet types/odds formats when edge supports it.

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

Use them for consistent rule enforcement.

## General Rules
- Repo is single source of truth.
- Additive updates for documentation.
- Validate before committing.
- Strict EV filter after deep research.
- Bankroll discipline and continuous learning.

This is the living playbook. Update additively when processes improve.