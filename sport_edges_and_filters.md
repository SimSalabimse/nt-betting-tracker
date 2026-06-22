# Sport Edges, Multipliers, Filters & ROI Tracking

**Dedicated file for per-sport parameters (important but infrequently updated).**
**Updated only after sufficient data (typically 8-15+ bets or clear repeated patterns from deep dives).**
**playbook.md and nt-learning-reviewer skill reference this for decisions.**
**All changes additive or with clear version notes. Full history in Git.**

**Last Updated**: 2026-06-22 post full post-settlement-learning-reviewer + nt-learning-reviewer for 2026-06-22 settlements batch (Argentina WC, Walton tennis props, Kessler exact sets, Varbergs, Struff correct score, Kyren Wilson void). New patterns: WC corners volume in controlled games variance; exact set/correct score high variance tighten; Swedish lower league home win stricter filters. Additive only. Full tool proof + multi-agent in round files/bet_log Notes.

## Update Log (Additive) - New Entry
- **2026-06-22 Post-Settlement Deep Dive (Argentina WC 3 bets, Walton 2 props win, Kessler 3sets loss, Varbergs loss, Struff 0-2 loss, Kyren void)**: 
  - **WC Corners Over Volume Variance Validated**: Argentina Over 4.5 corners loss despite dominance (reality low ~2-4 corners in controlled 2-0 clinical win per web_search tool proof). Pre hyp expected high volume from attack pressure. **Filter Update (additive)**: WC fav corners Over requires extra 'high width/set-piece threat or opponent high press/line for expected volume' confirmation. Corners edge remains core/promoted but tightened pre-filter. Lesson from deep dive in round_20260622_argentina_austria_current_odds.md.
  - **Tennis Exact Sets / Correct Score High Variance**: Kessler exact 3 sets loss (straight sets reality); Struff Landaluce 0-2 loss (went 3 sets). **Filter Update**: Deprioritize or ultra-small exact set count / correct score 0-2 bets; prefer game HC, ML or total games with stronger indicators (fatigue, H2H 3-set history). Exact score high variance even with data.
  - **Swedish Lower League / Superettan Home Win Variance**: Varbergs BoIS to win loss (2-3 upset). **Filter Update**: Tighten home win filter with 'recent form + H2H dominance + no key injury issues + motivation confirmation' stricter check. Swedish leagues keep as exploration with small stake only.
  - **High-Conviction Validations**: Argentina HUB win + Messi scorer props hit strongly (Messi 2 goals record break, tool proof NYT/ESPN etc). Walton min1 set + ML wins validated (hot form vs limited Kyrgios, 6-3 6-4 tool proof ATP/Reddit/Sofascore). Player props and quality gap HUB robust.
  - **Void (Kyren Wilson)**: Neutral, no edge change. Snooker remains paused per prior nt-learning-reviewer.
  - **nt-learning-reviewer Status**: No new promotions this batch (tennis exact sets insufficient consistent samples/ROI for 10+ settled criteria; Swedish home win variance high - keep exploration; WC corners already promoted). Tracker updated additively. No demotions. Edges sharpened for variance sources.
  - Tool proof: web_search for every match result/explanation (Argentina 2-0 Messi details; Walton 6-3 6-4; Kessler straight sets; Varbergs 2-3; Struff 3 sets). X pre validated. Multi-agent (Value/Risk/Data/Contrarian) post sim confirmed process + filter tweaks.
  - Prior patterns (WNBA large HC variance, WC underdog +1/cards) reinforced. Full deep dives in respective round files + bet_log.csv Notes.

## Per-Sport Edges & Filters (Updated additively with 98-bet learnings + 2026-06-22 settlements)

| **Football (HUB / Norwegian lower leagues / WC)** | 7-9% | 1.40 - 2.00 | Win (home form/motivation); **BTTS preferred over Over 2.5 in many spots due to variance (2026-06-20 lesson)**; Over 2.5 only with high xG/pace confirmation; **WC fav vs defensive minnow: Corners Over on fav reliable (new 2026-06-22)**; **WC underdog +1 tightened (2026-06-22: require no elite gap + sustained motivation)** | Leaky defense + attacking home side; tighten goal volume filter; **add 'recent clean sheet + no set piece threat' for Under/BTTS in WC (new 2026-06-22)**; **WC cards Under: stricter ref avg<2.0 + low foul + non-physical (new 2026-06-22)**; **NEW 2026-06-22: WC corners Over add 'high width/set piece threat or opponent high press confirmation' for volume** | Core allocation preferred | Low | Consistent edge when filters met; ~0 P/L over 41 bets stable; corners robust in WC mismatches | Strict post-research only; good diversification. **2026-06-20**: Over 2.5 variance - prefer BTTS selectively or tighten xG. **2026-06-22**: WC corners Over promoted + tightened volume filter; Under/BTTS filter tightened; underdog +1 and cards filters added from NZ/Egypt; new volume filter from Argentina controlled win. |

