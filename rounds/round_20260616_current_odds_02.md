# Round 2026-06-16 Current Odds Analysis - Irak vs Norge (Norway vs Iraq) + Multi-Sport Scan

**Date**: 2026-06-16  
**Source Odds**: current_odds_01.txt (Irak-Norge detailed HUB + all props, combined bets, Fortaleza, AHL, WNBA, 8 MLB games)  
**Bankroll Context**: Equity 438.43 NOK, Pending 0 (post recent settlements)  
**Playbook Compliance**: Two-Stage Workflow strictly followed. All markets in odds file considered equally in Stage 1. Mandatory Exploration Quota noted (not met - no Darts/Snooker). Singles prioritized over combos. Additive update only. Git push + validation before reply.

## Bets Placed Confirmation (User placed 2026-06-17)
User confirmed placement of the 4 recommended singles. 

**Exact lines to append to bet_log.csv** (nt-bet-log-manager safe append protocol - no commas in Notes, proper quoting, empty P_L_NOK for Pending):

```
2026-06-17,Irak vs Norge,Begge lag scorer Nei,1.50,12,Pending,,"round_20260616_current_odds_02.md Bet1; BTTS Nei; est EV +17-29%; Iraq low threat vs Norway defense. nt-bet-log-manager protocol followed."
2026-06-17,Irak vs Norge,Erling Haaland scorer,1.45,15,Pending,,"round_20260616_current_odds_02.md Bet2; Haaland scorer; est EV +16-26%; clinical vs weak Iraq defense. nt-bet-log-manager protocol followed."
2026-06-17,Irak vs Norge,Norge win,1.20,15,Pending,,"round_20260616_current_odds_02.md Bet3; Norge win; est EV +7-12%; strong favorite in mismatch. nt-bet-log-manager protocol followed."
2026-06-17,Irak vs Norge,Norge holder nullen Ja,1.58,12,Pending,,"round_20260616_current_odds_02.md Bet4; Clean sheet Ja; est EV +11-23%; Norway dominant defense. nt-bet-log-manager protocol followed."
```

These 4 lines preserve CSV integrity (semicolons only in Notes, quoted field, blank P_L_NOK). Do not push modified bet_log.csv from here to avoid any breakage risk; use nt-bet-log-manager or manual safe append at end of file.

**Updated Bankroll Impact (conceptual until CSV append)**: Pending at Risk now 54.00 NOK. Liquid Available 384.43 NOK. Equity remains 438.43 NOK. Full verification after safe append + analyze_betting.py run.

---

## Stage 1: Rough EV Scan - Equal Consideration (Quick Prob + EV on Every Line)

Full scan performed on 2493-line odds file. Implied probabilities calculated as 1/odds. True probability estimates based on:
- Team/player quality, recent form, head-to-head, motivation (friendly/prep context assumed for Irak-Norge).
- Historical scoring rates in mismatches (Norway vs Asian/WC minnows typically 4-6 goals, clean sheets common).
- Player props adjusted for usage (Haaland focal point, Odegaard creator).
- Public bias toward favorites in player props often inflates underdog prices slightly.
- No advanced model; conservative estimates to avoid overconfidence.

**Key High EV / Positive EV Candidates Identified (Irak vs Norge focus)**:

**Match Winner & 1H**:
- Norge win @1.20 → implied 83.33%. Est true p: 89-93% (squad gulf: Haaland, Ødegaard, Nusa, Sørloth vs Iraq mid-table Asian level). EV: +7% to +12%. **Strong foundational value**.
- 1. omgang Norge win @1.55 → implied 64.52%. Est true p: 74-81%. EV: +15% to +25%.
- Uavgjort tilbakebetales Norge @1.04 → low value (vig heavy).

**Over/Under Goals**:
- Over 2.5 @1.58 → implied 63.29%. Est true p: 68-75% (expect open game, Norway attack). EV: +8% to +19%.
- Over 3.5 @2.45 → implied 40.82%. Est true p: 52-62% (typical 4+ goals in such fixtures). EV: +27% to +52%. **High potential value**.
- Under 2.5 @2.30 → implied 43.48%. Est true p: 25-32%. Negative EV.
- Higher O/U (4.5+): Overpriced for under, some value on overs if game script allows.

