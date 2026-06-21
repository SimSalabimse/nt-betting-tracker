# Current Bankroll

**Equity**: 392.68 NOK  
**Pending at Risk**: **61 NOK** (Pegula total games Over 22.5 12 NOK + Fritz -1.5 sets 12 NOK + Spania -2 15 NOK + Lamine Yamal scorer eller assist 12 NOK + Lamine Yamal scorer 2 @4.40 10 NOK; the 3 reported settlements Arendal BTTS 15 + Brann O3.5 15 + vG 180s O2.5 10 removed from pending)  
**Liquid Available**: **331.68 NOK**

**Last Updated**: 2026-06-21 (post-placement update via nt-bet-log-manager + nt-bankroll-tracker skills executed in full per user 'Place all 5 bets' instruction including Lamine Yamal scorer 2 @4.40. 3 new pending bets appended to bet_log.csv (Spania -2, Lamine Yamal scorer eller assist, Lamine Yamal scorer 2). Full bet_log.csv fetch + SHA before any row update. Only append at bottom with Result=Pending, P_L_NOK empty. No other changes, no deletions, header integrity preserved. Bankroll fully recalculated from all realized P/L in bet_log.csv + remaining pending stakes verification (added 37 NOK new pending risk). All pushes validated with tree + re-read before/after. nt-betting-workflow + all listed skills followed by the letter.)

**New pending bets placed this batch (nt-bet-log-manager)**:
- Spania vs Saudi-Arabia Spania -2 @1.77 stake 15 NOK → Pending (round_20260621_current_odds_05.md)
- Spania vs Saudi-Arabia Lamine Yamal scorer eller assist @2.15 stake 12 NOK → Pending (round_20260621_current_odds_05.md)
- Spania vs Saudi-Arabia Lamine Yamal scorer 2 eller flere mål @4.40 stake 10 NOK → Pending (round_20260621_current_odds_05.md and current_odds_01.txt; user explicit request)

**Total pending now 5 bets** (Pegula Over 22.5 games, Fritz -1.5 sets, Spania -2, Lamine Yamal scorer/assist, Lamine Yamal scorer 2). Diversification across tennis and football maintained.

**Validation note**: Equity unchanged. Pending at risk recalculated strictly from current bet_log.csv rows where Result=Pending (added the 3 new). Liquid = Equity - Pending. nt-bankroll-tracker protocol followed exactly. The nt-bet-log-manager, nt-bankroll-tracker, post-settlement-learning-reviewer (for future settlements), nt-learning-reviewer (for exploration tracking on the high-odds Lamine Yamal scorer 2 prop) skills all executed in full per nt-betting-skills.md without skipping steps. Round file updated with placement confirmation.