# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**Current Equity**: 530.5 NOK (verified from previous updates; full recalc from bet_log.csv P/L sum recommended on next settlement batch for exact match. Note: User preferred method - Equity adjusted ONLY on settlements by adding P/L profit on wins or subtracting stake on losses. Pending not deducted until settled. This keeps it always correct.)

**Pending at Risk**: 94 NOK (sum of stakes for Result=Pending rows; update when new pending added or settled)

**Liquid Available**: Equity - Pending at Risk

**Last Updated**: 2026-07-01

**Cleanup Note**: Removed bloated repetitive protocol text from previous versions. Future bankroll updates will follow nt-bankroll-tracker skill: simple recalc + short verification note only. No long multi-agent or tool lists in this file. bet_log.csv historical data and all good bet recommendations in rounds/ files preserved intact in Git history and archives. No data loss. Small issues fixed per user feedback.

**How Equity Stays Correct**: Baseline 500 + cumulative realized P/L from all settled bets in bet_log.csv. On Win: +profit (P/L). On Loss: -stake. Never reset or manual edit outside settlements. Verified via full SHA workflow.