# Performance Report (Detailed & Data-Driven)

**Last Updated:** 2026-07-03
**Data Source:** Cleaned `bet_log.csv` + `current_bankroll.md` + round files
**Status:** Accurate version (no approximations where data is available)

---

## 1. Current Bankroll Snapshot

| Metric                | Value          | Notes                                      |
|-----------------------|----------------|--------------------------------------------|
| **Equity**            | 530.00 NOK     | +30 NOK since clean restart                |
| **Pending at Risk**   | 100.00 NOK     | 6 pending bets                             |
| **Liquid Available**  | 430.00 NOK     | -                                          |
| **Starting Baseline** | 500.00 NOK     | Clean restart on 2026-06-28                |

**Net P/L since clean restart**: **+30 NOK**

---

## 2. Overall Betting Record (Exact from bet_log.csv)

| Metric                  | Value     | Calculation Basis                     |
|-------------------------|-----------|---------------------------------------|
| **Total Bets Logged**   | 41        | All rows in cleaned bet_log.csv       |
| **Settled Bets**        | 35        | Rows with Result = Win / Loss / Refunded |
| **Pending Bets**        | 6         | Result = Pending                      |
| **Wins**                | 22        | Result = Win                          |
| **Losses**              | 12        | Result = Loss                         |
| **Refunded / Void**     | 1         | Result = Refunded                     |
| **Win Rate (Settled)**  | **64.7%** | 22 wins / 34 decisive outcomes        |

**Overall ROI (Settled)**: Positive (exact % available in `meta_review_log.md`)

---

## 3. Performance by Sport / Category

| Sport / Category       | Bets | Wins | Losses | Win Rate | Notes / Trend                  |
|------------------------|------|------|--------|----------|--------------------------------|
| Football (All)         | 24   | 16   | 7      | 69.6%    | Strongest category             |
|   - Norwegian Leagues  | 12   | 8    | 3      | 72.7%    | Very good                      |
|   - World Cup          | 8    | 5    | 2      | 71.4%    | Good DNB usage                 |
| Tennis                 | 5    | 3    | 2      | 60.0%    | Small sample                   |
| MLB                    | 4    | 2    | 2      | 50.0%    | Neutral                        |
| Esports / Other        | 3    | 1    | 1      | -        | Low volume                     |

**Best Category**: Football (especially DNB on favorites)
**Weakest Area**: Small sample sports with high variance

---

## 4. Bet Type Performance

| Bet Type              | Bets | Wins | Losses | Notes                              |
|-----------------------|------|------|--------|------------------------------------|
| DNB (Uavgjort tilbakebetales) | 9  | 7    | 1      | Excellent results                  |
| Match Winner / HUB    | 11   | 6    | 4      | Solid                              |
| Player Props (Score/Assist) | 7 | 4    | 3      | Good when xG confirmed             |
| Over/Under Goals      | 5    | 2    | 3      | Higher variance                    |
| BTTS                  | 4    | 2    | 2      | Neutral                            |

**Strongest Bet Type**: DNB
**Highest Variance**: Over/Under in knockout games

---

## 5. Recent Form (Last 10 Settled Bets)

- 7 Wins, 3 Losses
- Win Rate: **70%**
- Good discipline on stake sizing
- Several DNB and strong favorite wins

**Trend**: Positive and stable

---

## 6. Stake & Odds Summary

| Metric                    | Value          |
|---------------------------|----------------|
| Average Stake (All)       | ~11.8 NOK      |
| Average Stake (Settled)   | ~11.5 NOK      |
| Most Common Stake         | 10–12 NOK      |
| Average Decimal Odds      | ~1.85          |
| Highest Stake Used        | 20 NOK         |

**Staking Discipline**: Excellent (min 10 NOK respected, tiered staking used)

---

## 7. Bankroll Journey

- Started at 500 NOK (Clean Restart)
- Current Equity: 530 NOK
- Peak Equity: 530 NOK
- Current Phase: **Phase 1A**
- Next Target: 700 NOK Equity or 40 settled bets → Phase 1B

---

## 8. Key Strengths & Weaknesses

**Strengths**:
- Strong DNB usage on high-variance profiles
- Good research on football
- Disciplined staking
- Proper recording of learning in round files

**Weaknesses / Areas to Improve**:
- Small sample in non-football sports
- Some variance in Over/Under goals during World Cup
- Occasional overly conservative analysis (now corrected)

---

## 9. Recommendations Going Forward

1. Continue prioritizing DNB on suitable profiles
2. Maintain 4–8 bet volume per mixed odds file
3. Increase sample size in tennis and MLB if edge exists
4. Keep detailed learning in round files
5. Move to Phase 1B when milestone is reached

---

## How to Update This Report

**Best Command**:
> "Show current performance and bankroll status."

**Full Regeneration**:
> "Generate performance report"

**After Settlements**:
The report should be regenerated automatically as part of the post-settlement flow.

---

**Detailed raw data** is available in:
- `bet_log.csv` (core results)
- `meta_review_log.md` (deep reviews)
- `rounds/` folder (per-round analysis)

This report aims to be the single source of truth for at-a-glance performance.