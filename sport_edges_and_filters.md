# Sport Edges, Multipliers, Filters & ROI Tracking

**Dedicated file for per-sport parameters (important but infrequently updated).**
**Updated only after sufficient data (typically 10-20+ bets or clear patterns from deep dives).**
**playbook.md references this for daily decisions.**
**All changes additive or with clear version notes. Full history in Git.**

**Last Updated**: 2026-06-14 (Initial extraction and organization from playbook.md)

## Core Rules for This File
- This is the single source for current edges, min EV per sport, best odds bands (multipliers), key filters, paused items, and high-level ROI summary.
- **Update Trigger**: After batches of settlements + deep dives reveal patterns (e.g. consistent underperformance in a league or strong validation for Darts). Not on every bet.
- **Exploration Priority**: Sports with low tracked volume but positive historical signals get priority in bet selection even if rough EV is borderline.
- **ROI Tracking**: Simple table updated periodically from bet_log.csv analysis (or future script).

## Global Parameters (Current Phase 1/2)
- Base Min EV: 7% (football primary); 8-10%+ for high-variance (esports, F1, lower leagues with limited data).
- Preferred Multiplier Band (most sports): 1.70 - 3.20 (balances edge realization and variance; avoid heavy favs <1.60 unless exceptional conviction, avoid longshots >4.0 unless data supports).
- Daily Portfolio Risk: 40-80 NOK max (Phase 1 conservative). Scale with bankroll growth.
- Stake per high-conviction single: 10-20 NOK (or system equivalent with 10 NOK/leg min). Individual sizing by EV + confidence.

## Per-Sport Edges, Filters & Status

| Sport | Current Min EV | Best Multiplier Range | Key Positive Edges / Markets | Key Filters / Cautions | Status / Allocation | Tracked Bets (approx) | ROI Summary (last update) | Exploration Priority |
otes |
|-------|----------------|-----------------------|------------------------------|------------------------|---------------------|-----------------------|---------------------------|----------------------|-------|
| **Fotball (Primary)** | 7% | 1.80 - 3.20 | Draws in cagey/motivated spots; Over/Under 2.5 (xG trends); BTTS; Asian HC; Underdogs in relegation/derby; Home strong defenses (clean sheet) | Lower leagues (Eliteserien/OBOS/2.div/Ykkösliiga): Higher variance for favorites -> stricter recent form + GD filters. Avoid heavy favs in very low tiers without strong H2H. | High allocation. Core of portfolio. | High (dozens) | Positive overall; monitor lower leagues separately | Low (well tested) | Norwegian domestic focus for edge vs sharp Euro leagues |
| **Darts** | 7-8% | 1.70 - 2.80 | Match winner (form, H2H, averages, streaks); Legs handicap | Veteran vs inconsistent; avoid fatigue spots in long events | Selective volume encouraged | Low | Highly profitable when selected (per history) | **HIGH** - Force inclusion in rounds with opportunities | Excellent diversifier; consistent player metrics |
| **Snooker** | 8% | 1.70 - 3.20 | Match winner (form, ranking diff, H2H in format, motivation); Frame handicap / total frames | Long matches: mental/tactical edges; motivated underdogs | Selective when clear +EV | Very Low | Positive signals in history | **HIGH** - Actively test more | Strong predictive factors; good for learning |
| **Tennis** | 7-8% | 1.70 - 3.50+ | Match winner (surface/form/H2H/fatigue); Set or games HC | Cancellations common in best-of-5 late rounds; physical toll | Good diversifier; low-variance short-odds favs reliable | Medium-High | Mixed (strong favs good, variance in dogs) | Medium | Accept cancellations as variance; prefer earlier rounds if similar |
| **Ishockey / Handball** | 8% | 1.85 - 2.80 (totals) | Totals (over often value); Period betting; HC in mismatches | High variance -> stricter filters | Medium allocation in systems | Medium | Positive in good spots | Medium | Good for systems with football |
| **Esports (CS2, LoL, Dota)** | 8-9%+ | 1.80 - 3.00 | Map/series winner (form, meta, H2H map record); -1.5 maps on strong teams | High variance; require strong recent map stats (>60-65% win rate); no major roster issues | Selective; tighter after losses | Medium | Mixed; good on handicaps when filtered | Medium (test more with filters) | Caution on singles; systems or handicaps preferred |
| **Basketball / MLB / Baseball** | 7-8% | 1.80 - 2.60 | Totals (pace/defense); ML/HC in mismatches | | Medium when data good | Medium | Positive in researched spots | Low-Medium | Stats-heavy good for modeling |
| **F1 / Motorsports** | 9-10%+ | 2.0 - 4.0+ (podium/value) | Outright or podium (practice/qual pace, strategy, track history) | High variance; require fresh tool research every time (practice results, weather, strategy) | Low volume, selective | Low | Variance realized (e.g. IndyCar) | Low (but test when strong data) | Full tool-assisted research mandatory; no shortcuts |
| **Sjakk / Chess** | 8%+ | Varies | Match winner or specific (prep, form, time control) | Low volume, high confidence only | Rare | Very Low | Positive when selected | Low (opportunistic) | Prep edge strong when data available |
| **Golf** | 10%+ | 2.5+ | Outright / Top placements (course fit, form, weather) | Low volume | Selective | Low | - | Low | Public bias on big names creates value |

## Exploration & Diversification Rules
- **Mandatory Exploration**: In any round with 3+ solid +EV opportunities in core sports (football/tennis), allocate at least **1 exploration slot** to Darts, Snooker, or other low-volume positive-ROI sports if any +EV (even at slightly lower bar ~5-6% rough EV) is available. Goal: Test to learn/confirm profitability. "If not tested, how can we learn?"
- **Diversification Target**: Aim for bets across 3+ uncorrelated sports per round when possible (reduces daily variance).
- **Portfolio Check**: Total daily risk 40-80 NOK; no over-concentration in one sport/league.

## Update Log (Additive)
- **2026-06-14**: Initial creation and organization from playbook Sport-by-Sport section. Added exploration priority column and explicit rules. Darts/Snooker flagged HIGH priority based on user feedback on past profitability and low volume.
- Future updates will document specific deep dive learnings that triggered changes (e.g. "After 12 more Darts bets with +X% ROI, lowered min EV to 6.5% for selective spots").

**This file is now the go-to for edge parameters. playbook.md will link here and focus on process.**
