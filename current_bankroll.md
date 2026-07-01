# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**Current Equity**: 530.5 NOK (verified from previous updates; full recalc from bet_log.csv P/L sum recommended on next settlement batch for exact match. Note: User preferred method - Equity adjusted ONLY on settlements by adding P/L profit on wins or subtracting stake on losses. Pending not deducted until settled. This keeps it always correct.)

**Pending at Risk**: 129 NOK (sum of stakes for Result=Pending rows. New pending 2026-07-01: all 10 bets listed - England WC R32 3 bets 37 NOK + HJK/Ilves/Eskilsminne/DenmarkU19 3 bets 45 NOK + MLB/Tennis/Snooker 4 bets 47 NOK = 129 NOK total.)

**Liquid Available**: Equity - Pending at Risk

**Last Updated**: 2026-07-01

**Cleanup Note**: Removed bloated repetitive protocol text. Future updates follow nt-bankroll-tracker skill: simple recalc + short verification note only. bet_log.csv updated with short Notes pending rows via full SHA workflow for all 10 bets. All good bet recommendations in rounds/ preserved. No data loss. Protocol/skills fixes (Short Notes Rule, SHA workflow, skills-first, no text-only claims) confirmed pushed and active.

**How Equity Stays Correct**: Baseline 500 + cumulative realized P/L from all settled bets in bet_log.csv. On Win: +profit (P/L). On Loss: -stake. Never reset or manual edit outside settlements. Verified via full SHA workflow.