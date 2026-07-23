# Agent rules — nt-betting-tracker

Real-money capital desk. Engines in `nt/` are law. UI (LuminaNT, Flet desktop) presents and invokes — never invents bankroll math.

**Status (permanent package):** clean-restart **500 NOK** era · capital_v2 live · **hybrid half-steps (1A+/1B+) + continuous unit** · **secure bucket Variant A** (soft/hard skim) · **Exploration→Survival→Normal** bankroll regimes · multi-stage quant prefilter · engine deep queue (composition ≥**55%** preferred / ≤**25%** short-main · band **1.85–2.60**) · Coverage Health + soft gate · `force_coverage_priority` · totalgrense residual buffer · closed-loop ControlSignals · PhaseState v5 · **neutral sport start at zero data**.  

Docs: `docs/PACKAGE_IMPLEMENTATION_SUMMARY.md` · `docs/RESEARCH_COVERAGE_FIX_SUMMARY.md` · `docs/RESEARCH_WORKFLOW.md` · `docs/BANKROLL_PLAN.md` · `docs/CAPITAL_HYBRID_PROGRESSION.md` · `docs/RESIDUAL_RISKS.md` · `docs/LUMINA_INTEGRATION.md` · `artifacts/PACKAGE_VALIDATION_REPORT.md`.

---

## When the user provides a new or updated odds file

**Trigger:** Any new/updated odds dump in `inbox/` (e.g. `odds_*.txt`, “here’s today’s odds”, “updated odds”), or an explicit request to analyze/recommend from odds.

**You are the Research + Recommendation Agent.** Follow this workflow **every time** — do not skip to mechanical recommend, and do not invent `p_model`.

### Mandatory workflow

1. **Identify the file**  
   Prefer the path the user named; else use the **newest** `inbox/odds*.txt` by mtime.

2. **Market coverage (high-volume matches)**  
   ```bash
   python run_nt.py research market-scan --odds <odds_file>
   ```  
   Also auto-runs inside `research board` unless `--skip-market-scan`.

3. **Research board + Stage 1 Light Research**  
   ```bash
   python run_nt.py research board --odds <odds_file>
   python run_nt.py research light --odds <odds_file>   # if board did not auto-light
   ```  
   Read shortlist + **Light coverage %** + **engine Deep queue** + **Coverage Health** from board / `outbox/light_research/` / `data/state/coverage_health.json`.

4. **Tiered research (mandatory coverage)**  

   | Stage | Scope | Output | Can recommend? |
   |-------|--------|--------|----------------|
   | **Prefilter** | Stage1 screens + Stage2 classical prior on light assess | discard noise/chalk/hopeless; `prior_ev` rank-only | **No** |
   | **Light** | ≥70–85% of shortlist; sports with ≥5 lines get ≥3 light | verdict pass/fail + notes | **No** |
   | **Deep queue** | Engine-built worklist (`engine_deep_queue: true`) from light-pass | ranked promote list (preferred ≥55%, short-main ≤25%) | **No** until packs |
   | **Deep packs** | Agent writes full `evidence/*.json` + honest `p_model` for queue lines | gradeable packs | **Yes** |

   - **Assess never auto-promotes** (`auto_promote_to_deep: false`) — `auto_light_assess` always leaves `promote_to_deep=false`.  
   - **Engine fills deep_queue** via anti-chalk `promotion_score` + **composition quotas** (see below).  
   - **You must deep-research the deep queue** — queue alone does not invent `p_model` or place bets.  
   - Do **not** deep-dive 2–3 short favourites while ignoring mid-price / preferred lines on the queue.  
   - Light is quick/heuristic; Deep stays high quality (gates, sources, script).  
   - Prefer kick-off balance: early and late KO both get Light; Deep queue must not be 100% chalk ML/O2.5.

### Engine deep queue (permanent — inherit every session)

**Code:** `nt/light_research.py` (`promotion_score`, `build_deep_queue`) · config `research.tiers`.

