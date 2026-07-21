# Residual Risks — Final Honest List

**As of:** 2026-07-21 (post P0–P2 implementation + regression + historical replay)  
**Purpose:** What can still lose real money or mislead process — **not** a backlog of nice-to-haves.

Severity: **S0** can corrupt bankroll/settlement truth · **S1** can size or select wrong under load · **S2** process/ops drag · **S3** visibility/docs only.

---

## S0 — Settlement / ledger truth

| ID | Risk | Why it remains | Mitigation in place | Residual |
|----|------|----------------|---------------------|----------|
| R-S0-1 | **Wrong-ticket settle** | Soft match + multi-sport name collisions still exist | Fail-closed ambiguous match; dual soft-match path | Operator must not force settle when engine refuses |
| R-S0-2 | **USER_PAYOUT vs odds×stake** | NT payouts are not always `odds * stake` | Settlement prefers explicit user payout | Agent must never “fix” payout from odds alone |
| R-S0-3 | **Manual ledger edit** | CSV is human-editable | Process discipline; validate CLI | No cryptographic ledger integrity |

---

## S1 — Risk, sizing, selection

| ID | Risk | Why it remains | Mitigation in place | Residual |
|----|------|----------------|---------------------|----------|
| R-S1-1 | **Stranded under unit floor** | Open risk can leave liquid in (0, unit) | Fail-closed no partial ticket; Lumina stranded chip | Capital can sit idle until settles free room |
| R-S1-2 | **Kelly dormant then sudden lift** | Gate is step at liquid ≥ 1500 + cal n/Brier | Lift-only, max 1.5× unit, thin-cal fail-closed | First day above 1500 can jump stakes; watch calibration |
| R-S1-3 | **Portfolio open-room vs concurrent history** | New packing is tighter than early live tickets | Room ∩ phase budget; historical replay showed 0 floor violations but refused some concurrent seats | Edge opportunities refused; under-betting vs past behaviour |
| R-S1-4 | **Soft correlation only** | Same-match hard reject exists for combos; soft demote for league/script/KO is not a hard ban | Soft packing demote; diversify max_per_sport/market | Correlated same-theme multi-ticket still possible if EV clears |
| R-S1-5 | **Process gates raise bar, not p_model** | Weak process cannot invent edge but can still pass if EV already high | min_ev raise; grade A uncertainty | Overconfident packs with high EV still bookable |
| R-S1-6 | **Peak / DD on thin sample** | Settlement peak with small n is noisy | Single settlement-day HWM shared phase + capital_v2 | Early book can REDUCED/FROZEN on variance, or stay NORMAL with lucky peak |
| R-S1-7 | **Learning mults on thin sports** | Multipliers clamp but n per sport is small on live book | min_sample, clamps, auto_apply with soft-modify path | Sport mults can lag or overreact as samples pass thresholds |
| R-S1-8 | **Combos enabled (standard)** | Live config allows combos | Correlation score + per-leg evidence requirements | Correlated multi-leg variance if agent pushes doubles |

---

## S2 — Process, research, ops

| ID | Risk | Why it remains | Mitigation in place | Residual |
|----|------|----------------|---------------------|----------|
| R-S2-1 | **Phantom Pending** | Intent rows still open risk until place-ack / abandon / settle | place-ack + abandon CLI; UI open-risk | Agent/human delay burns seats and distorts room |
| R-S2-2 | **Light coverage without deep quality** | Light is heuristic; deep is optional promote | No auto-promote; ready check | Volume pressure can still starve deep quality |
| R-S2-3 | **High-context / lineup miss** | Confirmed not always available pre-KO | Gates + high_context_require_confirmed | Predicted lineups still wrong; late XI flips |
| R-S2-4 | **Sims misread as edge** | Coarse tennis/BB models | Explicit SUGGESTION ONLY; no place path | Agent might paste sim p into pack without sources |
| R-S2-5 | **Failure index stale** | Rebuild is manual | CLI rebuild/query | Index lies until rebuilt after settle/learn |
| R-S2-6 | **Era archive off** | Live `include_era_archive: false` | Intentional thin book | Learning/calibration lack long history; tests no longer pin 193+ counts |
| R-S2-7 | **Sport tag / taxonomy drift** | Inference + collector tags imperfect | Taxonomy normalize helpers | Wrong sport bucket → diversify/learning mis-bucket |

---

## S3 — Visibility, validation, docs

| ID | Risk | Why it remains | Mitigation in place | Residual |
|----|------|----------------|---------------------|----------|
| R-S3-1 | **Counterfactual replay ≠ full recommend** | Replay re-sizes stakes; does not re-run full gates/packing pipeline | Stake-integrity pass is hard; ROI is illustrative | Do not use replay P/L to claim edge or to loosen rules |
| R-S3-2 | **Edge decay is descriptive** | Calendar place→settle lag only | Desk chart | Not causal; no auto stake change from decay |
| R-S3-3 | **CAPITAL_V2_GO_LIVE.md status lag** | Doc still frames “default OFF” in places | Live config is ON; AGENTS.md states live policy | Operator skimming go-live only may assume flag off |
| R-S3-4 | **Lumina / engine dual repo** | Forensic UI lag or wrong root path | Integration doc; engines sole truth | Stale snapshot if refresh skipped |
| R-S3-5 | **MC ≠ live path identity** | Monte Carlo approximates layers | Floor violation checks in suite | Rare path differences vs production packing order |

---

## Explicitly **not** residual bugs (closed by design)

| Claim | Status |
|-------|--------|
| Pure continuous Kelly at small BR | **Blocked** — liquid + Brier + unit floor |
| Light auto-promote to deep | **Blocked** — P1 |
| Grade A on bare p_model | **Blocked** — uncertainty required |
| Stake in (0, min_stake) | **Blocked** — NT floor + unit path |
| Peak on match date only | **Closed** — settlement-day HWM |
| Sims auto-place | **Blocked** — suggestion only |
| Engine equity rewritten by GUI | **Policy** — forbid; engines sole write path for bankroll |

---

## Highest-leverage operator vigilance (no code)

1. **Abandon or place-ack** every Pending before next round.  
2. **Do not force settle** when match is ambiguous.  
3. **Treat empty slip as success** under room/process pressure.  
4. When liquid approaches **1500**, re-check calibration Brier before assuming Kelly is free size.  
5. Rebuild **failure index** after messy settles if you rely on it in review.  
6. Keep Lumina pointed at the **live tracker root** and refresh after CLI.

---

## Re-check commands

```bash
python -m pytest tests/ -q
python scripts/run_historical_replay.py -n 40
python run_nt.py capital status
python run_nt.py validate
```

---

## Verdict line

**Ship integrity for P0–P2 is validated on current live book.** Residual risk is dominated by **operator process**, **thin-sample learning**, **soft (not hard) correlation**, **phantom Pending**, and **Kelly step-up when liquid crosses 1500** — not by known floor/settlement math holes in the regression suite.
