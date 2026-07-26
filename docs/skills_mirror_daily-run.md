---
name: daily-run
description: >
  Full NT betting-desk daily run under Edge-Seeking Research (ESR) Stage 0–4:
  settle → Settlement Lessons (warn if missing/stale) → odds dump →
  market-scan → board+light → multi-agent Stage 1b scan (A favourites /
  B totals+props / C HC+matchup dogs, max 5 each) → merge shortlist 8–15 →
  primary worklist (shortlist ∪ coverage_critical, cap 15) → Exa both-sides
  deep packs ONCE on primary worklist → recommend best +EV (hard max 2
  market_family; similar-recent + lessons soft demotion; form_continuity
  soft-reject on weak flips; ranking-gap HC soft max 1; explore boost
  only if base_ev clear; opposite-side always in PLACE_THESE; soft dogs
  not guilty; short 1.40–1.80 OK) → expand if large board & <2 picks →
  Reasoning (why · support · main risk · opposite side · form continuity
  · EV split) → PLACE_THESE.md → place-ack (10 NOK TEST_CAP:esr_v1 when
  active). Live ledger only — never history/archives or history/rounds.
  Use when the user runs /daily-run,
  says "daily run", "run the day", "today's desk", "full research day",
  or drops a new inbox/odds file for a complete session. Accepts optional
  kick-off window and odds filename.
metadata:
  short-description: "Full day ESR Stage 0–4 — multi-agent scan + primary worklist"
---

# /daily-run — Full desk day (Edge-Seeking Research)

Real-money capital desk. **Engines in `nt/` are law.** Load project rules first; never invent `p_model` or soften min_EV by hand.

**ESR:** Find the best available edges. Soft underdogs are **not** guilty by default. Short favourites **1.40–1.80** are allowed when research supports them. Empty slip only after full scan + **expansion** + no honest +EV. FEH is **demoted / shadow only** — not place law.

**Automatic hardenings (every run):** Settlement Lessons after terminal settle · hard max **2** `market_family` · similar-recent + lessons soft demotion · **form continuity / anti-flip** (narrow `form_continuity:` soft-reject only) · ranking-gap HC soft max 1 · explore boost only if base_ev clear · opposite-side always in PLACE_THESE · **archive isolation** (never `history/archives/` or `history/rounds/`) · **multi-agent Stage 1b** after board/light. ControlSignals, capital_v2, phase, secure, 10 NOK cap **unchanged**. **No FEH / anti-soft place-law revival.** See root `AGENTS.md` § Portfolio diversify + form continuity · multi-agent Stage 1b.

**Exa** is the primary HQ search for every **primary-worklist** line (both sides). Exa feeds packs and reasoning — it does **not** hard-reject and does not re-arm FEH. See `docs/EXA_RESEARCH_USAGE.md`.

> **Repo mirror:** keep `~/.grok/skills/daily-run/SKILL.md` in sync with `docs/skills_mirror_daily-run.md`. Desk pointer: `docs/DESK_SKILLS.md`. Philosophy: `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`. Multi-agent scan: `docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md`. Diversify: `docs/DIVERSITY_AND_EXPLORE.md`. Form continuity: `docs/FORM_CONTINUITY_AND_ANTI_FLIP_HARDENING_2026-07-26.md`. Lessons: `docs/SETTLEMENT_LEARNING.md`.

## 0) Bootstrap (mandatory)

1. `Read` the repo root **`AGENTS.md`** — especially **Edge-Seeking Research (ESR)** Stage 0–4 and multi-agent Stage 1b.
2. Skim **`docs/DESK_SKILLS.md`** / **`docs/EXA_RESEARCH_USAGE.md`** / **`docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md`** if needed.
3. Confirm CWD is the **nt-betting-tracker** worktree root (`run_nt.py` present).
4. Force **real tools** — shell CLI, **Exa** + page open for deep research, file read/write. Do not simulate board/light/recommend output.
5. Identify odds file:
   - Path the user named, **or**
   - Path they asked to write (e.g. `inbox/odds_2026-07-25.txt`), **or**
   - **Newest** `inbox/odds*.txt` by mtime.

### Optional: kick-off window + dump

If the user specifies a timeframe (Europe/Oslo) and filename, collect/write the Oddsen dump to that path **first**, then continue.

```text
/daily-run Collect the current Oddsen board from Norsk Tipping for kick-offs between
14:00 and 23:00 Europe/Oslo.
Write the dump to inbox/odds_YYYY-MM-DD.txt,
then run the full ESR Stage 0–4 path.
```

