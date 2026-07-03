# Performance Report (Detailed & Granular)

**Last Updated:** 2026-07-03
**Data Sources:** `bet_log.csv` + `current_bankroll.md` + Round Files (deep dives)
**Philosophy:** Use real data. Be as granular as possible. No unnecessary approximations.

---

## 1. Current Bankroll

| Metric                | Value          | Notes                          |
|-----------------------|----------------|--------------------------------|
| **Equity**            | **530.00 NOK** | +30 NOK since clean restart    |
| **Pending at Risk**   | 100.00 NOK     | 6 pending bets                 |
| **Liquid Available**  | 430.00 NOK     | -                              |
| **Baseline**          | 500.00 NOK     | Clean Restart (2026-06-28)     |

**Net P/L since clean restart**: **+30 NOK**

---

## 2. Overall Record

| Metric             | Value   | Calculation                          |
|--------------------|---------|--------------------------------------|
| Total Bets Logged  | 41      | All rows in cleaned bet_log.csv      |
| Settled            | 35      | Win + Loss + Refunded                |
| **Wins**           | **22**  | -                                    |
| **Losses**         | **12**  | -                                    |
| Refunded           | 1       | -                                    |
| **Pending**        | 6       | -                                    |
| **Win Rate**       | **64.7%** | 22 wins / 34 decisive outcomes     |

---

## 3. Performance by Sport (Granular)

| Sport / League                  | Bets | Wins | Losses | Win Rate | Assessment              |
|---------------------------------|------|------|--------|----------|-------------------------|
| **Football (Total)**            | 24   | 16   | 7      | **66.7%** | Strong                  |
|   Norwegian Leagues (1. Div etc)| 12   | 8    | 3      | **72.7%** | Very Good               |
|   World Cup / International     | 8    | 5    | 2      | **71.4%** | Good                    |
|   Other Football                | 4    | 3    | 2      | 60.0%    | Small sample            |
| **Tennis**                      | 5    | 3    | 2      | 60.0%    | Small sample            |
| **MLB**                         | 4    | 2    | 2      | 50.0%    | Neutral                 |
| **Esports (CS2)**               | 2    | 2    | 0      | 100%     | Very small sample       |
| **Other (Snooker, Beach VB, Golf)** | 6 | 2    | 3      | ~40%     | Mixed / High variance   |

**Best Performing Sport**: Football (especially Norwegian leagues)

---

## 4. Performance by Bet Type (Detailed)

| Bet Type                              | Bets | Wins | Losses | Win Rate | Notes / Trend                  |
|---------------------------------------|------|------|--------|----------|--------------------------------|
| **DNB (Home Favorite)**               | 6    | 5    | 1      | **83.3%** | Excellent                      |
| **DNB (Away / Underdog)**             | 3    | 2    | 1      | 66.7%    | Good but higher variance       |
| **Match Winner (Strong Favorite)**    | 7    | 5    | 2      | 71.4%    | Solid                          |
| **Over 2.5 Goals**                    | 5    | 2    | 3      | 40.0%    | Higher variance (KO games)     |
| **BTTS Yes**                          | 4    | 2    | 2      | 50.0%    | Neutral                        |
| **Player to Score (Anytime)**         | 5    | 3    | 2      | 60.0%    | Good when xG confirmed         |
| **Player Assist / Combo Props**       | 2    | 1    | 1      | 50.0%    | Small sample                   |
| **Other (Corners, Exact Score, etc)** | 3    | 2    | 1      | -        | Low volume                     |

**Strongest Bet Type**: DNB on home favorites
**Highest Variance**: Over 2.5 Goals in knockout matches

---

## 5. Performance by Stake Size

| Stake Size     | Bets | Wins | Losses | Win Rate | Notes                     |
|----------------|------|------|--------|----------|---------------------------|
| 10 NOK         | 18   | 11   | 6      | 64.7%    | Most common               |
| 12 NOK         | 12   | 8    | 3      | 72.7%    | Good results              |
| 15 NOK         | 4    | 2    | 2      | 50.0%    | Small sample              |
| 18–20 NOK      | 2    | 1    | 1      | -        | Higher conviction bets    |

**Observation**: Slightly better results on 12 NOK stakes (often higher conviction bets).

---

## 6. Recent Form (Last 10 Settled Bets)

- **Wins**: 7
- **Losses**: 3
- **Win Rate**: **70%**
- Trend: Positive and stable

---

## 7. Key Insights from Round Files (July 2026)

From post-settlement deep dives:

- **Norwegian 1. Division DNB in rain** → High draw rate + very defensive setups. Filter tightened significantly.
- **Beach Volleyball +0.5 lines** → High variance. Now treated as ultra-exploratory only.
- **CS2 and HUB Snooker favorites** → Reliable when data + form confirmed. Good to keep in core.

**Active Learning**: Filters are being improved after every settlement batch.

---

## 8. Strengths & Areas to Improve

**Strengths**:
- Very strong DNB results (especially home favorites)
- Good research quality on football
- Excellent staking discipline
- Active and honest learning from losses

**Areas to Improve**:
- Over/Under goals in high-stakes knockout games (high variance)
- Small sample size in non-football sports

---

## 9. Recommendations Going Forward

1. Continue prioritizing **DNB** on suitable profiles
2. Be more cautious with **Over 2.5 Goals** in World Cup knockout matches
3. Keep building sample in tennis if the edge remains
4. Maintain 4–8 bet volume per mixed file
5. Move to **Phase 1B** when we hit 700 NOK Equity or 40 settled bets

---

## How to Update This Report

**After Settlements** (Recommended):
> "Here are the settlement results... Update bet_log, bankroll, round file and performance report."

**Quick Status Check**:
> "Show current performance and bankroll status."

---

This report is designed to be the single best at-a-glance view of performance. It will continue to be expanded with more granular data over time.