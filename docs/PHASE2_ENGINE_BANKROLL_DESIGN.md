# Phase 2 Design — Betting Engine & Bankroll Management

**Status:** Design only — **no production sizing/risk code until explicit acceptance**  
**Date:** 2026-07-21  
**Binding constraints:** Operator Set B (see §2)  
**App context:** LuminaNT capital cockpit Phase 1 locked; App-gated learning proposals default  

**Related code (as of design date):**  
`nt/portfolio.py`, `nt/risk.py`, `nt/phase.py`, `nt/bankroll.py`, `nt/project.py`, `nt/learning.py`, `nt/settlement_review.py`, `config.yaml`, `docs/BANKROLL_PLAN.md`, `docs/PHASE_PLAN.md`

---

## 1. Purpose & non-goals

### Purpose
Define an institutional-grade, **fail-closed** multi-layer risk and sizing system that:

1. Respects the **Norsk Tipping 10 NOK floor** (and market-specific higher floors later if needed).  
2. Implements Set B: drawdown circuit breakers, daily/weekly loss limits, fixed-unit then step scaling, secure-profit bucket, no pure continuous Kelly.  
3. Leaves a full **audit trail** of every stake decision for LuminaNT and forensics.  
4. Is **stress-testable** (Monte Carlo) and **deterministically replayable**.

### Non-goals (this design phase)
- Implementing production code.  
- Changing research/EV gates (except where risk layer must refuse after EV pass).  
- CLV capture (still de-scoped until close-line path exists).  
- Pure Kelly or continuous fractional-Kelly without bands/floors.

---

## 2. Binding Set B rules (normative)

| ID | Rule |
|----|------|
| **B1** | **DD soft reduce:** drawdown from peak ≥ **15%** → size = half unit or next lower band (whichever is safer). |
| **B2** | **DD hard freeze:** drawdown from peak ≥ **25%** → **no new risk** until manual review + explicit unfreeze flag. |
| **B3** | **Daily loss limit:** soft warn at **2% liquid** (or 1.5 units if preferred UI-only); **hard stop** at **4% of liquid** or **3 units**, whichever hits first. |
| **B4** | **Weekly loss limit:** soft warn at **5% liquid**; **hard stop** at **8% of liquid** or **6 units**, whichever hits first. |
| **B5** | **Unit ladder (liquid equity):**  
  · &lt; **1 500 NOK liquid** → fixed **unit = 10 NOK** (or `norsk_tipping.min_stake_nok` if higher).  
  · ≥ 1 500 → unit **15**  
  · ≥ 2 500 → unit **20** (then phase/percentage bands may take over — see §5).  
  Never recommend stake &lt; NT floor. |
| **B6** | **Secure-profit bucket:** when equity ≥ last reset HWM × **1.30**, move **40%** of profit above that HWM into non-risked **secure**; working bankroll continues on remainder; **reset reference HWM** after transfer. |
| **B7** | **Sizing philosophy:** no pure continuous Kelly. Phased bands + floors + optional vol shrink. After unit steps, optional **conservative Kelly fraction** max **0.25–0.35**, always clipped by floors/caps/layers. |
| **B8** | **Learning proposals:** default **App-gated** accept/reject; engine keeps capability for later auto mode. |

**Unit definition (normative):**  
`1 unit = current absolute unit size in NOK` (10 / 15 / 20 / …), not a percentage of bankroll until post-threshold fractional mode.

**Drawdown definition (normative):**  
Same conceptual HWM as phase peak: max end-of-settled-path equity (baseline + cumulative performance P/L). Implementation must use **one shared peak function** for phase demote, strip DD%, and circuit breaker (see §4.3).

**Liquid definition (normative):**  
`liquid = equity − open_risk` where open_risk = sum of stakes with `Pending` + `ConfirmedPlaced` (`nt/bankroll.py` today).  
Daily/weekly limits use **liquid at start of evaluation** (or start-of-day snapshot — fix one rule in implementation; recommend **start-of-day liquid** frozen in `risk.json` for the calendar day Oslo).