## Research standards (automatic — do not skip)

### A) Edge-Seeking Research (Stage 0–4)

| Stage | Action |
|-------|--------|
| **0 Collect** | Odds file in `inbox/` |
| **1a Engine baseline** | market-scan → board → light → engine `deep_queue` SSOT |
| **1b Multi-agent scan** | Spawn A/B/C (max 5 each) → merge/dedupe/diversity → shortlist **8–15** |
| **1c Primary worklist** | shortlist ∪ coverage_critical · hard cap **15** |
| **2 Deep** | Exa both-sides **once** on **primary worklist only** → `evidence/*.json` + honest `p_model` |
| **3 Select** | ready → recommend best +EV (gates + grade + EV) |
| **3b Expand** | Large board & **&lt;2** picks → deep next 5–8 engine tier → re-recommend |
| **4 Output** | PLACE_THESE + why/support/risk → place-ack |

- Soft underdog HC: place when **matchup + EV** support — mixed H2H is not automatic reject.
- Short **1.40–1.80**: welcome with form/rank support (Grade B + core + EV).
- Prefer **finding honest edges** over empty-slip culture. Empty only after expansion + no +EV.

### B) Sport research (cards optional aid)

- Sport cards / SAEF may inform notes; they are **not** FEH place law.
- Individual sports: H2H still high-value research — record polarity honestly.
- New/thin sports: research carefully; do not invent edges.

### C) Exa search — every primary-worklist line

| Must | Detail |
|------|--------|
| Intent queries | Natural language |
| Both sides | Favourite **and** underdog (or home/away) |
| Targets | Form · H2H · ranking · natural markets · injuries/motivation |
| Pack proof | Sources/takeaways show HQ search |
| Coupling | Feeds pack + **why · support · main risk** — not hard FEH reject |

Fallback if Exa unavailable: HQ web search + sport sites; note fallback in pack.

### D) Empty slip law

- Empty after honest deep **and** expansion with no +EV = OK.
- Empty while primary worklist / next tier unresearched = **process miss**.
- Do **not** force weak EV seats to “use budget.”
- Do **not** reject everything imperfect (anti-soft ideology is off).

### E) 10 NOK test stake cap (when active)

- First **10 placed** bets tagged `TEST_CAP:esr_v1` → max **10 NOK** per seat.
- Absolute-last clip — **does not** change capital_v2 / unit / phase math.
- See `data/state/status.md` for test_cap progress.

### F) Reasoning (every pick + short near-miss)

```markdown
### N. {Selection} @ {odds} · Grade · EV · stake
- **Why:** …
- **Support:** …
- **Main risk:** …
- **Opposite side:** {one_liner or "not evaluated"}
- **Form continuity:** {form_continuity_reason or "none"}
- **EV split:** base_ev=… · explore_boost=… · placed_ev=…
- **Diversity:** {family} · sort_ev=… · penalties: {similar; lessons; form_continuity}
- **scan_agent:** A   # or A+C / B / … when multi-agent Stage 1b ran
```

**Opposite side is always required** in PLACE_THESE / reasoning (default text **`not evaluated`** if missing). Form continuity + EV split when engine annotates them.

**Provenance (when multi-agent Stage 1b ran):** each placed pick's why block **must** include `scan_agent: A` or `A+C` (union from shortlist). Source = `MULTI_AGENT_SHORTLIST.md` / merge `scan_agents`. Omit only if the line never appeared on the multi-agent shortlist (pure coverage_critical / Stage 3b expansion).

Near-misses: one short line each (why not / what would change) — include `form_continuity:` / ranking-gap soft-skip reasons when present.

### G) Settlement Lessons + diversify + form continuity + archive isolation + multi-agent (automatic)

