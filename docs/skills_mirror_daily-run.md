---
name: daily-run
description: >
  Full NT betting-desk daily run under Edge-Seeking Research (ESR) Stage 0–4:
  settle → odds dump → market-scan → board+light (1a) → adaptive multi-agent
  scan A/B/C(+D) → merge shortlist 8–15 → primary worklist ≤15 →
  /deep-research once → Dual Decision ARGUE (advisory) → engine recommend
  (sole place set; soft dogs not guilty by default; short 1.40–1.80 OK) →
  annotate PLACE_THESE from engine picks → expand once if large board & <2 picks
  (re-argue → re-recommend → re-annotate) → place-ack
  (10 NOK TEST_CAP:esr_v1 when active). Use when the user runs /daily-run,
  says "daily run", "run the day", "today's desk", "full research day",
  or drops a new inbox/odds file for a complete session.
  Accepts optional kick-off window and odds filename.
metadata:
  short-description: "Full day ESR Stage 0–4 — adaptive 1b + Dual Decision advisory Stage 3"
---

# /daily-run — Full desk day (Edge-Seeking Research)

Real-money capital desk. **Engines in `nt/` are law.** Load project rules first; never invent `p_model` or soften min_EV by hand.

**ESR:** Find the best available edges. Soft underdogs are **not** guilty by default. Short favourites **1.40–1.80** are allowed when research supports them. Empty slip only after full scan + **expansion** + no honest +EV. FEH is **demoted / shadow only** — not place law.

**Exa** is the primary HQ search for every deep-queue / primary-worklist line (both sides). Exa feeds packs and reasoning — it does **not** hard-reject and does not re-arm FEH. See `docs/EXA_RESEARCH_USAGE.md`.

> **Repo mirror:** keep `~/.grok/skills/daily-run/SKILL.md` in sync with `docs/skills_mirror_daily-run.md`. Desk pointer: `docs/DESK_SKILLS.md`. Philosophy: `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`. Adaptive design: `docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md`.

## 0) Bootstrap (mandatory)

1. `Read` the repo root **`AGENTS.md`** — especially **Edge-Seeking Research (ESR)** Stage 0–4 + **Stage 1b multi-agent**.
2. Skim **`docs/DESK_SKILLS.md`** / **`docs/EXA_RESEARCH_USAGE.md`** if needed.
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
| **1a Engine baseline** | market-scan → board → light → `data/state/deep_queue.json` SSOT |
| **1b Adaptive multi-agent scan** | A∥B∥C always (+ **D** when any match has ≥41 Candidate lines) → merge → shortlist **8–15** |
| **1c Primary worklist** | shortlist ∪ `coverage_critical` · cap **15** |
| **2 Deep** | `/deep-research` **once** on primary worklist only (not full board) |
| **3.1 Dual Decision ARGUE** | Edge Maximiser ∥ Portfolio Guardian — **advisory artifacts only** (≤8 min; no new Exa) |
| **3.2 Engine recommend** | `research ready` → `recommend` — **sole place set + stakes** |
| **3.3 Annotate** | PLACE_THESE from **engine picks** + dual-decision cards (`decision:` / `dual_decision:` tags **post-engine only**) |
| **3.4 Expand (optional once)** | Large board & **&lt;2** picks → deep next 5–8 → re-run **3.1–3.3 once** |
| **4 Output** | PLACE_THESE + why/support/risk → place-ack |

