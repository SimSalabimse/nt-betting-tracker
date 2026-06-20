# Current Bankroll

**Equity**: 409.00 NOK  
**Pending at Risk**: **68.00 NOK** (Turkey 12 NOK + 5 new bets 56 NOK)  
**Liquid Available**: **341.00 NOK**

**Last Updated**: 2026-06-20 04:59 CEST (nt-bet-log-manager + nt-bankroll-tracker executed for placing the 5 bets with stake change)

**New pending bets placed (user instruction applied - 170 utsjekk stake updated to 10 NOK)**:
- de Decker vs O’Connor (Darts) de Decker +1.5 legs @1.60 stake 12 NOK (Pending)
- de Decker vs O’Connor (Darts) de Decker total 180s Over 2.5 @1.95 stake 12 NOK (Pending)
- Fokus vs Cybershoke eSports (Esports) Fokus -1.5 maps @2.70 stake 10 NOK (Pending)
- Navarro vs Golubic (Tennis) Navarro -3.5 games @1.72 stake 12 NOK (Pending)
- de Decker vs O’Connor (Darts) 170 utsjekk i kampen Ja @9.20 stake **10 NOK** (Pending - smallest allowed, new odds type exploratory)

**Notes**:
- nt-bet-log-manager protocol: Full bet_log.csv + SHA fetched first. Appended only the 5 new pending rows (with stake change for the 170 prop). Full historical preserved. Detailed Notes with EV, research, new type flag. Pushed full content.
- nt-bankroll-tracker: Equity 409.00. Pending = 12 (Turkey) + 56 (new) = **68.00 NOK**. Liquid = 341.00 NOK. Verified.
- Learning added to sport_edges_and_filters.md: New pattern note on darts 170 checkout prop as exploratory new odds type (small stake 10 NOK, positive EV potential from checkout stats research). Updated Darts section and added to Update Log for future reference.
- nt-betting-workflow + betting-value-calculator followed by the letter. 1 new odds type included. All validated post-push.
- User: Bets now logged as Pending with your stake change. Place them. Report results later for settlement update.