| Rule | Detail |
|------|--------|
| **Settlement Lessons** | After settle with **≥1 terminal**: read + print `outbox/SETTLEMENT_LESSONS.md` / `data/state/settlement_lessons.json` **before** Stage 1 research. Missing or stale → **warn**, continue (not hard-stop). Soft awareness only (TTL); no permanent hard rejects. |
| **Hard max 2** `market_family` | Engine diversify on open+slip. Coarse family (line not in key). Expect family rejects on 3rd same family. |
| **similar-recent** | Soft `sort_ev` demotion + notes on live recent same sport/family/line — true EV honest. **Sort-only.** |
| **Lessons soft** | Independent portfolio demotion from Settlement Lessons soft_awareness. **Sort-only.** |
| **Form continuity / anti-flip** | After successful heavy-fav HC, opposite side within window (hours **AND** games) needs ≥2 strong signals; weak → soft-reject with prefix **`form_continuity:` only**. Visible in notes / PLACE_THESE. Do **not** hand-override without structural why_flip. |
| **Narrow soft-reject class** | **Only** `form_continuity:` weak flips. Not FEH, not anti_soft, not similar_recent hard_reject expansion. Similar/lessons remain sort-only. |
| **Ranking-gap HC soft cap** | Prefer ≤1 tagged ranking-gap HC per slip (EV-slack skip-then-fill; same-match non-HC preferred). Soft preference — force-accept when only RG remain. |
| **Explore boost gate** | Explore/virgin boost + explore floor only if **base_ev ≥ explore_base_ev_min**; show base vs boosted EV in reasoning. |
| **Opposite-side check** | Every deep candidate; PLACE_THESE always emits line (default “not evaluated”). Audit-only if pack missing check — not a reject. |
| **Archive isolation** | **FORBIDDEN** for memory/peers: `history/archives/`, `history/rounds/`, **and git stash/branch copies of `data/*`**. Use only live working-tree `data/bets.csv`, pending, latest results, current odds, `data/state/*`. |
| **Live desk SSOT** | Never `git checkout`/`restore`/`stash apply` onto `data/bets.csv` or `data/state/*` during engineering. Clean era: **era_start 2026-07-25**, baseline **500 NOK**. Verify with `python run_nt.py status` before research. |
| **Diversity triad** | (1) Engine `deep_queue` **not** family-demoted. (2) Multi-agent shortlist soft family **≤2** (work-order only; no rewrite of queue). (3) Portfolio hard max 2 family + sport at recommend. |
| **Stage 1 engine queue** | Do **not** hand-demote `deep_queue` by family/lessons/continuity — engine queue SSOT intact; diversify + form continuity bind at recommend. |
| **Stage 1b multi-agent** | After board/light; A/B/C scan only (max 5); parallel preferred / sequential A→B→C / ≤12 min; partial merge + engine top-up; all-fail → engine `deep_queue`; **never silent-skip Stage 2**. Merge → `MULTI_AGENT_SHORTLIST.md`; primary = shortlist ∪ coverage_critical (cap 15). Agents A/C: surface `form_continuity_risk:` when scan shows recent Win on opposite heavy fav for same teams (soft only). |
| **Untouched** | **No FEH/anti-soft revival** · capital_v2/phase/secure/unit/10 NOK · ControlSignals contracts. |

## 1) Results first (if any open risk)

```powershell
python run_nt.py status
python run_nt.py settle --draft
# After outcomes known:
# python run_nt.py settle --results inbox/results.yaml
python run_nt.py control-signals list --json
python run_nt.py refresh
```

- Fill **PostSettlementPacket** on process_error / poor retro.
- Classify **predictability + variance_class + learning_weight** (`/learning-rootcause` if batch).
- Learning proposals auto-apply when configured — do not ask user to accept.
- **Do not** propose new hard-reject lists from losses.
- **If ≥1 terminal settled this batch:** print Settlement Lessons (`outbox/SETTLEMENT_LESSONS.md` + soft notes from `data/state/settlement_lessons.json`) **before** market-scan/board. Missing/stale → warn and continue.

## 2) Stage 1a — Market coverage + board + light

```powershell
python run_nt.py research market-scan --odds <odds_file>
python run_nt.py research board --odds <odds_file>
python run_nt.py research light --odds <odds_file>
python run_nt.py research light --odds <odds_file> --merge-deep   # after packs
```

| Artifact | Path |
|----------|------|
| Board report | `outbox/research_board*.md` |
| Light batch | `outbox/light_research/` |
| Deep queue SSOT | `data/state/deep_queue.json` |
| Coverage Health | `data/state/coverage_health.json` |
| Status | `data/state/status.md` · `data/state/risk.json` |

Check: Light coverage % · deep queue size · Coverage Health · test_cap · ControlSignals.  
Engine queue rank = research **hint** / coverage SSOT — **not** automatic place pass. Do **not** rewrite `deep_queue.json` from multi-agent merge.

## 2b) Stage 1b — Multi-agent scan (default on full daily-run)

