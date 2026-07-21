# Market Coverage Agent

## Purpose

On high-volume matches (internationals, WC, big leagues with **40–200+ lines**), research used to tunnel-vision on:

- Match winner  
- Over/Under 2.5  
- BTTS  

and miss team totals, first goal, corners, cards, goalscorers, and specials.

The **Market Coverage Agent** is a mandatory pre-research catalog of **all** lines.

## CLI

```bash
# Auto: scan all high-volume matches in the dump
python run_nt.py research market-scan --odds inbox/current_odds_01.txt

# One match
python run_nt.py research market-scan --odds inbox/current_odds_01.txt --match "Frankrike"

# JSON only
python run_nt.py research market-scan --odds inbox/current_odds_01.txt --json --no-write

# Board runs coverage automatically
python run_nt.py research board --odds inbox/current_odds_01.txt
python run_nt.py research board --odds inbox/current_odds_01.txt --skip-market-scan
```

## Tiers

| Tier | ID | Markets |
|------|-----|---------|
| 1 | `T1_main` | ML, draw, O/U goals, BTTS, HC, DNB, team totals, first team goal |
| 2 | `T2_props` | Goalscorer, anytime, player stats (180s, etc.) |
| 3 | `T3_alt` | Corners, cards, halves/periods, odd/even |
| 4 | `T4_specials` | SGPs, multi-leg specials, exotic |

## Flags per line

| Flag | Meaning |
|------|---------|
| `interesting` | Priority deep-research candidate |
| `review` | Include in coverage pass; second priority |
| `skip` | Too short / too long / low research value |
| `noise` | Correct score / extreme longshots |

## Output

- `outbox/market_scans/<match>_<date>.md` — human **Market Scan Summary**
- `outbox/market_scans/<match>_<date>.json` — structured
- `outbox/market_scans/INDEX.json` — batch index

### Summary fields

- `total_lines` / `total_markets_approx`
- `tier_counts` / `family_counts`
- `interesting` / `review` / `skipped` / `noise`
- `recommended_deep_research` (queue)
- **`coverage_confidence_pct`** (0–100)
- `needs_manual_review` + `manual_review_tiers`
- `full_board_covered` (catalog complete enough to proceed)

## Workflow integration

1. `research market-scan` (or auto via `research board`)
2. Read coverage confidence; if low, manual-review flagged tiers
3. Deep-research **recommended_deep_research** + shortlist (not only O2.5)
4. Evidence packs → recommend

## Config (optional in `config.yaml` research section)

```yaml
research:
  high_volume_market_threshold: 40
  market_scan_top_n: 5
```

## Note

Coverage is **catalog + prioritization**, not automatic p_model. Honest research is still required before recommend.