| Rule | Live default |
|------|----------------|
| Short chalk (odds &lt; **1.70** / `short_chalk_odds`) | Heavy score penalty unless rare structural note |
| Boost band **1.85–2.60** | Strong promotion weight (Calibration-survivable) |
| Boost | Alt totals (O3.5+), handicaps, dogs (ML ≥1.85), period as preferred |
| Soft-book longer than NT | Optional boost only if `soft_decimal_odds` / `soft_odds=` present — **never invent** |
| Preferred share of queue | ≥ **55%** (odds ≥1.85 **or** non short-main with odds ≥1.80) |
| Short-main cap | ≤ **25%** pure short-fav **ML / O2.5 / first-goal** |
| Thin preferred pool | **Shrink queue** — never pad with chalk to hit target n |
| Target size | Dynamic via `deep_target_dynamic` (~**8–15**; `deep_target_min`/`max`/`divisor`) — never pad chalk to hit n |

**Short-main** = odds &lt; 1.85 **and** (ML / O2.5 / first-goal).  
**Preferred (survivable)** = odds ≥ **1.85** **or** (non short-main **and** odds ≥ **1.80**). Short alts &lt;1.80 do **not** pad the preferred floor.

### Coverage floor + temp_ev_relax (permanent)

Two orthogonal mechanisms. Operators see both on **`data/state/status.md`** → **Coverage floor** section.

#### Mechanism A — quality-preserving floor (never softens EV)

**Code:** `nt/light_research.py` (`coverage_floor_cfg`, `dynamic_deep_target_n`, `build_deep_queue`)  
**Config:** `research.coverage_floor` + `research.tiers.deep_target_*`

| Piece | Behaviour |
|-------|-----------|
| Dynamic `deep_target_n` | `clamp(board_lines // divisor, min, max)` when `deep_target_dynamic` |
| Top-promo scaffold | Force top **~20%** by `promotion_score` into queue consideration (`top_promo_scaffold_pct`) — still composition-capped; never pure short-main chalk |
| Sport rotation | Sports with ≥`sport_rotation_min_lines` (default **5**) eligible light-pass and **zero** deep picks get one forced preferred/non-chalk line when composition allows |
| `require_real_pack` | Queue never includes rows that already have `p_model` as invented work |

**Never invents `p_model`. Never softens min_EV / haircut.** Expands *what to research*, not *what clears EV*.

#### Mechanism B — `temp_ev_relax` safety net (auditable ControlSignal)

**Code:** `nt/control_signals.py` (`emit_temp_ev_relax`, `active_temp_ev_relax_overlay`, `maybe_emit_temp_ev_relax*`) · applied in `nt/portfolio.py`  
**Config:** `learning.control_signals.temp_ev_relax` (optional mirror `research.coverage_floor.ev_relax`)

| Rule | Live default |
|------|----------------|
| When | Large board (≥`min_board_matches` **15**) **and** coverage health **warn/critical** **and** deep_queue empty **and** light-pass survivors exist |
| Soften | Per-line allowlist only · `delta_ev` **1–2pp** · TTL **24h** · `clear_on_settle` |
| Stake | Extra **×0.80** (20% haircut) while active on that line |
| Never | High-odds (when `exclude_high_odds`) · grade **C** (when `exclude_grade_c`) · grade **F** · global min_EV rewrite |
| Blocked | If **`process_gate_raise` > 0** for the candidate → skip relax entirely (fail-closed coexistence with process_error gate) |

**Agent mandate:**

- **Do not invent `p_model`** to fill seats or clear EV.  
- **Do not manually lower min_EV** outside ControlSignals (`temp_ev_relax` / engine emit only).  
- Prefer Mechanism A (more deep research) over waiting for B.  
- Verify: `python scripts/verify_coverage_floor.py --synthetic-large`

5. **Deep research (engine deep queue first — not only O2.5/ML)**  
   Work the **Deep queue** from light report / board. Use web search / page open aggressively (Sofascore, FBref, HLTV, ATP/WTA, Flashscore, official sites, etc.).  
   Quality over quantity. Multi-sport shortlist **and** market-scan interesting lines.

### Multi-sport research gates (engine-enforced)

Full design: **`docs/RESEARCH_GATES.md`**. Empty slip beats betting against your own script.