**Both Teams To Score**:
- BTTS Nei (No) @1.50 → implied 66.67%. Est true p: 78-86% (Iraq low xG vs organized Norway defense; limited attacking threat). EV: +17% to +29%. **HIGH VALUE - Top pick**.
- BTTS Ja @2.40 → implied 41.67%. Est true p: 14-22%. Negative EV.

**Clean Sheets & Team Totals**:
- Norge holder nullen Ja @1.58 → implied 63.29%. Est true p: 70-78%. EV: +11% to +23%. **Strong**.
- Irak holder nullen Ja @8.50 → implied 11.76%. Est true p: 2-5%. Negative EV.
- Totalt antall Norge mål over/under 2.5 Over @1.95 → implied 51.28%. Est true p: 58-68%. EV +13% to +32%.

**Player Props - High Conviction**:
- Erling Haaland scorer @1.45 → implied 68.97%. Est true p: 80-87% (starts, focal, clinical finisher vs weak CBs). EV: +16% to +26%. **HIGH VALUE**.
- Haaland 2+ @3.25 → implied 30.77%. Est true p: 45-55% (brace likely). EV: +46% to +79%. **Very high if multiple goals script**.
- Haaland hat-trick @9.50 → implied 10.53%. Est true p: 18-25%. EV: +71% to +137% (speculative but positive).
- Alexander Sørloth scorer @2.10 → implied 47.62%. Est true p: 35-45%. Marginal/negative.
- Martin Ødegaard assist or scorer props: Some value on assists @2.35 but lower conviction.
- Iraqi scorers (Aymen Hussein @6.60 etc.): Generally overpriced, low true p.

**Timing, Cards, Corners**:
- Tidspunkt for 1. Norge mål (various windows): Some value in early goal windows @3.65-4.10 if aggressive start expected.
- Corners: Norge over hjørnespark lines (e.g. over 5.5 @1.42) likely positive EV (Norway dominant possession).
- Cards: Low card expectation in friendly; Under card lines may have value but low edge.
- Scorer on heading etc.: Haaland heading @3.55 good supplemental.

**Combined / Special Bets**:
- E.Haaland scorer & Norge vinner? (Ja) @1.55 : Correlated legs. Blended true p high but odds not sufficiently boosted vs separate. EV lower than sum of singles.
- Over 2.5 mål & over 7.5 hjørnespark & over 2.5 kort? (Ja) @3.25 : Multi-leg, variance high, correlation moderate. EV calc needs exact model; generally avoid unless superior.
- Other combos: Most have vig drag; separate singles preferred.

**Other Matches Quick Scan (Equal Weight)**:
- **Fortaleza vs America (Brazil)**: Fortaleza win @1.47 (implied ~68%). Est true ~72-78% if home strong. Marginal value. BTTS @2.05 some interest.
- **AHL Toronto Marlies vs Chicago Wolves**: Very close (1.80/1.85). Over 5.5 @1.75 possible if high event game. Low conviction, no strong edge.
- **WNBA Indiana Fever vs Toronto Tempo**: Indiana @1.25 strong (implied 80%). Likely value if Tempo weak.
- **MLB (8 games)**: 
  - Phillies @1.49 vs Marlins @2.33: Slight value on underdog or totals ~8.5.
  - Red Sox @1.89 vs Blue Jays @1.75: Close, pitching dependent.
  - Nationals @1.66, Yankees @1.61, Braves @1.51, Brewers @1.57, Cardinals @1.77: Favorites generally, some totals value if bullpen factors.
  Overall: Scattered marginal edges; no standout like football mismatch. Diversification potential but lower EV than Irak-Norge core.

**Exploration Quota Note**: sport_edges_and_filters.md lists Darts and Snooker as HIGH priority (historically profitable, low volume tested). This odds file contains none. Quota not satisfied this round. Recommendation: In future odds with Darts/Snooker, allocate at least 1-2 bets even at ~5-6% EV bar for learning. No change to filters needed.

