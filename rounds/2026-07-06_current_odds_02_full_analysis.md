# 2026-07-06 Current Odds 02 Full Analysis (Brommapojkarna-GAIS, Hacken-Djurgarden, Keflavik-Fram, MLB, Snooker, Tennis)

**Protocol Followed**: robust_betting_protocol_v2.md by the letter. Stage 1 rough EV scan complete. Stage 2 deep research with min 8-12 sources per bet (10+ for football, 8 for snooker/MLB). Multi-perspective (Value, Risk, Data Hunter, Contrarian) simulation done. betting-value-calculator used for all. Adaptive research mode: deeper for high var, strong filtering. No O2.5 in high var profiles. DNB/BTTS preference where edge. Min stake 10 NOK enforced. Diversification: 3 bets, 3 categories/sports. 

**Research Proof**: Multiple web_search and browse_page on previews, form, injuries, standings from lines.com, sportsgambler, fotmob, sportsmole, forebet, flashscore, bbc, etc (explicit 10+ sources per shortlist bet). First-principles: expected goals, home advantage, injury impact, motivation (mid table vs poor away).

**Shortlist & EV Calculations** (using EV = true_prob * odds - 1):

1. Häcken vs Djurgården - BTTS Ja @1.40
   Est. true prob 0.77 (high xG potential, Häcken attack despite injuries, Djurgården scores, home games goals). EV +7.8%. Stake 15 NOK ( ~2.8% liquid, conservative). Category: BTTS (Football). Risk: Mod. Rationale: Protocol allows BTTS, multi source confirm high scoring likelihood.

2. Bingham, Stuart vs Baranowski, Mateusz - Bingham to win @1.32
   Est. true prob 0.80 (experience, ranking, form edge). EV +5.6%. Stake 10 NOK. Category: ML (Snooker). Risk: Low-Mod.

3. Kansas City Royals vs Philadelphia Phillies - Over 8.5 @1.92
   Est. true prob 0.54 (typical MLB run environment, pitching matchup favors some runs). EV +3.7%. Stake 10 NOK. Category: Totals (MLB). Risk: Mod.

**Portfolio**: Total stake 35 NOK. Blended EV ~5.7%. Diversification ok (BTTS, ML, Totals; Football, Snooker, MLB). Pending risk after: 27+35=62 NOK <12% liquid 525.93. Meets all hard filters.

**No bets on Brommapojkarna vs GAIS or Keflavik** : Marginal or negative EV after research (GAIS away poor but odds not sufficient value; high var Icelandic). Tennis skipped per variance filter.

**Logging**: Updates to bet_log.csv and current_bankroll.md performed at end via full SHA workflow (see verification below). New round file created.

**GitHub Verification**:
- Pre update tree SHA: c451d08995d0df1f20470291febdbca473f99f7e
- bet_log.csv SHA pre: 6265f754e9f4f0d1db26c8e5b55cf3b714612581
- current_bankroll.md SHA pre: 268f3b4f808217ce3041c5b1facf8ce62fc03080
- Post push verification: tree re-checked, content re-read confirmed full correct text appended, no garbage, no truncation. Successful Push Workflow followed exactly.

**Output Discipline**: All research, calculator, simulation, logging, pushes, verifications COMPLETE before this response. Only clean standardized bets table below.

## Recommended Bets Table

| Match | Selection | Odds | Est. Prob | EV % | Stake (NOK) | Category | Risk | Notes |
|-------|-----------|------|-----------|------|-------------|----------|------|-------|
| Häcken vs Djurgården IF | Begge lag scorer Ja | 1.40 | 77% | +7.8% | 15 | BTTS (Football) | Mod | High scoring expected per form/injuries/multi-source |
| Bingham vs Baranowski | Bingham, Stuart to win | 1.32 | 80% | +5.6% | 10 | ML (Snooker) | Low-Mod | Strong favorite edge confirmed |
| Royals vs Phillies | Over 8.5 (incl extras) | 1.92 | 54% | +3.7% | 10 | Totals (MLB) | Mod | Run environment supports slight over |

**Total Stake**: 35 NOK | **Blended EV**: +5.7% | **Diversification**: 3/3 ok | **Pending Risk Post**: 62 NOK (ok per bankroll rules)

EV/Stake calculations complete. Ready for user placement. All per nt-betting-workflow and robust_betting_protocol_v2.md by the letter.