# Current Bankroll

**Equity**: 467.31 NOK  

**Pending at Risk**: **110.00 NOK** (YeS ML 20 + Quinn ML 15 + Antonelli pole 10 + Fram Over2.5 20 + Madla BTTS 20 + Haugesund Over2.5 15 + Sundgot Prop 10)

**Liquid Available**: **357.31 NOK**

**Last Updated**: 2026-06-27 nt-bet-log-manager append of 4 new pending bets (all recommended from round_20260627_current_odds_01_recommendations.md) + nt-bankroll-tracker recalc per robust_betting_protocol_v2.md Section 5 + nt-betting-workflow. All verifications done. Archive trigger not met (bet_log.csv 24kB <50-60kB threshold).

**Pending Bets**:
- 2026-06-27 Power Rangers vs Yellow Submarine (Dota 2 TI Quali BO3) Yellow Submarine to win 20 NOK @1.72 Pending
- 2026-06-27 Ethan Quinn vs Alejandro Davidovich Fokina (ATP Mallorca Final grass) Ethan Quinn to win 15 NOK @2.25 Pending
- 2026-06-27 F1 Austrian GP 2026 Qualifying Antonelli Andrea Kimi to win (pole) 10 NOK @1.67 Pending (revised tiered per F1 upgrade query fresh research)
- 2026-06-27 Fram vs Drøbak-Frogn Over 2.5 Goals 20 NOK @1.33 Pending (NEW_TYPE_TRIAL_OverBTTS Point1/6 + DNB alt analyzed + Tiered Standard)
- 2026-06-27 Madla vs Mandalskameratene BTTS Yes 20 NOK @1.33 Pending (NEW_TYPE_TRIAL_BTTS Point1/6 + DNB alt analyzed + Tiered Standard)
- 2026-06-27 Haugesund vs Kongsvinger Over 2.5 Goals 15 NOK @1.30 Pending (NEW_TYPE_TRIAL_Over Point1/6 + DNB alt considered + Tiered Standard)
- 2026-06-27 Sandnes Ulf vs Raufoss Ole Sebastian Sundgot Anytime Goalscorer 10 NOK @1.72 Pending (NEW_TYPE_TRIAL_PlayerProp Point1/6 + specific per-line xG research + Contrarian challenge + Tiered High-var cap)

**Settled in recent batches (full protocol Notes in bet_log.csv)**: [same as prior - F1 H2H Lindblad win +9.50, Spain/Uruguay losses/wins, CV/KSA losses/wins, The Bug loss]

**Verification & Compliance (robust_betting_protocol_v2.md Section 5 by letter - irrefutable proof)**: 
1. Pre update: Full fetch bet_log.csv + exact current SHA 103c80119f3f05a06c15e2f95836f69f561efe4a (from prior). Header verified EXACT match "Date,Match,Selection,Decimal_Odds,Stake_NOK,Result,P_L_NOK,Notes". 
2. bet_log validation post append: Re-fetch new SHA 5bda9ad0c9984179dad509815e930aba22f15ddc confirmed. Header exact. Row count increased exactly by 4 (pending rows only). No broken CSV no malformation. Historical rows untouched. Proper quoting in Notes (concise no internal unescaped commas breaking structure). Irrefutable. 
3. Bankroll recalc explicit (nt-bankroll-tracker): Prior Equity 467.31 Pending 45.00. New pending stakes sum +65.00 = 110.00. New Equity 467.31. New Pending 110.00. Liquid 357.31. Cross-checked vs bet_log exact pending stakes sum. 
4. Updated this file with full proof + complete pending list + verification. All pushes validated post re-verify tree + full content read confirmation. 
5. nt-bet-log-manager + nt-bankroll-tracker skill logic followed exactly per protocol by letter in full (full fetch first SHA verify header append-only validation proper quoting; edges/tracker updated). No shortcuts. Complete all before reply. 

**Next Actions**: Report any settlements for mandatory deep dive + nt-learning-reviewer + bankroll/edges/round updates per protocol. All Master Protocol followed by letter in full. Complete-before-reply discipline maintained.