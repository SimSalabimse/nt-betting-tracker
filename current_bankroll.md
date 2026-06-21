# Current Bankroll

**Equity**: 383.78 NOK  
**Pending at Risk**: **64 NOK** (previous 37 NOK from 2026-06-21 WC round + new 15 NOK Arendal BTTS + 12 NOK Pegula total games = 27 NOK added)  
**Liquid Available**: **319.78 NOK**

**Last Updated**: 2026-06-21 (nt-bet-log-manager + nt-bankroll-tracker executed after user request to update files with the 2 bets from round_20260621_current_odds_02.md. Full CSV fetch + SHA first, append-only pending rows. nt-betting-workflow diversification/min-stake/EV rules enforced.)

**New pending bets logged (2026-06-21 round_20260621_current_odds_02.md)**:
- Arendal vs Træff: Begge lag scorer Ja @1.38 stake 15 NOK — Norwegian 2. div BTTS from full Stage 1/2 research (H2H high BTTS/scoring rates); est EV positive. Diversification from WC pending.
- Pegula vs Noskova: Totalt antall games Over 22.5 @1.77 stake 12 NOK — Tennis total games from diversified portfolio (different sport + bet type); est EV positive post research. Min stake + rules enforced.

**Previous pending (still active)**:
- Ecuador vs Curacao: Ecuador clean sheet (Ja) @1.52 stake 15 NOK
- Tunisia vs Japan: Over 2.5 goals @2.00 stake 12 NOK
- Tunisia vs Japan: Hannibal Mejbri yellow card (Ja) @3.00 stake 10 NOK

**Validation**: bet_log.csv appended via nt-bet-log-manager (full fetch + SHA c1361f65189d89cea9feb1f8375529128bcc578f before edit; append-only, Result=Pending, P_L empty, detailed Notes). nt-bankroll-tracker full recalc verified (Pending = sum all Pending stakes). All GitHub pushes re-validated with tree + full content read on both files. No skips on nt-betting-workflow, playbook, or nt-bet-log-manager / nt-bankroll-tracker skill rules. Repo state verified before/after.