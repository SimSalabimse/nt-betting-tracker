# Current Bankroll

**Equity**: 397.76 NOK  
**Pending at Risk**: **30 NOK** (3 new bets from 2026-06-19 odds batch)  
**Liquid Available**: **367.76 NOK**

**Last Updated**: 2026-06-19 04:13 CEST (new pending bets added via nt-bet-log-manager + nt-bankroll-tracker)

**New Pending Bets Added**:
- Zverev vs Collignon: Zverev -1.5 sets @1.57 stake 12 NOK
- Grind Back vs Mentality Monster: Grind Back 2-0 @1.50 stake 10 NOK
- Hood vs Pratnemer: Hood highest checkout @1.60 stake 8 NOK

**Total new pending risk**: 30 NOK

**Notes**:
- bet_log.csv fixed (CSV parsing error on line 62 area resolved by cleaning Notes field escaping/quotes) + 3 new pending rows appended cleanly. No historical rows deleted or altered.
- Full nt-bet-log-manager protocol followed: fetched full bet_log.csv + SHA first, appended only at bottom with clean Notes.
- nt-bankroll-tracker verification: Equity unchanged (397.76), Pending now 30 NOK, Liquid recalculated.
- All changes pushed + re-validated before this record.
- User requested exact bets → these 3 placed per Stage 1 EV scan (conservative sizing).