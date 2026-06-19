# Sport Edges, Multipliers, Filters & ROI Tracking

**Dedicated file for per-sport parameters (important but infrequently updated).**
**Updated only after sufficient data (typically 8-15+ bets or clear repeated patterns from deep dives).**
**playbook.md and nt-learning-reviewer skill reference this for decisions.**
**All changes additive or with clear version notes. Full history in Git.**

**Last Updated**: 2026-06-19 (post-settlement batch for Zverev/Sabalenka/Team Spirit via post-settlement-learning-reviewer + nt-bankroll-tracker + nt-bet-log-manager)

## Core Rules for This File
- This is the single source for current edges, min EV per sport, best odds bands (multipliers), key filters, paused items, and high-level ROI summary.
- **Update Trigger**: After batches of settlements + deep dives reveal patterns, or when nt-learning-reviewer skill runs and decides changes are needed. Not on every bet.
- **Exploration Approach**: Focus on **broad variety across sports and bet types**. Test low-volume or historically positive areas selectively when strong +EV lines appear. Use data volume and pattern consistency from deep dives to decide when to conclude or reduce focus on a specific sport/bet type. Avoid over-concentration in any one area (e.g., Snooker or Darts).
- **ROI Tracking**: Simple table updated periodically from bet_log.csv analysis or nt-learning-reviewer reviews.

## Global Parameters (Current Phase 1/2)
- Base Min EV: 7% (football primary); 8-10%+ for high-variance (esports, F1, lower leagues with limited data).
- Preferred Multiplier Band (most sports): 1.70 - 3.20 (balances edge realization and variance; avoid heavy favs <1.60 unless exceptional conviction, avoid longshots >4.0 unless data supports).
- Daily Portfolio Risk: 40-80 NOK max (Phase 1 conservative). Scale with bankroll growth.
- Stake per high-conviction single: 10-20 NOK (or system equivalent with 10 NOK/leg min). Individual sizing by EV + confidence.

## Post-Settlement Learning Review (2026-06-19 Zverev / Sabalenka / Team Spirit batch)

**Executed via post-settlement-learning-reviewer + nt-bet-log-manager + nt-bankroll-tracker skills** (fresh GitHub fetch of bet_log.csv, round_20260619_current_odds_tennis_darts_esports_recommendations.md, current_bankroll.md, this file; all SHAs + full content verified pre/post push).

**Outcomes**:
- Zverev vs Collignon Zverev -1.5 sets @1.57 stake 12 NOK → **Win** +6.84 NOK (payout 18.84). Hit cleanly as modeled from heavy class gap research.
- Sabalenka vs Bartunkova Sabalenka -1.5 sets @1.35 stake 12 NOK → **Loss** -12.00 NOK. Variance realized (likely set dropped or opponent overperformance).
- Team Spirit vs G2 Esports Team Spirit -1.5 maps @1.90 stake 10 NOK → **Loss** -10.00 NOK. Esports map variance in BO3 realized.

**Net from batch**: **-15.16 NOK** realized P/L
**Previous Equity**: 411.26 NOK → **New Equity 396.10 NOK** (Pending now 0)

**Pattern Insight (Additive Note)**: 
- Zverev heavy fav -1.5 sets held strong — reinforces tennis class mismatch handicap value when ranking/form gap is large and research aligns. Good validation for this bet type.
- Sabalenka and Team Spirit losses are normal variance on positive-EV lines (small stakes used). No indication of research flaw; continue conservative sizing (10-12 NOK) on such high-conviction handicaps.
- Esports map HC variance confirmed again (consistent with prior Jijiehao note). Strict recent map stats filter + max 10 NOK stake remains appropriate. Single loss does not pause the approach.
- Overall: Mixed batch but within expected variance for the selected +EV lines. No major filter changes needed at this sample size. Continue selective use of tennis/esports HC when Stage 2 research (form, H2H, meta) is strong.

**Bankroll note**: Equity now 396.10 NOK. All pending cleared. Strict discipline maintained.

## Post-Settlement Learning Review (2026-06-19 Grind Back + Hood batch)

