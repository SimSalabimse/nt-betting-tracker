**Current Bankroll**: [TO BE CONFIRMED - see correction below] NOK liquid / available. Pending stakes / risk: 0 NOK.

**Bankroll Calculation Correction (Added strictly additive 2026-06-06)**:
The previous figure of 477.00 NOK was based on a snapshot (462.60 liquid + net +14.40 from the 4 settlements). You have correctly identified that this running total is incorrect.

**Reason for error**: The carrying balance (462.60) from prior updates did not perfectly align with cumulative realized P/L from all bets in bet_log.csv + actual Norsk Tipping wallet movements (including how pending stakes were deducted/re-added across multiple rounds).

**Correct approach going forward**:
- The single source of truth for **actual liquid bankroll** is your Norsk Tipping account balance.
- bet_log.csv tracks every individual bet's P/L for analysis and learning.
- current_bankroll.md will now show the actual reported balance from you, with clear notes on how it was derived.

**Action required from you**: Please tell me the **exact current liquid/available balance** shown in your Norsk Tipping account right now (after all these settlements). I will immediately update this file with the correct number and a full reconciliation note.

**Gyeongnam FC vs Yongin City FC**: Confirmed would have won (2-2). Noted in bet_log.csv. No stake was placed, so no P/L impact on actual bankroll.

**Proper tracking method** (already documented in previous section and remains in effect):
On placement: deduct stake from available. On win: add full payout (stake + profit). On loss: add 0.

Once you provide the current actual Norsk Tipping liquid balance, I will set it correctly here with full additive explanation and history note. All updates remain strictly additive per the File Management Rule.

*This correction section added strictly additive 2026-06-06. Playbook followed by the letter.*