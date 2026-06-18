# Grok Skill Integration

## Updated Workflow (2026-06-18) - Option A Active

When the user places bets (or confirms Grok's proposed bets):

1. Grok **directly updates** the GitHub copies of:
   - `bet_log.csv` (appends pending rows after fetching full current content + SHA)
   - `current_bankroll.md` (updates pending risk and liquid available)
   - Relevant round file (records what was actually placed)

2. All updates are pushed in one go and validated before the final reply to the user.

3. The local `safe_bet_log_edit.py` is still available as a fallback/manual tool, but it is no longer required for routine bet adding.

This makes the system more decisive and reduces back-and-forth.

Previous overly cautious behavior (asking user to run local scripts every time) is deprecated.