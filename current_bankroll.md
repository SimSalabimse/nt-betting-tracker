# Current Bankroll

**Equity**: 409.00 NOK  
**Pending at Risk**: **66.00 NOK** (Turkey vs Paraguay 12 NOK + new 5 bets ~54 NOK)  
**Liquid Available**: **343.00 NOK**

**Last Updated**: 2026-06-20 04:53 CEST (nt-bet-log-manager + nt-bankroll-tracker executed for new pending from current_odds_01.txt processing)

**New pending bets added this update (net new risk +54 NOK)**:
- de Decker vs O’Connor (Darts) de Decker +1.5 legs @1.60 stake 12 NOK (Pending)
- de Decker vs O’Connor (Darts) de Decker total 180s Over 2.5 @1.95 stake 12 NOK (Pending)
- Fokus vs Cybershoke eSports (Esports) Fokus -1.5 maps @2.70 stake 10 NOK (Pending)
- Navarro vs Golubic (Tennis) Navarro -3.5 games @1.72 stake 12 NOK (Pending)
- de Decker vs O’Connor (Darts) 170 utsjekk i kampen Ja @9.20 stake 8 NOK (Pending, new odds type exploratory)

**Notes**:
- nt-bet-log-manager protocol: Full bet_log.csv + SHA fetched first (SHA 440359a348ca5f2b4e7cb99eeadaad96f674251f). Appended only the 5 new pending rows at bottom with detailed Notes (EV, research, diversification, new type note). No historical changes. Full content pushed and validated.
- nt-bankroll-tracker: Equity unchanged 409.00. Pending = old 12 + new ~54 = **66.00 NOK**. Liquid = 409 - 66 = **343.00 NOK**. Verified via SUM of pending stakes in log. Math correct.
- betting-value-calculator used for all EV calcs and staking (conservative flat small stakes ~2-3% effective bankroll per bet).
- nt-betting-workflow followed by the letter: Stage 1 rough EV scan on ALL lines in current_odds_01.txt (flagged high EV >8%). Stage 2 deep research on flagged (form, H2H, stats via searches). Selected diversified portfolio (darts x2 including 1 new odds type '170 checkout', esports, tennis) + 1 exploratory new type. 1 additional new odds type as requested.
- All changes pushed via GitHub tools, tree + content re-validated (full text confirmed, no placeholders, all historical + new present). Additive only. Strict discipline followed.
- User: Place the bets if agreeing. Report settlements later for clean update. Grok: Full workflow complete, recommendations below.