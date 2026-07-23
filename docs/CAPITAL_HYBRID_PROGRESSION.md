# Capital hybrid progression — half-steps, continuous unit, Variant A skim

**Status:** live (PR-1 secure Variant A · PR-2 half-steps + continuous unit)  
**SSOT numbers:** `config.yaml` (`phases`, `phase_continuous`, `capital_v2.secure_bucket`)  
**Engines:** `nt/phase.py` · `nt/capital_v2.py` · `nt/capital_runtime.py` · `nt/risk.py`  
**Projection (offline):** `python scripts/mc_phase_progression.py`  
**Agent rules:** `AGENTS.md` (Capital v2 + Phase hybrid sections)

This note is the operator-facing **before/after** and **Monte-Carlo narrative** for the hybrid capital package. It does not change live risk math — engines remain law.

---

## What changed (package)

| Piece | Before (pre hybrid package) | After (live) |
|-------|----------------------------|--------------|
| Phase labels | 1A → 1B → 2 → … (big equity jumps) | **1A → 1A+ → 1B → 1B+ → 2 → …** |
| 1A+ / 1B+ | — | Named half-steps; **`hard_phase_id`** keeps parent doubles/max_bets |
| Unit | Liquid ladder only (High-Volume **12 / 15 / 20**) | **`phase_continuous`**: unit rises inside band; ladder is fallback |
| Open / daily risk | Static phase floor/ceil/pct | **Lerp** toward next phase by `progress_inside_phase` |
| Secure bucket | Single-tier legacy or early Variant A | **Variant A:** soft **1.25×/15%**, hard **1.50×/30%** (hard replaces soft) |
| Unit at promotion | Could feel flat/jumpy | **Carry-forward floor** — unit never drops on promotion |

---

## Before / after: equity 500 → 550

Snapshot from live config via `scripts/mc_phase_progression.py` (static sizing; no bets).

**Before** = pre half-steps / continuous (old ladder: 1A until **580**, daily risk clamp **8% · 30–42**, unit **12** from capital ladder).  
**After** = live hybrid (`phase_continuous.enabled`, half-steps, continuous open-risk lerp).  
Secure ref HWM = **500** (baseline). Open risk free for this table (sizing only).

| Metric | Equity **500** before | Equity **500** after | Equity **550** before | Equity **550** after |
|--------|----------------------:|---------------------:|----------------------:|---------------------:|
| **Phase id** | 1A | 1A | 1A | **1A+** |
| **Hard phase** | 1A | 1A | 1A | **1A** (inherits) |
| **Unit (NOK)** | 12 | 12 | 12 | 12 |
| **Daily / open risk budget** | 40.00 | **42.31** | 42.00 (ceil-capped) | **47.44** |
| **Risk floor–ceil** | 30–42 | ~33.7–46.6 (lerped) | 30–42 | 35.0–48.25 (lerped toward 1B) |
| **Secure skim** | none (&lt;1.25×ref) | none | none | none |

### How to read 500→550

1. **Phase recognition:** hybrid awards **1A+ at 540** — the first named progress step before full 1B (580). Before hybrid, 550 was still plain 1A until 580.
2. **Unit stays 12:** continuous formula is whole-krone with `scale_factor=100` and 1A/1A+ bands cap early progress at **12** until later equity (unit **13** appears at **1B+ / 620**, **14** at phase **2 / 750**). The win is **earlier open-risk headroom**, not an immediate stake jump.
3. **Daily / open risk rises ~5 NOK** by 550 (42 → ~47) because continuous lerp lifts floor/ceil/pct inside 1A+ — more room to pack unit seats under the same research quality bar.
4. **Secure skim silent:** Variant A soft trigger is **1.25 × 500 = 625**. Path 500→550 never skims; profit stays fully working.

---

## Unit trajectory (static, continuous)

Live continuous unit + daily risk at operator checkpoints (equity-only phase; no demote):

