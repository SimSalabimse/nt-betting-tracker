# Performance Report

**Last Updated:** 2026-07-03
**Status:** Active & Detailed Version

---

## 1. Current Bankroll

| Metric              | Value      | Change Since Clean Restart |
|---------------------|------------|----------------------------|
| **Equity**          | 530.00 NOK | +30 NOK                    |
| **Pending at Risk** | 100.00 NOK | -                          |
| **Liquid Available**| 430.00 NOK | -                          |
| **Baseline**        | 500.00 NOK | -                          |

**Net Performance**: **+30 NOK** since clean restart (2026-06-28)

---

## 2. Overall Record

| Status        | Count     | Notes                              |
|---------------|-----------|------------------------------------|
| Wins          | ~22+      | Majority of settled bets           |
| Losses        | ~13+      | Controlled                         |
| Pending       | 6         | Recent bets from 2026-07-03        |
| Total Settled | ~35+      | Approximate from cleaned log       |

**Current ROI (Settled)**: Positive but modest (detailed breakdown in `meta_review_log.md`)

---

## 3. Recent Performance (Last 7 Days)

- Strong focus on Norwegian football + World Cup Round of 32
- Good use of **DNB** on high-variance profiles
- Diversification into tennis (Sabalenka) and other sports
- Tiered staking applied correctly
- Several positive EV bets logged

**Recent Highlights**:
- Multiple DNB wins on favorites
- Good player prop hits (Embolo, Balogun)
- Controlled losses on high-variance plays

---

## 4. Performance by Category (Summary)

| Category             | Bets | Wins | Losses | ROI Trend   | Notes                              |
|----------------------|------|------|--------|-------------|------------------------------------|
| Football (HUB/DNB)   | Many | Good | Medium | Positive    | Strongest category currently       |
| Player Props         | Some | Good | Few    | Positive    | Good when xG confirmed             |
| Tennis               | Few  | Mixed| -      | Neutral     | Low volume                         |
| Other Sports         | Few  | Mixed| -      | Neutral     | Exploration phase                  |

**Best Performing**: Football DNB + strong home favorites
**Needs Improvement**: High-variance player props in knockout stages

---

## 5. Key Lessons (Last Period)

- DNB is very effective on high-variance profiles
- Stupid loss filter is working well
- Overly conservative analysis (only 2 bets) was corrected
- Learning is now properly recorded in round files

---

## 6. Bankroll Progression

- **Phase**: Currently in **Phase 1A** of Long-Term Staking Plan
- **Next Milestone**: 700 NOK Equity **or** 40 settled bets → Move to Phase 1B (allow 1 double)
- **Risk Management**: Excellent discipline maintained

---

## 7. Action Items

- Continue balanced analysis (target 4–8 quality bets per mixed file)
- Keep recording detailed learning in round files
- Monitor progression toward Phase 1B

---

## How to Update This Report

**Manual Command**:
> "Show current performance and bankroll status."

**Regenerate Full Report**:
> "Generate performance report"

**Automatic Update**: This report should be regenerated after every settlement batch (handled by `post-settlement-learning-reviewer` + `nt-betting-workflow`).

---

**Detailed historical data** lives in:
- `meta_review_log.md`
- Individual round files in `rounds/`
- `bet_log.csv` (core data only)

This report is designed to be a clean, at-a-glance summary with tables.