---

## 3. Biggest remaining engine weaknesses (current)

| # | Weakness | Where | Why it matters |
|---|----------|--------|----------------|
| W1 | **Sizing is not bankroll-fractional Kelly** — linear EV band between `stake_min`/`stake_max` | `portfolio._stake_for` | Fine for small BR; not aligned with Set B unit ladder or 0.25–0.35 Kelly cap |
| W2 | **Daily kill-switch uses % of equity**, not liquid; floor 40 NOK | `risk.stop_day_loss_limit`, `config risk.*` | At ~550 equity, 8% = 44 NOK ≈ 4+ units; Set B wants **4% liquid or 3 units** |
| W3 | **No weekly loss limit** | `risk.py` | Multi-day bleed can continue after soft daily stops |
| W4 | **DD demote only drops phase one step at 12%** — no 15% half-size, no 25% hard freeze | `phase.evaluate_phase` + `phase_stability.demote_drawdown_pct_of_peak: 0.12` | Set B freeze is stronger and operator-visible |
| W5 | **Peak equity for phase uses match-date curve** | `phase._peak_equity` | Can disagree with settlement-day narrative / Lumina DD if not unified |
| W6 | **No secure bucket** | `bankroll.compute_bankroll` | All equity is riskable; Set B needs segmented capital |
| W7 | **No structured stake audit log** | recommend → notes fragments | Cannot forensically answer “why 12 NOK?” |
| W8 | **No recommended vs actual stake fields** | `BET_HEADER` | Overrides invisible |
| W9 | **Learning auto-apply vs App gate** | `config learning.auto_apply_proposals: true` + settle path | Contradicts Set B App-gated default |
| W10 | **Monte Carlo projection ignores DD freeze, weekly limits, unit ladder** | `project.simulate_paths` | Stress tests don’t prove new rules |
| W11 | **Stranded &lt; min_stake remainder** still possible under multi-layer caps | `rebalance_stakes` + diversify | Operational annoyance; must be explicit fail-closed (no partial illegal stake) |
| W12 | **Correlation** is diversify max_per_match/sport/market — no league/script family | `portfolio` + `learning.diversification` | Acceptable baseline; extend later |
| W13 | **`evaluate_risk` remaining = cap − open only** — does not subtract today’s realized loss from remaining capacity | `risk.evaluate_risk` | After a −20 day, can still open full remaining cap unless kill-switch fires |

### Current sizing formula (reference)

```text
# portfolio._stake_for
frac = clamp((ev - 0.03) / 0.12, 0, 1)
stake = stake_min + frac * (stake_max - stake_min)
stake *= high_odds_mult? learning_stake_mult?
stake = whole_krone; clamp [min_stake, remaining_risk]
```

No unit ladder, no DD size reduce, no Kelly fraction, no weekly budget.

### Current risk formula (reference)

```text
daily_cap = clamp(equity * phase.daily_risk_pct, floor, ceil)
stop_lim  = max(40, equity * 0.08)
stopped   = today_realized_pl <= -stop_lim
remaining = max(0, daily_cap - open_pending)   # realized loss does not shrink remaining
can_bet   = not stopped and remaining >= min_stake
```

---

## 4. Target architecture

### 4.1 Layered risk model (evaluate top-down, fail-closed)

```
┌─────────────────────────────────────────────────────────────┐
│ L0  Manual freeze flag (operator unfreeze after 25% DD)     │
├─────────────────────────────────────────────────────────────┤
│ L1  Drawdown circuit: ≥25% freeze; ≥15% size_mode=reduced   │
├─────────────────────────────────────────────────────────────┤
│ L2  Weekly loss hard stop (8% liquid_sod OR 6 units)        │
├─────────────────────────────────────────────────────────────┤
│ L3  Daily loss hard stop (4% liquid_sod OR 3 units)         │
├─────────────────────────────────────────────────────────────┤
│ L4  Daily open-risk budget (phase cap − open − policy)      │
├─────────────────────────────────────────────────────────────┤
│ L5  Portfolio diversify (match/sport/market/band/football)  │
├─────────────────────────────────────────────────────────────┤
│ L6  Per-bet size (unit ladder → band → EV scale → vol)      │
│     always ≥ NT floor or zero (never illegal partial)       │
└─────────────────────────────────────────────────────────────┘
```

