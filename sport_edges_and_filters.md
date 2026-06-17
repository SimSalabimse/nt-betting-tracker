# Sport Edges, Multipliers, Filters & ROI Tracking

**Dedicated file for per-sport parameters (important but infrequently updated).**
**Updated only after sufficient data (typically 8-15+ bets or clear repeated patterns from deep dives).**
**playbook.md and nt-learning-reviewer skill reference this for decisions.**
**All changes additive or with clear version notes. Full history in Git.**

**Last Updated**: 2026-06-17 (Dynamic variety update + nt-learning-reviewer integration)

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

## Per-Sport Edges, Filters & Status

| Sport | Current Min EV | Best Multiplier Range | Key Positive Edges / Markets | Key Filters / Cautions | Status / Allocation | Tracked Bets (approx) | ROI Summary (last update) | Exploration Approach |
|-------|----------------|-----------------------|------------------------------|------------------------|---------------------|-----------------------|---------------------------|----------------------|
| **Fotball (Primary)** | 7% | 1.80 - 3.20 | Draws in cagey/motivated spots; Over/Under 2.5 (xG trends); BTTS; Asian HC; Underdogs in relegation/derby; Home strong defenses (clean sheet); BTTS No in mismatch | Lower leagues: stricter recent form + GD filters. Avoid heavy favs without strong H2H. | High allocation. Core of portfolio. | High (dozens) | Positive overall; monitor lower leagues separately | Selective testing of props and BTTS; high volume supports detailed filters |
| **Darts** | 7-8% | 1.70 - 2.80 | Match winner (form, H2H, averages, streaks); Legs handicap | Veteran vs inconsistent; avoid fatigue spots in long events | Selective volume when strong data | Low-Medium | Highly profitable when selected (per history) | Test selectively when +EV; conclude phase after 10-15 bets with patterns; do not over-allocate |
| **Snooker** | 8% | 1.70 - 3.20 | Match winner (form, ranking diff, H2H in format, motivation); Frame handicap / total frames; margin HC in mismatches | Long matches: mental/tactical edges; motivated underdogs | Selective when clear +EV and not over-represented in recent portfolio | Low-Medium | Positive signals in history but watch for variance | **Variety priority** - Test when strong +EV; avoid consecutive rounds heavy in Snooker; conclude or reduce after sufficient data (10+ bets); favor other sports for diversification |
| **Tennis** | 7-8% | 1.70 - 3.50+ | Match winner (surface/form/H2H/fatigue); Set or games HC; Over/Under totals | Cancellations common in best-of-5 late rounds; physical toll | Good diversifier; low-variance short-odds favs reliable | Medium-High | Mixed (strong favs good, variance in dogs) | Active testing of totals and HC; good for variety |
| **Ishockey / Handball** | 8% | 1.85 - 2.80 (totals) | Totals (over often value); Period betting; HC in mismatches | High variance -> stricter filters | Medium allocation in systems | Medium | Positive in good spots | Use for portfolio balance and systems |
| **Esports (CS2, LoL, Dota)** | 8-9%+ | 1.80 - 3.00 | Map/series winner (form, meta, H2H map record); -1.5 maps on strong teams | High variance; require strong recent map stats (>60-65% win rate); no major roster issues | Selective; tighter after losses | Medium | Mixed; good on handicaps when filtered | Test map handicaps and series when data supports; good diversifier |
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

**This file is now the go-to for edge parameters. nt-betting-workflow and nt-learning-reviewer skills reference it. Changes are driven by data from deep dives.**
