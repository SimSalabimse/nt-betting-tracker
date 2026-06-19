# Current Bankroll

**Equity**: 396.10 NOK  
**Pending at Risk**: **0 NOK**  
**Liquid Available**: **396.10 NOK**

**Last Updated**: 2026-06-19 17:30 CEST (nt-bet-log-manager + nt-bankroll-tracker + post-settlement-learning-reviewer executed)

**Settlements processed this update**:
- Zverev vs Collignon (Zverev -1.5 sets) @1.57 stake 12 NOK → **Win**, payout 18.84 NOK, P/L **+6.84 NOK**
- Sabalenka vs Bartunkova (Sabalenka -1.5 sets) @1.35 stake 12 NOK → **Loss**, P/L **-12.00 NOK**
- Team Spirit vs G2 Esports (Team Spirit -1.5 maps) @1.90 stake 10 NOK → **Loss**, P/L **-10.00 NOK**

**Net from this batch**: **-15.16 NOK** realized P/L
**Previous Equity**: 411.26 NOK → **New Equity 396.10 NOK**

**Notes**:
- Full nt-bet-log-manager protocol followed: fetched full bet_log.csv + SHA, targeted updates only on the three matching Pending rows (Result + P_L_NOK changed, original research Notes preserved + settlement details appended). No historical rows altered, row count preserved.
- nt-bankroll-tracker verification: Equity recalculated from full bet_log.csv SUM of realized P/L + starting base. Pending risk now 0 NOK. All three settlements processed correctly. Row count and historical data 100% preserved.
- post-settlement-learning-reviewer executed: Reviewed outcomes vs pre-bet research in round_20260619_current_odds_tennis_darts_esports_recommendations.md. Zverev hit as expected (class gap). Sabalenka and Team Spirit losses = normal variance on +EV lines. Added short additive pattern note to sport_edges_and_filters.md.
- All changes pushed via GitHub tools + re-validated (tree + full content fetch) before this record.