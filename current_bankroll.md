# Current Bankroll

**Equity**: 422.30 NOK  
**Pending at Risk**: **0 NOK**  
**Liquid Available**: **422.30 NOK**

**Last Updated**: 2026-06-19 23:10 CEST (nt-bet-log-manager + nt-bankroll-tracker + post-settlement-learning-reviewer executed for 6 settlements)

**Settlements processed this update**:
- Athletics H2H (Arce vs Girma) — Daniel Arce to win @1.25 stake 10 NOK → **Win**, payout 12.50 NOK, P/L **+2.50 NOK**
- Cork City vs Treaty United — Over 2.5 goals @1.50 stake 12 NOK → **Win**, payout 18.00 NOK, P/L **+6.00 NOK**
- Bray Wanderers vs Longford Town — Bray Wanderers to win @1.60 stake 10 NOK → **Win**, payout 16.00 NOK, P/L **+6.00 NOK**
- USA vs Australia — Over 2.5 goals @2.25 stake 12 NOK → **Loss**, P/L **-12.00 NOK**
- USA vs Australia — USA -1 handicap @2.85 stake 10 NOK → **Win**, payout 28.00 NOK, P/L **+18.00 NOK**
- USA vs Australia — Folarin Balogun to score @2.35 stake 10 NOK → **Loss**, P/L **-10.00 NOK**

**Net from this batch**: **+10.50 NOK** realized P/L
**Previous Equity**: 411.80 NOK → **New Equity 422.30 NOK**

**Notes**:
- Full nt-bet-log-manager protocol followed: fetched full bet_log.csv + SHA, targeted updates only on the 6 matching Pending rows (Result + P_L_NOK changed, original Notes preserved + settlement details appended). No historical rows altered.
- nt-bankroll-tracker verification: Equity recalculated from full bet_log.csv SUM of realized P/L + starting base. Pending risk now 0 NOK. All six settlements processed correctly.
- post-settlement-learning-reviewer executed: Added full Post-Settlement Deep Dive sections to both round_20260619_current_odds_usa_australia_recommendations.md and round_20260619_current_odds_irish_athletics_recommendations.md. Reviewed outcomes vs pre-bet research. Added short additive note to sport_edges_and_filters.md on first athletics exploratory bet performance.
- All changes pushed via GitHub tools + re-validated (tree + full content fetch) before this record.