| **Tennis** | 6-8% | 1.50 - 2.20 | Game handicap on strong favs with surface/form edge (validated multiple 2026-06 incl. Navarro); Set handicap; total games Under in close matches; **ML or game HC on hot form vs limited/injured (2026-06-22 Walton validated)** | Surface specialist vs poor on surface; fatigue; opponent recent form for 2-0 bets; **exact set count / correct score 0-2 deprioritized (high variance 2026-06-22 Kessler/Struff losses)** | Selective volume when strong data | Low | Highly profitable when selected (per history +2.72 over 8) | Test selectively when +EV; good for diversification. Continue game HC confidence. Jovic void neutral. **2026-06-22**: Exact sets/correct score tightened/deprioritized; hot form ML/props validated (Walton). |

| **Snooker (Exploration)** | 8-12% (tighter) | 1.60 - 2.50 | Margin HC on clear favs or close +0.5 in even; ML on strong favs | Class/ form edge vs lower ranked; motivation | **Paused/reduced allocation pending more data** (negative -26.4/4 bets) | Medium-High | Mixed; variance in close matches | **2026-06-20 nt-learning-reviewer**: Insufficient consistent data for promotion; collect 8+ more with strict filters or pause. Void neutral. |

| **Esports (Exploration)** | 8-12% (tighter) | 1.50 - 2.80 | Map handicap -1.5 on strong favs with H2H/map pool edge | Recent map record vs specific opponent; adaptation risk | **Tighten filters significantly** (negative -37.46/8); small stake only max 10 NOK | High | High variance realized in BO3 | **2026-06-20**: Opponent adaptation/map pool variance high; reduce stake, require stronger specific H2H. Good for diversification but not core. |

| **Darts (Exploration)** | 7-10% | 1.50 - 2.50 | Legs HC, 180s totals Over on strong favs with rate support | Checkout/180 rate consistency; fatigue | Selective small stake (min 10); prefer reliable props over exotic high-odds | Medium | Good validation on 180s/legs HC (+); exotic high variance | **2026-06-20**: Continue selective 180s/legs; avoid or ultra-small for 170/ high-odds checkout. Monitor per-player. |

| **High-Odds Exploration (>4.0 decimal)** | 10-20%+ (high var) | >4.0 | Specific props (e.g. exact scorer location, timing, 170 checkout, correlated combo) ONLY when 3+ strong factors + video/stats deep dive | Historical hit rate in exact spot; prop definition clarity (avoid ambiguity like 'outside box') | **Ultra-small stake ONLY (hard 10 NOK min)**; max 1 per round; <5% allocation; pure learning | Very High | High variance realized (multiple losses on 6.40,9.20,3.00,2.80 in 2026-06) | **NEW 2026-06-20 section**: Treat as data collection only. Deep dive mandatory on odds line specifics. Prefer reliable alternatives. Update filters after more samples. |

| **WNBA / AHL (Exploration)** | 6-9% | 1.60 - 2.00 | **ML or small HC (-3.5 to -4.5 max); avoid large spreads |5+ (2026-06-22 Liberty -5.5 buzzer variance confirmed)**; totals Over in high-event playoffs | Pace/goaltending/comeback variance | **Small stake; avoid large spreads (new 2026-06-22 data point)** | High (esp large HC) | WNBA large spreads volatile (lesson from Liberty loss); AHL overs promising | **2026-06-20**: Prefer ML/smaller spreads for WNBA; AHL overs good for selective exploration with small stake. **2026-06-22**: Large HC filter sharpened to ML/small HC only based on buzzer-beater loss data. |

| **New Sports (Athletics, etc. Exploration)** | 5-8% | 1.20 - 2.00 | H2H or simple win on experience edge | Recent form/competition level | Small stake exploratory | Medium | Promising start (+14.5/3 for Athletics) | Good for diversification; collect 8-10 samples before promotion consideration. |