| Field | Role |
|-------|------|
| `context_risk` / `rotation_risk` | `low` \| `medium` \| `high` (WC/intl/B2B/bronze = high) |
| `availability_status` / `lineup_status` | `confirmed` \| `predicted` \| `stable_guess` — not blank on sensitive markets |
| `availability_notes` | Injuries, minutes, fitness, rotation |
| `script_lean` | Must agree with selection |
| `selection_vs_script` | Never `conflict` |
| `base_rate_conflict` | `true` if history opposes the bet |

**12h balance:** predicted + availability research is OK for domestic / late-XI leagues. High context needs deeper notes (not silent “full strength”). **High context requires confirmed** availability when `high_context_require_confirmed: true` (live). Confirmed preferred always — not always required on low context.

**Hard rejects:** script conflict · base-rate conflict · missing availability on totals/BTTS/props · anti-script unders (football high_scoring + Under/BTTS No) · tennis retirement + overs · basketball star_rest + player overs.

**Grade A (P1):** needs uncertainty — `p_model_sd`, edge CI, or multi-model — not a bare point `p_model` alone (`grade_a_require_uncertainty`).

**Sports:** football, tennis, basketball profiles + default (hockey/handball/darts/…).

#### Evidence packs (`evidence/*.json`)

- Honest `p_model` · `summary` · `failure_modes` · real sources  
- Gate fields above on sensitive markets  
- No mechanical filler; no correlated stack after demoted research

6. **Ready check + Coverage Health**  
   ```bash
   python run_nt.py research ready --odds <odds_file>
   ```  
   Also read **`data/state/coverage_health.json`** (written on board/recommend):  
   - `shortlist_deep_pct` — % of shortlist with deep pack  
   - `deep_survivable_pct` — % of deep packs at odds ≥1.85 or preferred (non-chalk)  
   - `mid_unresearched_n` / `empty_slip_risk` / `level` (`ok` \| `warn` \| `critical`)  
   - Lumina DeskStrip + ShortlistBoard show the same metrics.

7. **Recommend (default = real / logs pending)**  
   ```bash
   python run_nt.py recommend --odds <odds_file>
   # only if Coverage Health critical and user/ops explicitly override:
   python run_nt.py recommend --odds <odds_file> --allow-low-coverage
   ```  
   Present the slip with reasoning.  
   - **Default = live recommend** — writes **Pending** to the ledger when the engine picks bets.  
   - **Coverage soft gate:** if Coverage Health is **critical**, recommend is **blocked** (not a silent empty slip) unless `--allow-low-coverage`. Optional auto-expand of deep queue first.  
   - **Pending = intent, not NT confirmation.** It still counts as open risk until `place-ack`, settle, or `abandon`.  
   - **Dry-run only when the user asks** (`--dry-run` / “dry-run” / “preview only”).  
   - **Do not include already-open bets** (Pending or ConfirmedPlaced) in the “new place” advice.  
   - Only recommend lines with **strong research backing**.  
   - **Empty slip after honest deep research** (packs written, EV/grade fail) = success.  
   - **Empty / near-empty because mid-price lines were never researched** = process miss — engine raises **`force_coverage_priority`** and soft-gates recommend.  
   - **ControlSignals:**  
     - `temp_gate_raise` — min_ev raise + force confirmed lineup (process_error path).  
     - `force_coverage_priority` — research pressure (TTL **4–7d**, default 5; target band **`1.85-2.60`**; min_deep_packs 8–10). Raises next deep-queue weights; **does not invent p_model or soften EV/haircut**.  
     - `temp_ev_relax` — **safety net only** (Mechanism B): per-line min_EV soften ≤2pp + stake ×0.80 · TTL 24h · never high-odds/grade-C · blocked when process_gate active. See **Coverage floor + temp_ev_relax** above.

