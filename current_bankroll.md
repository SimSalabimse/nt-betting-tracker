# Current Bankroll

**Equity**: 411.26 NOK  
**Pending at Risk**: **34 NOK** (Zverev vs Collignon 12 NOK + Sabalenka -1.5 sets 12 NOK + Team Spirit -1.5 maps 10 NOK)  
**Liquid Available**: **377.26 NOK**

**Last Updated**: 2026-06-19 14:20 CEST (nt-betting-workflow + nt-bet-log-manager + nt-bankroll-tracker executed)

**New Pending Bets Added (Grok autonomous decisions)**:
- Sabalenka vs Bartunkova — Sabalenka -1.5 sets @1.35 stake 12 NOK (Pending)
- Team Spirit vs G2 Esports — Team Spirit -1.5 maps @1.90 stake 10 NOK (Pending)

**Previous Pending**: Only Zverev 12 NOK (still open)

**Notes**:
- Full nt-betting-workflow followed: Stage 1 EV scan of new current_odds_01.txt (tennis/darts/esports batch) + targeted research + bet selection. 2 new high-conviction +EV bets chosen (Sabalenka HC and Team Spirit map HC). Conservative sizing.
- nt-bet-log-manager: Fetched full bet_log.csv + SHA, appended 2 new Pending rows at bottom only (original historical data 100% preserved, proper quoting). New round_20260619_current_odds_tennis_darts_esports_recommendations.md created with full rationale.
- nt-bankroll-tracker verification: Equity unchanged (no new settlements). Pending risk now 34 NOK total. Liquid = Equity - Pending. Row count validated.
- All changes pushed via GitHub tools (create/update + push_files where applicable) + re-validated with tree + full content fetch before this record.
- Post-settlement deep dives + edge updates to sport_edges_and_filters.md will follow after results (additive only).