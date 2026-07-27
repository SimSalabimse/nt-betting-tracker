# Residual Risks — Final Honest List

**As of:** 2026-07-27 (after ESR adaptive scan PR0–PR5 landings + closed-loop ControlSignals / PhaseState baseline)  
**Purpose:** What can still lose real money or mislead process — not a feature backlog.

Severity: **S0** bankroll/settlement truth · **S1** size/select wrong · **S2** process/ops · **S3** visibility/docs.

---

## S0 — Settlement / ledger truth

| ID | Risk | Mitigation | Residual |
|----|------|------------|----------|
| R-S0-1 | Wrong-ticket settle | Fail-closed soft-match | Operator must not force settle on refuse |
| R-S0-2 | USER_PAYOUT ≠ odds×stake | Prefer explicit payout | Never invent payout from odds |
| R-S0-3 | Manual CSV edit | Process discipline | No crypto integrity |
| R-S0-4 | Strict packet skipped if tags omitted | Packet only when process_error/poor tagged | Untagged misses skip forensic packet |

---

## S1 — Risk, sizing, selection

| ID | Risk | Mitigation | Residual |
|----|------|------------|----------|
| R-S1-1 | Stranded under unit floor | Fail-closed partial stake | Idle capital until settle frees room |
| R-S1-2 | Kelly step-up at liquid ≥1500 | Lift-only, cal gates, max 1.5× unit | First day above gate can jump size |
| R-S1-3 | Open-room packing vs history | min(phase, 18% liquid) | Under-betting vs early concurrent history |
| R-S1-4 | Soft correlation only | Soft demote + diversify caps | Same-theme multi-ticket still possible |
| R-S1-5 | temp_gate raises bar, not hard sport ban | min_ev + force confirmed | High-EV packs can still clear after process miss |
| R-S1-6 | Peak/DD noise on thin book | Shared settlement HWM | Early REDUCED/FROZEN or lucky NORMAL |
| R-S1-7 | Learning mult dual-writer | ControlSignals durable; mult full-delta n≥8 conf≥0.40 | Mult patches still ephemeral after recompute |
| R-S1-8 | Combos enabled (standard) | Per-leg evidence / corr score | Multi-leg variance if pushed |
| R-S1-9 | Phase process_error rate needs n≥4 | Fail-open rate when thin | Book-level REDUCED force rare until reviews accumulate |
| R-S1-10 | Review vs notes label mismatch | Emit uses poor retro **or** variance_class process_error | Operator feel=expected + retro=poor still works; pure narrative “process miss” without tags may not |

---

## S2 — Process, research, ops

| ID | Risk | Mitigation | Residual |
|----|------|------------|----------|
| R-S2-1 | Phantom Pending | place-ack / abandon | Delay burns seats |
| R-S2-2 | Light without deep quality | No auto-promote | Volume can starve deep packs |
| R-S2-3 | Predicted XI wrong | Gates + force confirmed under temp_gate | Late flips still hurt |
| R-S2-4 | Sims as edge | Suggestion-only | Agent paste without sources |
| R-S2-5 | Failure index stale | Manual rebuild | Offline until rebuild |
| R-S2-6 | Era archive off | Intentional thin book | Weak long-history learning |
| R-S2-7 | Sport tag drift | Taxonomy normalize | Wrong diversify/learning bucket |
| R-S2-8 | settlement_reviews pollution | Ops hygiene (test rows removed once) | Future tests must not write live state paths |
| R-S2-9 | ControlSignal JSONL growth | Append-only + revoke tombstones | No compaction job |
| R-S2-11 | Dual Decision becomes place theater (LLM preferred slate treated as place list) | **Mitigated (PR4):** KD-DD-wire in skill + AGENTS Stage 3.1–3.4 + golden `docs/templates/DUAL_DECISION_TEMPLATE.md`; place set + stakes only from engine `recommend` / `build_portfolio`; never hand-remove engine picks; `decision:` tags only post-recommend; skill_smoke gates template phrases | **Residual:** skill/agent discipline — operators who ignore KD-DD-wire can still treat advisory ranks as a place list (no code-level place lock) |
| R-S2-12 | Agent D spawn / role drift (wrong threshold, main-board seats on high-volume boards) | **Mitigated (PR3):** `research scan-depth` + `should_spawn_agent_d` with `adaptive_scan_agent_d_min_lines=41` (n=40 false / n=41 true); D long-tail soft role-drift annotate only; sequential skip if A/B/C already ≥10 min; skill_smoke pytest 40/41 | **Residual:** soft drift may still pollute shortlist; manual line-count fallback if CLI skipped; sequential budget is skill-only |
| R-S2-13 | Branch hygiene: missing `scan_merge` / `market_family` / `live_ledger` / `form_continuity` sources vs pycache | **Mitigated (PR0 + PR-H):** sources restored — A/B/C(+D) merge + CLI; form_continuity + portfolio base_ev / ranking-gap soft-cap wiring without math redesign; skill_smoke covers one-agent-missing merge path | **Residual:** low — re-check after merge conflicts / Syncthing; Guardian soft-reject claims now match live portfolio wiring on this stack |