8. **Place confirmation / abandon (real-money control)**  
   ```bash
   # User confirmed ticket is live on Norsk Tipping
   python run_nt.py place-ack --ids <bet_id>[,<bet_id>...]
   # Never placed / missed prematch — frees risk, P/L 0, keeps audit row
   python run_nt.py abandon --ids <bet_id> --reason missed_prematch
   python run_nt.py abandon --match "Humphries" --reason missed_prematch
   ```  
   - **Operator default (this desk):** the user **always places** recommended tickets on NT. After live `recommend` writes Pending, **`place-ack` those new bet_ids** in the same session unless they say a bet was skipped/missed (then `abandon`). Do not leave tickets stuck on Pending after a place session.  
   - **ConfirmedPlaced** — still open risk until Win/Loss/Refunded.  
   - **Abandoned** — not open risk; not a phase/learning sample.  
   - Never leave unplaceable Pending counting against daily risk.

9. **Dry-run (opt-in)**  
   Use `--dry-run` only if the user explicitly requests a dry-run / preview / no-write pass.

---

## Clean restart + neutral sport start (permanent)

| Rule | Detail |
|------|--------|
| **Baseline** | `bankroll.baseline_nok: 500` · equity = baseline + Σ terminal P/L on `data/bets.csv` only |
| **Era** | `bankroll.era_start` · `include_era_archive: false` (prior archives do **not** enter equity) |
| **Fresh start** | `python scripts/fresh_start_500.py` — archives ledger/state, resets learning/signals/**coverage_health**, sets era_start, refresh → equity **500** |
| **Zero data** | Learning mults **1.0 / 0** until `min_sample`; **no** sport hard-edges |
| **Virgin explore** | Same `explore_virgin_ev_boost` for all sports at n=0 — **symmetrical** |
| **Regime floor** | Exploration **4%** / Survival **7.5%**; weekly `EXPLORE_REGIME` quota may use **2.0–3.9%** (≤2 unit bets/week, mid/alt only) |
| **Haircut / Grade A** | High-Volume v2: **3pp** haircut · Grade A + elevated EV for odds **≥2.5** · Grade C placeable with core reason |

---

## Bankroll regimes (Exploration → Survival → Normal)

**Orthogonal to phase ladder.** Code: `nt/bankroll_regime.py` · config `bankroll_regime:` · binds via `risk.json`.

| Regime | When | min-EV (after haircut) | Open-risk cap (pending only) |
|--------|------|------------------------|------------------------------|
| **Exploration** | settled **&lt; 40** **and** equity **&lt; 650** | **4%** + ≤**2 unit**/week at **2.0–3.9%** mid/alt (`EXPLORE_REGIME`) | **50 NOK** |
| **Survival** | after Exploration exit until graduate | **7.5%** (no thin quota) | **50 NOK** |
| **Normal** | settled ≥**100** **or** equity ≥**800** | `selection.standard_min_ev` (3%) | phase + capital_v2 only |

**Open risk law:**

- Counts **Pending + ConfirmedPlaced** only (`day_pending_risk`).  
- **Frees immediately** on Win / Loss / Refunded (and Abandon).  
- `remaining_risk = min(phase, portfolio_room, regime_cap − open_pending, totalgrense_usable)`.  
- Soft mid-odds prefer (1.85–2.50) under Exploration/Survival — **sort only**, not hard ban.

---

## Totalgrense (NT account ceilings)

**Code:** `nt/totalgrense.py` · config `norsk_tipping.totalgrense`.

| Key | Default | Role |
|-----|---------|------|
| `residual_buffer_nok` | **5000** | Refuse if residual headroom &lt; buffer after stake |
| `daily_limit_nok` / `monthly_limit_nok` | **null** | Operator mirror of NT; null = period unconstrained |
| Place time | `created_at` → Europe/Oslo | Stake-commitment turnover |

- **place-ack** fails closed if residual already &lt; buffer.  
- Set real NT limits before relying on L6; buffer alone does nothing without limits.

---

## Capital v2 (live policy)

**Live config:** `capital_v2.enabled: true` (see `docs/CAPITAL_V2_GO_LIVE.md` for rollback).  
Ledger equity formula is **unchanged**: `baseline + Σ performance P/L`. Engines remain sole bankroll truth.  
**Hybrid progression examples + MC:** `docs/CAPITAL_HYBRID_PROGRESSION.md` · `python scripts/mc_phase_progression.py`

