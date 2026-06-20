# Sport Edges, Multipliers, Filters & ROI Tracking

**Dedicated file for per-sport parameters (important but infrequently updated).**
**Updated only after sufficient data (typically 8-15+ bets or clear repeated patterns from deep dives).**
**playbook.md and nt-learning-reviewer skill reference this for decisions.**
**All changes additive or with clear version notes. Full history in Git.**

**Last Updated**: 2026-06-20 post 98-bet comprehensive review (post-settlement-learning-reviewer + nt-learning-reviewer executed). Analysis of 97 settled bets: overall win rate 54.6%, total P/L -91.36 NOK. Core Football/HUB ~0 P/L over 41 bets (stable); exploration categories mixed (Athletics/WNBA positive small sample, Snooker/Esports negative - tighten). Key fixes applied: min 10 NOK hard stake, diversification to prevent repeat bet types, automated exploration promotion criteria, high-odds (>4) guidelines with deep dive notes.

## Update Log (Additive) - New Entry
- **2026-06-20 Comprehensive 98-Bet Post-Settlement Review (nt-learning-reviewer + post-settlement-learning-reviewer)**: 
  - **Duplicate/Same Bet Issue Fixed**: Identified clustering of similar edges (e.g. multiple Over 2.5/BTTS/Game HC in same rounds, duplicate Navarro entry). New rule: max 2 per bet category/type per round, require >=2 different sports/bet types in every portfolio. Statistical improbability of identical edge profiles across unrelated matches now enforced in nt-betting-workflow and recommendation logic.
  - **Exploration Logic Improved & Automated**: Added data sufficiency tracker and promotion criteria (see new section). nt-learning-reviewer skill now maintains per-category settled count, ROI, variance notes. Auto-flag promotion when e.g. >=10-12 settled + ROI>4% + consistent deep dive patterns. Removes manual reminder need. Current: Snooker exploration paused/reduced (negative ROI -26.4 over 4); Esports map HC tightened (variance high, -37 over 8); Darts props selective small stake only.
  - **High-Odds (>4.0) New Type Deep Dive**: Reviewed 6.40 (Vini outside box - lost, location ambiguity), 9.20 (170 checkout - lost, high variance), 3.00 (timing prop - lost), 2.80/2.75 correlated. Lesson: massive variance even with research support; hit rate lower than rough EV suggested. Rule: ultra-small stake (hard min 10 NOK), max 1 per round, pure learning bucket (<5% allocation). Prefer reliable props (180s totals, legs HC) over exotic. Added to filters.
  - **Min Stake Enforcement**: Hard filter implemented - any calc stake <10 NOK skipped or adjusted to exactly 10 only if EV remains positive post-adjust. All future recs enforce this (user confirmed hard limit).
  - **Edge/Sport Multiplier Adjustments**: Football core stable (keep 7-9% edge); Tennis game HC validated good (keep 6-8%, expand selectively); HUB Over 2.5 variance noted - tighten expected goal volume or prefer BTTS selectively (update from 2026-06-20 settlements); WNBA large spreads volatile - prefer ML/smaller HC (-4.5 to -6.5); Exploration allocation reduced for negative categories pending more data.
  - **Data Collection Needs**: More samples needed for: Athletics (promising +14.5/3), AHL overs (+), WNBA (volatility lesson), Darts props consistency, high-odds exotic props (more video verification). Prioritize 5-10 more per new category before promotion decisions. Snooker/Esports need pause or stricter filters.
  - Equity impact noted; bankroll discipline reinforced.

## Per-Sport Edges & Filters (Updated additively with 98-bet learnings)

| **Football (HUB / Norwegian lower leagues / WC)** | 7-9% | 1.40 - 2.00 | Win (home form/motivation); **BTTS preferred over Over 2.5 in many spots due to variance (2026-06-20 lesson)**; Over 2.5 only with high xG/pace confirmation | Leaky defense + attacking home side; tighten goal volume filter | Core allocation preferred | Low | Consistent edge when filters met; ~0 P/L over 41 bets stable | Strict post-research only; good diversification. **2026-06-20**: Over 2.5 variance - prefer BTTS selectively or tighten xG. |

