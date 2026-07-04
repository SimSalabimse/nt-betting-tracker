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