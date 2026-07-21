# Post-Audit Implementation Summary

**Period:** Adversarial capital integrity audit → P0 → P1 → P2 → full regression + historical replay  
**Repos:** SimSalabimse/nt-betting-tracker (+ LuminaNT desk surfaces)  
**Date frozen:** 2026-07-21  
**Scope of this document:** What was implemented. No new features beyond that record.

---

## Context

Production capital desk for real Norsk Tipping stakes. Ledger equity remains:

```text
equity = baseline_nok + Σ performance P/L (Win/Loss/Refunded)
```

Engines in `nt/` are sole bankroll truth. LuminaNT / Flet present and invoke; they do not redefine risk.

---

## P0 — Settlement & capital integrity

| Item | Implementation | Intent |
|------|----------------|--------|
| Settlement match fail-closed | Soft-match dual path; refuse ambiguous settle rather than wrong ticket | No silent mis-settlement |
| Peak = settlement day | Single HWM from settlement calendar (Oslo / `updated_at`), shared by phase demote + capital_v2 DD | Kill-switch and size_mode align with when money moved |
| Learning full-delta gates | n / confidence floors before aggressive mult moves | Thin sample cannot rewrite process |
| High-context confirmed | `high_context_require_confirmed` live | WC/intl/B2B cannot pass on silent “full strength” |
| Portfolio packing | Open-room ∩ phase budget respected | No stake past remaining room |

**Not changed:** ledger equity identity; NT min stake floor (10 NOK); whole-krone discipline.

---

## P1 — Correlation, process, grade A, light demote, Lumina ops

| Item | Implementation | Intent |
|------|----------------|--------|
| Soft correlation | League / script family / KO proximity packing soft-demote | Reduce same-story stacks without hard-banning multi-sport books |
| Process gates | Raise `min_ev` on weak process — do not invent edge | Honest process → higher bar, not synthetic p |
| Grade A uncertainty | `grade_a_require_uncertainty` — needs sd / CI / multi-model | Bare point p is not A |
| Light research demote | `auto_promote_to_deep: false`; light pass never sets promote | Agent/manual deep only |
| Lumina ops surfaces | Risk status / stranded / gate chips / calibration force-review / shortlist chips / Case File deep-dive | Operator sees can-bet truth |

---

## P2 — Kelly, multi-sport sims, failure index, Lumina forensic

| Item | Implementation | Intent |
|------|----------------|--------|
| Fractional Kelly | `nt/kelly.py` after unit path in `portfolio`; liquid ≥ 1500; Brier + cal n fail-closed; soft Brier scale; max 1.5× unit; **lift only** | Optional size-up when bankroll + calibration earn it |
| Tennis / basketball sims | `nt/sim_tennis.py`, `nt/sim_basketball.py`; CLI `simulate --sport …` | Suggestion-only p_model; never places |
| Failure index | `nt/failure_index.py`; `failures rebuild` / `failures query` | Inverted-token lookup of losses / process_error / evidence failure_modes |
| Lumina risk heatmap | Sport × status open stake matrix; cell → forensic | Concentration visible on desk |
| Edge decay | ROI by place→settle lag buckets | Post-hoc edge aging signal |
| Bidirectional re-trigger | Open-risk → ledger; Case File → related open peers / sport heatmap | Forensic hop both ways |
| Full-text search | Multi-token AND across ledger fields; `id:` exact | Faster ticket find |
| Historical replay harness | `nt/historical_replay.py`, `scripts/run_historical_replay.py` | Read-only stake replay under current rules |

---

## Validation snapshot (post-implementation)

| Check | Result |
|-------|--------|
| Full pytest | **266 passed**, 2 skipped, 0 failed |
| Historical replay last 40 settled | **28/28** available settled; **0** stake-integrity violations |
| Kelly on live history | **0 applications** — liquid gate (expected at ~500 NOK working book) |
| Engine bankroll math loosened for green CI? | **No** — brittle count assertions updated to structural/policy identity |

Artifacts:

- `artifacts/P2_VALIDATION_REPORT.md`
- `artifacts/HISTORICAL_REPLAY_VALIDATION.md`

---

## Live policy flags (as frozen)

| Flag | Live value | Note |
|------|------------|------|
| `capital_v2.enabled` | **true** | Production on; rollback via config/env |
| `include_era_archive` | **false** | Live book is thin (post-reset era) |
| Light auto-promote | **false** | P1 intentional |
| Combos | enabled / standard | Assess path still safety-gated |
| Kelly | enabled in capital_v2 defaults | Dormant until liquid + Brier gates |

---

## What this audit deliberately did **not** do

- Rewrite historical `bets.csv` stakes or P/L  
- Enable pure continuous Kelly  
- Auto-place from tennis/basketball sims  
- Re-enable era archive or inflate settled counts for vanity metrics  
- Claim edge from counterfactual replay ROI (illustrative only)

---

## Operator references

- Agent rules: `AGENTS.md`  
- Residual risks (honest): `docs/RESIDUAL_RISKS.md`  
- Capital go-live / rollback: `docs/CAPITAL_V2_GO_LIVE.md`  
- Capital design: `docs/PHASE2_ENGINE_BANKROLL_DESIGN.md`