**Executed via post-settlement-learning-reviewer + nt-bankroll-tracker + nt-bet-log-manager skills** (fresh GitHub fetch of bet_log.csv, round_20260619_current_odds_02.md, current_bankroll.md, this file; all SHAs + full content verified pre/post push).

**Outcomes**: 2 wins (Grind Back +7.50, Hood +6.00). Net +13.50 NOK on the two new bets. Combined with previous Mexico U2.5 confirmation.

**Pattern Insight (Additive Note)**: 
- Esports map/series lines on strong favorites (Grind Back -1.5 / 2-0) continue to deliver when recent map record + meta fit is strong. Variance is expected in BO3 but edge held.
- Darts props (highest checkout on dominant favorite) offered good value vs short ML and hit. Reinforces using props on clear favorites when data supports (form, averages, H2H).
- No major filter changes needed (small sample), but reinforces conservative 10 NOK max on high-variance props and esports map lines.

**Bankroll note**: Equity now 411.26 NOK. Pending only Zverev 12 NOK. Strict discipline maintained.

## Post-Settlement Learning Review (2026-06-19 batch) — 4 Under 2.5/5.5 bets

**Executed via post-settlement-learning-reviewer + nt-bankroll-tracker skills** (fresh GitHub fetch of bet_log.csv, round files, current_bankroll.md, this file; all SHAs + full content verified pre/post push).

**Outcomes**: 3 wins (SC Recife +7.44, U de Chile +7.00, Mexico WC +6.50) / 1 loss (Marlies -10.00). Net +10.94 NOK. Strong hit rate on pre-bet research edges (home defensive tendencies in Serie B, key injuries + moderate xG in Chile, elite goaltending + checking in AHL finals, cagey WC group stage low xG consensus).

**Pattern Insight (Additive Note)**: Unders in these specific controlled/low-event environments (domestic lower leagues with motivation/defensive edges, playoff finals, WC group stage with qualification caution) performed very well in this small batch. Validates continued selective use of Under 2.5/5.5 when Stage 2 research (xG, injuries, motivation, recent form) aligns strongly. No change to global min EV or core filters yet (sample of 4 is below typical 8-15 threshold for major update), but reinforces confidence in this bet type for diversification. Future rounds: prioritize similar profiles when +EV lines appear.

**Bankroll note**: Equity now 397.76 NOK (from 386.82). All pending cleared. Strict discipline maintained.

### Previous Post-Settlement Review (2026-06-18) — Retained for history

**Executed via post-settlement-learning-reviewer skill** (fresh GitHub fetch of bet_log.csv settled rows, recent round_*.md deep dive sections, current_bankroll.md, and this file; SHA + full content verified before/after).

### Executive Summary
Analyzed ~35 settled bets from June 15–18 2026 (including WC/friendlies football, grass tennis, esports, snooker, WNBA, MLB). Realized P/L net negative (~ -136.80 NOK total, bankroll equity now 363.20 NOK per nt-bankroll-tracker verification). 

**Key Wins**: Clear mismatch main lines performed well — tennis dominant fav 2-0 / HC (Svitolina, Bouzkova), football mismatch wins/over/BTTS (Ghana, England, Switzerland, Uzbekistan), some esports (Fokus -1.5).
**Key Losses & Variance Realized**: Czechia WC triple loss (win + Over 2.5 + Schick anytime, ~-60 NOK); Shelton grass 2-0 prop loss despite +25% EV (set dropped); Portugal props (Over + Ronaldo) loss; several snooker HIGH exploration and one esports map HC loss. Deep dives in round files (e.g. round_20260618_*.md) already documented initial post-match factors and learnings.

**Overall Assessment**: Main lines in strong mismatches continue to deliver when research aligns. High-specificity props (2-0 tennis, anytime scorer) and early int'l matches show elevated variance. Bankroll drawdown requires continued strict staking discipline. Research quality mostly strong but int'l data gaps highlighted.