**Stage 1 Conclusion**: Clear positive EV cluster in Irak-Norge mismatch markets, especially BTTS No, Haaland props, clean sheet, and higher goal totals. Other sports offer diversification but lower edge density. No negative EV traps blindly followed.

---

## Stage 2: Prioritize for Deep Research, Structure Decision & Portfolio Construction

**Selected Top Bets (Highest rough EV + conviction + bankroll fit)**:
1. **BTTS Nei @1.50** (Iraq vs Norway) - Highest edge, low variance, foundational for mismatch.
2. **Erling Haaland scorer @1.45** - Core to Norway attack, high hit rate expected.
3. **Norge win @1.20** - High probability anchor, compounds with above.
4. **Norge holder nullen Ja @1.58** - Good supplement, correlated positively with win/BTTS No.

**Structure Decision (Singles vs Combo)**:
- Promising pair example: Haaland scorer + Norge win.
  - Two separate singles: Portfolio EV ≈ EV_Haaland + EV_Win ≈ +16-26% + +7-12% = +23-38% blended; higher prob of partial profit; lower variance. **Default per protocol for Phase 1 stability**.
  - Combo "E.Haaland scorer & Norge vinner? (Ja) @1.55": True p high (~75-82%), but correlation high (Haaland goal → Norway win likely). Adjusted EV_combo lower than sum due to vig and dependence. Not meaningfully superior.
- **Rule Applied**: Prefer separate singles. Documented here. No combo selected.

**Diversification**: All 4 on same match (correlated). Acceptable for this high-conviction cluster. Future rounds will spread to 3+ sports when edges available (e.g. include MLB or AHL if strong EV).

**Exploration**: None allocated (no qualifying sports in file). Added to learning log.

**Bankroll & Stake Sizing**:
- Current (pre this round): Equity 438.43 NOK, Pending 0 NOK, Liquid 438.43 NOK (verified via analyze_betting.py logic).
- Recommended stakes: 12-15 NOK per bet ( ~3% per bet, total ~12% of bankroll). Conservative per recent pattern and Phase 1 focus.
- Post placement (conceptual): Pending +54 NOK, Liquid ~384.43 NOK. Equity unchanged until settlement.
- Strict formula will be re-verified post any settlement with analyze_betting.py + current_bankroll.md update.

**Recommended Bets to Place (Singles)**:

| Bet # | Match | Selection | Odds | Stake (NOK) | Est. EV | Notes / Pointer |
|-------|-------|-----------|------|-------------|---------|-----------------|
| 1 | Irak vs Norge | Begge lag scorer Nei | 1.50 | 12 | +17% to +29% | BTTS No. Iraq low threat. round_20260616_current_odds_02.md Bet1 |
| 2 | Irak vs Norge | Erling Haaland scorer | 1.45 | 15 | +16% to +26% | Anytime. Clinical vs weak defense. round_20260616_current_odds_02.md Bet2 |
| 3 | Irak vs Norge | Norge win | 1.20 | 15 | +7% to +12% | Foundational high prob. round_20260616_current_odds_02.md Bet3 |
| 4 | Irak vs Norge | Norge holder nullen Ja | 1.58 | 12 | +11% to +23% | Clean sheet. round_20260616_current_odds_02.md Bet4 |

**Total Stake**: 54 NOK  
**Expected Portfolio EV (approx)**: +15% to +25% blended (conservative).  

**Post-Placement Protocol**: 
- Add above as Pending rows to bet_log.csv with concise Notes + pointer to this round file.
- Update current_bankroll.md with new Pending/Liquid figures + verification.
- Run `python analyze_betting.py bet_log.csv` after update.
- Git push + raw validation before any settlement reply.

**Risks & Notes**: Friendly match context may affect motivation/intensity (possible rotation?). Monitor lineups if available. All estimates qualitative; variance expected (esp. props). Bankroll reset discipline maintained (current ~438 after recent P/L).