**After** board/light and Settlement Lessons (if any). **Before** Stage 2 Exa deep.

**Skip only when:** recommend-only on already-researched packs; odds parse fail / empty dump (warn, no spawn).

### Spawn three scan agents (parallel preferred; sequential A→B→C if parallel unavailable)

| Agent | Focus | Odds / markets | Max | Hard bans |
|-------|--------|----------------|-----|-----------|
| **A** | Favourites & lower odds | **1.40–1.90** inclusive (prefer 1.40–1.80 when strong); ML / clear fav side | **5** | No Exa pack · no write-pack · no recommend · no ledger |
| **B** | Totals & player props | Any reasonable; natural totals/props story | **5** | Same · **self-limit ≤2** same `market_family` |
| **C** | HC & matchup dogs | Open; dogs/HC with **real reason** (form/rank/H2H/style/injury/rest/motivation) | **5** | Same · not “long odds = value” |

**Shared scan contract:**

- Purpose: **fast scanning only** — surface promising lines for deep later.
- Legal universe: **full current odds dump** — board/light/deep_queue are hints only.
- Depth: one-sentence form/rank/matchup — **no** `p_model`, no pack, no FEH place language.
- Forbidden inputs: `history/archives/`, `history/rounds/`, git stash ledger copies.
- Output (recommended): `outbox/scan_agent_{a,b,c}_YYYY-MM-DD.jsonl` (or `.md`).

**Main agent loads (read-only hints):** odds dump · board MD · light · `data/state/deep_queue.json` · open family/sport occupancy from live `status` (Pending+ConfirmedPlaced only).

### Merge algorithm (main agent)

```text
1. Normalize: evidence_pair_key(match, selection); attach scan_agents, odds, reason, sport, market_family
2. Drop invalid: off odds dump; empty reason; Agent A odds outside [1.40, 1.90]
3. Dedupe by key; union scan_agents → render scan_agent: A+C
4. Family rule: each market_family MUST be ≤2 after merge (drop at ≥3)
5. Open occupancy soft: deprioritize open_family_full / open_sport_full (live ledger only)
6. Soft sport: prefer ≤3 per sport on multi-sport boards when size allows
7. Light-eligibility (KD16) for multi-agent-only lines (not in engine deep_queue):
     light pass OR never lighted → eligible
     hard light-fail → DROP unless reason contains "force_scan:" and main keeps with note
     (default DROP — no expensive Exa on light-fail noise)
8. Size clamp: multi-agent shortlist 8–15 (board-limited may be <8;
     if <8 and engine has unused light-pass not open-full → top up by promo)
9. Build primary_worklist = shortlist ∪ coverage_critical (cap 15)
10. Write outbox/MULTI_AGENT_SHORTLIST.md including ## Primary worklist + ## Dropped
```

**coverage_critical** = engine deep_queue lines with tags `coverage_floor:top_promo_scaffold` OR `coverage_floor:sport_rotation` (Mechanism A — never silently drop).

### Failure / timeout / fallback (KD17 · KD12) — never silent-skip Stage 2

| Case | Behaviour |
|------|-----------|
| **Parallel preferred** | Spawn A/B/C together when the host supports parallel subagents. |
| **Parallel spawn unavailable** | Run **sequential A → B → C** (same role cards); still apply full merge. |
| **Wait budget** | Wait ≤ **12 minutes** wall-clock for the scan layer (host-dependent skill default). Do **not** wait forever for a hung agent. |
| **Partial fail / timeout (≥1 complete)** | Merge **what completed**; note `scan_agent_missing: X[,Y]`; **engine top-up** from light-pass / coverage_critical / promo so shortlist band stays useful (target 8–15 when board allows). `scan-merge` helper already supports partial agent sets. |
| **Proceed after 2/3** | Allowed once timeout fires or one agent hard-fails — do not block the desk on the third. |
| **All-fail / empty scan merge** | `primary_worklist = engine deep_queue` (pre-plan path). Empty multi-agent shortlist → **engine fallback** (`scan-merge` `fallback: engine_deep_queue` / ISS-2). Warn **process miss on multi-agent layer** — still continue. |
| **Never silent-skip Stage 2** | After Stage 1b (success, partial, or all-fail fallback), **always** deep the resulting primary worklist. Multi-agent spawn failure is **not** a hard-stop and is **not** a license to jump to empty recommend without deep. |
| **Agent returns &gt;5** | Truncate to 5 before merge. |
| **Lines not on odds dump** | Drop at merge. |