### Research Quality Flags
- **Positive**: Most rounds show thorough Stage 1 full-scan + Stage 2 tool use (form, H2H, motivation, injuries via web_search / x_keyword_search). Post-settlement deep dives in round files are detailed and reference actual outcomes.
- **Flag for Improvement**: Czechia vs South Africa and Portugal vs DR Congo int'l matches — pre-bet research on squad/motivation/suspensions/attack volume was present but limited recent competitive data + possible low motivation in friendlies/WC prep led to higher slippage on props. **Recommendation**: For WC 2026 qualifiers and friendlies, mandate extra x_keyword_search or browse_page for last-24h team news/motivation confirmation before props or specific team bets. Consider raising min EV bar or reducing stake on props in these fixtures.
- **Flag for Improvement**: Shelton 2-0 grass bet — research captured grass power/serve edge well but opponent (Quinn) recent form/fatigue/set resilience not fully stress-tested. Deep dive correctly called it out. **Good learning capture**.

### Pattern Insights (with Sample Discipline)
- **Tennis (esp. grass surface 2-0 / set HC bets)**: Clear class mismatches (Svitolina 6-3 6-2, Bouzkova HC) hit reliably at high EV. However, Shelton 2-0 loss shows even strong grass favs can drop sets (opponent resilience or variance). Sample of strict 2-0 bets small but pattern of elevated variance vs main match-winner lines. **Actionable**: Add filter for opponent recent form/fatigue.
- **Football — Int'l / WC qualifiers & friendlies**: Main lines (team win, Over/Under, BTTS) in clear mismatches performed better (Ghana win hit, Uzbekistan Over+BTTS hit, England/Switzerland wins). Player props (Schick, Ronaldo anytime) and some team outcomes missed despite research. Pattern: Early int'l games have higher unpredictability due to motivation, experimental lineups, limited recent form. Domestic leagues more predictable.
- **Esports (map/series HC)**: Fokus -1.5 hit, Jijiehao -1.5 loss — variance as expected in Bo3. Reinforces existing filter for strong recent map stats + small stake (10 NOK). Single loss does not pause but tightens monitoring.
- **Snooker (HIGH exploration class)**: Multiple losses (OConnor, Brecel, Walden, etc.) consistent with high-variance nature noted in filters. Useful for portfolio variety but keep allocation low and selective.
- **Bankroll Impact**: Current equity 363.20 NOK (down ~27% from 500). All settlements processed with full nt-bankroll-tracker + nt-bet-log-manager validation and Git push. No pending risk. Continue 10-15 NOK max high-conviction stakes.

### Proposed Additive Updates to Filters/Edges
Ready-to-commit text blocks below. All changes additive. Pushed + re-validated via GitHub tools before this summary.

**Tennis Filters Addition**:
- For 2-0 or set handicap bets on strong grass favorites: require explicit check of opponent recent form, fatigue indicators, or H2H set resilience on surface. If opponent shows recent set-winning ability or match context suggests competitiveness (e.g. all-American QF), prefer match-winner or games handicap alternatives. Monitor hit rate on strict 2-0 props over next 8–10 instances before expanding allocation. (Based on Shelton deep dive + Svitolina confirmation.)

