# NT Status (auto-generated)

## Bankroll
- **Equity**: 547.57 NOK
- Realized P/L: +47.57 NOK (baseline 500.0)
- Pending risk: 0.00 NOK
- Liquid: 547.57 NOK
- Ledger: 193 bets (47 archive + 146 later)

## Phase (auto)
- **1B** — Controlled volume + selective doubles
- Stake band: 12–20 NOK
- Max bets/round: 5 | Max doubles: 1
- Rolling ROI: -1.2%

## Daily risk (auto — changes with equity/phase)
- Cap: **65.71 NOK** (`daily_cap = clamp(equity * phase.daily_risk_pct, floor, ceil)`)
- Open pending: 0.00
- Remaining today: **65.71 NOK**
- Today P/L: +0.00 | Stop if ≤ -43.81
- Can bet: **True**

## High odds policy
- Odds **> 2.5 are allowed** when evidence grade **A**, EV ≥ high-odds min after haircut, and stake uses high-odds multiplier.
- Historical bad band ROI raises the EV bar further — it does not hard-ban the band.

## ROI by odds band (this era ledger)
| Band | n | ROI | P/L |
|------|---|-----|-----|
| 1.5-1.8 | 71 | 0.0% | +0.0 |
| 1.8-2.2 | 53 | 15.3% | +102.3 |
| 2.2-2.5 | 21 | -32.2% | -78.6 |
| 2.5-3.0 | 10 | -1.9% | -2.3 |
| <1.5 | 28 | 16.6% | +64.6 |
| >=3.0 | 10 | -33.8% | -38.5 |

## Open pending
_None_

## Your workflow
1. Put odds in `inbox/`
2. `python -m nt recommend --odds inbox/YOURFILE.csv`
3. Place bets from `outbox/PLACE_THESE.md`
4. Put results in `inbox/`
5. `python -m nt settle --results inbox/YOUR_RESULTS.yaml`

Updated: 2026-07-12T18:06:58Z