- Soft underdog HC: place when **matchup + EV** support — mixed H2H is not automatic reject.
- Short **1.40–1.80**: welcome with form/rank support (Grade B + core + EV).
- Prefer **finding honest edges** over empty-slip culture. Empty only after expansion + no +EV.
- **KD-DD-wire:** Dual Decision is **non-binding advisory ranking only**. Place set comes **exclusively** from engine `recommend` / `build_portfolio`. Never hand-remove engine picks because Guardian challenged them.

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
- Empty while next tier unresearched / queue ignored = **process miss**.
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
- **scan_agent:** A|B|C|D|…   # when multi-agent shortlist used
- **decision:** both | edge_only | guardian_only | edge_over_guardian | engine_only
- **dual_decision:** maximiser_rank=#k · guardian_rank=#j · note: …
```

Near-misses: one short line each (why not / what would change). Write `decision:` / `dual_decision:` **only after** engine recommend (KD-prov).

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

## 2) Stage 1a — Market coverage + board + light (engine baseline)

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

**Engine `deep_queue.json` is SSOT for light baseline and top-up.** Multi-agent merge **never rewrites** it. When a multi-agent shortlist exists, **Stage 2 works the primary worklist** (shortlist ∪ coverage_critical), not deep_queue-first alone.

Queue rank = research priority signal, not automatic place pass.

---

## 3) Stage 1b — Adaptive multi-agent scan (A / B / C / +D)

Shallow scan agents only. **Hard bans (all scan agents):** no Exa pack · no `write_deep_research_pack` · no recommend · no ledger write · no invent `p_model` · no `history/archives/` or `history/rounds/`.

**Parallelism:** Prefer **A ∥ B ∥ C (∥ D)**. Sequential fallback: **A → B → C → (D if armed)**. Wait budget: **≤12 minutes** for the **entire** scan layer including D.

### Spawn matrix

| Agent | Role | Focus markets | Odds band | Max | Spawn |
|-------|------|---------------|-----------|-----|--------|
| **A** | Favourites & HUB | **HUB / 1X2 Match Result** (esp. football), clear fav ML/side | **1.40–1.90** incl. | **5** | Always |
| **B** | Totals & Props | Team totals, player props, cards, corners, specials, natural O/U | Open | **5** | Always |
| **C** | Handicaps & Matchup | HC + matchup dogs with real reason | Open | **5** | Always |
| **D** | Deep Props & Specials | Long-tail only (T2–T4 style) | Prefer non-main | **5** | **Conditional** |

### Agent D spawn predicate

```text
lines_count(M) = |{ Candidate rows from parse_odds_file with match == M }|
SPAWN_D := exists M such that lines_count(M) >= 41   # n=40 → false; n=41 → true
```

- **Never** reuse market-scan `high_volume` bool for spawn_d.
- **Must run `research scan-depth` when available** (CLI lands PR3). **Until then: manual line-count is OK** — group parseable Candidate / priced selections per match from the dump (or count selections per match). Log in shortlist header: `agent_d: spawned | skipped (max_lines_per_match=N, min_lines=41)`.
- **Sequential D budget (KD-scan-seq):** if sequential and wall-clock after A+B+C is **≥10 minutes**, **skip D** even if spawn true; note `scan_agent_missing: D (budget)`. Do not extend the 12 min law.

### Agent A — Favourites & HUB (strengthened)

**Purpose:** Surface short-to-mid favourite edges with **mandatory active search** of football (and other 3-way) **HUB/1X2 Match Result**, in a way that can **reach Stage 2**.

**Must:**

1. Scan every football (and other HUB) match for **1X2 / HUB** selections in **[1.40, 1.90]**.
2. Prefer **main Match Result** over diverting a clear 1X2 edge into handicap solely because HC is “more interesting.”
3. If a clear favourite 1X2 edge exists (form/rank/H2H one-liner supports fav or draw), include it among the ≤5 — **MUST NOT ignore clear 1X2 for HC**.
4. Still allow non-football short ML/Vinner in band when stronger than football HUB.
5. **Light / short_chalk interaction:**
   - Prefer odds **≥ 1.70** (`short_chalk_odds`) when structural support is thin (default A seats).
   - Allow **1.40–1.69** only with an **explicit structural one-liner** (form/rank/H2H/table) **and** prefix reason with `force_scan:` when the edge is real enough to justify Stage 2 cost despite light fail risk.
   - Prefer mid-band **1.70–1.90** football HUB over 1.40–1.55 chalk that will be process-theater (scanned then KD16-dropped).
6. Soft `form_continuity_risk:` when live ledger shows recent heavy-fav Win on opposite side (scan note only).

**Must not:**

- Fill all five seats with 1.40–1.55 chalk ML that light will drop without `force_scan:`.
- Treat “longshot ML” as A territory.
- Skip HUB entirely on a football-heavy board to fill seats with non-football chalk.

**Self-check:** odds ∈ [1.40, 1.90]; ≥1 football HUB/1X2 when such lines in band exist; clear 1X2 not replaced by HC without one-line justification; if odds &lt; 1.70: structural why + `force_scan:` when intending Stage 2; non-empty reason.

**Output:** `outbox/scan_agent_a_YYYY-MM-DD.jsonl` (max 5 rows). Example fields: `match`, `selection`, `odds`, `sport`, `market_family`, `market_type`, `reason`, `scan_agent: "A"`, optional `form_continuity_risk`.

```text
You are ESR Scan Agent A — Favourites & HUB (max 5).
Odds band 1.40–1.90. Prefer ≥1.70 (short_chalk_odds) so seats survive light/KD16.
MUST search football HUB/1X2. MUST NOT ignore clear 1X2 for HC.
If 1.40–1.69: structural one-liner + force_scan: when Stage 2 intended.
No p_model, packs, Exa, place. Output: outbox/scan_agent_a_YYYY-MM-DD.jsonl
```

### Agent B — Totals & Props (strengthened)

**Must actively consider (when present on dump):** match totals / maps / runs; **team totals**; **player props**; **cards**; **corners**; other specials with a one-sentence natural story.

**Self-limit:** ≤**2** same coarse `market_family` in B’s own five.

**Coordination with D (when `spawn_agent_d=true`):**

| Rule | Detail |
|------|--------|
| B hard self-bias | Prefer **main natural totals + team totals**; at most **1** pure long-tail prop/card/corner seat |
| D owns | Deep props, cards, corners, shots, specials on high-volume matches |
| Merge (when D-armed) | If B and D collide on the **same long-tail family key**, **prefer D’s row** (soft priority; still subject to family ≤2). Note `b_yielded_longtail_to_d` when relevant |

When D is **not** spawned, B must cover props itself (full strengthened mandate).

```text
You are ESR Scan Agent B — Totals & Props (max 5).
Team totals, player props, cards, corners, specials, natural totals.
Self-limit ≤2 same market_family.
If spawn_agent_d=true: bias main totals; at most 1 long-tail seat (D owns deep props).
No p_model, packs, Exa, place. Output: outbox/scan_agent_b_YYYY-MM-DD.jsonl
```

### Agent C — Handicaps & Matchup

HC + matchup dogs with **real reasons**; `force_scan:` only for real matchup vs light-fail risk; soft `form_continuity_risk:`; not “long odds = value.” Do not steal clear HUB 1X2 edges that belong in A without a distinct HC thesis. Max **5**.

```text
You are ESR Scan Agent C — Handicaps & Matchup (max 5).
Real matchup reasons only. force_scan: only when justified.
No p_model, packs, Exa, place. Output: outbox/scan_agent_c_YYYY-MM-DD.jsonl
```

### Agent D — Deep Props & Specials (conditional)

| Rule | Detail |
|------|--------|
| Focus | Long-tail **only**: player props, cards, corners, shots, specials, exotic team stats |
| Avoid | Pure HUB/1X2, main ML, main HC, primary O2.5 |
| Prefer | High-volume matches (≥3 of 5 bias — soft, not merge-hard in v1) |
| Max | **5** |
| Depth | Same shallow scan contract as A/B/C |
| Hints | `outbox/market_scans/*` interesting/review when present |
| Self-limit | ≤2 same `market_family` |
| Role-drift | Soft annotate only if ≥3/5 kept rows are main-board — **never hard-drop** D for role drift in v1 |

```text
You are ESR Scan Agent D — Deep Props & Specials (max 5).
Spawned only because a match has ≥41 parseable lines. Long-tail ONLY (props/cards/corners/shots/specials).
Bias to high-volume matches. Avoid pure HUB/main HC/main O2.5.
No p_model, packs, Exa, place. Output: outbox/scan_agent_d_YYYY-MM-DD.jsonl
```

### Merge (A+B+C + D when active)

**Use `research scan-merge` when present** (PR0). Manual merge is allowed if CLI missing — same rules.

```powershell
python run_nt.py research scan-merge --odds <odds_file> `
  --agent-a outbox/scan_agent_a_YYYY-MM-DD.jsonl `
  --agent-b outbox/scan_agent_b_YYYY-MM-DD.jsonl `
  --agent-c outbox/scan_agent_c_YYYY-MM-DD.jsonl
# or: --agents-dir outbox
# After PR3 (scan-depth + D merge): add --agent-d when D ran
# Until PR3: if D ran, fold D rows into merge carefully by hand (family ≤2; prefer D on long-tail collision)
```

| Rule | Detail |
|------|--------|
| Per agent | Truncate each to **5** |
| Agent A band | Drop A rows outside odds **[1.40, 1.90]** |
| Invalid | Off odds dump · empty reason → drop |
| Dedupe | By evidence_pair_key; union `scan_agents` (e.g. A+C, B+D) |
| Family | Each `market_family` ≤**2** after merge |
| Sport soft | Prefer ≤**3** per sport on multi-sport boards |
| Light KD16 | Multi-agent-only **hard light-fail → DROP** unless reason contains `force_scan:` (main may keep with note) |
| Size | Clamp shortlist **8–15**; engine top-up from `deep_queue` if &lt;8 |
| Coverage | `primary_worklist` = shortlist ∪ coverage_critical · cap **15** |
| Continuity | `form_continuity_risk` / anti-flip notes from agents = **annotation only** after merge — no new hard-drop class; form-continuity engine math unchanged |
| Engine SSOT | **Never rewrite** `data/state/deep_queue.json` from multi-agent merge |
| Artifact | `outbox/MULTI_AGENT_SHORTLIST.md` (+ optional JSON); provenance `scan_agent:` |

**Failure / timeout:**

| Case | Behaviour |
|------|-----------|
| D not spawned | A/B/C path only |
| D armed but fails / timeout / budget skip | Merge A+B+C; `scan_agent_missing: D`; still Stage 2 |
| Partial A/B/C | Partial merge + engine top-up |
| All fail | `fallback: engine_deep_queue`; still Stage 2 — **never silent-skip Stage 2** |
| Wait budget | Single **12 min** for entire scan layer |

### Stage 1c — Primary worklist

```text
primary_worklist = multi_agent_shortlist ∪ coverage_critical
cap = 15
```

- Prefer rows from `outbox/MULTI_AGENT_SHORTLIST.md` → `## Primary worklist` when present.
- **When multi-agent shortlist exists, it drives Stage 2** (not bare deep_queue-first).
- Engine `deep_queue` remains light baseline SSOT and supplies top-up / all-fail fallback / coverage_critical candidates.
- Full-board deep remains **refused**.

---

## 4) Stage 2 — Deep research on primary worklist only

1. Invoke **`/deep-research` once** on the **primary worklist ≤15** (see `~/.grok/skills/deep-research/SKILL.md`).  
2. **Refuse** full-board / dump-wide deep.  
3. Scaffold only if needed for a worklist line:

```powershell
python run_nt.py research board --odds <odds_file> --write-scaffolds
python run_nt.py research scaffold --match "…" --selection "…" --sport darts --write
```

4. Packs: **atomic** `python scripts/write_deep_research_pack.py` (never bare `research write-pack` as final step). Honest `p_model`, both sides, form · H2H · rank · natural markets.  
5. Form-continuity / opposite-side / anti-flip fields: follow deep-research skill + engine soft rules — do not invent weak-phrase flips.

**Pack minimum (not F):** `p_model` · `summary` · `failure_modes` · real sources (≈4+).  
**Hard rejects only:** script/base-rate conflict · missing availability on sensitive markets · missing `p_model` · empty takeaways.  
**Never invent `p_model`.** Soft dog without edge → skip that line, not the whole philosophy.

Optional critique:

```powershell
python run_nt.py research critique evidence/<file>.json --odds 1.95
```

## 5) Stage 3 — Dual Decision ARGUE → engine recommend → annotate (+ expand once)

### KD-DD-wire (normative — do not violate)

> Dual Decision artifacts are **non-binding advisory ranking only**.  
> **PLACE_THESE content and stakes come exclusively from engine `recommend` / `build_portfolio`.**  
> The judge **never** publishes a preferred 2–6 as a place list.  
> **Never** hand-remove engine picks because Guardian challenged them.

| Conflict | Rule |
|----------|------|
| Engine **drops** a dual-decision want | Near-miss with **engine reject reason**; do not hand-force place |
| Engine **includes** a dual-decision **drop** | **Still place** the engine pick; annotate `decision: engine_only` or `edge_over_guardian` — **do not hand-remove** |
| Dual agents agree on X, engine picks Y | Place **Y**; narrative explains disagreement |
| No dual artifacts (skip path) | PLACE_THESE as today; omit dual tags |

**Order law:**

```text
deep packs ready
  → 3.1 Dual Decision ARGUE (advisory artifacts only)
  → 3.2 engine recommend (SOLE place set)
  → 3.3 annotate PLACE_THESE from engine picks + dual cards
  → (optional once) 3.4 expansion deep → re-run 3.1–3.3 once
```

### Skip rules (KD-dd-skip)

| Session type | Dual Decision |
|--------------|---------------|
| Full `/daily-run` | Run **3.1–3.3** |
| Recommend-only / already-researched packs only | **Skip 3.1** (same spirit as Stage 1b skip) |
| Empty deep-ready set | **Skip argue**; still run recommend path (may empty) |
| Skill kill-switch | Comment out Stage 3.1 in this skill + mirror (no YAML flag) |

### Stage 3.1 — Dual Decision ARGUE (before recommend)

**Speed law:** ≤ **8 minutes** wall-clock. Prefer Edge Maximiser **∥** Portfolio Guardian.  
**Inputs only:** deep packs + shortlist reasons + open occupancy + Settlement Lessons soft notes.  
**Hard bans:** no new Exa · no new packs · no invent `p_model` · no soften min_EV · **no place** · no ledger write · no re-open full board.

#### Decision Agent 1 — Edge Maximiser

**Mission:** Rank **3–6 wants** by honest +EV from deep-ready cards. Advisory only.

```text
Advisory only. Packs exist. No new research. Rank 3–6 wants by honest +EV.
You do NOT place bets. Output: outbox/decision_agent_edge_YYYY-MM-DD.md
```

**Output:** `outbox/decision_agent_edge_YYYY-MM-DD.md` — ranked wants + one-line why each. **Does NOT place.**

#### Decision Agent 2 — Portfolio Guardian

**Mission:** Balanced argument + challenges. Advisory only.

```text
Advisory only. Challenge family concentration, max_per_match stacks, sport pile-ups;
also ranking-gap HC / form_continuity when engine notes present — do not invent engine soft-rejects.
You do NOT place bets. Output: outbox/decision_agent_guardian_YYYY-MM-DD.md
```

**Challenge keys (branch-aware):**

| Priority | Challenge using | When |
|----------|-----------------|------|
| **P0 live always** | `max_per_market` / market_family concentration, **max_per_match**, sport caps, correlation / same-match stacks | Always |
| **P1 when present** | `form_continuity:` soft-reject notes, ranking-gap HC soft cap signals | Only if engine/portfolio or pack notes emit them |
| Soft | lessons_soft pile-ons; explore-boost-only thin base_ev | When notes available |

**Output:** `outbox/decision_agent_guardian_YYYY-MM-DD.md` — ranked wants + challenges. **Does NOT place.**

#### Draft reconciliation (pre-engine)

Write draft `outbox/DUAL_DECISION_YYYY-MM-DD.md` with **wants / challenges only** — **not** a place list. Golden shape: `docs/templates/DUAL_DECISION_TEMPLATE.md`.

### Stage 3.2 — Engine recommend (SOLE place set)

```powershell
python run_nt.py research ready --odds <odds_file>
python run_nt.py recommend --odds <odds_file>
# Coverage critical + explicit override only:
# python run_nt.py recommend --odds <odds_file> --allow-low-coverage
# dry-run ONLY if user asks
```

- Engine output = **sole** picked set + stakes + rejects.  
- Target **2–6** picks on large boards when honest EV exists.  
- When test cap active, expect ≤ **10 NOK** and `TEST_CAP:…` in notes.  
- Do not re-advise already open tickets.  
- **No** `--prefer-keys` / dual-decision pin in v1 — recommend API unchanged.

### Stage 3.3 — Annotate PLACE_THESE (post-engine only)

Main agent is **annotator**, not a second place list:

1. For each **engine-picked** row:
   - On both E1 and E2 top lists → `decision: both`
   - Only E1 → `decision: edge_only` (or `edge_over_guardian` if E2 challenged)
   - Only E2 → `decision: guardian_only`
   - On neither → `decision: engine_only`
2. For each E1/E2 want **not** picked → near-miss with **engine reject reason** (not dual veto).
3. **Never** hand-remove an engine pick because Guardian challenged it.
4. **Never** hand-add a dual want the engine did not pick.
5. Finalize PLACE_THESE reasoning + `outbox/DUAL_DECISION_YYYY-MM-DD.md` **reconciliation** section (post-engine match table).
6. Provenance: `scan_agent:` when multi-agent shortlist was used; `decision:` / `dual_decision:` **only after** recommend.

```markdown
### N. {Selection} @ {odds} · Grade · EV · stake
- **Why:** …
- **Support:** …
- **Main risk:** …
- **Opposite side:** …
- **Form continuity:** …
- **EV split:** …
- **Diversity:** …
- **scan_agent:** A+D
- **decision:** both | edge_only | guardian_only | edge_over_guardian | engine_only
- **dual_decision:** maximiser_rank=#k · guardian_rank=#j · note: …
```

**Integrity (KD-prov):** Any claim of `both` requires the pick on **both** agent want lists **and** in engine picks. No pre-recommend `decision:` tags.

### Stage 3.4 — Expansion (optional, once)

If board is large (≥15 matches or ≥80 lines) **and** recommend yields **&lt; 2** picks after full deep of primary worklist:

1. Deep next **5–8** light-pass by promo / `next_tier_keys` / `expansion_needed`.  
2. Re-run **3.1 → 3.2 → 3.3 exactly once** (`re_dual_once` consumed).  
3. Do **not** loop expansion further.  
4. Do not accept empty slip while next tier is unresearched — that is a process miss.

### What Dual Decision must not do

- Invent or edit `p_model`  
- Soften min_EV / haircut  
- Publish a place list separate from engine picks  
- Hand-remove or hand-add bets vs engine output  
- Re-open full odds board  
- Replace `build_portfolio`  
- Run &gt; ~8 minutes or nest deep-research inside argue

## 6) Stage 4 — Place session

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
| Research 1a | `research market-scan` · `board` · `light` · `ready` · `scaffold` · `critique` |
| Research 1b | `research scan-merge` (when present) · `research scan-depth` (**when available**; else manual line-count for D) |
| Stage 2 packs | `python scripts/write_deep_research_pack.py` · `/deep-research` skill |
| Decision 3.1 | Dual Decision argue → `outbox/decision_agent_{edge,guardian}_*.md` · `outbox/DUAL_DECISION_*.md` (advisory) |
| Decision 3.2–4 | `recommend` · `place-ack` · `abandon` |
| Sims | `simulate --sport tennis\|football\|basketball …` (suggest only) |

## Deliverables (list paths in final reply)

1. Odds file: `inbox/…`
2. Light: `outbox/light_research/…`
3. Deep queue SSOT: `data/state/deep_queue.json`
4. Scan agents: `outbox/scan_agent_{a,b,c[,d]}_YYYY-MM-DD.jsonl`
5. Multi-agent shortlist / primary worklist: `outbox/MULTI_AGENT_SHORTLIST.md`
6. Evidence packs: `evidence/*.json`
7. Coverage Health: `data/state/coverage_health.json`
8. Dual Decision: `outbox/decision_agent_edge_YYYY-MM-DD.md` · `outbox/decision_agent_guardian_YYYY-MM-DD.md` · `outbox/DUAL_DECISION_YYYY-MM-DD.md` (or skip note)
9. Slip: **`outbox/PLACE_THESE.md`** (engine picks only; post-engine `decision:` tags)
10. Status: `data/state/status.md` · `risk.json`
11. Reasoning: why · support · main risk (+ near-misses + dual tags when dual ran)
12. Expansion done? (if large board &lt;2 initially; re_dual_once consumed?)
13. place-ack / abandon ids if place session ran
14. Agent D: spawned / skipped (max lines, budget) note

## Hard rules (do not break)

- Load AGENTS.md first every session.
- Live recommend by default; dry-run only on request.
- **Stage 1b** A∥B∥C always; D only when any match ≥41 Candidate lines (manual count OK until scan-depth available).
- **Primary worklist ≤15** drives Stage 2 when multi-agent shortlist exists; never full-board deep.
- Engine `deep_queue.json` is light baseline SSOT — multi-agent merge never rewrites it.
- Deep-research primary worklist; expand before accepting empty on large boards.
- **ESR** — soft dogs not guilty by default; short 1.40–1.80 OK with support.
- **Exa (or HQ fallback)** on every primary-worklist line — both sides.
- FEH is **not** place law (shadow only).
- Empty slip only after expansion + no +EV.
- Coverage Health **critical** → soft-gate unless explicit `--allow-low-coverage`.
- Engines own bankroll/phase/risk; UI never invents stakes.
- **Do not change** capital_v2, phase ladder, secure bucket, unit sizing (10 NOK is post-size clip only).
- Form-continuity / anti-flip engine math unchanged; scan notes are soft annotations after merge.
- After place session: place-ack new Pending unless user says missed → abandon.
- Learning: no permanent hard-reject list growth.
- **KD-DD-wire:** Dual Decision is advisory only; place set + stakes **only** from engine `recommend`; never hand-remove engine picks; never publish judge preferred set as place list; `decision:` tags **post-engine only**.
- Dual Decision argue ≤8 min; no new Exa; skip on recommend-only / empty deep-ready.