| Layer | Behaviour |
|-------|-----------|
| Peak / DD | **Settlement calendar day** peak (Oslo via `updated_at`) — not match-date-only |
| size_mode (**capital hard floor**) | NORMAL → REDUCED (≥15% DD) → FROZEN (≥25% DD or manual freeze). Phase health may **only tighten** (e.g. force REDUCED), never loosen FROZEN. |
| **Unit (primary)** | When `phase_continuous.enabled`: **continuous unit** = `stake_min + (equity − enter) / scale_factor` (whole krone, clamp band) with **carry-forward floor** so promotions never drop unit. Fallback liquid ladder: **12 / 15 / 20** (`capital_v2.unit_ladder`). Never stake in (0, min_stake). |
| Open room | Phase open budget (continuous **lerp** of floor/ceil/pct toward next phase) ∩ portfolio open-risk cap (~18% riskable liquid) ∩ **regime open cap** ∩ **totalgrense usable** |
| Daily / weekly | Hard loss stops on liquid SoD / SoW; day-loss may shrink remaining (intentional) |
| **Secure bucket Variant A** | Soft **1.25× ref / 15%** of (eq−ref); hard **1.50× ref / 30%** — **hard replaces soft, never stacked**. Min-working softener max(55% eq, 8×unit); **liquid floor** never skim below phase `daily_risk_ceil`; ref → working after skim. Unlock: auto after **25** settles since lock, or manual 7d cooldown. |
| **Kelly (P2)** | Optional **lift above unit only** when liquid ≥ **1500**, calibration n ≥ 30, Brier ≤ max; fail-closed if thin cal; max **1.5× unit**. Never pure continuous Kelly; never shrinks below unit. |
| Audit | `data/state/stake_decisions.jsonl`, `capital_segments.json` |

### Config key pointers (do not invent values)

| Concern | Keys |
|---------|------|
| Enable capital stack | `capital_v2.enabled` |
| Liquid unit fallback | `capital_v2.unit_ladder` · grade mults `capital_v2.grade_stake_mult` |
| Secure Variant A | `capital_v2.secure_bucket.variant: A` · `soft_trigger_multiple_of_ref` / `soft_transfer_fraction` · `hard_trigger_multiple_of_ref` / `hard_transfer_fraction` · `min_working_frac_of_equity` · `min_working_units` · `unlock_after_settled` · `manual_unlock_cooldown_days` |
| Half-steps | `phases."1A+"` / `phases."1B+"` · `hard_phase_id` (parent hard gates) |
| Continuous unit / open-risk | `phase_continuous.enabled` · `phase_continuous.scale_factor` (default **100**) |
| Phase ladder numbers | `phases.*.enter_equity` / `stake_min` / `stake_max` / `daily_risk_*` |
| Stability / demote | `phase_stability.*` |

**Stranded remainder:** liquid may sit under one unit while open risk is high — UI surfaces this; do not force a ticket below floor.

**Secure unlock (operator):**  
`python run_nt.py capital unlock-secure --confirm` (manual; respects cooldown)  
**Unfreeze (after human review only):**  
`python run_nt.py capital unfreeze --confirm`

---

## Phase system (v5 multi-factor + hybrid half-steps)

**Labels:** **1A → 1A+ → 1B → 1B+ → 2 → … → 5** (`config.yaml`).  
`phase_id` is equity/count hybrid (seats, daily open budget, soft stake band).  
**Half-steps** (`1A+`, `1B+`) keep **parent hard gates** via `hard_phase_id` (max_doubles / max_bets) while display id and continuous sizing advance.  
**Continuous unit / open-risk** progress inside each band when `phase_continuous.enabled` — unit is non-decreasing at promotions (carry-forward floor).  
Examples 500→550 and MC milestones: **`docs/CAPITAL_HYBRID_PROGRESSION.md`**.

**Additionally** `evaluate_phase` attaches multi-factor `phase_state` and health overlays:

| Factor | Use |
|--------|-----|
| `equity_score`, `dd_score` | Progress / drawdown health |
| `process_error_rate_14d` | From `settlement_reviews.jsonl` (window 14d) |
| `calibration_score` | Brier-based (neutral if cal n thin) |
| `open_risk_concentration` | Max single-sport open stake share |
| `learning_health` | Blocked sports share |

**Hard overlays (fail-closed):**

- `process_error_rate_14d > 0.25` with n_reviews ≥ 4 → `size_mode_floor=REDUCED` (or `RESEARCH_ONLY` if cfg), **sticky 7 days**
- High open concentration (≥55% one sport) **or** poor Brier → **block high-odds** entirely
- `RESEARCH_ONLY` → `can_bet=False` (no new risk)

**Law:** `risk.size_mode` severity ≥ capital DD mode. Phase never upgrades FROZEN/REDUCED from DD.

State: `data/state/phase.json`, reasons also on `risk.json` (`size_mode_capital`, `size_mode_floor`, `phase_health`).

---

## Settlement + learning + ControlSignals (agent-owned)

After every settle:

1. **Match fail-closed** — dual soft-match; never force wrong ticket.  
2. **PostSettlementPacket** — if `variance_tag=process_error` (or research_miss/miss) **or** `research_quality_retro=poor|wrong|miss`, **required fields** before ledger write:  
   `actual_score`, `actual_lineup_status`, `predicted_vs_actual_xi_delta`, `script_realized`, `process_root_cause`.  
   Lumina SettleDesk blocks incomplete strict rows; engine rejects incomplete items.  
3. **Taxonomy (every settled bet)** — fill on the packet / settle item (agent preferred; engine auto-fills if blank):  
   | Field | Values |
   |-------|--------|
   | `predictability` | `highly_predictable` · `moderately_predictable` · `weakly_predictable` · `unpredictable_from_available_info` |
   | `variance_class` | `systematic_script_form` · `research_process_miss` · `model_error` · `one_off_injury_late` · `one_off_referee` · `true_randomness` · `unknown` |
   | `learning_weight` | `clamp(base[class] × pred_mult[predictability], 0, 1)` — engine formula in `nt/settlement_taxonomy.py` |
   | `classification_notes` / `classified_by` / `classified_at` | short free text · `agent\|auto\|backfill\|user` · ISO-8601 |

   **Weight intent:** systematic/process misses move mults; late injury / ref / true randomness barely do (base 0.05–0.10).  
   Legacy map: `process_error` / `research_miss` → `research_process_miss`; `expected`/`skill` → `systematic_script_form`; `variance`/`luck` → `true_randomness`.  
   Backfill: `python scripts/backfill_settlement_taxonomy.py` (last 30 + re-weight report).  
4. Learning recompute (`run_learning`) + settlement analysis — sample influence × `learning_weight`.  
5. **ControlSignals (primary closed loop)** — store `data/state/control_signals.jsonl`:  
   - **`temp_gate_raise`** — on process_error / poor retro even at **n=1**, **only if `learning_weight` ≥ `min_learning_weight_for_gate` (default 0.5)**: raise min_ev · force confirmed availability · TTL **7–14d** (default 10). Near-zero weight one-offs **skip** temp_gate.  
   - **`force_coverage_priority`** — on empty/near-empty recommend from **research starvation** (high `no p_model` share + mid unresearched): band **1.85–2.60** / alt totals / dogs / HC / period · TTL **4–7d** · does **not** change haircut or EV bar.  
   - **`temp_ev_relax`** — empty deep-queue safety net on large boards (Mechanism B): allowlisted lines only · ΔEV 1–2pp · stake ×0.80 · TTL **24h** · clear_on_settle · never invents p_model · **never** stack with process_gate raise on the same candidate.  
6. **Learning proposals** auto-resolve (`auto_apply_proposals: true`):  
   - Full permanent mult delta only if **n_hist ≥ 8** and **conf ≥ 0.40**  
   - Else soft-modify or reject noise  
   - Mult patches can be overwritten by next full recompute — **do not treat mults as durable process control**; ControlSignals are.