Any layer that says **no** → no new bets (or stake 0 / reject with reason code).  
Prefer **empty slip** over violating floor or freeze.

### 4.2 Capital segments (secure bucket)

Introduce explicit state (new file, not redefining equity formula silently):

```json
// data/state/capital_segments.json  (proposed)
{
  "schema_version": 1,
  "working_baseline_nok": 500.0,
  "secure_nok": 0.0,
  "secure_transfers": [],
  "unit_hwm_reset_equity_nok": 500.0,
  "freeze": {
    "active": false,
    "reason": null,
    "activated_at": null,
    "unfreeze_requires": "manual"
  },
  "day_snapshot": {
    "oslo_date": "2026-07-21",
    "liquid_start_nok": 550.99,
    "unit_size_nok": 10
  },
  "week_snapshot": {
    "week_id": "2026-W30",
    "liquid_start_nok": 550.99,
    "realized_pl_nok": 0.0
  }
}
```

**Accounting law (critical):**

| Concept | Definition |
|---------|------------|
| **Ledger equity** | Unchanged: `baseline + Σ performance P/L` on `bets.csv` (historical truth) |
| **Secure** | Non-risked reserve; **not** available for stake/open-risk/daily cap |
| **Working equity** | `ledger_equity − secure_nok` (or equivalently track working_baseline — pick one implementation; recommend **secure subtract from riskable equity**) |
| **Riskable / working liquid** | `working_equity − open_risk` |

Daily/weekly limits and unit ladder use **working liquid**, not secure.  
UI strip must show: Equity (total), Secure, Working/Liquid riskable.

Secure transfer algorithm (on refresh/settle when not frozen):

```text
ref = unit_hwm_reset_equity_nok   # last reset HWM for bucket rule
if equity >= ref * 1.30:
    profit_above = equity - ref
    transfer = round(0.40 * profit_above, 2)   # whole øre/krone policy: whole NOK
    if transfer >= 1:
        secure += transfer
        # Riskable capital effectively shrinks for limits:
        # working_equity := equity - secure
        unit_hwm_reset_equity_nok := equity - transfer
          # OR reset to equity after transfer so next +30% is from new base
        append secure_transfers audit row
```

**Reset reference after transfer:** Set B says “reset the reference high-water after the transfer.” Interpret as:

`unit_hwm_reset_equity_nok := equity_after_accounting` where equity_after is total equity still on ledger, and next trigger is +30% from **that** reset mark. Secure is already extracted so growth is measured on full equity or working equity — **recommend measuring +30% on full ledger equity** with reset mark updated to current equity at transfer time, so we don’t double-skim.

### 4.3 Shared peak / drawdown service

New module (proposed): `nt/capital_risk.py` (or extend `risk.py` carefully).

```text
peak_equity(rows, baseline) → float
  # single implementation used by phase demote, DD strip, L1 freeze
  # Prefer settlement-day ordered curve for consistency with kill-switch narrative

drawdown_from_peak(equity, peak) → float in [0,1]
```

Phase demote at 12% can remain for ladder softness **or** be replaced by Set B 15%/25% only — **recommend:** keep phase demote at 12% as soft ladder control; **hard size reduce at 15%**; **hard freeze at 25%** (override phase entirely).

### 4.4 Unit ladder & stake construction

