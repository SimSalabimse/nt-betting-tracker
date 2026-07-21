# Multi-Year Bankroll Plan (from ~500 NOK)

**Baseline:** 500 NOK (era start 2026-06-28)  
**Currency:** NOK · Operator: Norsk Tipping Oddsen  
**Engine truth:** `config.yaml` phases + `nt/phase.py` + `nt/risk.py`  
**Simulation:** `python run_nt.py project`

## Philosophy

1. **Survive first** — small bankrolls die from over-staking and tilt, not from missing one longshot.
2. **Equity drives size** — settled count only *nudges* +1 phase when form is healthy.
3. **Fractional risk** — daily risk % *falls* as equity scales (Phase 5: 6%, not 12%).
4. **Demote into drawdowns** — never “play up” to recover losses.
5. **Realistic math** — even +3–5% ROI on turnover is excellent after NT margin; compounding is slow and jagged.

## Current snapshot (illustrative)

| Metric | Typical early-era |
|--------|-------------------|
| Equity | ~550–580 NOK |
| Phase | 1A Protect (or 1B if unlocked) |
| Daily cap | ~30–52 NOK (phase floor/ceil) |
| Unit | 10–15 NOK |

Run `python run_nt.py status` for live numbers.

## Phase ladder (v4, still control-plane)

| Phase | Label | Enter equity | Stake | Doubles | Daily risk |
|-------|--------|--------------|-------|---------|------------|
| 1A | Protect | 0 | 10–12 | 0 | 8% · 30–42 |
| 1B | Stabilize | 580 | 10–15 | 0 | 9% · 38–52 |
| 2 | Build | 750 | 12–18 | 1 | 10% · 50–75 |
| 3 | Expand | 1200 | 15–28 | 2 | 9% · 70–140 |
| 4 | Mature | 2500 | 18–45 | 2 | 7% · 100–250 |
| 5 | Scale | 5000 | 20–70 | 3 | 6% · 120–400 |

Stability: count unlock needs rolling ROI ≥ 0%; demote if rolling ROI < −10% or drawdown ≥ 12% of peak (see `docs/PHASE_PLAN.md`).

## Multi-year roadmap

### Stage A — Protect & Stabilize (0–12 months)

| Item | Target |
|------|--------|
| Equity band | 500 → 750 |
| Phase | 1A → 1B → edge of 2 |
| Bet types | **Singles only** |
| Max acceptable DD | ~12–15% of peak equity |
| Process goals | Grade B+ always; high-odds only A; empty slip OK |
| Growth math | ~+30–50 NOK/month if edge slight; **flat is OK** |

**Rules of engagement**

- Never raise stakes outside phase band.
- After 3 consecutive losses → grade A only (config `loss_streak_grade_a_only`).
- If kill-switch fires → stop for the day; review edges next morning.
- **Kill-switch / today P/L** uses **settlement calendar day** (`updated_at` → Europe/Oslo), not match kickoff `date`.
- **Pending = recommend intent** (counts as open risk). Confirm with `place-ack` when live on NT; `abandon` if never placed (P/L 0, frees risk).

### Stage B — Build (12–24 months)

| Item | Target |
|------|--------|
| Equity band | 750 → 1 200–2 500 |
| Phase | 2 → 3 |
| Bet types | Singles default; **≤1 double/round** with correlation checks |
| Max acceptable DD | ~12% of peak; hard review at 15% |
| Growth | Compound via larger *allowed* daily risk, not reckless units |

Unlock doubles only when:

1. Phase ≥ 2 (`max_doubles_per_round ≥ 1`)
2. Each leg would pass as a single (EV, grade, p_model)
3. Combined stake ≤ phase stake_max × combo stake mult
4. Correlation score acceptable (see `docs/BET_TYPES.md`)

### Stage C — Expand / Mature (24–48 months)

| Item | Target |
|------|--------|
| Equity band | 1 200 → 5 000+ |
| Phase | 3 → 4 → 5 |
| Daily risk % | Declines (9% → 7% → 6%) |
| Focus | Attribution by sport/market/band; cut deep-red groups |

### Stage D — Scale (if and only if edge proven)

| Item | Target |
|------|--------|
| Equity | 5 000 → 15 000+ |
| Phase | 5 |
| Unit | Still fractional; never “life-changing” single-day risk |
| Optional | External bankroll split (play vs reserve) — *manual*, not in engine |

## Risk parameters (hard)

| Control | Rule |
|---------|------|
| Daily risk | `clamp(equity × pct, floor, ceil)` per phase |
| Kill-switch | Today P/L ≤ −max(floor, 8% equity) → no new bets |
| Phase demote | Rolling deep red or peak drawdown |
| High odds | Grade A + higher EV + stake × mult |
| Empty slip | Success |

## Growth scenarios (order-of-magnitude)

Assumptions for `nt project` defaults — **illustrative, not promises**:

| Scenario | Edge (ROI on stake) | Bets/week | 24-month equity (rough) |
|----------|---------------------|-----------|-------------------------|
| Bear | −2% | 8–12 | ~350–500 (demote, smaller stakes) |
| Base | +2% | 8–12 | ~700–1 200 |
| Bull | +5% | 10–15 | ~1 500–3 500 |

Variance is high: sequences of −80 NOK weeks are normal at 1A/1B. **Never change phase by hand to “catch up.”**

## When to increase unit size

Only when the **phase engine** advances you (equity + stability). Manual override of `config.yaml` stake bands is an expert action and breaks the “code is law” feedback loop if done for tilt recovery.

## Kill conditions (pause system, not revenge-bet)

1. Rolling 40 ROI < −15% with n ≥ 40 → full process audit before next recommend.
2. Equity < 0.85 × peak for prolonged period → stay demoted; reduce research volume if quality drops.
3. Agent or human repeatedly bypassing evidence → disable agent; return to checklist-only.

## Simulation

```bash
python run_nt.py project                    # default paths
python run_nt.py project --years 3 --sims 2000
python run_nt.py project --roi 0.03 --bets-per-week 10
```

Writes a report under `outbox/PROJECTION_*.md` without touching `bets.csv`.

## Relation to companion GUI

LuminaNT / desktop shows live equity, phase progress, and risk. The **ladder numbers** remain in `config.yaml`. GUI never invents a parallel bankroll.
