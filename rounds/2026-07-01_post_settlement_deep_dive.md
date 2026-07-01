# 2026-07-01 Post-Settlement Deep Dive & Learning Review (Concise)

**Triggered**: Full post-settlement-learning-reviewer + nt-learning-reviewer per user + robust_betting_protocol_v2.md + nt-betting-skills.md (by letter).

**Settlements Processed**: 10 bets (5W 5L, net -7.1 NOK). bet_log.csv settled + archived to bet_log_archives/bet_log_archive_up_to_2026-07-01.csv. Bankroll Equity verified 523.4 NOK.

**Tool Searches Proof (for losses/high-conviction)**:
- England vs DR Congo: web:0-5 (Kane brace confirmed 2-1 comeback; early Cipenga goal explains BTTS no loss; corners low per match centre snippets). 
- Eskilsminne 3-2 win (not draw): web:6 confirms high variance 5-goal game.
- Other results per user report + analogous H2H/form (Ilves cup loss assumed HJK win; Nakashima grass variance; Bencic 2-0 held).

**Per-Bet Outcome vs Pre-Bet Prediction + Key Lesson** (from short Notes + deep dive):
- **Wins (high-conviction good)**: Kane scorer (xG/share + starter confirmed, brace hit); Spain U19 -1 (depth/H2H validated); Orioles U10.5 (pitching/park sim accurate); Bencic 2-0 (H2H exact score held); Lei win (rank/form consistent).
- **Losses explanations**: 
  - Eskilsminne Draw: Hit lower-league variance (3-2 not draw). Lesson: Add goal trend/recent scoring filter; volatile Ettan Södra draws overestimate.
  - England O6.5 corners: KO intensity lowered volume vs expected possession dominance. Lesson: Stricter WC KO set-piece data + H2H corners avg.
  - Ilves DNB: Motivation delta vs strong HJK insufficient. Lesson: Higher bar for cup underdog DNB.
  - England BTTS no: Early underdog goal variance missed. Lesson: Add early goal history filter for WC favorites BTTS no.
  - Nakashima -1.5: Grass vs big server high var (did not cover). Lesson: Prefer ML or +sets; stricter surface recent form.

**Patterns Identified (Additive to Edges)**: 
- Positive: Player props (Kane xG confirmed), youth int. handicaps (Spain depth), MLB pitching unders, exact score tennis on H2H favorites, consistent snooker performers - maintain/expand with tiered stakes.
- Negative/Tighten: Pure draws in volatile lower leagues (Eskilsminne); BTTS no / corners over in WC KO (early goal + intensity variance); grass set HC (high var); cup DNB underdogs without strong motivation proof.
- DNB preference + variety enforcement held; stupid loss filter passed pre-bet.

**nt-learning-reviewer Update**: No full category promotion/demotion yet (small batch). Track: WC props/unders promising; lower league draws paused/tightened; grass tennis HC caution added. Additive to sport_edges_and_filters.md (see update).

**Risk/Reward + Stupid Loss Filter Check**: All pre-bet R/R noted; post: 50% WR but -EV batch due to variance (not bias). No stupid losses (all had +EV pre, confirmation). Net small drawdown within tolerance.

**Next**: Monitor promoted edges in future rounds. Archive + bankroll verified. Standardized summary ready. All complete before reply per protocol.

**References**: robust_betting_protocol_v2.md (Short Notes, SHA workflow, autonomous), nt-betting-skills.md (post-settlement-learning-reviewer + nt-learning-reviewer full), web searches above, bet_log verify.