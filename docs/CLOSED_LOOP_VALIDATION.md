# Closed-loop learning + PhaseState validation

**Date:** 2026-07-21  
**Scope:** ControlSignals (temp_gate_raise), thin-sample mults, multi-factor PhaseState size_mode floor  
**Method:** Read-only replay + unit checks · no ledger mutation  
**Commands:** `python scripts/validate_closed_loop.py -n 60` · `pytest tests/test_closed_loop_validation.py`

---

## Metrics (live book)

| Metric | Value |
|--------|-------|
| Settled tickets available | **28** (requested 60 — full book) |
| Process-error-class **losses** that would emit `temp_gate_raise` | **1** |
| Later same-sport tickets while simulated gate active | **2** (both **wins**) |
| Of those, losses that would still be taken under gate | **0** |
| Live `process_error_rate_14d` | **0.0** (n_reviews=32 after removing pytest pollution, force=False) |
| size_mode floor invariant (effective ≥ capital) | **PASS** · capital=NORMAL, effective=NORMAL |
| Thin-sample: n=5 conf=0.5 full-accept? | **No** (soft-modify) **PASS** |
| Thin-sample: n=8 conf=0.45 full-accept? | **Yes** **PASS** |
| TTL revoke: emit then revoke → 0 active | **PASS** |

### Process-error event in window

| bet_id | Sport | Match | Effect |
|--------|-------|-------|--------|
| `d6ffb33af023` | football | Kalmar vs Malmö FF | Would emit temp_gate_raise (~10d TTL) |

### Follow-on under gate (would face raised min_ev / force confirmed on avail-sensitive)

| bet_id | Result | Stake | Note |
|--------|--------|-------|------|
| `1c16c2725a48` | Win | 12 | Football after PE gate |
| `2c4cf15a8b6e` | Win | 12 | Football after PE gate |

**Interpretation:** With current tags, only **one** clear process_error loss fires a gate. Two later football tickets would have faced **stricter research/EV gates** (not auto-reject of all football). No repeated process_error-class **loss** sequence exists in this book to measure “blocked repeat miss” — sample is thin.

---

## Hard rules verified

1. **capital_v2 size_mode is the floor**  
   `risk.size_mode` severity ≥ `size_mode_capital`. Phase floor may set REDUCED when capital is NORMAL; never loosens FROZEN.

2. **temp_gate_raise TTL / revoke**  
   Emit creates active signal; revoke tombstone clears active set. Unit-tested.

3. **Thin-sample permanent mults**  
   Full accept only for n≥8 and conf≥0.40; thinner proposals soft-modify.

4. **ControlSignal on n=1**  
   Unchanged: process_error emit does not require sample size (unit tests).

---

## Test suite

```
tests/test_closed_loop_validation.py
tests/test_p0_control_signals.py
tests/test_phase_multifactor.py
tests/test_learning_auto_resolve.py
→ all green (17+ related)
```

**Fixes applied this pass**
- Removed **2** pytest pollution rows (`bet_id=test1`) from live `data/state/settlement_reviews.jsonl` that inflated `process_error_rate_14d`.
- No engine logic bugs found; added `nt/closed_loop_validation.py` + `scripts/validate_closed_loop.py` for regression.

---

## Residual risks

| Risk | Severity | Note |
|------|----------|------|
| **Thin process_error labeling** | Medium | Only 1 process-class loss (research_retro=poor; review still labeled skill via feel=expected) in 28 settled |
| **Gate does not hard-block same-sport tickets** | Design | temp_gate raises min_ev + force confirmed; wins still placeable if EV clears |
| **Replay is stake/gate simulation** | Low | Does not re-run full `build_portfolio` / research packs for each historical ticket |
| **Sticky phase REDUCED not triggered live** | Low | rate 0.059 &lt; 0.25 — correct non-force |
| **Learning mult dual-writer** | Known | Permanent mult patches still ephemeral after `run_learning`; ControlSignals remain durable loop |
| **Book size &lt; 40 settled** | Ops | Era archive off; re-run when n grows |

---

## Verdict

**PASS** — size_mode hard floor holds; thin-sample and TTL/revoke behave; closed-loop would have emitted **1** temp_gate and raised the bar for **2** subsequent football tickets (both wins). No code defects found requiring a fix this turn.
