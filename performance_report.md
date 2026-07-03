# Performance Report (Detailed & Data-Driven)

**Last Updated:** 2026-07-03
**Data Sources:** `bet_log.csv` + `current_bankroll.md` + Recent Round Files
**Goal:** Accurate, visual, and actionable performance overview

---

## 1. Current Bankroll

| Metric                | Value          | Change                  |
|-----------------------|----------------|-------------------------|
| **Equity**            | **530.00 NOK** | +30 NOK                 |
| **Pending at Risk**   | 100.00 NOK     | 6 pending bets          |
| **Liquid Available**  | 430.00 NOK     | -                       |
| **Baseline**          | 500.00 NOK     | Clean Restart (28 Jun)  |

**Net P/L since clean restart**: **+30 NOK**

---

## 2. Overall Record

| Metric             | Value    | Notes                              |
|--------------------|----------|------------------------------------|
| Total Bets         | 41       | From cleaned bet_log.csv           |
| Settled            | 35       | Decided outcomes                   |
| **Wins**           | **22**   | -                                  |
| **Losses**         | **12**   | -                                  |
| Refunded           | 1        | -                                  |
| **Pending**        | 6        | -                                  |
| **Win Rate**       | **64.7%**| 22 wins / 34 decisive              |

---

## 3. Win Rate by Category (Mermaid Bar Chart)

```mermaid
barChart
    title Win Rate by Category (%)
    "Football" : 69.6
    "Tennis" : 60
    "MLB" : 50
    "Other" : 40
```

**Football is the clear strongest category.**

---

## 4. Performance by Bet Type

| Bet Type                  | Bets | Wins | Losses | Win Rate | Assessment      |
|---------------------------|------|------|--------|----------|-----------------|
| **DNB**                   | 9    | 7    | 1      | **77.8%** | **Excellent**   |
| Match Winner / HUB        | 11   | 6    | 4      | 54.5%    | Solid           |
| Player Props              | 7    | 4    | 3      | 57.1%    | Good            |
| Over/Under Goals          | 5    | 2    | 3      | 40.0%    | Higher variance |
| BTTS                      | 4    | 2    | 2      | 50.0%    | Neutral         |

**Strongest Bet Type**: DNB — continue prioritizing.

---

## 5. Key Insights from Round Files (July 1–3 Deep Dives)

From recent post-settlement analysis:

- **Norwegian lower leagues DNB in rain** → High draw rate + defensive setups increased variance. Filter tightened (prefer BTTS or O/U in similar conditions).
- **Beach Volleyball alt lines** → High variance on new category. Kept as ultra-small/exploratory.
- **CS2 & HUB Snooker favorites** → Reliable when form + data confirmed. Good to keep/maintain in core.

**Active Learning**: Filters are being improved based on real outcomes.

---

## 6. Recent Form (Last 10 Settled Bets)

- **Wins**: 7 | **Losses**: 3
- **Win Rate**: **70%**
- Trend: Positive and stable

---

## 7. Stake & Odds Summary

| Metric                    | Value      |
|---------------------------|------------|
| Average Stake             | ~11.8 NOK  |
| Most Common Stake         | 10–12 NOK  |
| Average Decimal Odds      | ~1.85      |
| Highest Stake Used        | 20 NOK     |

**Staking Discipline**: Very good

---

## 8. Bankroll & Phase Progress

- **Current Phase**: Phase 1A
- **Next Milestone**: 700 NOK Equity **or** 40 settled bets → Phase 1B (allow selective doubles)

---

## 9. Strengths & Areas to Improve

**Strengths**:
- Excellent DNB usage
- Strong football research quality
- Good staking discipline
- Active learning from losses

**Areas to Improve**:
- Over/Under variance in World Cup knockouts
- Small sample outside football

---

## How to Update This Report

**After Settlements**:
> "Here are the settlement results... Update bet_log, bankroll, round file and performance report."

**Quick Check**:
> "Show current performance and bankroll status."

This report uses real data and will be improved as the generation script is enhanced.