```text
function unit_size(working_liquid, min_floor):
  if working_liquid < 1500: return max(min_floor, 10)
  if working_liquid < 2500: return max(min_floor, 15)
  return max(min_floor, 20)

function size_mode(dd, freeze_flag):
  if freeze_flag or dd >= 0.25: return FROZEN
  if dd >= 0.15: return REDUCED   # half unit or next lower band
  return NORMAL

function stake_for_bet(...):
  if FROZEN: return 0
  u = unit_size(...)
  if REDUCED: u = max(min_floor, floor(u / 2))  # or drop one unit step
  # Band around unit for EV quality (whole NOK):
  lo = u
  hi = min(phase.stake_max, max(u, u + k))  # e.g. k=0..2 NOK only at small size
  # Optional fractional Kelly after liquid >= 1500:
  if working_liquid >= 1500 and p_model and odds:
    f_kelly = clamp( (p*odds - 1)/(odds - 1) , 0, 1) * bankroll_fraction  # edge/odds form
    k_stake = working_liquid * min(0.35, kelly_frac_cap) * f_kelly
    stake = clamp(k_stake, lo, hi)
  else:
    stake = lo + ev_frac * (hi - lo)   # keep simple EV scale inside [lo,hi]
  stake = whole_krone(stake)
  if stake < min_floor: return 0
  if stake > remaining_layers: return 0 or reduce to floor if remaining>=floor
  return stake
```

**Awkward stakes rule:**  
Always integer NOK. Never 10.5. Never “remaining 6 → stake 6”. If remaining &lt; min_floor → **no bet**, leftover idle (document as correct).

### 4.5 Daily / weekly loss limits

| Limit | Soft | Hard |
|-------|------|------|
| Daily | warn UI at 2% liquid_sod *or* 1.5u (UI) | **4% liquid_sod OR 3u** |
| Weekly | warn at 5% liquid_sod | **8% liquid_sod OR 6u** |

```text
unit = day_snapshot.unit_size_nok
daily_hard = min(0.04 * liquid_sod, 3 * unit)   # "whichever is reached first" as loss magnitude
# Hard stop when -today_realized_pl >= daily_hard
# Same for week with week_realized_pl and 0.08 / 6u
```

**Interaction with daily open-risk cap:**  
Keep phase daily_risk cap as **open exposure** budget.  
Additionally: after hard daily loss, `can_bet=false` even if open_risk is 0.

**Optional improvement (recommend implement):**  
`remaining_open = min(phase_cap - open, remaining_after_daily_loss_budget)` where loss budget shrinks usable room after partial day losses (not only binary kill). Design:

```text
loss_room = daily_hard + today_realized_pl   # today_realized negative on losses
if loss_room <= 0: freeze day
else: remaining = min(cap - open, loss_room)  # conservative interpretation
```

Document choice in config: `risk.daily_loss_shrinks_remaining: true` (default true under Set B).

### 4.6 Simultaneous multi-bet exposure

Keep existing diversify (code law):

| Control | Current default | Set B stance |
|---------|-----------------|--------------|
| max_per_match | 1 | Keep |
| max_per_sport | 2 | Keep |
| max_per_market | 2 | Keep |
| max_bets_per_round | phase | Keep |
| max_football_per_round | soft fill | Keep |
| Open risk total | daily_cap | Keep + weekly doesn’t increase open |

**New hard rule:**  
`open_risk + sum(new_stakes) ≤ daily_open_cap` and each stake ≥ floor.  
If packing would force stake &lt; floor, drop lowest-EV seat (`rebalance_stakes` already drops seats when budget too small).

**Correlation (phase 2.1 later):** same-league / same-script soft penalty — not required for first engine PR.

### 4.7 Stake decision audit log

New append-only: `data/state/stake_decisions.jsonl`

```json
{
  "ts": "2026-07-21T12:00:00Z",
  "schema_version": 1,
  "rule_bundle_version": "br_v2.0.0",
  "bet_id": "…",
  "match": "…",
  "selection": "…",
  "inputs": {
    "equity": 550.99,
    "secure": 0,
    "working_liquid": 550.99,
    "open_risk": 0,
    "dd_from_peak": 0.0,
    "unit_size": 10,
    "size_mode": "NORMAL",
    "phase_id": "1A",
    "p_model": 0.64,
    "odds": 1.85,
    "ev": 0.156,
    "learning_stake_mult": 1.0
  },
  "constraints_applied": [
    "unit_ladder:10",
    "nt_floor:10",
    "daily_remaining:42",
    "max_per_match:1"
  ],
  "recommended_stake_nok": 12,
  "final_stake_nok": 12,
  "reject_reason": null
}
```

