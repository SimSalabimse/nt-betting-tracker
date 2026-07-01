# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**Current Equity**: 530.5 NOK (verified from previous updates; full recalc from bet_log.csv P/L sum recommended on next settlement batch for exact match. Note: User preferred method - Equity adjusted ONLY on settlements by adding P/L profit on wins or subtracting stake on losses. Pending not deducted until settled. This keeps it always correct.)

**Pending at Risk**: 82 NOK (sum of stakes for Result=Pending rows; update when new pending added or settled. New pending 2026-07-01: England WC R32 Kane scorer 15 + BTTS No 12 + Over corners 10 + HJK Ilves DNB 15 + Eskilsminne Draw 12 + Denmark U19 Spain -1 18 = 82 NOK total.)

**Liquid Available**: Equity - Pending at Risk

**Last Updated**: 2026-07-01

**Cleanup Note**: Removed bloated repetitive protocol text. Future updates follow nt-bankroll-tracker skill: simple recalc + short verification note only. bet_log.csv updated with short Notes pending rows via full SHA workflow. All good bet recommendations in rounds/ preserved. No data loss. Protocol/skills fixes (Short Notes Rule, SHA workflow, skills-first, no text-only claims) confirmed pushed and active.

**How Equity Stays Correct**: Baseline 500 + cumulative realized P/L from all settled bets in bet_log.csv. On Win: +profit (P/L). On Loss: -stake. Never reset or manual edit outside settlements. Verified via full SHA workflow.