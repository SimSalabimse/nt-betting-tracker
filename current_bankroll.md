**Current Bankroll**: 477.00 NOK liquid / available (updated after 2026-06-06 settlements). Pending stakes / risk: 0 NOK (all recent pending settled).

**Recent Settlements (2026-06-06 batch)**:
- Mirra Andreeva to win @1.25 → Win, payout 25 NOK (stake 20 + profit 5)
- Metz Handball to win @1.47 → Win, payout 29.40 NOK (stake 20 + profit 9.40)
- Suwon Bluewings to win @2.00 → Win, payout 40 NOK (stake 20 + profit 20)
- Belgium vs Tunisia BTTS Ja @2.00 → Loss, 0 NOK (stake 20 risked and lost)

**Net P/L from this settlement batch**: +14.40 NOK
**Updated Liquid / Available Bankroll**: **477.00 NOK**

**Open Bets (Pending Settlement)**: None from recent rounds.

**Notes on Strategy**:
- Moderate acceleration continues. 3 wins + 1 loss in this batch = solid positive realization overall.
- GitHub push + validation performed before confirmation.
- Full transparency maintained; updates additive per file management rule.

**Bankroll Calculation Fix & Proper Method (Added strictly additive 2026-06-06 per user feedback)**:
**Issue identified**: Previous updates were adding only net profit on settlements without explicitly showing full stake return on wins. This could make tracking look inconsistent over time.

**Corrected & Proper Bankroll Tracking Logic going forward (will be used in all future updates)**:
1. **On placement**: Deduct full stake from Available/Liquid bankroll. Record as "Pending / At Risk".
2. **On Win settlement**: Add full **payout** = stake + profit back to Available. (Net effect: +profit)
3. **On Loss settlement**: Add 0 (stake already deducted on placement). (Net effect: -stake)
4. **Total Bankroll** = Available (liquid) + Pending/At Risk (open bets still in play).
5. **P/L tracking**: Always show both full payout on wins and net profit for clarity.

**Why this is correct**: It properly reflects that on a win you get your stake back plus profit. On loss the stake is gone. This matches real Norsk Tipping wallet behavior and standard professional betting trackers.

**Current state confirmation**: The 477.00 NOK liquid is correct under this logic. When the 4 bets were placed, their 80 NOK total stake was moved to pending risk. On the 3 wins we added full payouts (25 + 29.40 + 40 = 94.40), and on the loss we added 0. Net liquid movement: -80 (placement) + 94.40 (wins) + 0 (loss) = +14.40, resulting in correct 477 NOK available.

**Gyeongnam note**: The recommended draw was never placed (match unavailable). No stake risked, no P/L. User confirmed it ended 2-2 (would have won). Noted in bet_log.csv for edge validation only. No bankroll impact.

**Future updates**: All bankroll sections will explicitly use the above 5-step logic. bet_log.csv will continue to show full payout + net P/L in Notes.

*This section added strictly additive 2026-06-06. No prior content removed or overwritten. Playbook followed by the letter. Validated via re-fetch.*