Ledger: add optional columns later (migration careful):

- `recommended_stake_nok`  
- `stake_rule_version`  

Until migration: dual-write in notes `stake_rec=12; rules=br_v2.0.0` **and** JSONL (JSONL is source of truth for App).

### 4.8 Learning proposals (App-gated)

| Config | Target default |
|--------|----------------|
| `learning.auto_apply_proposals` | **false** |
| Settle | write proposals only |
| LuminaNT Learnings | Accept / Reject actions call `nt learn --accept|--reject` |
| CLI | keep force auto for power users: `--auto-apply-proposals` |

---

## 5. Complete bankroll management plan (operational)

### 5.1 Regimes

| Working liquid | Unit | Stake band (illustrative) | Kelly? |
|----------------|------|---------------------------|--------|
| &lt; 1 500 | **10** | 10–12 (phase may still say 10–12) | No — fixed/unit EV top-up only |
| 1 500–2 499 | **15** | 15–18 | Optional ≤0.25–0.35 Kelly clipped to band |
| ≥ 2 500 | **20** | 20–phase max | Optional Kelly clipped |
| Phase 3+ equity | max(unit, phase.stake_min) | phase band | Kelly clipped |

**Priority when phase band conflicts with unit:**  
`lo = max(nt_floor, unit_size, phase.stake_min under NORMAL)`  
Under REDUCED: `lo = max(nt_floor, unit_size // 2)` even if phase.stake_min is higher — **document as deliberate risk-off** (may be below phase min for exposure but never below NT floor).

### 5.2 Simultaneous multi-bet example (1A, unit 10, liquid 550, remaining 42)

| Seat | Action |
|------|--------|
| Max seats | floor(42/10)=4 |
| Pack | 4×10 or 3×12+ leftover &lt;10 idle |
| Never | 3×12 + 1×6 |

### 5.3 Secure bucket example

```text
ref HWM reset = 500
equity = 700  (≥ 500*1.3 = 650) ✓
profit_above = 200
transfer = 0.4 * 200 = 80 → secure=80
working riskable equity for limits = 700-80 = 620
reset mark = 700 (or 620 — pick & test; recommend reset mark = full equity 700)
```

### 5.4 Drawdown example

```text
peak = 600, equity = 510 → dd = 15% → REDUCED (half unit)
peak = 600, equity = 450 → dd = 25% → FROZEN until capital_segments.freeze.active=false via CLI/App
```

### 5.5 Forbidden behaviors (explicit)

- Pure continuous Kelly without floor/band  
- Raising unit after a win streak without ladder threshold  
- Ignoring 10 NOK floor (“almost full remaining”)  
- Curve-fitting unit thresholds to last 2 weeks of results without design review  
- Auto-unfreeze after DD recovers without operator action  
- Counting secure capital as liquid for risk limits  

---

## 6. Monte Carlo / stress requirements

### 6.1 Extend `nt/project.py` (or new `nt/stress_bankroll.py`)

Must simulate **paths under the new rule bundle**, not only fixed ROI Bernoulli:

| Scenario | Spec |
|----------|------|
| Base edge | ROI +3% / +0% / −5% on stake |
| Fat left tail | Occasional 8–12 loss streaks |
| Variance by market | Higher σ on totals/props if tagged |
| Unit ladder transitions | Paths that cross 1500 / 2500 |
| Secure skims | Paths that hit +30% from ref |
| DD freeze | Measure time-in-freeze and recovery |
| Weekly/daily stops | Count stops per year; capital left |

### 6.2 Metrics to report

- P5 / P50 / P95 terminal working equity and total equity  
- Max DD distribution  
- % paths hitting 25% freeze  
- % paths “ruin” (working liquid &lt; 3× unit)  
- Turnover and fraction of days can_bet=false  
- Mean idle stranded NOK (leftover &lt; floor)  