| **Tennis** | 6-8% | 1.50 - 2.20 | Game handicap on strong favs with surface/form edge (validated multiple 2026-06 incl. Navarro); Set handicap; total games Under in close matches | Surface specialist vs poor on surface; fatigue; opponent recent form for 2-0 bets | Selective volume when strong data | Low | Highly profitable when selected (per history +2.72 over 8) | Test selectively when +EV; good for diversification. Continue game HC confidence. |

| **Snooker (Exploration)** | 8-12% (tighter) | 1.60 - 2.50 | Margin HC on clear favs or close +0.5 in even; ML on strong favs | Class/ form edge vs lower ranked; motivation | **Paused/reduced allocation pending more data** (negative -26.4/4 bets) | Medium-High | Mixed; variance in close matches | **2026-06-20 nt-learning-reviewer**: Insufficient consistent data for promotion; collect 8+ more with strict filters or pause. |

| **Esports (Exploration)** | 8-12% (tighter) | 1.50 - 2.80 | Map handicap -1.5 on strong favs with H2H/map pool edge | Recent map record vs specific opponent; adaptation risk | **Tighten filters significantly** (negative -37.46/8); small stake only max 10 NOK | High | High variance realized in BO3 | **2026-06-20**: Opponent adaptation/map pool variance high; reduce stake, require stronger specific H2H. Good for diversification but not core. |

| **Darts (Exploration)** | 7-10% | 1.50 - 2.50 | Legs HC, 180s totals Over on strong favs with rate support | Checkout/180 rate consistency; fatigue | Selective small stake (min 10); prefer reliable props over exotic high-odds | Medium | Good validation on 180s/legs HC (+); exotic high variance | **2026-06-20**: Continue selective 180s/legs; avoid or ultra-small for 170/ high-odds checkout. Monitor per-player. |

| **High-Odds Exploration (>4.0 decimal)** | 10-20%+ (high var) | >4.0 | Specific props (e.g. exact scorer location, timing, 170 checkout, correlated combo) ONLY when 3+ strong factors + video/stats deep dive | Historical hit rate in exact spot; prop definition clarity (avoid ambiguity like 'outside box') | **Ultra-small stake ONLY (hard 10 NOK min)**; max 1 per round; <5% allocation; pure learning | Very High | High variance realized (multiple losses on 6.40,9.20,3.00,2.80 in 2026-06) | **NEW 2026-06-20 section**: Treat as data collection only. Deep dive mandatory on odds line specifics. Prefer reliable alternatives. Update filters after more samples. |

| **WNBA / AHL (Exploration)** | 6-9% | 1.60 - 2.00 | ML or small HC (-4.5 to -6.5); totals Over in high-event playoffs | Pace/goaltending/comeback variance | Small stake; avoid large spreads | High (esp large HC) | WNBA large spreads volatile (lesson); AHL overs promising | **2026-06-20**: Prefer ML/smaller spreads for WNBA; AHL overs good for selective exploration with small stake. |

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

**Current Status (from 98-bet review)**:
- Athletics H2H: 3 settled, +ROI - keep exploratory, target 8+ more.
- AHL totals: 1-2, promising - continue small.
- WNBA: volatility lesson applied - keep exploratory with adjusted filters.
- Darts props (180s/legs): positive signals on reliable ones - consider promotion after 6-8 more consistent.
- Snooker margin HC: 4 settled, negative - paused, collect with stricter or pause 1 month.
- Esports map HC: 8 settled, negative high var - tightened, small stake only, review after 5 more.
- High-odds exotic props: new, high var - keep ultra-exploratory, max learning allocation.

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

**Changes driven by data from deep dives and 98-bet aggregate analysis. Pushed and validated.**