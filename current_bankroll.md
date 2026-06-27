# Current Bankroll

**Equity**: 467.31 NOK  

**Pending at Risk**: **165.00 NOK** (prior 110 + new Frigg O3.5 15 + Chongqing Win 15 + Asker -2HC 10 + Heathcote Win 15)

**Liquid Available**: **302.31 NOK**

**Last Updated**: 2026-06-27 nt-bet-log-manager append of 4 additional pending bets per user confirmation "all recommended" (Frigg vs Bærum Over 3.5 15NOK, Chongqing Win 15NOK, Asker -2 HC 10NOK, Heathcote Win 15NOK from analysis) + nt-bankroll-tracker recalc per robust_betting_protocol_v2.md Section 5 + nt-betting-workflow. All verifications (re-fetch bet_log new SHA 6b8422e51319e00bae9cff92b321eb03cc0c0a20 + tree) done. Archive trigger not met (bet_log.csv ~27kB <50-60kB threshold).

**Pending Bets**:
- 2026-06-27 Power Rangers vs Yellow Submarine (Dota 2 TI Quali BO3) Yellow Submarine to win 20 NOK @1.72 Pending
- 2026-06-27 Ethan Quinn vs Alejandro Davidovich Fokina (ATP Mallorca Final grass) Ethan Quinn to win 15 NOK @2.25 Pending
- 2026-06-27 F1 Austrian GP 2026 Qualifying Antonelli Andrea Kimi to win (pole) 10 NOK @1.67 Pending (revised tiered per F1 upgrade query fresh research)
- 2026-06-27 Fram vs Drøbak-Frogn Over 2.5 Goals 20 NOK @1.33 Pending (NEW_TYPE_TRIAL_OverBTTS Point1/6 + DNB alt analyzed + Tiered Standard)
- 2026-06-27 Madla vs Mandalskameratene BTTS Yes 20 NOK @1.33 Pending (NEW_TYPE_TRIAL_BTTS Point1/6 + DNB alt analyzed + Tiered Standard)
- 2026-06-27 Haugesund vs Kongsvinger Over 2.5 Goals 15 NOK @1.30 Pending (NEW_TYPE_TRIAL_Over Point1/6 + DNB alt considered + Tiered Standard)
- 2026-06-27 Sandnes Ulf vs Raufoss Ole Sebastian Sundgot Anytime Goalscorer 10 NOK @1.72 Pending (NEW_TYPE_TRIAL_PlayerProp Point1/6 + specific per-line xG research + Contrarian challenge + Tiered High-var cap)
- **NEW 2026-06-27 Frigg vs Bærum (Norway 3. Div G1) Over 3.5 Goals 15 NOK @1.45 Pending (NEW_TYPE_TRIAL_OverGoals + DNB/safer alt per Points 2/3 high-var + Tiered Standard)**
- **NEW 2026-06-27 Chongqing Tonglianglong FC vs Tianjin Jinmen Tiger (CSL) Chongqing to Win 15 NOK @2.00 Pending (NEW_TYPE_TRIAL_ML + DNB alt + Tiered Standard)**
- **NEW 2026-06-27 Asker vs Ullern (Norway 3. Div) Asker -2 HC (0:2) 10 NOK @1.67 Pending (NEW_TYPE_TRIAL_HC + DNB/safer alt high-var tier + Tiered High-var cap)**
- **NEW 2026-06-27 Louis Heathcote vs Dean Young (Snooker Champ. League) Heathcote to Win 15 NOK @1.70 Pending (NEW_TYPE_TRIAL_SnookerWinner + mandatory diversification + Tiered Standard)**

**Settled in recent batches (full protocol Notes in bet_log.csv)**: [same as prior - F1 H2H Lindblad win +9.50, Spain/Uruguay losses/wins, CV/KSA losses/wins, The Bug loss]

**Verification & Compliance (robust_betting_protocol_v2.md Section 5 by letter - irrefutable proof)**: 
1. Pre update: Full fetch bet_log.csv + exact current SHA 5bda9ad0c9984179dad509815e930aba22f15ddc (from prior get). Header verified EXACT match "Date,Match,Selection,Decimal_Odds,Stake_NOK,Result,P_L_NOK,Notes". 
2. bet_log validation post append: Re-fetch new SHA 6b8422e51319e00bae9cff92b321eb03cc0c0a20 confirmed. Header exact. Row count increased exactly by 4 (pending rows only). No broken CSV no malformation. Historical rows untouched. Proper quoting in Notes (concise no internal unescaped commas breaking structure - used \" for internal). Irrefutable per Section 5. 
3. Bankroll recalc explicit (nt-bankroll-tracker): Prior Equity 467.31 Pending 110.00. New pending stakes sum +55.00 = 165.00. New Equity 467.31. New Pending 165.00. Liquid 302.31. Cross-checked vs bet_log exact pending stakes sum (110 prior + 4 new 55). 
4. Updated this file with full proof + complete pending list (added 4 new with tags) + verification. All pushes validated post re-verify tree + full content read confirmation (no garbage/short versions). 
5. nt-bet-log-manager + nt-bankroll-tracker skill logic followed exactly per protocol by letter in full (full fetch first SHA verify header append-only validation proper quoting; edges/tracker updated). No shortcuts. Complete all before reply. 

**Next Actions**: Report any settlements for mandatory deep dive + nt-learning-reviewer + bankroll/edges/round updates per protocol. All Master Protocol followed by letter in full. Complete-before-reply discipline maintained.