# Agent rules — nt-betting-tracker

Real-money capital desk. Engines in `nt/` are law. UI (LuminaNT, Flet desktop) presents and invokes — never invents bankroll math.

> ### System status 2026-07
> | Live | Notes |
> |------|--------|
> | **500 NOK** clean-restart era · capital_v2 ON | Equity = baseline + Σ terminal P/L on `data/bets.csv` only |
> | **Hybrid phases** `1A/1A+/1B/1B+` + continuous unit | [`docs/CAPITAL_HYBRID_PROGRESSION.md`](docs/CAPITAL_HYBRID_PROGRESSION.md) |
> | **Secure Variant A** soft 1.25×/15% · hard 1.50×/30% | Hard replaces soft — never stacked |
> | **Edge-Seeking Research (ESR)** Stage 0–4 | Find best +EV edges · soft dogs not guilty by default · short 1.40–1.80 OK · empty only after scan + expansion |
> | **Stage 1b adaptive multi-agent scan** | A/B/C always + conditional **D** (≥41 Candidate lines/match); merge shortlist 8–15 → primary worklist ≤15 drives Stage 2 when present ([`docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md`](docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md)) |
> | **FEH** | **Demoted / shadow only** — not place law ([`docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md)) |
> | **Coverage floor (A)** + **`temp_ev_relax` (B)** | Floor expands research; never invents `p_model`; relax is rare safety net |
> | **Settlement taxonomy** `learning_weight` · CS gate ≥**0.5** | [`docs/SETTLEMENT_LEARNING.md`](docs/SETTLEMENT_LEARNING.md) |
> | **Desk skills** `/daily-run` · `/missed-audit` · `/chain-explain` · `/bankroll-tune` · `/learning-rootcause` | [`docs/DESK_SKILLS.md`](docs/DESK_SKILLS.md) |
> | **Reasoning** on recommend | `why · support · main risk` + short near-misses in `PLACE_THESE.md` |
>
> Package narrative: permanent rules below. Skills: **`docs/DESK_SKILLS.md`**. Capital hybrid: **`docs/CAPITAL_HYBRID_PROGRESSION.md`**. Taxonomy: **`docs/SETTLEMENT_LEARNING.md`**. **ESR philosophy: [`docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md).** FEH design doc is **SUPERSEDED**.

**Status (permanent package):** clean-restart **500 NOK** era · capital_v2 live · **hybrid half-steps (1A+/1B+) + continuous unit** · **secure bucket Variant A** · **Exploration→Survival→Normal** bankroll regimes · multi-stage quant prefilter · engine deep queue (**edge-seeking promise score**; preferred composition quotas **off**) · **ESR place path** (legacy grade + research_gates + EV + soft odds bands; FEH shadow) · Coverage Health + soft gate · `force_coverage_priority` · totalgrense residual buffer · closed-loop ControlSignals · PhaseState v5 · **neutral sport start at zero data** · **find best edges** (empty slip only after full scan + expansion).

Docs: `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` · `docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md` · `docs/RESEARCH_WORKFLOW.md` · `docs/RESEARCH_GATES.md` · `docs/EXA_RESEARCH_USAGE.md` · `docs/DESK_SKILLS.md` · `docs/BANKROLL_PLAN.md` · `docs/CAPITAL_HYBRID_PROGRESSION.md` · `docs/SETTLEMENT_LEARNING.md` · `docs/RESIDUAL_RISKS.md` · `docs/LUMINA_INTEGRATION.md` · `docs/FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md` (**SUPERSEDED**).

---

## Edge-Seeking Research (ESR) — core law

**Tagline:** Find the best available edges on the board. Evidence first; price is a parameter, not a moral judgment.

| Maxim | Meaning |
|-------|---------|
| **Curious, not paranoid** | Investigate promising lines; do not pre-convict underdogs or short prices |
| **Honest EV** | Haircut stays; do not invent `p_model` to fill seats |
| **Best edges, not perfect packs** | Incomplete notes → soft downgrade / note, not automatic F (unless missing `p_model` / hard research_gates) |
| **Empty slip is rare** | OK only when board truly has no +EV after Stage 2–3 **+ expansion** |
| **No price-led identity** | Neither "1.85–2.20 dog = good" nor "1.85–2.20 dog = bad" |
| **Short favourites OK** | **1.40–1.80** allowed and often preferred when research supports |
| **Soft underdogs not guilty** | Mid-odds UD/HC place on matchup + EV — not anti-soft hard reject |
| **FEH demoted** | Place path = grade + research_gates + EV + odds_confidence; FEH is shadow/audit only |

Full design: **`docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`**.

---

## When the user provides a new or updated odds file

**Trigger:** Any new/updated odds dump in `inbox/` (e.g. `odds_*.txt`, “here’s today’s odds”, “updated odds”), or an explicit request to analyze/recommend from odds.

**You are the Research + Recommendation Agent.** Follow **ESR Stage 0–4** every time — do not skip to mechanical recommend, and do not invent `p_model`.

### Mandatory workflow — Stage 0–4

```
0 Collect → 1a Engine baseline → 1b Adaptive multi-agent scan → 1c Primary worklist
  → 2 Deep (primary only) → 3 Select (+ expand) → 4 Output
```

#### Stage 0 — Collect

Identify the odds file: path the user named, or **newest** `inbox/odds*.txt` by mtime. Write/dump Oddsen for the user timeframe when asked. Odds collection pipeline behaviour unchanged.

#### Stage 1a — Engine baseline (market-scan → board → light)

```bash
python run_nt.py research market-scan --odds <odds_file>
python run_nt.py research board --odds <odds_file>
python run_nt.py research light --odds <odds_file>   # if board did not auto-light
```

| Step | Scope | Output | Can recommend? |
|------|--------|--------|----------------|
| **Prefilter** | Stage1 screens + classical prior on light assess | discard noise/hopeless; `prior_ev` **rank-only** | **No** |
| **Light** | ≥70–85% of board shortlist; sports with ≥5 lines get ≥3 light | verdict pass/fail + notes | **No** |
| **Deep queue SSOT** | Engine-built (`engine_deep_queue: true`) from light-pass | ranked **promising** list (~8–15) in `data/state/deep_queue.json` | **No** until packs |
| **Deep packs** | Agent writes `evidence/*.json` + honest `p_model` on **primary worklist** | gradeable packs | **Yes** |

- **Assess never auto-promotes** (`auto_promote_to_deep: false`).
- **Engine fills deep_queue** via **edge-seeking** `promotion_score` (prior_ev / soft value / natural / light signal — **not** anti-soft, not heavy short-chalk moralization).
- Preferred composition quotas **disabled** under ESR (`deep_min_preferred_share: 0`, `deep_max_short_main_share: 1.0`); coverage **must not** re-arm preferred floor.
- Light is quick/heuristic; Deep stays high quality (sources, script honesty, both sides).
- **No anti-underdog filters at Stage 1.** Soft dogs are candidates like anything else with signal.

### Engine deep queue (ESR — light baseline SSOT)

**Code:** `nt/light_research.py` (`promotion_score`, `build_deep_queue`) · config `research.tiers`.

| Rule | ESR default |
|------|-------------|
| Promise score | prior_ev / soft_value / natural totals / light signal ↑; bare mid-band mild only |
| Short chalk ultra-noise | Mild penalty only (`promo_short_chalk_penalty` small); **1.40–1.80 with signal ranks well** |
| Mid-band alone | **Neutral / mild** boost in ~1.85–2.40 — not identity |
| Bare HC / alt family | Boost **only with signal** (prior_ev / soft / natural / light note) |
| Preferred share / short-main cap | **Off** (0 / 1.0) — pure score ranking |
| Target size | Dynamic ~**8–15** (`deep_target_dynamic`) |
| Coverage re-arm | **Forbidden** when `deep_min_preferred_share <= 0` |

> **Queue rank ≠ place quality.** High promo is a research signal. Place still needs honest pack + research_gates + EV.

**Primary-worklist supersede (when multi-agent shortlist exists):**

| Source | Role |
|--------|------|
| `data/state/deep_queue.json` | **Engine SSOT** for light baseline, coverage floor, top-up, all-fail fallback. Multi-agent merge **never rewrites** it. |
| Multi-agent shortlist 8–15 | Prefer this for Stage 2 seat selection when present |
| **Primary worklist** | `shortlist ∪ coverage_critical`, hard cap **15** — **drives Stage 2** when multi-agent shortlist exists |
| All-fail fallback | Stage 2 uses engine `deep_queue` head (cap 15); never silent-skip deep |

#### Stage 1b — Adaptive multi-agent scan (skeleton)

Full role cards and merge rules: **`docs/skills_mirror_daily-run.md`** / `~/.grok/skills/daily-run/SKILL.md` · design: **`docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md`**.

| Agent | Role | Max | Spawn |
|-------|------|-----|--------|
| **A** | Favourites & HUB — odds **1.40–1.90**; prefer **≥1.70**; **MUST** search football HUB/1X2; **MUST NOT** ignore clear 1X2 for HC; 1.40–1.69 needs structural one-liner + `force_scan:` when Stage 2 intended | 5 | Always |
| **B** | Totals & props (team totals, player props, cards, corners, specials); self-limit ≤2 same `market_family`; if D armed → bias main totals (≤1 long-tail) | 5 | Always |
| **C** | HC + matchup dogs; `force_scan:` only when justified | 5 | Always |
| **D** | Long-tail only (props/cards/corners/shots/specials) | 5 | **Conditional:** any match with **≥41** parseable Candidate lines (`n=40` false, `n=41` true) |

- **Scan-only:** no Exa packs, no `p_model`, no recommend, no ledger write.
- **Budget:** entire scan layer ≤**12 min**. Sequential host: **skip D** if A+B+C already used ≥**10 min** (`scan_agent_missing: D (budget)`).
- **D depth count:** run `research scan-depth` **when available**; else **manual line-count** of Candidates per match is OK until that CLI lands.
- **Merge:** A+B+C(+D when active); family ≤2; shortlist **8–15**; light-fail drop unless `force_scan:`; engine top-up if &lt;8; form-continuity / anti-flip notes remain **soft annotations** after merge (engine math unchanged). Use `research scan-merge` when present.
- Artifacts: `outbox/scan_agent_{a,b,c[,d]}_YYYY-MM-DD.jsonl`, `outbox/MULTI_AGENT_SHORTLIST.md`.

#### Stage 1c — Primary worklist

```text
primary_worklist = multi_agent_shortlist ∪ coverage_critical
cap = 15
```

Stage 2 deep-researches **this list only**. Full-board deep is **refused**.

### Coverage floor + temp_ev_relax (permanent)

Two orthogonal mechanisms. Operators see both on **`data/state/status.md`** → **Coverage floor** section.

#### Mechanism A — quality-preserving floor (never softens EV)

**Code:** `nt/light_research.py` · **Config:** `research.coverage_floor` + `research.tiers.deep_target_*`

| Piece | Behaviour |
|-------|-----------|
| Dynamic `deep_target_n` | `clamp(board_lines // divisor, min, max)` when `deep_target_dynamic` |
| Top-promo scaffold | Force top ~20% by `promotion_score` into consideration |
| Sport rotation | Sports with enough lines and zero deep picks get pressure for one promising line |
| `require_real_pack` | Queue never invents `p_model` |

**Never invents `p_model`. Never softens min_EV / haircut.** Expands *what to research*.

#### Mechanism B — `temp_ev_relax` safety net

**Code:** `nt/control_signals.py` · applied in `nt/portfolio.py`

| Rule | Live default |
|------|----------------|
| When | Large board (≥15 matches) **and** coverage warn/critical **and** deep_queue empty **and** light-pass survivors exist |
| Soften | Per-line allowlist · `delta_ev` 1–2pp · TTL 24h · stake ×0.80 |
| Never | High-odds / grade C (when excluded) · grade F · global min_EV rewrite |
| Blocked | If `process_gate_raise` > 0 for the candidate |

**Agent mandate:** Do not invent `p_model`. Do not manually lower min_EV outside ControlSignals. Prefer Mechanism A (more deep research).

#### Stage 2 — Deep research (primary worklist)

Work the **primary worklist** (multi-agent shortlist ∪ coverage_critical, cap 15). When multi-agent shortlist is missing/all-fail, fall back to engine **deep_queue** head (cap 15). Prefer **`/deep-research`** skill + atomic `scripts/write_deep_research_pack.py`. Use **Exa** (primary) + sport sites (Sofascore, FBref, HLTV, ATP/WTA, Flashscore, etc.). See **`docs/EXA_RESEARCH_USAGE.md`**.

**Refuse full-board deep.**

For each line:

1. **Both sides** form and recent results  
2. **H2H** — record polarity honestly; **mixed is allowed**  
3. Ranking / strength  
4. Motivation, rest, injuries, style matchup  
5. Natural markets that fit the profile — elevate candidates; do not hard-F HC only for imperfect natural eval  
6. Honest `p_model` under `selection.probability_haircut: 0.03`  

**Side and matchup first, price second** — but do **not** treat soft underdogs as automatic rejects. Short favourites **1.40–1.80** are welcome when form/rank support them.

**Pack minimum (not F):** `p_model` · `summary` · `failure_modes` · real sources (ESR default **4**). Soft/recommended: structured H2H/form/rank.

### FEH — demoted / shadow only (not place law)

**Code:** `nt/evidence_hierarchy/` may still run soft audit. **Config:** `selection.evidence.forced_hierarchy.enabled: false`, `shadow_mode: true` → `place_uses_saef` **false**.

| Old FEH rule | ESR |
|--------------|-----|
| NON-BYPASSABLE place law | **Off** — legacy grade + research_gates + EV |
| Anti-soft hard F | **Off** — matchup + EV judge soft dogs |
| Checklist incomplete → F | Soft note / lower grade path only |
| Empty slip over weak soft B | Empty only after expansion + no +EV |
| `FEH_TEST_CAP:feh_v1` | **`TEST_CAP:esr_v1`** 10 NOK first 10 placed |

Historical design (do not follow for place): `docs/FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md` (**SUPERSEDED**).

### Multi-sport research gates (engine-enforced)

Full design: **`docs/RESEARCH_GATES.md`**. These block **real nonsense**, not volume of honest edges.

| Field | Role |
|-------|------|
| `context_risk` / `rotation_risk` | `low` \| `medium` \| `high` |
| `availability_status` / `lineup_status` | `confirmed` \| `predicted` \| `stable_guess` on sensitive markets |
| `availability_notes` | Injuries, minutes, fitness, rotation |
| `script_lean` | Should agree with selection |
| `selection_vs_script` | Never `conflict` |
| `base_rate_conflict` | `true` if history opposes the bet |

**Hard rejects (keep):** script conflict · base-rate conflict · missing availability on totals/BTTS/props · anti-script unders · tennis retirement + overs · basketball star_rest + player overs.

**Soft checks:** thin notes, high-odds + predicted — raise bar / note, do not stack five other volume killers.

**Grade A:** needs uncertainty when configured (`p_model_sd`, edge CI, or multi-model) — not bare point p alone for Grade A claim.

#### Evidence packs (`evidence/*.json`)

- Honest `p_model` · `summary` · `failure_modes` · real sources  
- Gate fields on sensitive markets  
- No mechanical filler; no inventing edge from price band alone  

#### Stage 3 — Ready + select

**No Dual Decision layer yet** (advisory Stage 3.1–3.3 is a later skill/AGENTS amendment). Stage 3 = engine ready + recommend only.

```bash
python run_nt.py research ready --odds <odds_file>
```

Also read **`data/state/coverage_health.json`**:

- `shortlist_deep_pct` · `deep_survivable_pct` · `mid_unresearched_n` · `empty_slip_risk` · `level` (`ok` \| `warn` \| `critical`)

```bash
python run_nt.py recommend --odds <odds_file>
# only if Coverage Health critical and user/ops explicitly override:
python run_nt.py recommend --odds <odds_file> --allow-low-coverage
```

Present the slip with reasoning.

- **Default = live recommend** — writes **Pending** when the engine picks bets.  
- **Coverage soft gate:** critical Coverage Health **blocks** recommend unless `--allow-low-coverage`.  
- **Pending = intent, not NT confirmation.** Open risk until `place-ack`, settle, or `abandon`.  
- **Dry-run only when the user asks.**  
- **Do not include already-open bets** in “new place” advice.  
- Recommend lines that clear **research_gates + grade + EV** (odds_confidence soft/band floors). Soft underdog OK with matchup + EV; short 1.40–1.80 OK with support.  
- **Target 2–6 picks** on large boards when honest EV exists (phase `max_bets` binds).  
- **Empty slip** only if truly no +EV after Stage 2–3 **and expansion** (below). Empty because promising lines were never researched = **process miss**.  
- **10 NOK test cap (when active):** seats clipped to **10 NOK** after stake mutations; notes carry `TEST_CAP:esr_v1` (legacy `FEH_TEST_CAP:` still counted). Does **not** change capital_v2.  
- **Reasoning (always):** even empty/blocked recommend, write chains + `## Reasoning` + `## Near-miss / Rejected` in `PLACE_THESE.md`.

##### Reasoning format (every pick)

```markdown
## Reasoning

### 1. {Selection} @ {odds} · Grade · EV · stake
- **Why:** …
- **Support:** …
- **Main risk:** …

## Near-miss / Rejected
- {line} — short reason (EV / gates / thin research)
```

Near-misses short. Prefer mid-band + light-pass for near-miss sources. Light LATEST is SSOT for promo join. Verify: `python scripts/verify_chain_residuals.py`.

##### Stage 3b — Expansion (large board)

If board is large (≥15 matches or ≥80 lines) **and** recommend yields **&lt; 2** picks after full deep of primary queue:

1. Deep next **5–8** light-pass lines by promo score (or engine `expansion_needed` / `next_tier_keys` in `deep_queue.json` when present).  
2. Re-run recommend.  
3. **Do not** accept empty slip while next tier is unresearched — that is a process miss.

##### ControlSignals

- `temp_gate_raise` — min_ev raise + force confirmed lineup (process_error path; learning_weight ≥ 0.5).  
- `force_coverage_priority` — **research** pressure (TTL 4–7d); target band widens under ESR (~1.40–2.80); **does not invent p_model or soften haircut**.  
- `temp_ev_relax` — safety net only (Mechanism B).

#### Stage 4 — Place confirmation / abandon

```bash
python run_nt.py place-ack --ids <bet_id>[,<bet_id>...]
python run_nt.py abandon --ids <bet_id> --reason missed_prematch
python run_nt.py abandon --match "Humphries" --reason missed_prematch
```

- **Operator default:** user places recommended tickets on NT. After live `recommend` writes Pending, **`place-ack` those new bet_ids** unless skipped/missed → `abandon`.  
- **ConfirmedPlaced** — open risk until Win/Loss/Refunded.  
- **Abandoned** — not open risk; not a phase/learning sample.  
- Never leave unplaceable Pending counting against daily risk.

#### Dry-run (opt-in)

Use `--dry-run` only if the user explicitly requests a dry-run / preview / no-write pass.

---

## Clean restart + neutral sport start (permanent)

| Rule | Detail |
|------|--------|
| **Baseline** | `bankroll.baseline_nok: 500` · equity = baseline + Σ performance P/L on `data/bets.csv` only |
| **Era** | `bankroll.era_start` · `include_era_archive: false` |
| **Fresh start** | `python scripts/fresh_start_500.py` — archives ledger/state, resets learning/signals/**coverage_health**, sets era_start, refresh → equity **500** |
| **Zero data** | Learning mults **1.0 / 0** until `min_sample`; **no** sport hard-edges |
| **Virgin explore** | Same `explore_virgin_ev_boost` for all sports at n=0 — **symmetrical** |
| **Regime floor** | Exploration **4%** / Survival **7.5%**; weekly `EXPLORE_REGIME` quota may use **2.0–3.9%** (≤2 unit bets/week, mid/alt only) |
| **Haircut** | High-Volume v2: **3pp** haircut · high-odds path for odds **>2.50** · Grade C placeable with core reason when configured |

---

## Bankroll regimes (Exploration → Survival → Normal)

**Orthogonal to phase ladder.** Code: `nt/bankroll_regime.py` · config `bankroll_regime:` · binds via `risk.json`.

| Regime | When | min-EV (after haircut) | Open-risk cap (pending only) |
|--------|------|------------------------|------------------------------|
| **Exploration** | settled **&lt; 40** **and** equity **&lt; 650** | **4%** + ≤**2 unit**/week at **2.0–3.9%** mid/alt (`EXPLORE_REGIME`) | **50 NOK** |
| **Survival** | after Exploration exit until graduate | **7.5%** (no thin quota) | **50 NOK** |
| **Normal** | settled ≥**100** **or** equity ≥**800** | `selection.standard_min_ev` | phase + capital_v2 only |

**Open risk law:**

- Counts **Pending + ConfirmedPlaced** only (`day_pending_risk`).  
- **Frees immediately** on Win / Loss / Refunded (and Abandon).  
- `remaining_risk = min(phase, portfolio_room, regime_cap − open_pending, totalgrense_usable)`.  
- Mid-odds prefer under Exploration/Survival is **research/sort only** when enabled — **not** place law; ESR prefers matchup + EV over mid-odds identity (`prefer_mid_odds: false` under ESR defaults).

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
| size_mode (**capital hard floor**) | NORMAL → REDUCED (≥15% DD) → FROZEN (≥25% DD or manual freeze). Phase health may **only tighten**, never loosen FROZEN. |
| **Unit (primary)** | When `phase_continuous.enabled`: **continuous unit** = `stake_min + (equity − enter) / scale_factor` (whole krone, clamp band) with **carry-forward floor**. Fallback liquid ladder: **12 / 15 / 20**. Never stake in (0, min_stake). |
| Open room | Phase open budget ∩ portfolio open-risk cap ∩ **regime open cap** ∩ **totalgrense usable** |
| Daily / weekly | Hard loss stops on liquid SoD / SoW |
| **Secure bucket Variant A** | Soft **1.25× ref / 15%**; hard **1.50× ref / 30%** — **hard replaces soft, never stacked**. Unlock: auto after **25** settles since lock, or manual 7d cooldown. |
| **Kelly (P2)** | Optional **lift above unit only** when liquid ≥ **1500**, calibration n ≥ 30, Brier ≤ max; max **1.5× unit**. Never shrinks below unit. |
| Audit | `data/state/stake_decisions.jsonl`, `capital_segments.json` |

### Config key pointers (do not invent values)

| Concern | Keys |
|---------|------|
| Enable capital stack | `capital_v2.enabled` |
| Liquid unit fallback | `capital_v2.unit_ladder` · grade mults `capital_v2.grade_stake_mult` |
| Secure Variant A | `capital_v2.secure_bucket.variant: A` · soft/hard trigger mults & fractions · unlock keys |
| Half-steps | `phases."1A+"` / `phases."1B+"` · `hard_phase_id` |
| Continuous unit / open-risk | `phase_continuous.enabled` · `phase_continuous.scale_factor` |
| Phase ladder numbers | `phases.*.enter_equity` / `stake_min` / `stake_max` / `daily_risk_*` |
| Stability / demote | `phase_stability.*` |

**Stranded remainder:** liquid may sit under one unit while open risk is high — UI surfaces this; do not force a ticket below floor.

**Secure unlock:** `python run_nt.py capital unlock-secure --confirm`  
**Unfreeze (after human review only):** `python run_nt.py capital unfreeze --confirm`

---

## Phase system (v5 multi-factor + hybrid half-steps)

**Labels:** **1A → 1A+ → 1B → 1B+ → 2 → … → 5** (`config.yaml`).  
Half-steps keep **parent hard gates** via `hard_phase_id`. Continuous unit / open-risk progress when `phase_continuous.enabled`.  
Examples: **`docs/CAPITAL_HYBRID_PROGRESSION.md`**.

Multi-factor `phase_state` overlays: equity/dd scores · process_error_rate_14d · calibration · open_risk_concentration · learning_health.

**Hard overlays (fail-closed):**

- `process_error_rate_14d > 0.25` with n_reviews ≥ 4 → `size_mode_floor=REDUCED` (or `RESEARCH_ONLY`), sticky 7 days  
- High open concentration (≥55% one sport) **or** poor Brier → **block high-odds**  
- `RESEARCH_ONLY` → `can_bet=False`

**Law:** `risk.size_mode` severity ≥ capital DD mode. Phase never upgrades FROZEN/REDUCED from DD.

State: `data/state/phase.json`, reasons also on `risk.json`.

---

## Settlement + learning + ControlSignals (agent-owned)

After every settle:

1. **Match fail-closed** — dual soft-match; never force wrong ticket.  
2. **PostSettlementPacket** — if `variance_tag=process_error` (or research_miss/miss) **or** `research_quality_retro=poor|wrong|miss`, **required fields** before ledger write:  
   `actual_score`, `actual_lineup_status`, `predicted_vs_actual_xi_delta`, `script_realized`, `process_root_cause`.  
3. **Taxonomy (every settled bet)** — predictability · variance_class · learning_weight (engine formula in `nt/settlement_taxonomy.py`).  
   Safe backfill defaults to **proposed file only** — never live without `--apply`:
   ```bash
   python scripts/backfill_settlement_taxonomy.py --n 30
   python scripts/backfill_settlement_taxonomy.py --n 30 --apply   # after review
   ```
4. Learning recompute (`run_learning`) — sample influence × `learning_weight`.  
5. **ControlSignals** — `temp_gate_raise` · `force_coverage_priority` · `temp_ev_relax` as above.  
6. **Learning proposals** auto-resolve when configured. Mults are soft; ControlSignals are durable process actuators.

### Learning must not grow hard reject lists

| Allowed | Forbidden |
|---------|-----------|
| stake_mult / ev_boost clamps | Auto hard-reject config patches |
| process_gate **temp** raises | Re-enable anti_soft / FEH place-owning from settlement |
| Taxonomy + learning_weight | Block lists from single-loss anecdotes |
| Soft mult recompute | FEH-style permanent guilt lists |

```bash
python run_nt.py control-signals list --json
python run_nt.py control-signals emit --sport football --source force_review --reason "…"
python run_nt.py control-signals revoke --sport football --actor agent
python run_nt.py failures rebuild
python run_nt.py failures query --q "rotation under"
python scripts/validate_closed_loop.py -n 60
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
| Research board first (Stage 1a all lines + Stage 1b multi-agent → primary worklist) | Jump straight to `recommend` with empty packs |
| Honest p_model from research | Invent p_model unless user orders emergency force |
| Live recommend by default | Assume dry-run unless user asks |
| Dry-run only when asked | Use dry-run as the silent default |
| Treat Pending as intent | Treat Pending as “already placed on NT” |
| `abandon` missed tickets promptly | Leave phantom Pending blocking risk seats |
| Exclude open risk from “new bets” list | Duplicate place advice for open tickets |
| **Find best honest edges** (target 2–6 large boards) | Flood slip with weak EV **or** reject everything imperfect |
| Engines in `nt/` are law | Bypass risk/phase/diversify without user consent |
| **ESR** — evidence first; soft dogs not guilty by default | Treat mid-band UD as auto-attractive **or** auto-guilty |
| Short favourites **1.40–1.80** when research supports | Demand Grade A + 8 sources only for every short price |
| Empty slip **only after** full deep + expansion + no +EV | Celebrate empty slip while next tier unresearched |
| **Auto-apply learning proposals** after settle | Ask the user to accept/reject learnings |
| Deep-research **primary worklist** (multi-agent shortlist when present; else deep_queue head) | Deep-dive only 2–3 lines while ignoring shortlist/queue; full-board deep |
| Treat Coverage Health **critical** as process miss | Silent empty slip while promising lines unresearched |
| Respect recommend soft gate / use `--allow-low-coverage` only explicitly | Bypass coverage with `--force-mechanical` casually |
| Light assess never promotes; engine builds deep_queue | Expect assess-time auto-promote |
| Prefilter discards noise; prior is rank-only | Use classical prior as recommend `p_model` |
| Trust Mechanism A floor for research pressure | Soften min_EV by hand or invent p_model |
| Let engine emit `temp_ev_relax` only under safety-net conditions | Manually lower min_EV or stack relax over process_gate |
| Respect **10 NOK** test cap (`TEST_CAP:esr_v1`) when active | Raise stakes above cap; change capital_v2 for the test |
| Respect Exploration/Survival min-EV + open cap + EXPLORE_REGIME | Soften haircut or invent thin EV beyond quota |
| Sports equal at zero data | Hardcode sport edges from thin history |
| Totalgrense residual ≥ buffer when limits set | place-ack when residual already &lt; buffer |
| Grade A with uncertainty when claiming A | Grade A on bare point p alone |
| Kelly only when liquid+Brier gates pass | Kelly at small bankroll / thin calibration |
| Trust unit ladder + room packing | EV-band stake above unit without Kelly lift |
| Fill PostSettlementPacket on process_error / poor retro | Settle without root cause / score / XI delta |
| Classify predictability + variance_class + learning_weight every settle | Leave taxonomy blank; invent p_model to “fix” |
| Learning soft mults + temp gates only | Grow permanent hard-reject lists from FEH/settlement |
| Trust ControlSignals as process loop | Expect permanent mults alone to stick after recompute |
| Respect RESEARCH_ONLY / size_mode floor | Force recommend when phase health blocks |
| Exa feeds packs + reasoning | Use Exa as FEH hard-reject gate |

---

## Validation (no feature work)

```bash
python -m pytest tests/ -q
python scripts/run_historical_replay.py -n 40
python scripts/validate_closed_loop.py -n 60
# → docs/CLOSED_LOOP_VALIDATION.md · docs/RESIDUAL_RISKS.md
```

---

## Desk skills (Grok)

User-scope skills in `%USERPROFILE%\.grok\skills\` — load **this file first**, force real tools, list deliverable paths. Full invoke guide: **`docs/DESK_SKILLS.md`**. Optional helpers: `scripts/skill_*.ps1`.

| Slash | Skill | When |
|-------|--------|------|
| `/daily-run` | Full day desk | settle → odds → 1a baseline → 1b adaptive A/B/C(+D) → primary worklist ≤15 → `/deep-research` → recommend + why/support/risk → `PLACE_THESE.md` → place-ack (10 NOK cap when active) |
| `/missed-audit` | Missed edges | promising lines out of deep; promo components; cheapest fix — **not** soft-dog guilt |
| `/chain-explain` | Reasoning | **why · support · main risk** for one match/selection (or whole slip) |
| `/bankroll-tune` | Capital tune | secure/phase/unit/regime proposal → MC + capital CLI |
| `/learning-rootcause` | Taxonomy | predictability + variance_class + learning_weight; **no hard-reject list growth** |

```powershell
# Grok (CWD = tracker root)
# /daily-run
# /missed-audit
# /chain-explain <match> | <selection>
# /bankroll-tune
# /learning-rootcause

.\scripts\skill_list.ps1
.\scripts\skill_invoke.ps1 daily-run
.\scripts\skill_smoke.ps1
```

---

## Related docs

| Doc | Role |
|-----|------|
| `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` | **ESR authoritative philosophy** |
| `docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md` | Adaptive Stage 1b + Dual Decision design (Dual Decision skill not landed yet) |
| `docs/RESEARCH_WORKFLOW.md` | Stage 0–4 map + CLI |
| `docs/RESEARCH_GATES.md` | Hard nonsense vs soft checks |
| `docs/EXA_RESEARCH_USAGE.md` | Exa feeds research (not FEH hard reject) |
| `docs/DESK_SKILLS.md` | Grok desk skills install + invoke |
| `docs/skills_mirror_daily-run.md` | Repo mirror of daily-run skill |
| `docs/FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md` | **SUPERSEDED** FEH design |
| `docs/BANKROLL_PLAN.md` | Clean 500 + multi-year |
| `docs/PHASE_PLAN.md` | Phase ladder 1A–5 + v5 multi-factor |
| `docs/CAPITAL_HYBRID_PROGRESSION.md` | Half-steps + continuous unit + Variant A |
| `docs/CAPITAL_V2_GO_LIVE.md` | Capital v2 enable / rollback |
| `docs/LUMINA_INTEGRATION.md` | LuminaNT cockpit contract |
| `docs/RESIDUAL_RISKS.md` | Honest remaining risks |
| `docs/SETTLEMENT_LEARNING.md` | Settle + learn loop |
| `docs/DIVERSITY_AND_EXPLORE.md` | Virgin explore + diversify |
| `docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md` | ControlSignals + Phase v5 |

### Desktop (Flet)

See `desktop/AGENTS.md` for UI layout rules. Engines remain law; UI only presents and invokes.

### LuminaNT

Separate repo. Forensic desk over the same tracker root. **Permanent cockpit surfaces:**

| Surface | Must show |
|---------|-----------|
| **DeskStrip primary** | Equity · Liquid · Open risk · Remaining · **Regime** (+cap) · Day TG (if active) · Mode · **Coverage** deep%/surv% · empty-slip · **COV FORCE** · Can bet |
| **Open + planned risk** | Heatmap Pending×ConfirmedPlaced · stacked bars · correlation |
| **Capital Plan** | Risk rooms · Regime · open-cap / min-EV · TG · Coverage Health |
| **Shortlist / Decision board** | Deep queue · force_coverage · Regime · Day TG · warn/critical banners |
| **Learnings** | ControlSignals table |

Data: `risk.json` · `coverage_health.json` · `control_signals.jsonl` · `bets.csv`. Refresh if fingerprint lags. **Never rewrite historical `bets.csv` from the GUI** except via settle/engine APIs.
