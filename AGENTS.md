# Agent rules — nt-betting-tracker

Real-money capital desk. Engines in `nt/` are law. UI (LuminaNT, Flet desktop) presents and invokes — never invents bankroll math.

> ### System status 2026-07
> | Live | Notes |
> |------|--------|
> | **500 NOK** clean-restart era · capital_v2 ON | Equity = baseline + Σ terminal P/L on `data/bets.csv` only |
> | **Hybrid phases** `1A/1A+/1B/1B+` + continuous unit | [`docs/CAPITAL_HYBRID_PROGRESSION.md`](docs/CAPITAL_HYBRID_PROGRESSION.md) |
> | **Secure Variant A** soft 1.25×/15% · hard 1.50×/30% | Hard replaces soft — never stacked |
> | **Edge-Seeking Research (ESR)** Stage 0–4 | Find best +EV edges · soft dogs not guilty by default · short 1.40–1.80 OK · empty only after scan + expansion |
> | **FEH** | **Demoted / shadow only** — not place law ([`docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md)) |
> | **Coverage floor (A)** + **`temp_ev_relax` (B)** | Floor expands research; never invents `p_model`; relax is rare safety net |
> | **Settlement taxonomy** `learning_weight` · CS gate ≥**0.5** | [`docs/SETTLEMENT_LEARNING.md`](docs/SETTLEMENT_LEARNING.md) |
> | **Settlement Lessons + diversify + archive isolation** | Soft lessons after settle · hard max **2** `market_family` · similar-recent demote · **never** read `history/archives/` or `history/rounds/` |
> | **Multi-agent Stage 1b scan** | Agents A/B/C ≤5 each → merge shortlist 8–15 → primary worklist = shortlist ∪ coverage_critical (cap 15) · design [`docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md`](docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md) |
> | **Desk skills** `/daily-run` · `/missed-audit` · `/chain-explain` · `/bankroll-tune` · `/learning-rootcause` | [`docs/DESK_SKILLS.md`](docs/DESK_SKILLS.md) |
> | **Reasoning** on recommend | `why · support · main risk` + short near-misses in `PLACE_THESE.md` |
>
> Package narrative: permanent rules below. Skills: **`docs/DESK_SKILLS.md`**. Capital hybrid: **`docs/CAPITAL_HYBRID_PROGRESSION.md`**. Taxonomy: **`docs/SETTLEMENT_LEARNING.md`**. **ESR philosophy: [`docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md).** FEH design doc is **SUPERSEDED**.

**Status (permanent package):** clean-restart **500 NOK** era · capital_v2 live · **hybrid half-steps (1A+/1B+) + continuous unit** · **secure bucket Variant A** · **Exploration→Survival→Normal** bankroll regimes · multi-stage quant prefilter · engine deep queue (**edge-seeking promise score**; preferred composition quotas **off**) · **multi-agent Stage 1b scan** (A/B/C → shortlist → primary worklist) · **ESR place path** (legacy grade + research_gates + EV + soft odds bands; FEH shadow) · Coverage Health + soft gate · `force_coverage_priority` · totalgrense residual buffer · closed-loop ControlSignals · PhaseState v5 · **Settlement Lessons** (soft TTL) · diversify hard max **2** `market_family` + similar-recent · **archive isolation** (no `history/archives|rounds` memory) · **neutral sport start at zero data** · **find best edges** (empty slip only after full scan + expansion).

Docs: `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` · `docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md` · `docs/RESEARCH_WORKFLOW.md` · `docs/RESEARCH_GATES.md` · `docs/EXA_RESEARCH_USAGE.md` · `docs/DESK_SKILLS.md` · `docs/BANKROLL_PLAN.md` · `docs/CAPITAL_HYBRID_PROGRESSION.md` · `docs/SETTLEMENT_LEARNING.md` · `docs/RESIDUAL_RISKS.md` · `docs/LUMINA_INTEGRATION.md` · `docs/FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md` (**SUPERSEDED**).

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

## Settlement Lessons + diversify + archive isolation (automatic desk law)

Engines already enforce these (PR1–PR3). Agents and `/daily-run` must **surface and respect** them every session — not re-invent place law.

### After settle with ≥1 terminal — Settlement Lessons first

When a settle batch writes **≥1** terminal outcome (Win / Loss / Refunded):

1. Engine writes **`outbox/SETTLEMENT_LESSONS.md`** (human) + **`data/state/settlement_lessons.json`** (SSOT, soft_awareness TTL).
2. **Before Stage 1 research / board**, the agent **reads and prints** Settlement Lessons (main_reason · outcome_driver · soft notes).
3. Missing or **stale** lessons (no file, empty, or older than TTL / not from this batch) → **warning only** — continue research. **Not** a hard-stop.
4. Soft awareness demotes portfolio **sort_ev** only (`lessons_soft:` …) — **never** permanent hard rejects; **never** invents `p_model` or softens min_EV.
5. **ControlSignals unchanged** (`temp_gate_raise` · `force_coverage_priority` · `temp_ev_relax` still primary process actuators).

Config: `learning.settlement_lessons.*` · code `nt/settlement_lessons.py`. Detail: [`docs/SETTLEMENT_LEARNING.md`](docs/SETTLEMENT_LEARNING.md).

### Portfolio diversify (visible; engine hard/soft)

| Rule | Behaviour |
|------|-----------|
| **Hard max 2** `market_family` | Coarse family open+slip (`max_per_market_family: 2`). Line is **not** in the key (tennis O/U 21.5–23.5 all → `tennis_totals`). |
| **similar-recent** | Soft demotion on last ~10–15 **live** settled+pending; same sport + family + line tolerance. Visible on rejects/notes / `sort_ev` — true EV stays honest. |
| **Lessons soft** | Independent of similar-recent; TTL soft awareness from Settlement Lessons. |
| Stage 1 engine queue | **No** engine demote of deep_queue by family/lessons — diversify binds at **recommend / portfolio**. |
| Multi-agent shortlist (1b) | Soft family **≤2** on Stage 2 **work order only** — does **not** rewrite `deep_queue.json`. See diversity triad below. |

Detail: [`docs/DIVERSITY_AND_EXPLORE.md`](docs/DIVERSITY_AND_EXPLORE.md) · multi-agent design [`docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md`](docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md).

### Archive isolation — FORBIDDEN memory paths

**Never** load, cite, or seed diversify / similar-recent / Settlement Lessons / learning peers from:

- `history/archives/`
- `history/rounds/`
- **Git history / stash / other branches' `data/bets.csv` or `data/state/*`**

**Allowed live memory only:** current working-tree `data/bets.csv` · open Pending/ConfirmedPlaced · latest results (`inbox/results*`) · **current** odds dump · current `data/state/*` live SSOT.

`load_bets` / `assert_not_archive_path` fail-closed on archive paths. Era rows (`source==era_archive`) stay out of live windows via `filter_live_rows`.

### Live desk SSOT — NEVER overwrite during engineering

**Hard law (2026-07-25 clean-restart era):** the live ledger is the operator's money state. Engineering (`/execute-plan`, worktrees, branch switch, cherry-pick, stash) **must not** replace it.

| Forbidden | Why |
|-----------|-----|
| `git checkout <branch> -- data/bets.csv` / `data/state/*` | Restores old era (e.g. 28-settled 550 NOK) over clean 500 NOK |
| `git stash pop/apply` that rewrites desk SSOT without explicit user ask | Same |
| `git restore` / merge that silently rewrites `data/bets.csv` | Same |
| Reading `history/archives/*` into live paths | Archive is cold storage only |
| Using equity/settled_count from an old branch as "current" | Desk is working tree only |

| Required | Detail |
|----------|--------|
| **Before any git branch switch that might touch data/** | Confirm live desk: `python run_nt.py status` — expect **era_start ≥ 2026-07-25**, baseline **500**, only this-era bets |
| **After accidental overwrite** | Stop. Restore from last known good live copy (operator-confirmed). Do **not** invent history from archives. |
| **Local protection** | Live files use `git update-index --skip-worktree` + `.gitignore` so checkouts do not clobber them |
| **Virgin learning** | Do not re-import pre-era `learning.json` sports ROI into the clean era |

**Current clean era (operator SSOT):** `bankroll.era_start: 2026-07-25` · baseline **500 NOK** · live open = ConfirmedPlaced/Pending from **2026-07-25 only** · no pre-2026-07-25 settled ledger in equity.

### Untouched by this layer

| Keep as-is | Meaning |
|------------|---------|
| **No FEH / anti-soft revival** | FEH stays shadow; soft dogs not guilty by default |
| **capital_v2 / phase / secure / unit / 10 NOK cap** | Unchanged |
| **ControlSignals** | Unchanged contracts and emit paths |

---

## When the user provides a new or updated odds file

**Trigger:** Any new/updated odds dump in `inbox/` (e.g. `odds_*.txt`, “here’s today’s odds”, “updated odds”), or an explicit request to analyze/recommend from odds.

**You are the Research + Recommendation Agent.** Follow **ESR Stage 0–4** every time — do not skip to mechanical recommend, and do not invent `p_model`.

### Mandatory workflow — Stage 0–4

```
0 Collect  →  1a Engine board/light  →  1b Multi-agent scan  →  1c Primary worklist
           →  2 Deep (primary worklist only)  →  3 Select (+ expand)  →  4 Output
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
| **Light** | ≥70–85% of shortlist; sports with ≥5 lines get ≥3 light | verdict pass/fail + notes | **No** |
| **Deep queue** | Engine-built worklist (`engine_deep_queue: true`) from light-pass | ranked **promising** list (~8–15) | **No** until packs |
| **Deep packs** | Agent writes `evidence/*.json` + honest `p_model` | gradeable packs | **Yes** |

- **Assess never auto-promotes** (`auto_promote_to_deep: false`).
- **Engine fills deep_queue** via **edge-seeking** `promotion_score` (prior_ev / soft value / natural / light signal — **not** anti-soft, not heavy short-chalk moralization).
- Preferred composition quotas **disabled** under ESR (`deep_min_preferred_share: 0`, `deep_max_short_main_share: 1.0`); coverage **must not** re-arm preferred floor.
- Light is quick/heuristic; Deep stays high quality (sources, script honesty, both sides).
- **No anti-underdog filters at Stage 1.** Soft dogs are candidates like anything else with signal.

#### Stage 1b — Multi-agent scan (after board/light; before deep)

**Default on full `/daily-run` and new-odds research.** Controlled parallel scan only — **no** Exa packs, **no** write-pack, **no** recommend, **no** ledger writes. Design: [`docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md`](docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md).

**Legal universe:** full current odds dump. Board / light / `deep_queue` are **hints only**.

| Agent | Role | Max | Notes |
|-------|------|-----|-------|
| **A** | Favourites **1.40–1.90** (prefer 1.40–1.80 when strong) | **5** | Scan only · ML/fav side with form/rank story |
| **B** | Totals & player props | **5** | Scan only · self-limit **≤2** same `market_family` |
| **C** | Handicaps & matchup dogs with **real reason** | **5** | Scan only · not bare price |

**Main agent merge:**

1. Dedupe by `evidence_pair_key(match, selection)`; union `scan_agents` → render `scan_agent: A+C`.
2. After merge each `market_family` **must be ≤2** (drop when ≥3); second seat allowed; prefer spread to 1 when priority equal.
3. Soft open-book occupancy: deprioritize / prefer drop when live open family or sport already at portfolio max (Pending+ConfirmedPlaced only — never archives).
4. Soft prefer **≤3** candidates per sport on multi-sport boards when shortlist stays ≥8.
5. **Light-eligibility (KD16) for multi-agent-only lines** (not already in engine `deep_queue`): light **pass** or **never lighted** → eligible; hard light-**fail** → **DROP** unless scan reason contains `force_scan:` and main agent keeps with note. Avoid expensive Exa on light-fail noise.
6. Final multi-agent shortlist band: **8–15** (may be &lt;8 on tiny boards; if &lt;8 and engine has unused light-pass not open-full, top up by promo).
7. Write **`outbox/MULTI_AGENT_SHORTLIST.md`** (+ optional `outbox/scan_agent_{a,b,c}_*.jsonl`).

**Failure / fallback:** parallel preferred; sequential A→B→C if spawn unavailable; wait ≤12 min; partial merge + engine top-up if some agents missing; **all-fail** → `primary_worklist = engine deep_queue` (pre-plan path). Do **not** rewrite `data/state/deep_queue.json`.

#### Stage 1c — Primary worklist (KD15)

```text
coverage_critical =
  engine deep_queue lines tagged coverage_floor:top_promo_scaffold
  OR coverage_floor:sport_rotation

primary_worklist =
  unique_by evidence_pair_key( multi_agent_shortlist ∪ coverage_critical )
  hard-capped at 15
  (shortlist first, then remaining coverage_critical by promo desc)

remaining engine-only lines → Stage 3b expansion only (not ignored forever)
```

When multi-agent layer fails entirely: primary worklist = engine `deep_queue`.

#### Diversity triad (law — do not misread)

| # | Layer | Rule |
|---|-------|------|
| **(1)** | **Engine `deep_queue` SSOT** | Unchanged. **No** family demote of engine queue at Stage 1. Coverage floor + promo ranking remain engine law. |
| **(2)** | **Multi-agent shortlist overlay** | Soft family cap on **Stage 2 agent work order only**: each `market_family` ≤2 after merge. Does **not** rewrite `deep_queue.json`. |
| **(3)** | **Portfolio place law** | Hard max **2** `market_family` **and** `max_per_sport: 2` on open+slip at recommend — **unchanged**. |

**Forbidden misreads:** (a) “family demote is illegal everywhere” → wrong, shortlist soft cap is legal; (b) “hand-prune engine queue by family before deep” → wrong, engine queue stays intact.

#### Multi-agent non-goals (hard)

- Parallel **deep** research agents · multi-agent recommend/place/stake · **FEH / anti-soft revival**
- Engine hard demote of `deep_queue` by family · rewrite `deep_queue.json` from merge
- **capital_v2 / phase / secure / unit / 10 NOK** changes · archive/history memory paths

### Engine deep queue (ESR — inherit every session)

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

> **Queue rank ≠ place quality.** High promo gets researched. Place still needs honest pack + research_gates + EV.

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

#### Stage 2 — Deep research (primary worklist only)

**When multi-agent Stage 1b ran:** deep **PRIMARY WORKLIST** from `outbox/MULTI_AGENT_SHORTLIST.md` (shortlist ∪ coverage_critical, cap 15). **Do not** default to “work engine deep_queue first.” **Do not** hand-prune `deep_queue.json`. **Do not** deep random odds lines outside primary worklist + Stage 3b expansion.

**When multi-agent failed entirely:** primary worklist = engine `deep_queue` (pre-plan path).

Deep **once** on the primary pass — scan agents never run Exa packs. Use **Exa** (primary) + sport sites (Sofascore, FBref, HLTV, ATP/WTA, Flashscore, etc.). See **`docs/EXA_RESEARCH_USAGE.md`**.

For each primary-worklist line:

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
7. **Settlement Lessons** (≥1 terminal) — engine writes `outbox/SETTLEMENT_LESSONS.md` + `data/state/settlement_lessons.json`. **Agent: print/use before next research.** Missing/stale → **warn**, not hard-stop. Soft awareness only (TTL); no hard-reject list growth. See [Settlement Lessons + diversify + archive isolation](#settlement-lessons--diversify--archive-isolation-automatic-desk-law).

### Learning must not grow hard reject lists

| Allowed | Forbidden |
|---------|-----------|
| stake_mult / ev_boost clamps | Auto hard-reject config patches |
| process_gate **temp** raises | Re-enable anti_soft / FEH place-owning from settlement |
| Taxonomy + learning_weight | Block lists from single-loss anecdotes |
| Soft mult recompute · Settlement Lessons soft TTL | FEH-style permanent guilt lists |
| Live ledger peers only (`data/bets.csv`) | Seeding lessons/similar/diversify from `history/archives/` or `history/rounds/` |

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
| Research board first (Stage 1 scan **all** lines) | Jump straight to `recommend` with empty packs |
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
| Deep **primary worklist** once (multi-agent shortlist ∪ coverage_critical; else engine queue) | Deep-dive only 2–3 lines; ignore primary worklist; deep inside scan agents |
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
| After settle ≥1 terminal: **print Settlement Lessons** before research | Skip lessons silently; treat missing/stale as hard-stop |
| Hard max **2** `market_family`; note similar-recent + lessons soft demotion | Stack same coarse family; ignore diversify rejects |
| Memory = **live** `data/bets.csv` + pending + current odds/results only | Read or cite `history/archives/` / `history/rounds/` for peers |
| Keep FEH demoted; capital_v2/phase/secure/10 NOK untouched | Revive anti-soft / FEH place law from losses |

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
| `/daily-run` | Full day desk | settle → **Settlement Lessons** (warn if stale) → odds → Stage 1a board/light → **1b multi-agent A/B/C** → primary worklist → deep once → expand if needed → recommend (max 2 family / similar soft) → why/support/risk → `PLACE_THESE.md` → place-ack (10 NOK cap when active) |
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
| `docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md` | Multi-agent Stage 1b scan design (roles · merge · primary worklist) |
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
| `docs/SETTLEMENT_LEARNING.md` | Settle + learn loop · **Settlement Lessons v1** |
| `docs/DIVERSITY_AND_EXPLORE.md` | Virgin explore · max 2 `market_family` · similar-recent · archive isolation |
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