| Equity | Phase | Hard | Unit | Daily risk | Floor–Ceil | Progress inside phase |
|-------:|:-----:|:----:|-----:|-----------:|:-----------|----------------------:|
| 500 | 1A | 1A | **12** | 42.31 | 33.70–46.63 | 0.93 |
| 520 | 1A | 1A | **12** | 44.10 | 33.85–46.81 | 0.96 |
| 540 | **1A+** | 1A | **12** | 45.90 | 34.00–47.00 | 0.00 |
| 560 | 1A+ | 1A | **12** | 49.00 | 36.00–49.50 | 0.50 |
| 580 | **1B** | 1B | **12** | 52.00 | 38.00–52.00 | 0.00 |
| 620 | **1B+** | 1B | **13** | 58.90 | 44.00–62.00 | 0.00 |
| 750 | **2** | 2 | **14** | 75.00 | 50.00–75.00 | 0.00 |

Formula (engine):  
`unit = floor( stake_min + (equity − enter_equity) / scale_factor )` clamped to `[stake_min, stake_max]`, then **max** with prior phase unit at this phase’s enter (carry-forward).  
Open knobs: lerp `daily_risk_{floor,ceil,pct}` from current → next by `progress_inside_phase`.

---

## Soft / hard skim interaction (Variant A)

**Config:** `capital_v2.secure_bucket` with `variant: A`

| Tier | Trigger | Transfer | Rule |
|------|---------|----------|------|
| **Soft** | equity ≥ **1.25 × ref_hwm** | **15%** of (equity − ref) whole krone | Fires first on a grind-up from baseline |
| **Hard** | equity ≥ **1.50 × ref_hwm** | **30%** of (equity − ref) | **Replaces** soft — never 15%+30% stacked |
| **Neither** | below soft | 0 | ref unchanged |

**Always applied after a candidate transfer:**

1. Working ≥ max(**55%** equity, **8 × unit**)  
2. Liquid floor: `equity − secure_after − open_risk ≥ phase daily_risk_ceil` (never skim the desk dry)  
3. **ref_hwm ← working equity after skim** (ratchet)

### Worked examples (ref = 500, open = 0, unit ≈ 12)

| Equity | Tier | Raw profit | Transfer | Working after | New ref |
|-------:|:----:|-----------:|---------:|--------------:|--------:|
| 620 | — | 120 | 0 | 620 | 500 (unchanged) |
| 625 | soft | 125 | **18** | 607 | **607** |
| 700 | soft | 200 | **30** | 670 | **670** |
| 750 | hard | 250 | **75** | 675 | **675** |
| 800 | hard | 300 | **90** | 710 | **710** |

### Path interaction (why hard is rare after soft)

If the book grinds through soft first (e.g. hits 625–700), **ref ratchets to working**. Hard’s absolute bar moves up with ref (`1.50 × new_ref`). A single soft skim at 700 leaves working **670** and ref **670** — hard now needs equity ≥ **1005**, not 750. Hard is the **jump / windfall** tier when equity leaps over 1.50× **before** soft can reset ref (or after unlock resets working/ref dynamics).

**Unlock (not automatic on every settle path in MC):**

- Auto: `unlock_after_settled` (**25**) settles since lock  
- Manual: `python run_nt.py capital unlock-secure --confirm` (7d cooldown)

Secure is **not** P/L — ledger equity still `baseline + Σ terminal P/L`. Secure only partitions **riskable working** capital.

---

## Monte-Carlo narrative (time to milestones)

**Command (smoke embedded below):**

```bash
python scripts/mc_phase_progression.py --paths 1500 --seed 42
```

### Documented assumptions (toy book — not live edge)

| Assumption | Value |
|------------|--------|
| Start | equity **500**, ref_hwm **500**, secure **0** |
| Market | odds **1.95**, edge **+2.5%** on stake → p_win ≈ **0.526** |
| Cadence | ≤ **2** unit singles / day, **same-day settle** (optimistic open-cap turnover) |
| Unit / risk | live continuous phase snapshot + exploration/survival **open_risk_cap** when bound |
| Secure | Variant A on after each day |
| Omitted | DD freeze, process_error size_mode floor, demote, Pending multi-day, empty slips, research gates, Kelly |
| Stop | max **400** days or equity **900** |
| Paths | **1500**, seed **42** |

