# Residual Risks — Final Honest List

**As of:** 2026-07-22 (after HV Research Regime **v3** + closed-loop ControlSignals + multi-factor PhaseState + Lumina surfaces + validation)  
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
| R-S1-11 | **Efficient NT board still empty after full HV v3 funnel** | Clearability dual-track + second-pass + soft pack + 3pp haircut | **Honest residual:** well-priced boards can yield **zero** clears after honest packs + second-pass (`honest_no_edge`). v3 reduces *process miss* (wrong lines / no refresh); it **does not mint edge**. Soft-book refs still optional |
| R-S1-12 | **Relative / classical prior mistaken for edge** | Prior is **rank-only** for deep-queue clearability; place path requires agent `p_model` | Operator or agent paste of prior as `p_model` would invent edge — blocked by process, not by math alone |
| R-S1-13 | Soft pack under 1A remaining ~40 → one place-capable slip | Document multi-run split; research-only after seats filled | Same-day volume pressure to invent second slip |

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
| R-S2-10 | Agent overclaim under volume KPI | Funnel KPI (not forced 3 places); T5 market-mimic empty; AGENTS wording | Still human p_model discipline |
| R-S2-11 | Mass `missing_odds_snapshot` / inferred on first dual-write desks | Fail-closed place; agent rewrite; second-pass prioritizes | Temporary volume dip until packs dual-write (expected migration) |
| R-S2-12 | `clearability_miss` celebrated as success | starvation_kind taxonomy; second-pass CLI | Operator skips second-pass |

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
| Auto-fill `p_model` from Stage2 / relative prior | Blocked — rank-only |
| Place with missing/inferred odds snapshot | Blocked — fail-closed |
| force_coverage on pure clearability_miss / honest_no_edge | Blocked — research-starvation path only |
| Cut haircut / min-EV to force volume | Rejected by design (HV v3 keeps 3pp + ≥2% Exploration) |

---

## Highest-leverage operator vigilance

1. **Tag honestly** at settle (process_error / poor retro) and fill **PostSettlementPacket**.  
2. **place-ack or abandon** every Pending before next round.  
3. Respect **empty slip** (`honest_no_edge` after second-pass), **RESEARCH_ONLY**, and **size_mode REDUCED/FROZEN**.  
4. On **`clearability_miss`**, run **`research second-pass`** and re-deep — do not force places.  
5. Dual-write **odds snapshot** on every pack; rewrite if place rejects `missing_odds_snapshot`.  
6. Expect **≈1 place-capable slip/day** under 1A remaining ~40; extra same-day passes are research-only.  
7. Use Lumina **ControlSignals** table / CLI revoke when a gate is wrong or expired early by design.  
8. Before liquid **1500**, assume Kelly stays off; re-check Brier when it approaches.  
9. Do not treat **learning mults** as the process memory — **ControlSignals + phase health** are.  
10. Keep Lumina on the **live tracker root**; refresh after CLI settles.  
11. Treat **relative prior as rank-only** — never as place probability.

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

For a **~500–1500 NOK working book**, NT min 10, unit ladder 10/15/20 (HV often unit **12** under 1500 liquid):

| Subsystem | Assessment |
|-----------|------------|
| **Closed-loop process** | **Best-in-class practical** — packet forensic + durable temp_gate (min_ev + confirmed XI) + thin mult protection + UI emit/revoke. Not academic full Bayesian process graph; correctly sized for real money and thin samples. |
| **Phase + capital** | **Best-in-class practical** — capital_v2 remains hard size floor; phase multi-factor adds process/cal/concentration without fighting unit law; 1A–5 continuity. Not a full hierarchical Bayesian bankroll controller (overkill here). |
| **HV v3 research funnel** | **Best-in-class practical for NT desk** — clearability rank-only prior, second-pass refresh, fail-closed pack odds, soft pack under 1A, starvation_kind taxonomy. Still **not** a soft-book arb engine; efficient boards may empty. |

**Caveat:** Best-in-class **for this scale and operator model** (human research + engine law + fail-closed). Not “beats institutional quant process systems.” Gaps above (soft correlation, mult dual-writer, thin PE tags, efficient-board empty slips) remain the honesty tax.

---

## Verdict line

**Closed-loop ControlSignals, multi-factor PhaseState, and HV v3 funnel controls are production-ready for this bankroll.** Residual risk is dominated by **honest no-edge on efficient NT boards**, **operator tagging discipline**, **p_model overclaim pressure**, **thin sample**, **soft (not hard) portfolio correlation**, **phantom Pending**, **odds-snapshot migration**, and **Kelly step-up at 1500** — not by missing process actuators or phase fighting capital_v2. **Relative prior remains rank-only and does not create placeable edge.**
