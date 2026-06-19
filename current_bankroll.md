# Current Bankroll

**Equity**: 397.76 NOK  
**Pending at Risk**: **0 NOK** (all 4 pending bets from 2026-06-19 settled)  
**Liquid Available**: **397.76 NOK**

**Last Updated**: 2026-06-19 ~03:00 CEST (post-settlement batch via nt-bet-log-manager + nt-bankroll-tracker + post-settlement-learning-reviewer skills)

**Settlements processed this update**:
- SC Recife PE vs AC Goianiense GO Under 2.5 @1.62 (12 NOK stake) → Win, payout 19.44 NOK, P/L +7.44 NOK
- Universidad de Chile vs CD O'Higgins Under 2.5 @1.70 (10 NOK stake) → Win, payout 17.00 NOK, P/L +7.00 NOK
- Toronto Marlies vs Chicago Wolves Under 5.5 @1.75 (10 NOK stake) → Loss, P/L -10.00 NOK
- Mexico vs South Korea Under 2.5 @1.65 (10 NOK stake) → Win, payout 16.50 NOK, P/L +6.50 NOK

**Net from this batch**: +10.94 NOK realized P/L
**Previous Equity**: 386.82 NOK → **New Equity 397.76 NOK**

**Notes**:
- Full nt-bet-log-manager protocol followed: fetched current bet_log.csv + SHA first, targeted updates only on the 4 matching Pending rows (Result + P_L_NOK changed, original research Notes preserved + settlement details appended). Missing Mexico pending row added as settled in same atomic update to maintain integrity.
- nt-bankroll-tracker verification: Equity recalculated from full bet_log.csv SUM of realized P/L + starting 500 base. Pending risk now 0. Row count and historical data 100% preserved.
- post-settlement-learning-reviewer executed: Reviewed outcomes vs pre-bet research (strong validation on Under 2.5 in these contexts: Serie B home defensive, Chilean injuries/xG, AHL finals goaltending, WC group stage cagey tactics). Minor positive pattern noted for selective unders in low-event controlled matches; no major filter change yet (sample small). Added short additive note to sport_edges_and_filters.md.
- All changes pushed via GitHub tools + re-validated (tree + full content fetch) before this record. Bankroll checklist passed.