```bash
# ControlSignals ops
python run_nt.py control-signals list --json
python run_nt.py control-signals emit --sport football --source force_review --reason "…"
python run_nt.py control-signals revoke --sport football --actor agent
# coverage: engine-emitted force_coverage_priority (sport=coverage); revoke with --sport coverage if needed

# Failures index (offline)
python run_nt.py failures rebuild
python run_nt.py failures query --q "rotation under"

# Closed-loop validation (read-only)
python scripts/validate_closed_loop.py -n 60
# Coverage validation (read-only harness)
python artifacts/_validate_coverage_fix.py
```

---

## Sims (suggestion only)

Football / tennis / basketball quant sims **never place bets**. They suggest `p_model` for evidence packs; human + research gates remain law.

```bash
python run_nt.py simulate --sport tennis --player-a A --player-b B ...
python run_nt.py simulate --sport basketball --home H --away A ...
```

---

## Hard rules

| Do | Don’t |
|----|--------|
| Research board first | Jump straight to `recommend` with empty packs |
| Honest p_model from research | Mechanical force / invent p_model unless user orders emergency force |
| Live recommend by default | Assume dry-run unless user asks |
| Dry-run only when asked | Use dry-run as the silent default |
| Treat Pending as intent | Treat Pending as “already placed on NT” |
| `abandon` missed tickets promptly | Leave phantom Pending blocking risk seats |
| Exclude open risk from “new bets” list | Duplicate place advice for open tickets |
| Prefer quality over volume | Flood slip with weak EV lines |
| Engines in `nt/` are law | Bypass risk/phase/diversify without user consent |
| **Auto-apply learning proposals** after settle | Ask the user to accept/reject learnings |
| Empty slip after **honest deep research** = success | Force seats to “use budget” |
| Deep-research engine **deep_queue** (anti-chalk) | Deep-dive only short ML/O2.5 favourites |
| Treat Coverage Health **critical** as process miss | Silent empty slip while mid-price unresearched |
| Respect recommend soft gate / use `--allow-low-coverage` only explicitly | Bypass coverage with `--force-mechanical` casually |
| Light assess never promotes; engine builds deep_queue | Expect assess-time auto-promote or empty queue forever |
| Prefilter discards majority noise/chalk; prior is rank-only | Use classical prior as recommend `p_model` |
| Composition ≥55% preferred / ≤25% short-main | Pad deep queue with short ML/O2.5 chalk or short alts &lt;1.80 |
| Trust Mechanism A floor (dynamic target / scaffold / sport rotation) for research pressure | Soften min_EV by hand or invent p_model to “fill” the floor |
| Let engine emit `temp_ev_relax` only under safety-net conditions | Manually lower min_EV outside ControlSignals or stack relax over process_gate |
| Respect Exploration/Survival min-EV + open cap + weekly EXPLORE_REGIME quota | Soften 5pp haircut or invent thin EV beyond 2 slots/week |
| Sports equal at zero data (symmetric virgin explore) | Hardcode sport edges from thin history |
| Totalgrense residual ≥ buffer when limits set | place-ack when residual headroom already &lt; buffer |
| Grade A with uncertainty | Grade A on bare point p alone |
| Kelly only when liquid+Brier gates pass | Kelly at small bankroll / thin calibration |
| Trust unit ladder + room packing | EV-band stake above unit without Kelly lift |
| Fill PostSettlementPacket on process_error / poor retro | Settle without root cause / score / XI delta |
| Classify predictability + variance_class + learning_weight every settle | Leave taxonomy blank forever or invent p_model to "fix" |
| Trust ControlSignals as process loop | Expect permanent mults alone to stick after recompute |
| Respect RESEARCH_ONLY / size_mode floor | Force recommend when phase health blocks |

---

## Validation (no feature work)

```bash
python -m pytest tests/ -q
python scripts/run_historical_replay.py -n 40
python scripts/validate_closed_loop.py -n 60
# → docs/CLOSED_LOOP_VALIDATION.md · docs/RESIDUAL_RISKS.md
# → docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md
```

---

## Desk skills (Grok)

