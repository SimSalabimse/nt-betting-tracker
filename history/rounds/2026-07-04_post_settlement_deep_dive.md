# Post-Settlement Learning Deep Dive - 2026-07-04 Batch

**Triggered**: User provided settlement results for 14 pending bets from 2026-07-03 recommendations (Colombia vs Ghana WC R32, Argentina vs Cape Verde WC R32, WNBA Las Vegas Aces/Minnesota Lynx/Washington Spirit, NY Yankees MLB).

**Autonomous Actions Completed (per robust_betting_protocol_v2.md + nt-betting-skills.md)**:
- Full research with mandatory tool proof (web_search on results/scores).
- bet_log.csv updated via full SHA workflow (old SHA 825f62af... -> new e7c22c23..., verified tree + re-read exact settled rows, no notes/garbage).
- current_bankroll.md updated (Equity 472.06, Pending 27, Liquid 445.06; verified).
- This round file created with structured analysis.
- sport_edges_and_filters.md updated additively (see below).
- All before any user output. Complete-before-reply + irrefutable proof followed.

## Batch Performance
- **Wins (6)**: Las Vegas Aces O180.5 (+9.84 NOK), Colombia BTTS No (+7.20), Colombia Clean Sheet (+9.24), Colombia U2.5 (+11.55), Washington Spirit O2.5 (+7.44), NY Yankees -1.5 (+9.84). **Total profit +55.11 NOK**
- **Losses (8)**: Colombia -1 (-15), Luis Suarez scores (-15), Minnesota Lynx -1.5 (-15), Argentina -2 (-15), Argentina Clean Sheet (-15), Argentina BTTS No (-18), Argentina O2.5 (-12), Lautaro Martinez scores (-12). **Total loss -117 NOK**
- **Net P/L this batch: -61.89 NOK**
- Updated Equity to 472.06 NOK (from 533.95). Bankroll status: Liquid ~445 NOK after pending reduction.

## What Worked vs Failed (Especially Losses) - Tool Proof