### 6.3 Seeds & determinism

- Fixed seed → identical path summaries  
- Rule bundle version in output JSON  
- No write to `bets.csv`

### 6.4 Pass criteria (design targets — tune after first sim)

- At 0% true edge: median equity not exploding; freeze rate non-zero under variance  
- At +3% edge: positive median after costs; freeze rate rare  
- At −5% edge: secure bucket still protects skims; freeze limits bleed  

---

## 7. Exact engine change map

| Area | File(s) | Change |
|------|---------|--------|
| Config | `config.yaml` | New `capital_v2` / `risk` / `unit_ladder` / `secure_bucket` blocks; set `auto_apply_proposals: false` |
| Shared peak/DD | `nt/phase.py` or `nt/capital_risk.py` | Single peak/DD; settlement-day option |
| Risk evaluate | `nt/risk.py` | Daily/weekly limits, freeze, liquid_sod, size_mode, remaining shrink |
| Bankroll | `nt/bankroll.py` | Expose secure, working_liquid; load segments |
| Segments I/O | **new** `nt/capital_segments.py` | Load/save transfers, freeze, day/week snapshots |
| Sizing | `nt/portfolio.py` | Unit ladder, reduced mode, audit emit, fail-closed |
| Recommend | `nt/recommend.py` | Pass capital context; write stake_decisions.jsonl |
| Settle | `nt/settle.py` | Update week P/L; evaluate secure transfer; no auto mult apply by default |
| Learning | `config` + settle/review | App-gated proposals |
| CLI | `nt/__main__.py` | `capital status`, `capital unfreeze`, `capital secure-status` |
| Projection | `nt/project.py` | Stress under rule bundle |
| Tests | `tests/test_capital_v2_*.py` | Floor, freeze, weekly, packing, secure math |
| Defaults | `nt/defaults.py` | Merge capital_v2 defaults |

### Proposed config sketch

```yaml
norsk_tipping:
  min_stake_nok: 10.0

capital_v2:
  enabled: true   # feature flag for staged rollout
  rule_bundle_version: "br_v2.0.0"
  unit_ladder:
    - { max_liquid_exclusive: 1500, unit: 10 }
    - { max_liquid_exclusive: 2500, unit: 15 }
    - { max_liquid_exclusive: null, unit: 20 }
  drawdown:
    reduce_at: 0.15
    freeze_at: 0.25
    reduce_mode: half_unit   # half_unit | step_down
  daily_loss:
    hard_pct_of_liquid: 0.04
    hard_units: 3
    soft_pct_of_liquid: 0.02
    shrink_remaining: true
  weekly_loss:
    hard_pct_of_liquid: 0.08
    hard_units: 6
    soft_pct_of_liquid: 0.05
  secure_bucket:
    enabled: true
    trigger_multiple_of_ref: 1.30
    transfer_fraction_of_profit_above_ref: 0.40
  kelly:
    enabled_above_liquid: 1500
    fraction_cap: 0.30        # within 0.25–0.35
    use_after_haircut_p: true
  audit:
    stake_decisions_jsonl: data/state/stake_decisions.jsonl

learning:
  auto_apply_proposals: false
```

**Feature flag:** ship `capital_v2.enabled: false` until golden tests pass; then enable.

---

## 8. App surfaces required (LuminaNT — after engine design acceptance)

| Surface | Need |
|---------|------|
| Capital strip | Show Secure + Working liquid if secure &gt; 0 |
| Desk / Settings | Active rule bundle version, freeze banner, unfreeze button (calls CLI) |
| Learnings | Accept/Reject proposals (no silent apply) |
| Ops | `capital status` readout |
| Case file / stake | Show recommended vs final stake from audit log |
| Risk strip | Weekly P/L vs weekly limit progress |

No App implementation in this design-only phase beyond documenting requirements.

---

## 9. Phased implementation order