User-scope skills in `%USERPROFILE%\.grok\skills\` — load **this file first**, force real tools, list deliverable paths. Full invoke guide: **`docs/DESK_SKILLS.md`**. Optional helpers: `scripts/skill_*.ps1`.

| Slash | Skill | When |
|-------|--------|------|
| `/daily-run` | Full day desk | results → odds → board+light → deep queue → scaffolds → recommend + Reasoning Chains → `outbox/PLACE_THESE.md` → place-ack |
| `/missed-audit` | Mid-band misses | 1.80–2.20 out of deep; `promotion_score` components; cheapest fix; Bodø/Glimt −1.5 & tennis/snooker patterns |
| `/chain-explain` | Reasoning Chain | forensic justify one match/selection (or whole slip) |
| `/bankroll-tune` | Capital tune | secure/phase/unit/regime proposal → `scripts/mc_phase_progression.py` + `capital` CLI |
| `/learning-rootcause` | Taxonomy | predictability + variance_class + learning_weight; `settlement_taxonomy` + `backfill_settlement_taxonomy.py` |

```powershell
# Grok (CWD = tracker root)
# /daily-run
# /missed-audit
# /chain-explain <match> | <selection>
# /bankroll-tune
# /learning-rootcause

# PowerShell helpers
.\scripts\skill_list.ps1
.\scripts\skill_invoke.ps1 daily-run
.\scripts\skill_smoke.ps1
```

---

## Related docs

| Doc | Role |
|-----|------|
| `docs/PACKAGE_IMPLEMENTATION_SUMMARY.md` | **This package** file map + confirmations |
| `docs/RESEARCH_COVERAGE_FIX_SUMMARY.md` | Coverage Health + deep queue + force_coverage |
| `docs/RESEARCH_WORKFLOW.md` | Full stage map (prefilter → deep) |
| `docs/DESK_SKILLS.md` | Grok desk skills install + PowerShell invoke |
| `docs/BANKROLL_PLAN.md` | Clean 500 + Calibration/Survival + multi-year |
| `docs/PHASE_PLAN.md` | Phase ladder 1A–5 + v5 multi-factor |
| `docs/CAPITAL_HYBRID_PROGRESSION.md` | Half-steps + continuous unit + Variant A skim; before/after 500→550; MC |
| `docs/CAPITAL_V2_GO_LIVE.md` | Capital v2 enable / rollback |
| `docs/LUMINA_INTEGRATION.md` | LuminaNT cockpit contract (visuals) |
| `docs/RESIDUAL_RISKS.md` | Honest remaining risks |
| `artifacts/PACKAGE_VALIDATION_REPORT.md` | Success-metric validation |
| `docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md` | ControlSignals + Phase v5 |
| `docs/DIVERSITY_AND_EXPLORE.md` | Virgin explore + diversify |
| `docs/RESEARCH_GATES.md` | Gate field design |
| `docs/SETTLEMENT_LEARNING.md` | Settle + learn loop |

### Desktop (Flet)

See `desktop/AGENTS.md` for UI layout rules. Engines remain law; UI only presents and invokes.

### LuminaNT

Separate repo. Forensic desk over the same tracker root. **Permanent cockpit surfaces:**

| Surface | Must show |
|---------|-----------|
| **DeskStrip primary** | Equity · Liquid · Open risk · Remaining · **Regime** (+cap) · Day TG (if active) · Mode · **Coverage** deep%/surv% · empty-slip · **COV FORCE** · Can bet |
| **Open + planned risk** | Heatmap Pending×ConfirmedPlaced · stacked bars · correlation (multi-ticket match, sport share) |
| **Capital Plan** | Risk rooms · Regime · open-cap / min-EV · TG · Coverage Health block |
| **Shortlist / Decision board** | Deep/Surv/Mid · force_coverage · Regime · Day TG · warn/critical banners |
| **Learnings** | ControlSignals table (temp_gate + force_coverage_priority) |

Data: `risk.json` · `coverage_health.json` · `control_signals.jsonl` · `bets.csv`. Refresh if fingerprint lags. **Never rewrite historical `bets.csv` from the GUI** except via settle/engine APIs.
