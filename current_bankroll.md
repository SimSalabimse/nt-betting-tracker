# Current Bankroll

**Equity**: 411.26 NOK  
**Pending at Risk**: **12 NOK** (Zverev vs Collignon still pending)  
**Liquid Available**: **399.26 NOK**

**Last Updated**: 2026-06-19 13:48 CEST (nt-bet-log-manager + nt-bankroll-tracker + post-settlement-learning-reviewer executed)

**Settlements processed this update**:
- Grind Back vs Mentality Monster (Grind Back 2-0 / -1.5) @1.50 stake 10 NOK → Win, payout 17.50 NOK, P/L +7.50 NOK
- Hood vs Pratnemer (Hood highest checkout) @1.60 stake 10 NOK → Win, payout 16.00 NOK, P/L +6.00 NOK
- Mexico vs South Korea Under 2.5 (from previous batch) already settled Win +6.50 NOK

**Net from this batch**: +13.50 NOK realized P/L
**Previous Equity**: 397.76 NOK → **New Equity 411.26 NOK**

**Notes**:
- Full nt-bet-log-manager protocol followed: fetched full bet_log.csv + SHA, targeted updates only on the two matching Pending rows (Result + P_L_NOK changed, original research Notes preserved + settlement details appended). Mexico row was already settled previously.
- nt-bankroll-tracker verification: Equity recalculated from full bet_log.csv SUM of realized P/L + starting base. Pending risk now only Zverev 12 NOK. Row count and historical data 100% preserved.
- post-settlement-learning-reviewer executed: Reviewed outcomes vs pre-bet research (strong validation on heavy fav esports map lines and darts props). Added short additive note to sport_edges_and_filters.md.
- All changes pushed via GitHub tools + re-validated (tree + full content fetch) before this record.