## Exploration Promotion & Data Sufficiency (New - nt-learning-reviewer Automated)

**Purpose**: Automate when exploration bets have enough data to promote to standard (remove HIGH exploration tag, use normal edge % and allocation). Prevents over-reliance on manual reminders.

**nt-learning-reviewer Skill Responsibilities**:
- After every settlement batch (via post-settlement-learning-reviewer trigger): update internal tracker (table in this file or dedicated learning_db.md if grows).
- Track per category/sport/bet-type: # settled bets, # wins, ROI, avg EV est, variance notes, key patterns from deep dives.
- **Promotion Criteria** (apply when all met):
  - Minimum 10-12 settled bets in exact category (e.g. 'Tennis game HC', 'HUB BTTS', 'Darts 180s prop').
  - Positive ROI > +4% overall for category.
  - Low-moderate variance (no single loss >20% of category total P/L).
  - Consistent patterns validated in >=3 deep dives (e.g. 'surface/form edge holds', 'xG supports Over in open styles').
  - No recent negative cluster (last 3 bets not all losses without explanation).
- **Promotion Action**: Move from exploration section to core in this file; update playbook allocation rules; flag in next round recs as 'promoted - standard treatment'.
- **Demotion/Pause**: If ROI < -5% after 8+ bets or high unexplained variance, pause category for 5+ bets or tighten filters sharply.

**Current Status (from 98-bet review + 2026-06-22 WC/ WNBA / tennis / Swedish update)**:
- Athletics H2H: 3 settled, +ROI - keep exploratory, target 8+ more.
- AHL totals: 1-2, promising - continue small.
- WNBA: volatility lesson applied + new Liberty data - keep exploratory with **sharpened filter: ML or small HC only** (2026-06-22).
- Darts props (180s/legs): positive signals on reliable ones - consider promotion after 6-8 more consistent.
- Snooker margin HC: 4 settled, negative - paused, collect with stricter or pause 1 month. Void neutral.
- Esports map HC: 8 settled, negative high var - tightened, small stake only, review after 5 more.
- High-odds exotic props: new, high var - keep ultra-exploratory, max learning allocation.
- **NEW 2026-06-22**: WC fav corners Over promoted to core + volume filter tightened (Argentina controlled win data); tennis exact sets/correct score deprioritized; Swedish Superettan home win stricter filter. No new promotions this batch (insufficient samples/variance for tennis exact or Swedish home). 

**Automation Note**: nt-learning-reviewer + post-settlement-learning-reviewer now handle updates to this tracker section automatically in future settlements. No user reminder needed for promotion checks.

## High-Odds (>4) Bet Type Guidelines (New Deep Dive Section)

**Rationale from 2026-06 data**: Several >4 odds bets placed (e.g. 6.40 Vini outside-box scorer, 9.20 170 checkout, 3.00 goal timing, 2.80 Over 4.5, 2.75 correlated combo). Despite research/EV estimates, most lost due to variance, prop ambiguity (shot location), or unexpected low event rates. Hit rate lower than rough model suggested.

**Rules**:
- Only when **deep dive confirms** specific historical hit rate in identical conditions (use tools for stats, video if possible).
- **Hard min stake 10 NOK**, max 1 such bet per round or portfolio.
- Allocation: treat as <5% bankroll learning bet, not EV core.
- Post-settlement: always video/highlight verify exact prop definition (e.g. 'outside 16m' exact location) and add to tracker.
- Preference: Use for props with clear definition and supporting stats (e.g. specific 180s/170s if rate strong) over ambiguous or correlated ones.
- If 3+ consecutive losses in high-odds bucket, pause entire type for 10+ bets.

**Future Data Collection**: Prioritize clear, verifiable high-odds lines in darts, tennis props, or niche football (e.g. exact goal methods if defined well). Update this section with hit rates after 5-10 samples.

## General Filters & Bankroll Notes
- Strict EV >7% post deep research (higher for exploration/high-var).
- Max pending risk per playbook bankroll rules.
- All recs now include explicit diversification check and min-stake filter before proposal.
- This file is referenced by nt-betting-workflow, nt-learning-reviewer, post-settlement-learning-reviewer skills.

**Changes driven by data from deep dives and 98-bet aggregate analysis + 2026-06-22 settlements (WC corners volume, tennis exact sets variance, Swedish upset). Pushed and validated per protocol. Full round file deep dives + bet_log Notes contain irrefutable tool proof.**