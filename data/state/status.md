# NT Status (auto-generated)

## Bankroll
- **Equity**: 550.99 NOK
- Realized P/L: +50.99 NOK (baseline 500.0)
- Pending risk: 34.00 NOK
- Liquid: 516.99 NOK
- Ledger: 31 bets (0 archive + 31 later)

## Phase (auto)
- **1A+** — Protect+
- Stake band: 12–14 NOK
- Max bets/round: 5 | Max doubles: 0
- Rolling ROI: 16.6%

## Daily risk (auto — changes with equity/phase)
- Cap: **47.59 NOK** (`capital_v2 fail-closed: L0 freeze → L1 DD(15% REDUCED/25% FROZEN) → L2 weekly(8%|6u) → L3 daily(4%|3u) → remaining=min(phase_cap−open[−day_loss], portfolio_open_room 18% liquid); settlement-day P/L Europe/Oslo; working=equity−secure; phase_health may tighten size_mode/research_only only; unit = phase_continuous (primary) when enabled else liquid unit ladder`)
- Open pending: 34.00
- Remaining today: **13.59 NOK**
- Today P/L: +0.00 | Stop if ≤ -20.68
- Can bet: **True**

## High odds policy
- Odds **> 2.5 are allowed** when evidence grade **A**, EV ≥ high-odds min after haircut, and stake uses high-odds multiplier.
- Historical bad band ROI raises the EV bar further — it does not hard-ban the band.

## ROI by odds band (this era ledger)
| Band | n | ROI | P/L |
|------|---|-----|-----|
| 1.5-1.8 | 13 | -7.4% | -10.3 |
| 1.8-2.2 | 13 | 29.4% | +43.2 |
| 2.2-2.5 | 1 | 140.0% | +14.0 |
| <1.5 | 1 | 37.0% | +4.1 |

## Open pending
- [Pending] 2026-07-21: van Gerwen, Michael vs van Duijvenbode, Dirk / Vinner: van Gerwen, Michael @ 1.5 stake 12
- [Pending] 2026-07-21: Clayton, Jonny vs Anderson, Gary / Totalt antall runder 18.5: Over 18.5 @ 1.8 stake 12
- [Pending] 2026-07-21: Brockmann, Tessa Johanna vs Jacquemot, Elsa / Game handikap 3.5: Brockmann, Tessa Johanna +3.5 @ 1.87 stake 10

## Your workflow
1. Research → `evidence/*.json` (see `nt research scaffold`)
2. Put odds in `inbox/`
3. `python run_nt.py recommend --odds inbox/YOURFILE.txt`
4. Place bets from `outbox/PLACE_THESE.md`
5. Put results in `inbox/` → `python run_nt.py settle --results …`
6. Review: `python run_nt.py analyze` · `learn` · `edges`

Optional: `project` (bankroll sim) · `agent ask` (assist only)

Updated: 2026-07-23T16:34:31Z
