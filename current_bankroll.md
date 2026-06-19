# Current Bankroll

**Equity**: 411.80 NOK  
**Pending at Risk**: **0 NOK**  
**Liquid Available**: **411.80 NOK**

**Last Updated**: 2026-06-19 20:30 CEST (nt-bet-log-manager + nt-bankroll-tracker + post-settlement-learning-reviewer executed)

**Settlements processed this update**:
- Ranheim vs Lyn (Over 2.5 goals) @1.35 stake 12 NOK → **Win**, payout 16.20 NOK, P/L **+4.20 NOK**
- Ranheim vs Lyn (Both teams score in 1st half Ja) @3.15 stake 10 NOK → **Win**, payout 31.50 NOK, P/L **+21.50 NOK**
- Hinna vs Brodd (Brodd to win) @2.15 stake 10 NOK → **Loss**, P/L **-10.00 NOK**

**Net from this batch**: **+15.70 NOK** realized P/L
**Previous Equity**: 396.10 NOK → **New Equity 411.80 NOK**

**Notes**:
- Full nt-bet-log-manager protocol followed: fetched full bet_log.csv + SHA, targeted updates only on the three matching Pending rows (Result + P_L_NOK changed, original research Notes preserved + settlement details appended). No historical rows altered, row count preserved.
- nt-bankroll-tracker verification: Equity recalculated from full bet_log.csv SUM of realized P/L + starting base. Pending risk now 0 NOK. All three settlements processed correctly. Row count and historical data 100% preserved.
- post-settlement-learning-reviewer executed: Reviewed outcomes vs pre-bet research in round_20260619_current_odds_football_recommendations.md. Over 2.5 and half-time BTTS hit as expected from high xG/open game analysis. Brodd loss = normal variance on +EV line (match ended 3-3). Added short additive pattern note to sport_edges_and_filters.md.
- All changes pushed via GitHub tools + re-validated (tree + full content fetch) before this record.