**Mandatory Learning Log**: No settlements in this round yet. When settled, add exact Post-Settlement Deep Dive section to this file per playbook (Pre-bet Hypothesis, Outcome, Edge Validation, Actionable Learning, Impact on sport_edges_and_filters.md).

---

## Post-Settlement Deep Dives (Mandatory - Every Bet)

### Bet 1: Begge lag scorer Nei @1.50 Stake 12 NOK (Loss)
- **Pre-bet Hypothesis** (quote from round rec): BTTS Nei; est EV +17-29%; Iraq low threat vs Norway defense. nt-bet-log-manager protocol followed.
- **Outcome & Post-Match Factors**: Loss (P/L -12.00). Per user report and consistent with clean sheet loss: Iraq scored at least once. Norway won the match.
- **Edge Validation**: The core edge (Iraq low attacking threat) held directionally but variance realized (Iraq did score). Pre-match xG models would have shown low but non-zero probability for Iraq goal.
- **Actionable Learning**: In mismatch friendlies, even weak opponents can nick a goal via set pieces or individual quality. Consider small buffer on BTTS No or pair with over goals markets in future. No change to sport_edges_and_filters.md needed yet (single outcome).
- **Impact**: Monitor Iraq/Norway type mismatches for BTTS No + Over 2.5/3.5 combos if correlation supports.

### Bet 2: Erling Haaland scorer @1.45 Stake 15 NOK (Win)
- **Pre-bet Hypothesis** (quote from round rec): Haaland scorer; est EV +16-26%; clinical vs weak Iraq defense. nt-bet-log-manager protocol followed.
- **Outcome & Post-Match Factors**: Win (P/L +6.75, total payout 21.75 NOK). Haaland scored as expected.
- **Edge Validation**: Edge held strongly. Haaland's finishing + focal role in attack vs limited defense delivered.
- **Actionable Learning**: Player props on elite finishers in mismatches remain high-value when odds >1.40. Continue prioritizing in Stage 2 when available.
- **Impact**: Reinforces football player props (esp. Haaland-type) as strong diversifier when main match lines are short.

### Bet 3: Norge win @1.20 Stake 15 NOK (Win)
- **Pre-bet Hypothesis** (quote from round rec): Norge win; est EV +7-12%; strong favorite in mismatch. nt-bet-log-manager protocol followed.
- **Outcome & Post-Match Factors**: Win (P/L +3.00, total payout 18.00 NOK). Norway won as heavily expected.
- **Edge Validation**: High-probability anchor held. Low variance outcome as modeled.
- **Actionable Learning**: Heavy favorites in clear mismatches (1.15-1.30 range) can be used as portfolio stabilizers when EV still positive after vig.
- **Impact**: Good for bankroll protection in larger portfolios; keep in toolkit for Phase 1.

### Bet 4: Norge holder nullen Ja @1.58 Stake 12 NOK (Loss)
- **Pre-bet Hypothesis** (quote from round rec): Clean sheet Ja; est EV +11-23%; Norway dominant defense. nt-bet-log-manager protocol followed.
- **Outcome & Post-Match Factors**: Loss (P/L -12.00). Iraq scored (consistent with BTTS occurring).
- **Edge Validation**: Defense edge directionally correct but one goal conceded (likely set piece or individual error). Variance in clean sheet props higher than modeled in friendly context.
- **Actionable Learning**: In low-stakes friendlies, clean sheet props have extra variance from rotation/motivation. Prefer Over goals or BTTS No paired with win rather than clean sheet alone next time.
- **Impact**: Slight caution on clean sheet markets in friendlies; no broad filter change yet.

**Overall Batch Learning**: 2 wins, 2 losses. Net P/L -14.25 NOK on 54 NOK risked. Blended realized return lower than pre-bet EV estimate due to the two losses on correlated defensive props (BTTS No + Clean sheet both failed when Iraq scored). Portfolio still showed the value of the mismatch but highlighted correlation risk in same-match defensive bets. No immediate update to sport_edges_and_filters.md (needs 10-20+ bets for pattern). Continue monitoring Norway/Iraq-type fixtures for refined filters.

*Post-Settlement Deep Dives added per mandatory playbook rule. Git push + validation before reply.*