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