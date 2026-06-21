# Current Bankroll

**Equity**: 392.68 NOK  
**Pending at Risk**: **24 NOK** (Pegula total games Over 22.5 12 NOK + Fritz -1.5 sets 12 NOK; the 3 reported settlements Arendal BTTS 15 + Brann O3.5 15 + vG 180s O2.5 10 removed from pending)  
**Liquid Available**: **368.68 NOK**

**Last Updated**: 2026-06-21 (post-settlement update via nt-bet-log-manager + nt-bankroll-tracker + post-settlement-learning-reviewer skills executed in full. 3 settlements processed from user report: Michael van Gerwen total antall 180 O2.5 Win payout 18.70 NOK P/L +8.70; Arendal BTTS Win payout 20.70 NOK P/L +5.70; Brann (kvinner) vs LSK Kvinner Over 3.5 Loss P/L -15.00. Full bet_log.csv fetch + SHA before any row update. Only exact matching rows updated with Result, P_L_NOK and appended settlement + deep dive ref in Notes. No other changes, no deletions, header integrity preserved. Bankroll fully recalculated from all realized P/L in bet_log.csv + remaining pending stakes verification. All pushes validated with tree + re-read before/after.)

**Settlements processed this batch (nt-bet-log-manager + post-settlement-learning-reviewer)**:
- van Gerwen vs Gilding van Gerwen total 180s Over 2.5 @1.87 stake 10 NOK → **Win** total payout 18.70 NOK (P/L +8.70). Darts prop validation successful.
- Arendal vs Træff Begge lag scorer Ja @1.38 stake 15 NOK → **Win** total payout 20.70 NOK (P/L +5.70). HUB BTTS edge confirmed in open Norwegian lower league match.
- Brann (kvinner) vs LSK Kvinner Over 3.5 goals @1.55 stake 15 NOK → **Loss** P/L -15.00. High total variance realized even in strong mismatch.

**Net realized P/L this settlement batch**: -0.60 NOK

**Remaining pending (not yet settled)**:
- Pegula vs Noskova Totalt antall games Over 22.5 @1.77 stake 12 NOK (round_20260621_current_odds_02.md #2)
- Fritz vs Tiafoe Fritz -1.5 sets @2.15 stake 12 NOK (round_20260621_current_odds_03.md #2)

**Validation note**: Equity = previous 393.28 + net settlements P/L (-0.60). Pending at risk recalculated strictly from current bet_log.csv rows where Result=Pending. Liquid = Equity - Pending. nt-bankroll-tracker protocol followed exactly. post-settlement deep dives and learning notes added to round_20260621_current_odds_02.md and round_20260621_current_odds_03.md. All per nt-betting-skills.md in full without skipping steps.