| Phase | Scope | Depends on | Review checkpoint |
|-------|--------|------------|-------------------|
| **2.0 Design** | This document | Set B | **← acceptance gate** |
| **2.1 Foundation** | `capital_segments`, shared peak/DD, config flag off, unit tests for pure functions | 2.0 | Unit tests green |
| **2.2 Risk layers** | Daily/weekly limits, freeze, remaining shrink; risk.json schema extended | 2.1 | status/risk dry-run report |
| **2.3 Sizing** | Unit ladder + REDUCED mode in portfolio; stake audit JSONL | 2.2 | Replay fixtures |
| **2.4 Secure bucket** | Transfer on settle/refresh; bankroll fields | 2.3 | Simulated transfer cases |
| **2.5 Stress MC** | project/stress under bundle | 2.4 | Stress report vs pass criteria |
| **2.6 App gate** | auto_apply false; Lumina accept/reject; freeze UI; strip secure | 2.2+ | Operator UI review |
| **2.7 Enable** | `capital_v2.enabled: true` on live book | All above | Go-live checklist |

Each checkpoint: no next phase until explicit accept.

---

## 10. Testing plan (mandatory before enable)

### Unit
- unit_size boundaries 1499.99 / 1500 / 2499.99 / 2500  
- stake never ∈ (0, min_floor)  
- REDUCED half unit ≥ min_floor  
- FROZEN → all stakes 0  
- daily_hard = min(4% liquid, 3u)  
- weekly_hard = min(8% liquid, 6u)  
- secure transfer math + reset mark  
- rebalance never creates sub-floor stake  

### Integration / replay
- Historical odds file + fixed evidence → identical stake_decisions under seed  
- Open risk with ConfirmedPlaced counts  
- Kill-switch after synthetic day P/L  

### Stress
- §6 scenarios  

### Fail-closed cases
- remaining 6 NOK → 0 bets, reason `below_floor`  
- freeze active → reject all with `capital_frozen`  
- weekly exhausted Monday → no bets until week boundary  

---

## 11. Professional Standards Checklist — risk additions

- [ ] Multi-layer risk evaluated in fixed order; first deny wins  
- [ ] NT floor never violated by recommended stake  
- [ ] Empty slip preferred over illegal partial stake  
- [ ] 15% DD reduces size; 25% freezes until manual unfreeze  
- [ ] Daily 4% liquid / 3u and weekly 8% liquid / 6u hard stops  
- [ ] Secure bucket excluded from riskable liquid  
- [ ] Unit ladder thresholds explicit and tested  
- [ ] No pure continuous Kelly  
- [ ] Stake decision JSONL for every accept/reject  
- [ ] recommended vs final stake distinguishable  
- [ ] Learning proposals App-gated by default  
- [ ] MC stress under rule bundle before production enable  
- [ ] Deterministic replay for sizing  
- [ ] Feature flag + rollback path  
- [ ] Lumina shows freeze, secure, unit size, rule version  

---

## 12. Open design questions (non-blocking if defaults accepted)

Defaults proposed in parentheses — override only if you reject:

1. **Secure reset mark** after transfer: full ledger equity at transfer time (**default**).  
2. **Daily remaining shrinks with losses** (`shrink_remaining: true`).  
3. **Week boundary:** ISO week Europe/Oslo (**default**).  
4. **REDUCED mode:** half unit (**default**) vs step down ladder.  
5. **Phase demote at 12%** kept alongside Set B 15/25 (**default keep both**).  
6. **Kelly fraction_cap:** 0.30 within 0.25–0.35.  

---

## 13. Summary

The current engine is a **sound small-bankroll EV packer** with diversify and a daily kill-switch, but it lacks Set B’s **unit ladder, weekly limits, 15/25% DD circuit, secure capital, stake audit, and App-gated learning**. Phase 2 introduces a versioned **capital_v2** rule bundle with fail-closed layers, shared peak/DD, integer NOK floor discipline, Monte Carlo stress, and Lumina visibility — **without pure Kelly**.

**Stop here.** No production engine code until you explicitly accept this design (with any overrides to §12 defaults).