---

## S3 — Visibility / validation

| ID | Risk | Mitigation | Residual |
|----|------|------------|----------|
| R-S3-1 | Closed-loop replay ≠ full recommend | Validates gates/floor, not pack quality | Don’t claim edge from counterfactual ROI |
| R-S3-2 | Only 28 settled in live era | Full-book replay | Re-run when n grows |
| R-S3-3 | Dual-repo UI lag | Refresh after CLI | Stale signals if no refresh |
| R-S3-4 | CAPITAL_V2_GO_LIVE still says default OFF in places | AGENTS live policy ON | Skim risk |
| R-S3-5 | Demo cannot emit/revoke | Desktop-only mutates | Expected |

---

## Closed by design (not residuals)

| Claim | Status |
|-------|--------|
| Pure continuous Kelly at small BR | Blocked |
| Light auto-promote to deep | Blocked |
| Grade A on bare p_model | Blocked |
| Stake in (0, min_stake) | Blocked |
| Peak match-date only | Closed — settlement HWM |
| Sims auto-place | Blocked |
| Phase loosens capital FROZEN | Blocked — floor only tightens |
| Incomplete process_error settle | Blocked — packet fail-closed |
| Full permanent mult jump on n&lt;8 | Blocked — soft-modify |

---

## Highest-leverage operator vigilance

1. **Tag honestly** at settle (process_error / poor retro) and fill **PostSettlementPacket**.  
2. **place-ack or abandon** every Pending before next round.  
3. Respect **empty slip**, **RESEARCH_ONLY**, and **size_mode REDUCED/FROZEN**.  
4. Use Lumina **ControlSignals** table / CLI revoke when a gate is wrong or expired early by design.  
5. Before liquid **1500**, assume Kelly stays off; re-check Brier when it approaches.  
6. Do not treat **learning mults** as the process memory — **ControlSignals + phase health** are.  
7. Keep Lumina on the **live tracker root**; refresh after CLI settles.

---

## Re-check

```bash
python -m pytest tests/ -q
python scripts/validate_closed_loop.py -n 60
python run_nt.py capital status
python run_nt.py control-signals list --json
python run_nt.py validate
```

---

## Best-in-class assessment (this bankroll size)

For a **~500–1500 NOK working book**, NT min 10, unit ladder 10/15/20:

| Subsystem | Assessment |
|-----------|------------|
| **Closed-loop process** | **Best-in-class practical** — packet forensic + durable temp_gate (min_ev + confirmed XI) + thin mult protection + UI emit/revoke. Not academic full Bayesian process graph; correctly sized for real money and thin samples. |
| **Phase + capital** | **Best-in-class practical** — capital_v2 remains hard size floor; phase multi-factor adds process/cal/concentration without fighting unit law; 1A–5 continuity. Not a full hierarchical Bayesian bankroll controller (overkill here). |

**Caveat:** Best-in-class **for this scale and operator model** (human research + engine law + fail-closed). Not “beats institutional quant process systems.” Gaps above (soft correlation, mult dual-writer, thin PE tags) remain the honesty tax.

---

## Verdict line

**Closed-loop ControlSignals and multi-factor PhaseState are production-ready for this bankroll.** Residual risk is dominated by **operator tagging discipline**, **thin sample**, **soft (not hard) portfolio correlation**, **phantom Pending**, and **Kelly step-up at 1500** — not by missing process actuators or phase fighting capital_v2.