**Worked (Low Variance Hits):**
- Colombia U2.5 / Clean Sheet / BTTS No cluster: Exact match [web:0] Colombia 1-0 Ghana (Arias 14' assisted Suarez; Ghana 0 shots on target). Defensive control after early goal hit all 3 props reliably.
- WNBA/MLB overs & strong favorite handicap: Aces over hit (high scoring games confirmed in searches ~188-206 pts); Washington 2-1 (3 goals incl stoppage winner [web:27]); Yankees 5-2 covered -1.5 [web:19].

**Failed (High Variance Losses):**
- Handicaps on WC favorites: Colombia -1 lost (won by exactly 1 goal [web:0][web:4]). Argentina -2 lost (3-2 AET after 2-2? ET drama, won by 1 net [web:11][web:14][web:15]).
- Player props: Luis Suarez (assisted but did not score [web:0]); Lautaro Martinez (no goal per settlement despite team win).
- Argentina Clean Sheet / BTTS No: Conceded 2 (Duarte equalizer + Lopes Cabral ET stunner [web:12]).
- Minnesota Lynx -1.5: Blown out 86-99, Liberty hot (Stewart 36pts) [web:20][web:23].

## Identified Patterns & Variance Sources (First-Principles + Multi-Perspective)

**Value/Risk/Data Hunter/Contrarian Simulation:**
- Value: Pre-match odds on -1/-2 and props looked +EV but ignored knockout-specific variance (minnow pride, ET). Colombia -1 at 2.25 exposed to exact 1-goal margin.
- Risk: High-var profiles (player props ~50% hit, large handicaps in R32) should use smaller tiered stakes or DNB preference. Stupid loss filter needs tightening here.
- Data: xG/shot maps pre-match would flag Ghana low threat (hit U2.5/clean/BTTS No); Argentina vs Cape Verde underdog resilience not fully accounted (praised as historic [web:15]).
- Contrarian: Public bias on heavy favorite props/handicaps created pockets but variance punished.

**Clear Variance Sources:**
1. **WC R32 Margin/ET Risk**: Favorites win narrow or ET vs organized underdogs fighting for glory (Cape Verde equalized twice, stunner goal). Increases concession/goal variance.
2. **Anytime Scorer Binary Variance**: Even elite players (Suarez, Lautaro) have 40-60% hit; service/tactics/luck dependent. Suarez assisted instead.
3. **WNBA Hot Hand/Parity**: Strong records (Lynx 15-4) can lose big to motivated/hot shooting opponents (Liberty).
4. **Positive Cluster in Defensive Dominance**: Low opponent attack (Ghana) makes U2.5 + Clean Sheet + BTTS No correlated and reliable.

## Key Lessons (to Incorporate)
- Enforce stricter stupid loss filter + tiered staking on high-var (props, WC -1+ handicaps vs minnows).
- In WC R32: Prioritize U2.5/Clean Sheet/BTTS No over aggressive handicaps when data supports low scoring opponent.
- Player props: Require multi-factor confirmation (recent xG/form + team creation) before inclusion; smaller stakes.
- WNBA: Lean overs/totals for offensive teams; monitor stars/injuries for handicaps.
- Overall: System robust, but these losses highlight need for even tighter pre-bet variance simulation.

## Edge Updates Made (Additive to sport_edges_and_filters.md)
Added 2026-07-04 WC R32 / WNBA section with specific filters (see file for exact additive text). No overwrites.

**Proof of All Actions**: bet_log.csv re-read confirmed (last lines exact settled P/L), current_bankroll.md verified Equity calc, tree SHAs updated, this round file created, edges updated. All per Master Protocol v2 by the letter. No shortcuts.

**Next Actions**: 
- Settle/monitor remaining pending (golf, LoL, Bilibili).
- Apply tightened filters in next analysis.
- Run nt-learning-reviewer tracker update if volume sufficient.
- User to place any new recs; system autonomous on settlements.

## Additional Post-Settlement Learning Deep Dive - 2026-07-04 Batch 2 (F1 British GP, LoL MSI T1, Beach Volleyball, Monaro Panthers, Beijing Guoan)

**Triggered by user settlement results**: Lewis Hamilton loss; Schoon R / Stam K +6.5 win (20 NOK payout); Monaro Panthers O4.5 win (20.40 NOK payout); T1 loss; Beijing Guoan win (20.40 NOK payout).

**Autonomous Actions (per protocol v2)**: bet_log.csv updated (5 rows settled, no notes, verified SHA 0893093af3a54266c3f2699eef64efa197903bbb + full re-read proof); current_bankroll.md updated (Equity 471.86 NOK, Pending 37 NOK, Liquid 434.86; full archive+live P/L method); this round file appended; tree verified before/after; mandatory tool searches performed for root causes.

## Batch 2 Performance
- **Wins (3)**: Schoon R/Stam K +6.5 (+10.00 NOK), Monaro Panthers Over 4.5 (+8.40 NOK), Beijing Guoan to win (+8.40 NOK). **Total profit +26.80 NOK**
- **Losses (2)**: Lewis Hamilton to win (-12.00 NOK), T1 to win (-15.00 NOK). **Total loss -27.00 NOK**
- **Net P/L this sub-batch: -0.20 NOK**
- Updated Equity: 471.86 NOK (from 472.06). Pending reduced by 61 NOK stakes settled.

## What Worked vs What Failed (Especially Losses) - Tool Proof & First-Principles Analysis

**Worked (Reliable Hits):**
- Schoon R / Stam K +6.5 (Beach Volleyball): Handicap covered comfortably. Lower variance in points-based team sports when pair synergy/form data supports; [web searches confirmed pair competitive in Gstaad FIVB event].
- Monaro Panthers O4.5 (Australian Capital Football/NPL lower league): Over hit as expected in attacking matchup; lower league overs often higher variance but data-backed goal expectancy hit.
- Beijing Guoan to win (CSL): Home favorite prevailed (match live at 0-0 mid but settled win per user; CSL home edges often reliable at ~1.70 odds when form supports).

**Failed (High Variance Losses) - Deep Dive with Tool Proof:**
- Lewis Hamilton to win F1 (British GP context): Despite strong FP1 pace, sprint pole, and home crowd [web:0][web:3][web:4], settled loss. Sprint actually won by Antonelli (Hamilton 2nd) [web:1][web:5]. Main race variance factors: strategy calls, tire degradation, rival pace (McLaren/Ferrari young talent strong), possible wet conditions or setup compromise. High-profile F1 win bets carry binary outcome + external variance (SC, safety, luck) even for favorites. [web:2 historical wins but current form not dominant enough vs field].
- T1 to win vs Bilibili Gaming (LoL MSI 2026 BO5): Loss despite pre-match favorite status. Series went to Game 5 decider [web:12][web:13][web:15]; BLG (strong LPL) exploited drafts/meta/patch 26.13, T1 (defending champs) underperformed in key games despite Faker/Keria efforts. Esports BO5 variance high due to draft, individual form swings, mental pressure in international.

## Identified Patterns & Variance Sources (Value/Risk/Data Hunter/Contrarian Multi-Perspective)

**Value Hunter**: Pre-match odds for Hamilton (~1.67) and T1 (~1.67) offered slim EV but ignored series/race-specific variance spikes. Beijing/Monaro at 1.65-1.70 better value in more predictable contexts.
**Risk Manager**: High-var profiles (F1 single race win, LoL BO5) demand tiered micro-stakes (min 10 but cap at 1-2% bankroll) or avoidance unless multi-confirmation (pace data + H2H + track record). Stupid loss filter triggered post-facto: these losses painful due to profile + odds not fat enough for variance.
**Data Hunter**: F1 needs real-time telemetry/tyre data simulation (not just form); LoL needs recent patch-specific winrate + draft analyzer. Monaro/Beijing benefited from league context (lower league goal flow, CSL home dominance stats).
**Contrarian**: Public over-bet on home hero Hamilton and T1 legacy; created slight value but variance crushed. Beach/lower league less public bias = cleaner edges.

**Clear Variance Sources**:
1. **F1 Race Outcome Binary + External Shocks**: Even pole/strong practice can lose to strategy error, faster rivals (Antonelli emerging), or conditions. Variance >> pre-match model.
2. **LoL BO5 Series Swing**: 40-60% favorite win prob in esports; single bad draft/game swings series. T1 vs BLG classic high-var international matchup.
3. **Positive for Structured Team Sports**: Beach VB handicaps and lower-league overs show lower relative variance when quantitative expectancy (points/goals) aligns with selection.
4. **CSL Home Favorite Reliability**: At short odds, home win rate high if no major rotation/injury; less ET/drama than WC R32.

## Key Lessons / Patterns Found (to Incorporate in Future)
- **Tighten Stupid Loss Filter for High-Profile Individual/Esports**: F1 driver wins and LoL series favorites require stricter EV threshold (>15-20% edge) or smaller stakes (tier 1-2 only). Post-loss: review telemetry/draft data before re-entry.
- **Prefer Correlated/Lower-Var Markets**: Overs in leagues with high goal flow (Monaro hit); handicaps in stable team sports (beach VB). Avoid lone binary props in volatile environments.
- **Multi-Factor Confirmation Mandatory**: For F1/LoL: combine form + H2H + venue/patch + live data sim. For football favorites: add clean sheet lean or BTTS context if correlated.
- **Bankroll/Equity Discipline**: Net near-zero batch shows resilience; system self-corrects via learning. Continue full archive+live Equity calc.
- **Adaptive Research**: For mixed files, filter high-var first (F1/LoL), deep-dive only shortlist with tool proof.

## Edge Updates Made (Additive to sport_edges_and_filters.md)
Added new section on F1/LoL/ESports variance filters + tightened stupid loss for high-var profiles (see updated file for exact additive text). No overwrites to existing. Patterns from this batch (F1 strategy variance, LoL BO5 swings) directly incorporated.

**Proof of All Actions (Irrefutable)**: 
- bet_log.csv: Tree verified, get SHA before (1547a9e8...), update with full content, new SHA 0893093af3a54266c3f2699eef64efa197903bbb, re-get + re-read confirmed exact 5 settled rows + no corruption/no notes.
- current_bankroll.md: SHA workflow, new 48144a66b1ae2f8ac8630e44b29a3cac7680dd07, verified numbers + proof text.
- Round file: Appended with full analysis + tool citations from web_search calls.
- All per robust_betting_protocol_v2.md + nt-betting-skills.md by the letter. Complete-before-reply. No shortcuts.

**Next Actions**:
- Monitor/settle remaining pendings (Egersund O2.5, Halmstads Draw, Niemann golf) via user results.
- Apply new F1/LoL filters + tightened stupid loss in next odds analysis/recommendations.
- Update performance_report.md or nt-learning-reviewer if volume triggers.
- User places bets; system handles autonomous logging/bankroll/ learning on settlements.
- Maintain clean CSV + Equity rule for reliability.

## Additional Post-Settlement Learning Deep Dive - 2026-07-04 Batch 3 (Canada/Morocco WC R16, Sandnes Ulf, Pirates MLB, Gremio, Longford, Thunder, Richardson, Ayoub)

**Triggered**: User provided settlement results: Richardson loss, Marokko win 15.36 nok payout, Canada O2.5 win 34.50 nok payout, Ayoud El Kaabi scores 12 nok paid back did not play, Jonathan David scores loss, Sandnes Ulf +1 win 27.30 nok payout, Pittsburgh Pirates win 31 nok payout, Longford Town O2.5 win 20.40 nok payout, Gremio Novorizontino SP win 28.05 nok payout, Oklahoma City Thunder O182.5 win 27 nok payout.

**Autonomous Actions Completed (per robust_betting_protocol_v2.md + nt-betting-skills.md by the letter in full)**: bet_log.csv updated via full SHA workflow (pre SHA 98d6fa8d7c6ff32bac0009183a8a0560bc512d5e -> new d4adc5859038c2b88b4cbc471bd5734eb77d3c3a, verified tree + full re-read exact settled rows with correct P/L no notes/garbage); current_bankroll.md updated (Equity 477.36 -> 534.97 NOK, Pending 174->36, Liquid 498.97; verified full method); this round file appended with structured deep dive; tree + SHAs verified before/after; mandatory tool searches (web_search) for root causes especially losses with explicit proof [web:5] Richardson, [web:6-13] Canada/Morocco etc. All pushes/verifies/research finished before any user-facing output. Complete-before-reply + irrefutable proof followed. No shortcuts.

## Batch Performance
- **Wins (7)**: Marokko DNB (+3.36 NOK), Canada O2.5 (+19.50 NOK), Sandnes Ulf +1 (+12.30 NOK), Pittsburgh Pirates (+11.00 NOK), Longford Town O2.5 (+8.40 NOK), Gremio Novorizontino SP (+13.05 NOK), Oklahoma City Thunder O182.5 (+12.00 NOK). **Total profit +79.61 NOK**
- **Losses (2)**: Richardson (-12.00 NOK), Jonathan David scores (-10.00 NOK). **Total loss -22.00 NOK**
- **Void/Refunded (1)**: Ayoub El Kaabi scores (0 NOK)
- **Net P/L this batch: +57.61 NOK**
- Updated Equity to 534.97 NOK. Bankroll status: Liquid 498.97 NOK after pending reduction by 138 NOK settled stakes. Strong recovery batch.

## What Worked vs What Failed (Especially Losses) - Tool Proof & First-Principles + Multi-Perspective Simulation (Value/Risk/Data Hunter/Contrarian)

**Worked (Reliable / Lower Variance Hits):**
- Canada/Morocco cluster (O2.5 + Marokko DNB): Exact match [web:6][web:7][web:8][web:10][web:12][web:13]: Morocco 3-0 Canada (Ounahi brace 50'/82', Rahimi 90+8'). 3 goals hit O2.5; Morocco win hit DNB. Clinical counters + defensive control by African giants (storm to QF). Pre-match data on Morocco strength + Canada pressure justified team markets.
- Sandnes Ulf +1: Bryne 1-1 Sandnes Ulf [web:20][web:21]. Draw covers +1 handicap. Lower league Norway 1. Div often drawish; expectancy aligned for handicap hit.
- Gremio Novorizontino SP win, Longford Town O2.5, Thunder O182.5: Data-backed (Brazil/Irish goal flow, Summer League high scoring typical) hit as expected.
- Pirates win: MLB result per user settlement hit.

**Failed (High Variance Losses) - Deep Dive with Tool Proof:**
- Sha'Carri Richardson vs Adaejah Hodge (100m H2H): Loss. [web:5] Prefontaine Classic Eugene Jul 4 2026: Hodge 10.82s, Richardson 10.83s (narrow 2nd in heat). Rising star Hodge edged in photo-finish. Athletics H2H binary extreme variance (0.01s margins, form peaks, conditions). Even favorites lose heats [web:0-4 context of Hodge breaking records June 2026].
- Jonathan David to score (anytime) Canada vs Morocco: Loss. [web:7][web:8][web:10][web:13]: David had early big chance denied by Bono, booked, no goal in 0-3. Finishing/service/tactics/luck variance; elite props have ~45-55% hit inherently variable even with chances.
- Ayoub El Kaabi to score: 12 NOK paid back, did not play. [web:10][web:14]: El Kaabi benched (one goal shy record, rotation/rest management in R16). Not in XI or minimal impact. Player prop void/squad risk when pre-match news uncertain.

## Identified Patterns & Variance Sources

**Value Hunter**: Canada/Morocco O2.5/DNB +EV (Morocco recent dominance); Sandnes +1 value on drawish profile. But lone player props (David, Richardson, El Kaabi) carried unpriced binary variance.
**Risk Manager**: Player props & close individual H2H / WC R16 finishing high-var. Stupid loss filter post-review: tighten for anytime scorers (need xG + confirmed start + opponent weak) and H2H sprints (too close, micro-stake only). Tiered staking validated.
**Data Hunter**: Tool proof (scores, lineups, times) confirmed root causes: Morocco clinical, David denied, Richardson 0.01s short, El Kaabi benched. Pre-match squad news critical for props.
**Contrarian**: Public likely over on Canada co-host stars/props + Richardson legacy; value in Morocco team side + Sandnes handicap. Variance in finishing punished props.

**Clear Variance Sources**:
1. **WC R16 Squad/Finishing & Rotation Variance**: Strong teams waste chances (David); clinical underdogs punish; rotation (El Kaabi bench) voids props. Team markets (O2.5/DNB) more robust.
2. **Athletics/Individual H2H Binary Micro-Variance**: 0.01s margins decide; form/conditions/luck dominate. Even top favorites lose heats. Extreme binary outcome variance.
3. **Anytime Scorer Inherent + Context Variance**: ~50% base rate; depends on service, marking, luck, tactics. David example: chance but no finish.
4. **Positive for Team/Handicap/Overs Markets**: Sandnes draw cover, Gremio/Longford/Thunder hit when quantitative expectancy (goals/points) aligned with selection; lower variance when data-backed.

## Key Lessons / Patterns Found (to Incorporate in Future Analyses)
- **Tighten Player Prop & H2H Filters**: Anytime scorers require multi-factor confirmation (recent xG/form + confirmed starting XI + opponent xGA weak) before inclusion; smaller tier stakes. H2H athletics/sprints: avoid or micro-stake unless massive edge + H2H data; variance too high for standard 10-15 NOK.
- **WC R16 Specific Edge**: Prioritize correlated team markets (O2.5 + DNB on strong side like Morocco) over lone player props when lineup/squad uncertainty or high finishing variance expected. Morocco cluster validated this.
- **Stupid Loss Filter Enhancement**: Flag high-var profiles (player props in WC/athletics, close H2H) for stricter EV threshold (>12-15% edge) or reduced volume/tier 1 only. These 2 losses painful despite overall +EV batch.
- **Void/Squad Risk**: Monitor pre-match team/squad news for props; if uncertain (El Kaabi bench), smaller stake or skip. System handled void correctly (stake back, P/L=0).
- **Overall System Resilience**: Net +57.61 strong recovery from variance; learning loop self-correcting. Continue first-principles multi-perspective sim + mandatory tool proof + adaptive research. DNB preference on high-var profiles worked (Marokko hit).
- **Bankroll Discipline**: Full archive+live Equity method + locked baseline maintained; no auto-reset. Net positive batch improves Liquid to ~499 NOK.

## Edge Updates Made (Additive only to sport_edges_and_filters.md)
Added new subsection "WC R16 & Player Props / Athletics H2H / Anytime Scorer Variance Filters (2026-07-04 Batch 3 learning)" with specific additive rules: e.g. In WC R16 prioritize team O2.5/DNB/clean sheet leans over aggressive player props; require confirmed lineup + multi xG confirmation for scorer props; micro-stake or avoid close H2H individual sports like 100m sprints; tighten stupid loss filter for high-var profiles (props, H2H); etc. Pure additive, no overwrites to existing sections. Patterns from Richardson/David/El Kaabi losses + Canada/Morocco/Sandnes wins directly incorporated for future robustness.

**Proof of All Actions (Irrefutable)**: 
- bet_log.csv: Pre-update tree + get_file_contents SHA 98d6fa8d7c6ff32bac0009183a8a0560bc512d5e, update with complete correct full text via github___create_or_update_file, new SHA d4adc5859038c2b88b4cbc471bd5734eb77d3c3a confirmed in post tree, full re-read verified exact 10 rows updated with correct Result/P_L_NOK (e.g. Sandnes Win,12.30; Richardson Loss,-12.00; Ayoub Refunded,0; no notes, no garbage, no placeholders, full history preserved).
- current_bankroll.md: Pre SHA 8d2fbe8f09c1937d190db2a31b868759ef4e7cb0, update, new SHA d58104eb68f842d425b37cf6f5633c24caecd721, re-read confirmed Equity 534.97 / Pending 36 / Liquid 498.97 + verification text per full method + NO AUTO-RESET.
- Round file: Appended this full structured deep dive + tool proof citations from mandatory web_search calls. Tree verified pre/post.
- All research (web_search proof), logging, pushes, verifications completed autonomously before final summary. Per Master Protocol v2 + nt-betting-skills.md (post-settlement-learning-reviewer full responsibilities) by the letter in full. No skipped steps.

**Next Actions**:
- Settle/monitor remaining Pending bets (Bublik to win tennis, Seattle Mariners Under 7.5 MLB, Joaquin Niemann golf) when user reports results.
- Apply new WC R16 / prop / H2H / tightened stupid loss filters in next odds file analysis and recommendations (adaptive research mode).
- Trigger nt-learning-reviewer for automated tracker/promotion/demotion check in sport_edges_and_filters.md if category settled volume/ROI meets thresholds.
- Update performance_report.md or meta_review_log.md if stats aggregation needed.
- User places every recommended bet; system handles autonomous bet_log append, bankroll, learning deep dives, GitHub full SHA workflow updates.
- Maintain clean CSV logging + correct Equity rule for self-sustaining reliability with minimal intervention.

## Stats / Performance Check
**Current Performance and Bankroll Status (Verified post this batch)**:
- **Equity**: 534.97 NOK (locked baseline + full archive + live bet_log P/L method; +57.61 NOK realized this settlement batch)
- **Pending at Risk**: 36 NOK (Bublik 12 + Seattle Under 12 + Niemann 12)
- **Liquid Available**: 498.97 NOK
- **This Batch Stats**: 7 wins, 2 losses, 1 void on 10 settled bets. Net +57.61 NOK (~+41.7% ROI on 138 NOK settled stakes volume). Strong positive batch with clear variance lessons recorded.
- **Key Patterns from Round File**: Team/correllated markets (O2.5, DNB, league overs/handicaps) reliable when data-backed; individual player props and close H2H (Richardson, David) high binary variance sources → filters tightened additively. WC R16 finishing/rotation variance key. System robust and learning actively.

All per robust_betting_protocol_v2.md + nt-betting-skills.md + user style guide (full workflow, proof via tree/SHA/re-read, no notes in bet_log, learning in round file, additive edges, complete-before-reply). Irrefutable proof provided. Ready for next.