**Do not:** rewrite `deep_queue.json` · run deep inside A/B/C · revive FEH/anti-soft · touch capital · treat spawn failure as “skip research day.”

## 3) Stage 2 — Deep research on PRIMARY WORKLIST (Exa)

**When multi-agent shortlist exists (full or partial merge):** deep **every line on PRIMARY WORKLIST** from `outbox/MULTI_AGENT_SHORTLIST.md`.  
**Do not** “work engine deep_queue first” as the default primary pass when a multi-agent shortlist was produced.  
**Do not** deep random odds lines outside primary worklist + Stage 3b expansion.  
**Do not** hand-prune `deep_queue.json`.

**When multi-agent failed entirely / empty merge → engine fallback:** primary worklist = engine `deep_queue` (pre-plan path). **Still run Stage 2 deep once** on that worklist — never skip deep because scan agents failed.

1. Scaffold if needed:

```powershell
python run_nt.py research board --odds <odds_file> --write-scaffolds
python run_nt.py research scaffold --match "…" --selection "…" --sport darts --write
```

2. **Exa deep-research each primary-worklist line once** — both sides, form · H2H · rank · natural markets.  
3. Write packs with honest `p_model`:

```powershell
python run_nt.py research write-pack --match "…" --selection "…" --p-model 0.XX `
  --sport darts --odds-ref 1.95 --summary "…" --failure-modes "…" `
  --availability-status predicted --context-risk low `
  --script-lean competitive --selection-vs-script agree