**Football (Int'l) Filters Addition**:
- For WC 2026 qualifiers, friendlies and early international matches: limit player props (anytime scorer, specific goalscorer) and very specific team outcome bets unless exceptional recent form + motivation data. Prioritize main lines (win, Over/Under 2.5, BTTS, clean sheet) backed by strong mismatch evidence and tool-confirmed team news. Raise min EV threshold slightly (+1-2%) or reduce stake on props in these fixtures due to observed higher variance (Czechia triple loss, Portugal props). Monitor over next 10+ settled int'l bets.

**Esports Filters Reinforcement (Additive Note)**:
- Map HC on favorites: Maintain max 10 NOK stake and strict >60% recent map win rate + H2H map record filter. Variance is normal; single loss (Jijiehao) does not change approach but confirms conservative sizing. Continue selective use for diversification.

**General Process Note**:
- All future post-settlement reviews will reference this section and only propose changes after >=8-10 sample threshold per pattern. nt-learning-reviewer and post-settlement-learning-reviewer skills will drive updates.

## Per-Sport Edges, Filters & Status

| Sport | Current Min EV | Best Multiplier Range | Key Positive Edges / Markets | Key Filters / Cautions | Status / Allocation | Tracked Bets (approx) | ROI Summary (last update) | Exploration Approach |
|-------|----------------|-----------------------|------------------------------|------------------------|---------------------|-----------------------|---------------------------|----------------------|
| **Fotball (Primary)** | 7% | 1.80 - 3.20 | Draws in cagey/motivated spots; Over/Under 2.5 (xG trends); BTTS; Asian HC; Underdogs in relegation/derby; Home strong defenses (clean sheet); BTTS No in mismatch | Lower leagues: stricter recent form + GD filters. Avoid heavy favs without strong H2H. **Add 2026-06-18 (post-settlement review)**: For WC 2026 qualifiers/friendlies & early int'l: limit player props (anytime scorer) and specific team bets unless exceptional data + motivation confirmation via extra tool search. Prioritize main lines (win/over/BTTS) in mismatches. Higher variance observed in recent props (Czechia, Portugal). Monitor next 10+ bets. **Add 2026-06-19**: Unders in controlled low-event domestic/playoff/WC group contexts performing strongly when research (xG, injuries, motivation) aligns — continue selective use. | High allocation. Core of portfolio. | High (dozens) | Positive overall; monitor lower leagues separately | Selective testing of props and BTTS; high volume supports detailed filters |
| **Darts** | 7-8% | 1.70 - 2.80 | Match winner (form, H2H, averages, streaks); Legs handicap | Veteran vs inconsistent; avoid fatigue spots in long events | Selective volume when strong data | Low-Medium | Highly profitable when selected (per history) | Test selectively when +EV; conclude phase after 10-15 bets with patterns; do not over-allocate |
| **Snooker** | 8% | 1.70 - 3.20 | Match winner (form, ranking diff, H2H in format, motivation); Frame handicap / total frames; margin HC in mismatches | Long matches: mental/tactical edges; motivated underdogs | Selective when clear +EV and not over-represented in recent portfolio | Low-Medium | Positive signals in history but watch for variance | **Variety priority** - Test when strong +EV; avoid consecutive rounds heavy in Snooker; conclude after data sufficiency.
| **Tennis** | 7-8% | 1.70 - 3.50+ | Match winner (surface/form/H2H/fatigue); Set or games HC; Over/Under totals | Cancellations common in best-of-5 late rounds; physical toll. **Add 2026-06-18 (post-settlement review)**: For 2-0 or set handicap bets on strong grass favorites: require opponent recent form/fatigue/H2H set resilience check. If indicators of competitiveness or opponent set-winning recent form, prefer match-winner or games handicap alternatives to mitigate set-drop variance (Shelton grass example). Monitor strict 2-0 hit rate over next 8-10 instances. Clear mismatches (e.g. Svitolina) remain high-confidence. | Good diversifier; low-variance short-odds favs reliable | Medium-High | Mixed (strong favs good, variance in dogs) | Active testing of totals and HC; good for variety |
| **Ishockey / Handball** | 8% | 1.85 - 2.80 (totals) | Totals (pace/defense); Period betting; HC in mismatches | High variance -> stricter filters | Medium allocation in systems | Medium | Positive in good spots | Use for portfolio balance and systems |
| **Esports (CS2, LoL, Dota)** | 8-9%+ | 1.80 - 3.00 | Map/series winner (form, meta, H2H map record); -1.5 maps on strong teams | High variance; require strong recent map stats (>60-65% win rate); no major roster issues. **Add 2026-06-18**: Max stake 10 NOK confirmed for map HC; variance normal (Jijiehao loss realized within model). Strict map record filter remains. Good for selective diversification. | Selective; tighter after losses | Medium | Mixed; good on handicaps when filtered | Test map handicaps and series when data supports; good diversifier |
| **Basketball / MLB / Baseball** | 7-8% | 1.80 - 2.60 | Totals (pace/defense); ML/HC in mismatches; player props | | Medium when data good | Medium | Positive in researched spots | Stats-heavy modeling spots; good for variety |
| **F1 / Motorsports** | 9-10%+ | 2.0 - 4.0+ (podium/value) | Outright or podium (practice/qual pace, strategy, track history) | High variance; require fresh tool research every time (practice results, weather, strategy) | Low volume, selective | Low | Variance realized (e.g. IndyCar) | Full tool-assisted research mandatory; opportunistic |
| **Sjakk / Chess** | 8%+ | Varies | Match winner or specific (prep, form, time control) | Low volume, high confidence only | Rare | Very Low | Positive when selected | Opportunistic when prep edge clear |
| **Golf** | 10%+ | 2.5+ | Outright / Top placements (course fit, form, weather) | Low volume | Selective | Low | - | Public bias on big names creates value; selective |

## Exploration & Diversification Rules
- **Core Principle**: Prioritize **broad variety across uncorrelated sports and bet types** in every round with multiple opportunities. Aim for 3+ different sports when possible.
- **Low-Volume / Historical Positive Areas** (Darts, Snooker, etc.): Test selectively when clear +EV lines appear and they fit diversification. Do not force or over-allocate to any single area across rounds. Use nt-learning-reviewer skill after settlements to assess if enough data (typically 8-15+ bets with repeated patterns) has been gathered to conclude or adjust focus for that area.
- **If One Sport Dominates**: Explicitly note in Stage 2 and adjust future prioritization to restore variety (e.g., if Snooker heavy, de-prioritize in next rounds and favor tennis, football props, esports, etc.).
- **Diversification Target**: Aim for bets across 3+ uncorrelated sports per round when possible (reduces daily variance).
- **Portfolio Check**: Total daily risk 40-80 NOK; no over-concentration in one sport/league or bet type.

## Update Log (Additive)
- **2026-06-14**: Initial creation and organization from playbook Sport-by-Sport section. Added exploration priority column and explicit rules.
- **2026-06-16**: Softened language, added dynamic variety focus.
- **2026-06-17**: Major update for variety-first approach. Removed any "force" language. Integrated nt-learning-reviewer skill as the mechanism for deciding when enough data exists to adjust priorities or conclude phases for specific sports/bet types (e.g., Snooker). Updated table and rules to explicitly prevent over-focus on any one sport and encourage natural variety. Snooker Exploration Approach changed to prioritize variety and conclude after data sufficiency.
- **2026-06-18**: Post-settlement-learning-reviewer skill executed after June 15-18 settlements batch. Added dedicated review section with Executive Summary, Research Quality Flags, Pattern Insights, and ready-to-commit additive filter updates for Tennis (grass 2-0 variance), Football Int'l props (higher variance in WC/friendlies), and Esports (small stake confirmation). Updated table rows for Tennis and Football with new cautions. All changes additive only. Full Git push + tree/content re-validation completed before presentation. References specific deep dives (Shelton, Jijiehao, Czechia, Portugal) from round files. Bankroll at 363.20 NOK noted for context.
- **2026-06-19**: Minor additive update for 2026-06-19 Under bets batch (3/4 hit). Added short pattern insight on controlled low-event unders performing well when research aligns. Reinforced Football row. No major filter changes (sample size small). Full Git push + validation completed. Equity now 397.76 NOK.
- **2026-06-19 (later)**: Added post-settlement review for Grind Back esports map win and Hood darts prop win. Reinforced confidence in filtered esports map lines and darts props on dominant favorites. No major filter changes. Equity now 411.26 NOK.
- **2026-06-19 (this batch)**: Added post-settlement review for Zverev (hit), Sabalenka and Team Spirit (variance losses). Reinforced tennis class mismatch HC and esports map HC conservative approach. No major filter changes. Equity now 396.10 NOK. All pushes validated.

**This file is now the go-to for edge parameters. nt-betting-workflow and nt-learning-reviewer skills reference it. Changes are driven by data from deep dives.**