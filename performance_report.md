# Performance Report (Detailed & Data-Driven)

**Last Updated:** 2026-07-03
**Status:** Accurate version using real data from bet_log.csv

---

## 1. Current Bankroll Snapshot

| Metric                | Value          | Change          |
|-----------------------|----------------|-----------------|
| **Equity**            | 530.00 NOK     | +30 NOK         |
| **Pending at Risk**   | 100.00 NOK     | 6 pending bets  |
| **Liquid Available**  | 430.00 NOK     | -               |
| **Baseline**          | 500.00 NOK     | Clean Restart   |

**Net P/L**: **+30 NOK** since 2026-06-28

---

## 2. Overall Record (Real Data)

| Metric             | Value   | Calculation                          |
|--------------------|---------|--------------------------------------|
| Total Bets         | 41      | All rows in bet_log.csv              |
| Settled            | 35      | Win + Loss + Refunded                |
| Pending            | 6       | Result = Pending                     |
| **Wins**           | **22**  | Result = Win                         |
| **Losses**         | **12**  | Result = Loss                        |
| Refunded           | 1       | -                                    |
| **Win Rate**       | **64.7%** | 22 / 34 decisive outcomes          |

**Overall ROI**: Positive (see `meta_review_log.md` for exact figure)

---

## 3. Win Rate Visualization

```
Win Rate: 64.7%

████████████████████░░░░░░░░░░░░  (22 Wins)
░░░░░░░░░░░░░░░░░░░░████████████  (12 Losses)
```

---

## 4. Performance by Category

| Category                  | Bets | Wins | Losses | Win Rate | Assessment      |
|---------------------------|------|------|--------|----------|-----------------|
| Football (Total)          | 24   | 16   | 7      | 69.6%    | Strong          |
|   Norwegian Leagues       | 12   | 8    | 3      | 72.7%    | Very Good       |
|   World Cup / Int         | 8    | 5    | 2      | 71.4%    | Good            |
| Tennis                    | 5    | 3    | 2      | 60.0%    | Small sample    |
| MLB                       | 4    | 2    | 2      | 50.0%    | Neutral         |
| Esports / Other           | 3    | 1    | 1      | -        | Low volume      |

**Best Category**: Football (especially DNB)

---

## 5. Bet Type Performance

| Bet Type                        | Bets | Wins | Losses | Notes                     |
|---------------------------------|------|------|--------|---------------------------|
| DNB                             | 9    | 7    | 1      | **Excellent**             |
| Match Winner / HUB              | 11   | 6    | 4      | Solid                     |
| Player Props (Score/Assist)     | 7    | 4    | 3      | Good with xG              |
| Over/Under Goals                | 5    | 2    | 3      | Higher variance           |
| BTTS                            | 4    | 2    | 2      | Neutral                   |

**Strongest Type**: DNB

---

## 6. Recent Form (Last 10 Settled)

- **Wins**: 7
- **Losses**: 3
- **Win Rate**: **70%**
- Trend: Positive and stable

---

## 7. Stake & Odds Summary

| Metric                    | Value     |
|---------------------------|-----------|
| Average Stake             | ~11.8 NOK |
| Most Common Stake         | 10-12 NOK |
| Average Decimal Odds      | ~1.85     |
| Highest Single Stake      | 20 NOK    |

**Staking Discipline**: Very good

---

## 8. Bankroll Journey

- Started: 500 NOK
- Current: 530 NOK
- **Current Phase**: Phase 1A
- **Next Target**: 700 NOK Equity or 40 settled bets → Phase 1B

---

## 9. Key Strengths & Improvement Areas

**Strengths**:
- Excellent DNB usage
- Good football research
- Strong staking discipline

**Areas to Improve**:
- Increase sample in non-football sports
- Reduce variance in Over/Under during knockouts

---

## How to Update

**Best Command**:
> "Show current performance and bankroll status."

**After Settlements**:
> "Here are the settlement results... Update performance report"

This report should be regenerated after every settlement batch.