python run_nt.py research critique evidence/<file>.json --odds 1.95
```

**Pack minimum (not F):** `p_model` · `summary` · `failure_modes` · real sources (≈4+).  
**Hard rejects only:** script/base-rate conflict · missing availability on sensitive markets · missing `p_model` · empty takeaways.  
**Never invent `p_model`.** Soft dog without edge → skip that line, not the whole philosophy.

## 4) Stage 3 — Ready + recommend (+ expand)

```powershell
python run_nt.py research ready --odds <odds_file>
python run_nt.py recommend --odds <odds_file>
# Coverage critical + explicit override only:
# python run_nt.py recommend --odds <odds_file> --allow-low-coverage
# dry-run ONLY if user asks
```

- Target **2–6** picks on large boards when honest EV exists.  
- If large board and **&lt;2** picks: deep next **5–8** light-pass by promo / `next_tier_keys` (engine expansion tier — **not** a second multi-agent pass) → **re-recommend**.  
- Present slip with **why · support · main risk · opposite side · form continuity · EV split**.  
- When test cap active, expect ≤ **10 NOK** and `TEST_CAP:…` in notes.  
- Do not re-advise already open tickets.  
- Expect **max 2** open+slip per coarse `market_family`; surface similar-recent / `lessons_soft` demotions in near-misses when present.  
- Expect **`form_continuity:`** near-misses on weak opposite-side flips after heavy-fav wins — do **not** hand-override without structural why_flip (≥2 strong signals).  
- Expect ranking-gap soft-skips (`ranking_gap_hc:…`) when other markets compete; explore boost withheld when base_ev thin.

## 5) Stage 4 — Place session

```powershell
python run_nt.py place-ack --ids <bet_id>[,<bet_id>...]
python run_nt.py abandon --ids <bet_id> --reason missed_prematch
python run_nt.py status
```

## Exhaustive CLI map

| Stage | Command |
|-------|---------|
| Status | `python run_nt.py status` · `refresh` · `validate` |
| Capital | `capital status` · `capital segments` |
| Settle | `settle --draft` · `settle --results …` |
| Learning | `learn` · `control-signals list` |
| Research | `research market-scan` · `board` · `light` · `ready` · `scaffold` · `write-pack` · `critique` |
| Decision | `recommend` · `place-ack` · `abandon` |
| Sims | `simulate --sport tennis\|football\|basketball …` (suggest only) |

## Deliverables (list paths in final reply)

1. Odds file: `inbox/…`
2. Settlement Lessons (if settled ≥1 terminal): `outbox/SETTLEMENT_LESSONS.md` · `data/state/settlement_lessons.json`
3. Light: `outbox/light_research/…`
4. Deep queue SSOT: `data/state/deep_queue.json` (unrewritten)
5. **Multi-agent shortlist:** **`outbox/MULTI_AGENT_SHORTLIST.md`** (+ optional `outbox/scan_agent_{a,b,c}_*.jsonl`)
6. Evidence packs: `evidence/*.json`
7. Coverage Health: `data/state/coverage_health.json`
8. Slip: **`outbox/PLACE_THESE.md`**
9. Status: `data/state/status.md` · `risk.json`
10. Reasoning: why · support · main risk · opposite side · form continuity · EV split (+ near-misses; family/similar/lessons/form_continuity notes)
11. Expansion done? (if large board &lt;2 initially)
12. place-ack / abandon ids if place session ran

## Ops smoke + live dry desk day (PR4 checklist)

**Engine smoke (no live ledger writes required):**

```powershell
.\scripts\skill_smoke.ps1
# skills installed · coverage floor synthetic · MC phase · taxonomy weights
```

**Multi-agent scan-merge smoke (optional; docs/ops):**

| Check | Pass |
|-------|------|
| Simulated one-agent-missing merge | Shortlist still written; notes include missing agent; engine top-up if needed |
| Simulated all-fail / empty agent sets | `fallback: engine_deep_queue` · primary worklist from queue · Stage 2 still scheduled |
| Family ≤2 after merge | No `market_family` with ≥3 seats on shortlist |

**Live dry desk day (ops — real odds, no invent p_model; dry-run recommend only if operator asks):**

| Gate | Target |
|------|--------|
| Multi-agent shortlist size | **8–15** on large boards (board-limited may be &lt;8) |
| Primary worklist | shortlist ∪ coverage_critical · **≤15** |
| Stage 2 deep | **Once** on primary worklist only (no deep inside A/B/C) |
| Provenance | Placed / slip picks show `scan_agent: A` or `A+C` when line was on multi-agent shortlist |
| Fallback path exercised? | If any agent missing: still deep; if all-fail: engine path + still deep |
| Deliverables | `outbox/MULTI_AGENT_SHORTLIST.md` · packs · `PLACE_THESE.md` with why/support/risk |

Design residual: `docs/RESIDUAL_RISKS.md` · **R-S2-10** multi-agent spawn reliability.

## Hard rules (do not break)

- Load AGENTS.md first every session.
- Live recommend by default; dry-run only on request.
- After board/light: run **multi-agent Stage 1b** (A/B/C max 5) unless recommend-only / empty dump.
- Stage 1b spawn: **parallel preferred**; **sequential A→B→C** if needed; wait ≤**12 min**; partial → merge + engine top-up; all-fail → engine `deep_queue` path. **Never silent-skip Stage 2 deep.**
- Deep **primary worklist once** (shortlist ∪ coverage_critical, or engine queue on all-fail); do **not** “work engine deep_queue first” as primary when shortlist exists; expand before accepting empty on large boards.
- Scan agents: **scan only** — no Exa packs, no place, no ledger.
- Diversity triad: no engine-queue family demote · shortlist family ≤2 soft · portfolio hard max 2 at place.
- **ESR** — soft dogs not guilty by default; short 1.40–1.80 OK with support.
- **Exa (or HQ fallback)** on every primary-worklist line — both sides.
- FEH is **not** place law (shadow only). **Do not** revive anti-soft from losses.
- Empty slip only after expansion + no +EV.
- Coverage Health **critical** → soft-gate unless explicit `--allow-low-coverage`.
- Engines own bankroll/phase/risk; UI never invents stakes.
- **Do not change** capital_v2, phase ladder, secure bucket, unit sizing (10 NOK is post-size clip only). ControlSignals contracts unchanged.
- After place session: place-ack new Pending unless user says missed → abandon.
- Learning: no permanent hard-reject list growth.
- After settle ≥1 terminal: **print Settlement Lessons** before research; missing/stale = warn only.
- Hard max **2** `market_family`; respect similar-recent + lessons soft demotion (**sort only**).
- **One** narrow process soft-reject class allowed: **`form_continuity:`** weak flips only — never FEH/anti_soft codes; never expand similar_recent hard_reject.
- Ranking-gap HC soft max **1** per slip (EV-slack); explore boost only if **base_ev** clear; PLACE_THESE always emits **Opposite side**.
- **FORBIDDEN memory:** `history/archives/`, `history/rounds/`, git stash/branch `data/*` — live working-tree `data/bets.csv` + pending + current odds/results only.
- **Never overwrite live desk SSOT** via git during `/execute-plan` or branch work. Clean era = **2026-07-25 / 500 NOK**.