This is an **expectation-positive** illustration. Real desk EV is gated, haircut, and often empty — treat medians as **order-of-magnitude** under a friendly book, not a forecast.

### Smoke results (1500 paths, seed 42)

#### Unit trajectory

Printed by the script (same table as above) — unit **12** through 580, **13** at 620, **14** at 750.

#### Milestone medians

| Milestone | Hit rate | Median days | Median bets | P25–P75 days |
|-----------|---------:|------------:|------------:|-------------:|
| **+100 NOK** (equity ≥ 600) | 88.7% | **50** | **100** | 22–114 |
| **540** (enter 1A+) | 95.5% | **13** | **25** | 5–40 |
| **580** (enter 1B) | 91.1% | **36** | **71** | 15–87 |
| **620** (enter 1B+) | 86.4% | **62** | **124** | 29–131 |
| **750** (enter 2) | 68.3% | **153** | **305** | 86–236 |

#### Terminal (end of path)

| Stat | Value |
|------|------:|
| Median final equity | **~795** |
| p10 / p90 final equity | ~307 / ~920 |
| Median final secure | **43** |
| Mean total skimmed | **~36** (soft skims/path ~1.6; **hard ≈ 0** under grind+soft ratchet) |
| Ruin rate (equity &lt; min stake) | **~2.8%** |
| Mean bets / path | **~624** |

### Reading the MC

- **540 is close** under a +2.5% book (~2 weeks median at 2 bets/day). Hybrid’s half-step is meant to be *reachable*, not decorative.
- **+100 NOK / 580** sit in the **1–2 month** median band at this cadence — wide P25–P75: variance still dominates small BR.
- **750** is a longer grind (~5 months median among hitters; ~32% of paths never tag it inside 400 days under these assumptions).
- Soft skim **trims working** and **raises ref**, which **slows** hard-tier accumulation and slightly slows pure equity peaks vs a no-skim counterfactual — intentional desk protection, not a bug.
- Regime open cap (**100** in Exploration/Survival) often binds before phase ceil early on; continuous lerp still helps once equity and settled_count graduate.

Re-run anytime:

```bash
python scripts/mc_phase_progression.py --paths 2000 --seed 7 --edge 0.02
python scripts/mc_phase_progression.py --no-secure   # counterfactual without skim
```

---

## Operator checklist

| Do | Don’t |
|----|--------|
| Treat continuous unit + half-steps as live sizing law | Invent unit jumps not in `evaluate_phase` / risk JSON |
| Expect 1A+ at **540**, 1B at **580**, 1B+ at **620** | Assume 1B stakes at 550 |
| Read secure soft then hard as **mutually exclusive tiers** | Stack 15%+30% on the same equity print |
| Use MC for orientation only | Treat toy +2.5% paths as promised calendar |
| Prefer empty slip over forcing seats into new open room | “Spend” lerped daily risk without research packs |

---

## Related

| Doc / script | Role |
|--------------|------|
| `AGENTS.md` | Agent law: Variant A + hybrid pointers |
| `docs/PHASE_PLAN.md` | Ladder design history + v5 multi-factor |
| `docs/CAPITAL_V2_GO_LIVE.md` | Enable / rollback capital_v2 |
| `docs/BANKROLL_PLAN.md` | Multi-year bankroll narrative |
| `scripts/mc_phase_progression.py` | This projection harness |
| `scripts/run_capital_v2_mc.py` | Stake-rule stress suite (different purpose) |
| `tests/test_phase_continuous.py` | Half-step + continuous unit tests |
| `tests/test_secure_bucket_variant_a.py` | Soft/hard skim + liquid floor tests |
