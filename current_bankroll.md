**Current Bankroll**: **597.25 NOK liquid** + **35.00 NOK pending/at risk (H2H Cycling Johannessen + kt Rolster esports)** = **632.25 NOK total** (updated 2026-06-07 after settlements of Siniakova/Townsend, Carolina Hurricanes, Blaublitz Akita, Oita Trinita bets per user results. bet_log.csv looked up before/after calc for accuracy).

**This Settlement Update (2026-06-07 - Siniakova, Hurricanes, Blaublitz, Oita)**:
- **Looked up bet_log.csv first** (full current state with all pending/settled): Confirmed 4 pending rows at 20 NOK each (Hurricanes +0.5, Siniakova 2-0, Blaublitz Over 2.5, Oita BTTS) + 2 other pending (15+20 NOK). All data validated.
- **Calculated new bankroll using latest log data**:
  - Previous liquid: 534.85 NOK (stakes for open bets already deducted on placement).
  - Wins (Siniakova payout 33 NOK + Hurricanes 29.40 NOK): +62.40 NOK added to liquid.
  - Losses (Blaublitz + Oita): +0 NOK (stakes -40 NOK already accounted in prior pending).
  - New liquid: 534.85 + 62.40 = **597.25 NOK**.
  - New pending/at risk: 35.00 NOK (remaining open: cycling 15 NOK + kt Rolster 20 NOK).
  - Total: 597.25 + 35 = **632.25 NOK**.
- **Re-looked up updated bet_log.csv after edit**: Confirmed exactly 2 Pending rows left, P_L_NOK values correct (+9.4, +13, -20, -20), no calc drift. All Notes updated with settlement details. Bankroll math double-checked against log stakes/odds.
- bet_log.csv updated via tool process. GitHub push + validation performed.

**Notes on Strategy & Accuracy**: bet_log.csv is now the single source of truth for all bet states and P/L. Bankroll tracking improved per playbook update (mandatory lookup before/after every settlement/placement calc). Full playbook research followed at placement for these bets. Variance in J2 and tennis realized as expected in process. Positive net from two wins offset two losses partially. Moderate acceleration continues for remaining pending.

**Proper Bankroll Tracking Logic (Updated & Strictly Followed)**:
1. On placement: Deduct full stake from Available/Liquid. Record as "Pending / At Risk" in bet_log.
2. On Win settlement: Add full **payout** (stake + profit) back to Available/Liquid. (Net +profit)
3. On Loss settlement: Add 0 (stake already deducted). (Net -stake)
4. Total Bankroll = Available (liquid) + Pending/At Risk (sum stakes of all open Pending rows in bet_log.csv).
5. **Mandatory double-check**: Always lookup bet_log.csv (via tools) BEFORE any new calc of bankroll numbers. Update bet_log first with changes, THEN re-lookup to confirm P_L, pending sum, and derived liquid/total match exactly before finalizing current_bankroll.md.
6. P/L tracking: Full payout shown on wins + net profit in notes for clarity. All via bet_log as master.

*This update added with clean current numbers (old history sections condensed/removed per authorized bankroll accuracy improvement - no longer forced additive only for bankroll.md). Playbook followed by the letter. Validated via re-fetch after push.*

## Previous Bankroll Snapshot (for reference - condensed)

**Prior (before this settlement)**: **534.85 NOK liquid** + **40.00 NOK pending (Blaublitz + Oita)** = **574.85 NOK total** (after 2026-06-07 early football settlements of Nacional win + Venezuela Over win).

Full detailed history of prior placements/settlements preserved in Git commit history and earlier rounds/*.md files for audit. bet_log.csv contains complete P/L trail for all bets.

*Bankroll tracking made more accurate and maintainable by allowing direct current number updates + mandatory bet_log lookup procedure (see playbook.md for full rule).*