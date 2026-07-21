# NT Phase Plan v4 (2026-07-13 redesign)

## Why the old plan was too simple

Live era facts (baseline 500 → equity ~549, ~196 settled):

| Signal | Reading |
|--------|---------|
| Era ROI | ~+2% (fine, not explosive) |
| Rolling 20 ROI | **−11.7%** (recent form bad) |
| Rolling 40 ROI | **+6.3%** (longer window still OK) |
| Peak equity | ~590 · max drawdown ~100 NOK |
| Worst days | −88 / −86 NOK (far above early caps) |
| Bets logged as 1B | **n=12, ROI −26%** — size up during weak form hurt |
| Count ladder | Would unlock Phase 4 by settled count alone |

**Design flaws in the old ladder**

1. **Count unlock too soft** — advance allowed at rolling ROI ≥ **−5%** (still red).
2. **Doubles at 1B** while equity still near start (~550) — complexity without bankroll cushion.
3. **Stake jump 1A→1B** (10–15 → 12–20) + higher daily ceiling during a soft patch.
4. **Equity steps huge** (700 / 1200 / 2500 / 5000) with only ~2% ROI — progress felt binary or count-driven.
5. **No drawdown-from-peak demotion** — only a rolling-ROI demote.
6. **Historical volume** (200+ NOK/day) ignored phase caps in practice before the engine owned risk.

## Design principles (v4)

1. **Equity is the true size driver** — more settled bets only *nudge* one step if form is healthy.
2. **Never scale into a drawdown** — count unlock needs **non-negative** rolling ROI; deep red demotes.
3. **No doubles until Phase 2** — singles-only while proving edge near the baseline.
4. **Smaller steps** — more reachable equity milestones so the ladder teaches progression, not all-or-nothing.
5. **Daily risk shrinks in Protect mode** — caps that actually bite after a bad week.
6. **One-step advance** and **hybrid +1 count cap** stay (anti-“193 bets → Phase 4 stakes”).

## Phase ladder v4

| Phase | Label | Enter equity | Enter settled* | Stake NOK | Max / round | Doubles | Daily risk |
|-------|--------|--------------|----------------|-----------|-------------|---------|------------|
| **1A** | Protect | 0 | 0 | 10–12 | 3 | 0 | 8% · floor 30 · ceil **42** |
| **1B** | Stabilize | **580** | **60** | 10–15 | 4 | 0 | 9% · 38–52 |
| **2** | Build | **750** | **90** | 12–18 | 5 | **1** | 10% · 50–75 |
| **3** | Expand | **1200** | **130** | 15–28 | 6 | 2 | 9% · 70–140 |
| **4** | Mature | **2500** | **180** | 18–45 | 7 | 2 | 7% · 100–250 |
| **5** | Scale | **5000** | **250** | 20–70 | 8 | 3 | 6% · 120–400 |

\*Settled count only unlocks **at most one phase above** equity phase, and only if stability passes.

### Stability gates

| Gate | Rule |
|------|------|
| Count unlock | Rolling **25** settled ROI ≥ **0%** |
| Demote (ROI) | Rolling 25 ROI &lt; **−10%** and ≥ 25 settled → drop **one** phase |
| Demote (drawdown) | Equity ≤ **peak × (1 − 12%)** and ≥ 25 settled → drop **one** phase (does not stack twice same run) |
| Advance speed | At most **one step** vs previously stored phase |

Peak equity is max end-of-day equity on the era curve (baseline + cumulative settled P/L).

## Where you are now (~549 equity, rolling 20 ≈ −12%)

- **Equity phase:** 1A (&lt; 580)
- **Count phase:** would be high, but unlock **blocked** (ROI red) and/or demote active
- **Expected phase:** **1A Protect** — correct behaviour after a soft patch and after 1B sample went −26% ROI
- Path to **1B:** equity **≥ 580** *or* (settled already fine **and** rolling 25 ROI ≥ 0% **and** not in drawdown demote) with +1 cap → still need form recovery for pure count path; **+31 NOK** equity is the clean equity path

## What success looks like

| Checkpoint | Target |
|------------|--------|
| 1A → 1B | Equity ≥ 580 **or** stable non-negative rolling + count readiness |
| 1B → 2 | Equity ≥ 750, still singles-only discipline proven |
| 2+ | First selective doubles only with grade/EV rules already in portfolio engine |
| Risk days | Daily stake outlay near ceil only when edge is dense — empty slip still success |

## Relation to engines

- `config.yaml` → numeric truth for phases + `phase_stability`
- `nt/phase.py` → hybrid unlock, demote, one-step cap, peak drawdown
- Portfolio / recommend still enforce EV, grades, high-odds policy, empty-slip-OK
- Multi-year narrative + Monte Carlo: `docs/BANKROLL_PLAN.md` + `nt project`

## Phase v5 multi-factor (2026-07) — additive

Labels **1A–5** unchanged. Alongside the ladder, `evaluate_phase` attaches:

| Field | Role |
|-------|------|
| `phase_state` | equity_score, dd_score, process_error_rate_14d, calibration_score, open_risk_concentration, learning_health |
| `size_mode_floor` | May force **REDUCED** when process_error_rate_14d > 0.25 (n≥4), sticky 7d |
| `research_only` | Optional (cfg `process_error_action`) — blocks new risk |
| `high_odds_stress_block` | High open-sport concentration or poor Brier → block high-odds |

**Hard rule:** capital_v2 `size_mode` from DD/freezes is the **sizing floor**. Phase health may only **tighten** (NORMAL→REDUCED / RESEARCH_ONLY), never loosen FROZEN.

**Code:** `nt/phase.py`, `nt/phase_factors.py`, `nt/risk.py` merge.  
**Agent rules:** `AGENTS.md` · full map `docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md` · residuals `docs/RESIDUAL_RISKS.md`.

## Related docs (v5)

| Doc | Role |
|-----|------|
| [VISION.md](./VISION.md) | Strategic OS vision |
| [BANKROLL_PLAN.md](./BANKROLL_PLAN.md) | Multi-year growth + risk |
| [RESEARCH_WORKFLOW.md](./RESEARCH_WORKFLOW.md) | Idea → evidence → decide |
| [BET_TYPES.md](./BET_TYPES.md) | Singles vs combos |
| [MIGRATION.md](./MIGRATION.md) | Compatibility contract |

## Changelog

- **2026-07-15 v5:** Cross-links to bankroll plan / research / combos; no change to ladder numbers.
- **2026-07-13 v4:** Redesign from live ledger; remove early doubles; harder stability; denser equity ladder; peak drawdown demote; tighter 1A risk.
