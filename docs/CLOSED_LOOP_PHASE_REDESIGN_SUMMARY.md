# Closed-Loop + Phase Redesign — Implementation Summary

**Date frozen:** 2026-07-21  
**Scope:** Post-settlement ControlSignals closed loop · multi-factor PhaseState · Lumina surfaces · validation  
**Not in this batch:** New bankroll formulas · Kelly changes · learning dual-writer rewrite  

---

## What shipped (two subsystems)

### A. Closed-loop learning / process control

| Capability | Behaviour |
|------------|-----------|
| **PostSettlementPacket** | Required on process_error / poor retro; fail-closed settle |
| **ControlSignals** | `temp_gate_raise` → min_ev + force confirmed; TTL 7–14d; JSONL store |
| **Emit path** | settlement_review after settle; n=1 OK |
| **Research gates overlay** | Active signal forces confirmed on avail-sensitive markets |
| **Portfolio** | min_ev raise via process_gates bridge → ControlSignals |
| **Thin mults** | Full permanent stake/EV delta only n≥8 and conf≥0.40 |
| **CLI** | `control-signals list \| emit \| revoke` |
| **Lumina** | Learnings table, CaseFile packet, SettleDesk strict fields, Calibration force-review |

### B. Multi-factor PhaseState (v5)

| Capability | Behaviour |
|------------|-----------|
| **phase_id 1A–5** | Unchanged ladder (equity + count hybrid) |
| **phase_state scores** | equity, DD, process_error_rate_14d, calibration, concentration, learning_health |
| **size_mode floor** | process_error_rate > 0.25 (n≥4) → REDUCED (sticky 7d); optional RESEARCH_ONLY |
| **capital_v2 hard floor** | Phase may only **tighten** size_mode; never loosen FROZEN |
| **High-odds stress** | Concentration ≥55% or poor Brier → block high-odds |
| **Lumina** | DeskStrip mini radar, CapitalPlan “why size_mode”, shortlist chips |

---

## Exact file paths

### Engine — `nt-betting-tracker`

| Path | Role |
|------|------|
| `nt/post_settlement_packet.py` | Packet schema, strict validate, notes blob |
| `nt/control_signals.py` | Emit / load active / revoke / overlay |
| `nt/process_gates.py` | Thin bridge to ControlSignals (portfolio min_ev) |
| `nt/phase_factors.py` | Multi-factor scores + PE rate window |
| `nt/phase.py` | Ladder + phase_state + sticky process health |
| `nt/risk.py` | Merge size_mode floor + RESEARCH_ONLY |
| `nt/portfolio.py` | High-odds stress block; research_only guard; process_gate min_ev |
| `nt/research_gates/__init__.py` | ControlSignal overlay on evaluate_research_gates |
| `nt/settle.py` | Packet fail-closed before ledger write |
| `nt/settlement_review.py` | Emit signals; thin-sample full-delta n≥8 conf≥0.40 |
| `nt/closed_loop_validation.py` | Read-only replay + size_mode invariant |
| `nt/__main__.py` | `control-signals` CLI |
| `scripts/validate_closed_loop.py` | Validation CLI |
| `scripts/run_historical_replay.py` | Prior stake replay (capital/Kelly) |
| `nt/historical_replay.py` | Prior stake replay module |
| `config.yaml` | capital_v2 / learning / phases (live flags) |

### Engine tests

| Path |
|------|
| `tests/test_p0_post_settlement_packet.py` |
| `tests/test_p0_control_signals.py` |
| `tests/test_p0_research_gates_overlay.py` |
| `tests/test_p1_process_gates.py` |
| `tests/test_learning_auto_resolve.py` |
| `tests/test_phase_multifactor.py` |
| `tests/test_closed_loop_validation.py` |

### Engine docs

| Path |
|------|
| `AGENTS.md` |
| `docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md` (this file) |
| `docs/CLOSED_LOOP_VALIDATION.md` |
| `docs/RESIDUAL_RISKS.md` |
| `docs/PHASE_PLAN.md` (v5 multi-factor section) |
| `docs/SETTLEMENT_LEARNING.md` (ControlSignals note) |
| `docs/POST_AUDIT_IMPLEMENTATION_SUMMARY.md` (earlier P0–P2 capital batch) |

### State files (runtime, not all committed)

| Path |
|------|
| `data/state/control_signals.jsonl` |
| `data/state/process_gates.json` (legacy bridge; signals are JSONL) |
| `data/state/phase.json` |
| `data/state/risk.json` |
| `data/state/learning.json` |
| `data/state/learning_proposals.json` |
| `data/state/settlement_reviews.jsonl` |

### LuminaNT

| Path | Role |
|------|------|
| `src-tauri/src/nt/paths.rs` | control_signals + settlement_reviews paths |
| `src-tauri/src/nt/models.rs` | Snapshot fields |
| `src-tauri/src/nt/loader.rs` | Load JSONL into snapshot |
| `src/types/index.ts` | ControlSignal, PhaseState scores, RiskState floors |
| `src/lib/phaseRadar.ts` | Radar dims, sizeModeWhy, active signals, parse PSP |
| `src/lib/gateChips.ts` | temp_gate / board_penalty / hi-odds chips |
| `src/lib/capital.ts` | ShortlistCard.sport |
| `src/lib/demo-data.ts` | Empty control_signals / settlement_reviews |
| `src/components/learning/ControlSignalsPanel.tsx` | Learnings table + emit/revoke |
| `src/components/ops/SettleDesk.tsx` | Mandatory packet fields |
| `src/components/bets/CaseFileContent.tsx` | §8 PostSettlementPacket |
| `src/components/layout/DeskStrip.tsx` | Mini phase radar + mode why |
| `src/components/capital/CapitalPlanPanel.tsx` | Phase health + why size_mode |
| `src/components/research/ShortlistBoard.tsx` | Gate chips with signals |
| `src/views/Learnings.tsx` | Host ControlSignalsPanel |
| `src/views/Calibration.tsx` | Force process review emit |

---

## Validation snapshot

| Check | Result |
|-------|--------|
| Closed-loop replay (28 settled) | 1 PE-class loss → gate; 2 later football under gate (wins) |
| size_mode floor invariant | PASS |
| Thin-sample mult policy | PASS |
| TTL revoke | PASS |
| Live process_error_rate_14d | 0.0 after removing pytest pollution from reviews |

Reproduce: `python scripts/validate_closed_loop.py -n 60`

---

## Design laws (inherit in future sessions)

1. Engines sole bankroll truth; Lumina presents/invokes only.  
2. ControlSignals = **primary durable** process closed loop.  
3. Learning mults = secondary, thin-sample protected, may recompute away.  
4. capital_v2 size_mode = **hard sizing floor**; phase health only tightens.  
5. phase_id ladder labels 1A–5 preserved for continuity.  
6. Fail-closed: ambiguous settle, incomplete strict packet, RESEARCH_ONLY, unit floor.
