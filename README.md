# NT Betting Tracker v3

Code-owned Norsk Tipping Oddsen system. You supply **odds** and **results**. The system owns stakes, phase, daily risk, portfolio construction, and bankroll math.

## Your only jobs

1. Set / accept starting bankroll baseline (locked in `config.yaml`: **500 NOK** era start 2026-06-28).
2. Drop an odds file in `inbox/` → run recommend → place what is in `outbox/PLACE_THESE.md`.
3. Drop results in `inbox/` → run settle.

## Commands

```bash
cd nt-betting-tracker
python3 -m pip install -r requirements.txt

python3 -m nt status          # equity, phase, daily cap
python3 -m nt validate        # ledger integrity
python3 -m nt refresh         # recompute state files

python3 -m nt recommend --odds inbox/my_odds.csv
python3 -m nt recommend --odds inbox/my_odds.csv --dry-run   # no Pending rows

python3 -m nt settle --results inbox/my_results.yaml
```

Templates: `inbox/odds_template.csv`, `inbox/results_template.yaml`.

## Bankroll (full era history)

```
Equity = 500 + sum(settled P/L in data/bets.csv)
```

`data/bets.csv` is the **full current-era ledger**:

- `source=era_archive` → rows from `bankroll_archive_up_to_2026_07_01.csv`
- later rows → all bets after that archive  

Pre-restart and other snapshots live under `history/archives/` (kept, not double-counted).

## Daily risk cap (auto)

```
daily_cap = clamp(equity × phase.daily_risk_pct, phase.floor, phase.ceil)
```

Recomputed on every `status` / `recommend` / `settle`. It **changes when equity or phase changes**.

At ~548 NOK equity in Phase **1B** this is about **66 NOK/day** (12% of equity, floor 55, ceil 80).

Kill-switch: if today’s realized P/L ≤ −max(40, 8% of equity), no new bets.

## Phase (auto)

Hybrid but **safe**:

- Equity ladder sets a base phase.
- Settled-count may unlock **at most one phase above** equity phase (if rolling ROI is not terrible).
- Prevents “193 bets → Phase 4 stakes” while bankroll is still ~550 NOK.

## Odds &gt; 2.5 — still allowed when data supports

**Not banned.** A selection at odds &gt; 2.5 is recommended only if:

1. Evidence grade **A** (enough sources + `p_model` + summary + failure modes),
2. EV after haircut ≥ high-odds minimum (default 8%),
3. Optional extra EV if that odds band has bad historical ROI in *this* ledger,
4. Stake uses `high_odds_stake_multiplier` (default 0.6×),
5. Cap on high-odds bets per round.

If the model’s probability and research support it, it will appear on the place slip.

Put research packs in `evidence/*.json` (see `evidence/example.json`). You can also pass `p_model` in the odds CSV.

## Layout (what is kept)

| Path | Role |
|------|------|
| `config.yaml` | All rules and numbers |
| `nt/` | CLI + engines |
| `data/bets.csv` | Era ledger (archive + live) |
| `data/state/` | Generated bankroll, phase, risk, status |
| `data/edges.jsonl` | Append-only lessons |
| `inbox/` / `outbox/` | Your I/O |
| `evidence/` | Research packs for candidates |
| `history/` | Full archives, old rounds, legacy docs |

Legacy playbooks / skills / old scripts are under `history/` only — they are **not** control-plane.

## Evidence JSON (minimal)

```json
{
  "match": "Team A vs Team B",
  "selection": "Team A DNB",
  "p_model": 0.62,
  "summary": "Form + H2H + lineup support",
  "failure_modes": "Red card; key striker out late",
  "sources": [
    {"url": "https://fbref.com/...", "takeaway": "xG edge"},
    {"url": "https://...", "takeaway": "no injuries"}
  ]
}
```

## Design principles

1. **Code is law** — phase, risk, P/L, empty slips.
2. **Empty slip is success** when nothing clears the bar.
3. **Full history preserved** — active era in `data/bets.csv`, everything else in `history/`.
4. **No profit guarantee** — process maximizes disciplined +EV attempts under NT rules.
