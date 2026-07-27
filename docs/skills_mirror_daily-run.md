---
name: daily-run
description: >
  Full NT betting-desk daily run under data-first Edge-Seeking Research (ESR)
  Stage 0–4: settle → assert-can-bet halt → odds → market-scan board+light (1a)
  → Match Intelligence Cards (1x MIC) → adaptive multi-agent scan A/B/C(+D)
  → merge shortlist 8–15 → MIC hard top-up → primary worklist ≤15 →
  /deep-research once (MIC primary) → three Decision Agents (Edge ∥ Guardian ∥
  Quality) → apply-quality-veto (3.1z) → engine recommend (sole positive place
  set; soft dogs not guilty by default; short 1.40–1.80 OK) → annotate
  PLACE_THESE from engine picks → expand once if large board & <2 picks
  (MIC top-up → deep → re-3.1–3.3; re_expand_once) → place-ack
  (10 NOK TEST_CAP:esr_data_v1 when active). Use when the user runs /daily-run,
  says "daily run", "run the day", "today's desk", "full research day",
  or drops a new inbox/odds file for a complete session.
  Accepts optional kick-off window and odds filename.
metadata:
  short-description: "Full day ESR data-first Stage 0–4 — MIC + adaptive 1b + three decision agents"
---

# /daily-run — Full desk day (Edge-Seeking Research, data-first)

Real-money capital desk. **Engines in `nt/` are law.** Load project rules first; never invent `p_model` or soften min_EV by hand.

**ESR:** Find the best available edges. Soft underdogs are **not** guilty by default. Short favourites **1.40–1.80** are allowed when research supports them. Empty slip only after full scan + **expansion** + no honest +EV. FEH is **demoted / shadow only** — not place law.

**Data-first:** Match Intelligence Cards (MIC) are the primary structured free-facts object before deep and Decision Agents. **Exa is optional** narrative fill for packs (not a long-term hard dependency). See `docs/EXA_RESEARCH_USAGE.md`.

> **Repo mirror:** keep `~/.grok/skills/daily-run/SKILL.md` in sync with `docs/skills_mirror_daily-run.md`. Desk pointer: `docs/DESK_SKILLS.md`. Philosophy: `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`. Adaptive scan (Stage 1b still valid): `docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md` — **Stage 3 Dual Decision superseded** by three agents + 3.1z (this skill). Tri template: `docs/templates/TRI_DECISION_TEMPLATE.md`.

## 0) Bootstrap (mandatory)

1. `Read` the repo root **`AGENTS.md`** — especially **Edge-Seeking Research (ESR)** Stage 0–4 + **Stage 1b multi-agent** + **KD-place-law**.
2. Skim **`docs/DESK_SKILLS.md`** / **`docs/EXA_RESEARCH_USAGE.md`** if needed.
3. Confirm CWD is the **nt-betting-tracker** worktree root (`run_nt.py` present).
4. Force **real tools** — shell CLI, free MIC pipeline / optional Exa + page open for deep research, file read/write. Do not simulate board/light/recommend output.
5. Identify odds file:
   - Path the user named, **or**
   - Path they asked to write (e.g. `inbox/odds_2026-07-25.txt`), **or**
   - **Newest** `inbox/odds*.txt` by mtime.
6. Session token: start with **`re_expand_once = unused`** (note in `outbox/TRI_DECISION_YYYY-MM-DD.md` header when Stage 3 runs).

### Optional: kick-off window + dump

If the user specifies a timeframe (Europe/Oslo) and filename, collect/write the Oddsen dump to that path **first**, then continue.

```text
/daily-run Collect the current Oddsen board from Norsk Tipping for kick-offs between
14:00 and 23:00 Europe/Oslo.
Write the dump to inbox/odds_YYYY-MM-DD.txt,
then run the full ESR Stage 0–4 path.
```

## Research standards (automatic — do not skip)

### A) Edge-Seeking Research (Stage 0–4) — data-first order

```text
0a settle → 0b assert-can-bet halt → 0c odds → 1a board/light → 1x MIC
  → 1b A/B/C(+D) → 1c shortlist → 1x MIC hard top-up → 2 deep (MIC primary)
  → 3.1 three agents → 3.1z apply-quality-veto → 3.2 recommend
  → 3.3 annotate → 3.4 expand once → 4 place-ack
```

| Stage | Action |
|-------|--------|
| **0a Settle** | settle / abandon + learning + **refresh** |
| **0b Can-bet halt** | `research assert-can-bet` / `risk.json` **can_bet** — if false → PLACE_THESE halt (**stop**) |
| **0c Odds** | Collect / confirm odds dump in `inbox/` |
| **1a Engine baseline** | market-scan → board → light → `data/state/deep_queue.json` SSOT |
| **1x MIC** | Match Intelligence Cards — board if n≤max else defer; budget ≤**8 min** |
| **1b Adaptive multi-agent scan** | A∥B∥C always (+ **D** when any match has ≥41 Candidate lines); MIC-aware when present → merge → shortlist **8–15** |
| **1c Primary worklist** | shortlist ∪ `coverage_critical` · cap **15** |
| **1x MIC hard top-up** | MIC for worklist gaps (v1_sports hard intent; best-effort else) |
| **2 Deep** | `/deep-research` **once** on primary worklist only — **MIC primary input** |
| **3.1 Three Decision Agents** | Edge Maximiser ∥ Portfolio Guardian ∥ Quality Challenger (≤10 min; no new Exa) |
| **3.1z apply-quality-veto** | CLI pack mutation — **required**; applied marker always |
| **3.2 Engine recommend** | `research ready` → `recommend` — **sole positive place set + stakes** |
| **3.3 Annotate** | PLACE_THESE from **engine picks** + agent cards (`decision:` / `agents:` tags **post-engine only**) |
| **3.4 Expand (optional once)** | Large board & **&lt;2** picks → **MIC top-up** → deep → re-run **3.1–3.3 once** (`re_expand_once=consumed`) |
| **4 Output** | PLACE_THESE + why/support/risk → place-ack (`TEST_CAP:esr_data_v1` when active) |

- Soft underdog HC: place when **matchup + EV** support — mixed H2H is not automatic reject.
- Short **1.40–1.80**: welcome with form/rank support (Grade B + core + EV).
- Prefer **finding honest edges** over empty-slip culture. Empty only after expansion + no +EV.
- **KD-place-law:** engine is sole **positive** place-set + stakes. Main narrates only. **Exception:** Quality **hard_veto** via CLI pack mutation pre-recommend only (closed enum). Edge/Guardian remain fully advisory. Never hand-remove engine picks; never publish agent wants as a place list.

### B) Sport research (cards optional aid)

- Sport cards / SAEF may inform notes; they are **not** FEH place law.
- Individual sports: H2H still high-value research — record polarity honestly.
- New/thin sports: research carefully; do not invent edges.
- MIC v1 full pipeline = **football** (`v1_sports`); other sports get schema/skeletons + soft pressure until they join v1_sports.

### C) Exa search — **optional** (not long-term required)

| Rule | Detail |
|------|--------|
| Mode | `research.exa_mode: optional` until exit criteria (E1–E5) then `off` default |
| Role | Narrative / HQ fill for packs when free MIC + public pages are thin |
| Never | MIC body extraction; hard FEH reject; re-arm FEH place law |
| Both sides | When Exa/HQ is used: favourite **and** underdog |
| Fallback | HQ web + sport sites; free NT → Flashscore → FotMob first |
| `require_for_deep` | **false** until PR6; when true, **scoped to `v1_sports` only** (not all sports) — non-v1 seats are **not** hard-blocked by MIC alone |

See `docs/EXA_RESEARCH_USAGE.md`.

### D) Empty slip law

- Empty after honest deep **and** expansion with no +EV = OK.
- Empty while next tier unresearched / queue ignored = **process miss**.
- Do **not** force weak EV seats to “use budget.”
- Do **not** reject everything imperfect (anti-soft ideology is off).
- After quality-passed deep + expansion + no +EV = OK (KD-empty-slip).

### E) 10 NOK test stake cap (when active)

- First **10 placed** bets tagged `TEST_CAP:esr_data_v1` → max **10 NOK** per seat.
- Absolute-last clip — **does not** change capital_v2 / unit / phase math.
- See `data/state/status.md` for test_cap progress.
- Legacy tag `esr_v1` / `FEH_TEST_CAP:` may still count in engine history; **new** places use **`esr_data_v1`**.

### F) Reasoning (every pick + short near-miss)

```markdown
### N. {Selection} @ {odds} · Grade · EV · stake
- **Why:** …
- **Support:** … (cite MIC when present)
- **Main risk:** …
- **MIC:** grade B · score 0.78 · ref outbox/match_intel/…
- **Evidence quality:** adequate | thin | insufficient
- **scan_agent:** A|B|C|D|…   # when multi-agent shortlist used
- **decision:** both | edge_only | guardian_only | quality_ok | engine_only | engine_over_quality | …
- **agents:** maximiser_rank=#k · guardian_rank=#j · quality=pass|demote|veto
```

Near-misses: one short line each (why not / what would change). Write `decision:` / `agents:` **only after** engine recommend. Reconciliation: `outbox/TRI_DECISION_YYYY-MM-DD.md` (not Dual-as-sole Stage 3).

---

## 1) Stage 0a — Results first (if any open risk)

```powershell
python run_nt.py status
python run_nt.py settle --draft
# After outcomes known:
# python run_nt.py settle --results inbox/results.yaml
# Or abandon unplaceable Pending:
# python run_nt.py abandon --ids <id> --reason missed_prematch
python run_nt.py control-signals list --json
python run_nt.py refresh
```

- Fill **PostSettlementPacket** on process_error / poor retro.
- Classify **predictability + variance_class + learning_weight** (`/learning-rootcause` if batch).
- Learning proposals auto-apply when configured — do not ask user to accept.
- **Do not** propose new hard-reject lists from losses.

## 1b) Stage 0b — Can-bet early exit (**hard halt**)

**After refresh, before odds research / MIC / scan / deep / recommend:**

```powershell
python run_nt.py research assert-can-bet
# alias: python run_nt.py risk assert-can-bet
# optional: --no-refresh  (read data/state/risk.json only)
```

| Result | Action |
|--------|--------|
| exit **0** / `can_bet: true` | Continue Stage 0c+ |
| exit **non-zero** / `can_bet: false` | Write **PLACE_THESE capital halt** (no-bet); **stop** — **no** odds work, MIC, scan, deep, agents, or recommend |

Read fields from `data/state/risk.json` (live names): **`can_bet`**, `remaining_risk_nok`, `stopped`, capital_v2 L3 / freeze reasons — **not** a field named `remaining_today`.

## 2) Stage 0c — Odds dump

Confirm odds file path (user named / newest `inbox/odds*.txt`). Collect Oddsen dump when user requested a kick-off window.

## 3) Stage 1a — Market coverage + board + light (engine baseline)

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

## 4) Stage 1x — Match Intelligence Cards (MIC)

**Primary structured free facts** for every shortlist/deep match. Agents and decision logic consume MIC; they do not replace it.

```powershell
python run_nt.py research match-intel --odds <odds_file>
# single match / force rebuild:
# python run_nt.py research match-intel --match "Team A vs Team B" --sport football
# python run_nt.py research match-intel --odds <odds_file> --force
```

### Budget (KD-mic-budget)

| Rule | Detail |
|------|--------|
| Wall-clock | Stage **1x** ≤ **8 minutes** (separate from scan 12 min) |
| Board-wide | If unique matches on dump ≤ `research.match_intel.max_matches_per_run` (default **40**) → board MIC after 1a |
| Else | Defer full board; proceed 1b with `mic:missing` OK on scan rows |
| After 1c | **Hard top-up** MIC for primary worklist gaps (still ≤ max; prioritize worklist order) |
| Expansion 3.4 | MIC top-up for expansion matches before deep |
| v1_sports | Default **`[football]`** — full free pipeline; other sports: skeleton / best-effort |
| `require_for_deep` | **false** until exit criteria; when true → only seats with `sport ∈ v1_sports` hard-block on missing/D/F MIC |
| Never | Exa for MIC body; invent form/injuries on fetch fail → grade **F** skeleton |

| Artifact | Path |
|----------|------|
| MIC cards | `outbox/match_intel/{match_key}.json` |
| Optional index | `outbox/match_intel/_index_YYYY-MM-DD.json` |

Scan agents: when MIC present, **cite** grade/score/one fact in `reason`; when missing after defer, tag `mic:missing`.

---

## 5) Stage 1b — Adaptive multi-agent scan (A / B / C / +D)

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
- **Must run `research scan-depth` when available.** Else manual line-count is OK. Log: `agent_d: spawned | skipped (max_lines_per_match=N, min_lines=41)`.
- **Sequential D budget:** if sequential and wall-clock after A+B+C is **≥10 minutes**, **skip D** even if spawn true; note `scan_agent_missing: D (budget)`.

### Agent A — Favourites & HUB (strengthened)

**Purpose:** Surface short-to-mid favourite edges with **mandatory active search** of football (and other 3-way) **HUB/1X2 Match Result**, in a way that can **reach Stage 2**.

**Must:**

1. Scan every football (and other HUB) match for **1X2 / HUB** selections in **[1.40, 1.90]**.
2. Prefer **main Match Result** over diverting a clear 1X2 edge into handicap solely because HC is “more interesting.”
3. If a clear favourite 1X2 edge exists (form/rank/H2H/MIC one-liner supports fav or draw), include it among the ≤5 — **MUST NOT ignore clear 1X2 for HC**.
4. Still allow non-football short ML/Vinner in band when stronger than football HUB.
5. **Light / short_chalk interaction:**
   - Prefer odds **≥ 1.70** (`short_chalk_odds`) when structural support is thin (default A seats).
   - Allow **1.40–1.69** only with an **explicit structural one-liner** (form/rank/H2H/table/MIC) **and** prefix reason with `force_scan:` when the edge is real enough to justify Stage 2 cost despite light fail risk.
   - Prefer mid-band **1.70–1.90** football HUB over 1.40–1.55 chalk that will be process-theater.
6. Soft `form_continuity_risk:` when live ledger shows recent heavy-fav Win on opposite side (scan note only).
7. When MIC present: cite `mic:grade=X` or one MIC fact; else `mic:missing`.

**Must not:**

- Fill all five seats with 1.40–1.55 chalk ML that light will drop without `force_scan:`.
- Treat “longshot ML” as A territory.
- Skip HUB entirely on a football-heavy board to fill seats with non-football chalk.

**Self-check:** odds ∈ [1.40, 1.90]; ≥1 football HUB/1X2 when such lines in band exist; clear 1X2 not replaced by HC without one-line justification; if odds &lt; 1.70: structural why + `force_scan:` when intending Stage 2; non-empty reason.

**Output:** `outbox/scan_agent_a_YYYY-MM-DD.jsonl` (max 5 rows).

```text
You are ESR Scan Agent A — Favourites & HUB (max 5).
Odds band 1.40–1.90. Prefer ≥1.70 (short_chalk_odds) so seats survive light/KD16.
MUST search football HUB/1X2. MUST NOT ignore clear 1X2 for HC.
If 1.40–1.69: structural one-liner + force_scan: when Stage 2 intended.
Cite MIC when present. No p_model, packs, place. Output: outbox/scan_agent_a_YYYY-MM-DD.jsonl
```

### Agent B — Totals & Props (strengthened)

**Must actively consider (when present on dump):** match totals / maps / runs; **team totals**; **player props**; **cards**; **corners**; other specials with a one-sentence natural story.

**Self-limit:** ≤**2** same coarse `market_family` in B’s own five.

**Coordination with D (when `spawn_agent_d=true`):**

| Rule | Detail |
|------|--------|
| B hard self-bias | Prefer **main natural totals + team totals**; at most **1** pure long-tail prop/card/corner seat |
| D owns | Deep props, cards, corners, shots, specials on high-volume matches |
| Merge (when D-armed) | If B and D collide on the **same long-tail family key**, **prefer D’s row**. Note `b_yielded_longtail_to_d` when relevant |

When D is **not** spawned, B must cover props itself (full strengthened mandate).

```text
You are ESR Scan Agent B — Totals & Props (max 5).
Team totals, player props, cards, corners, specials, natural totals.
Self-limit ≤2 same market_family.
If spawn_agent_d=true: bias main totals; at most 1 long-tail seat (D owns deep props).
Cite MIC when present. No p_model, packs, place. Output: outbox/scan_agent_b_YYYY-MM-DD.jsonl
```

### Agent C — Handicaps & Matchup

HC + matchup dogs with **real reasons**; `force_scan:` only for real matchup vs light-fail risk; soft `form_continuity_risk:`; not “long odds = value.” Do not steal clear HUB 1X2 edges that belong in A without a distinct HC thesis. Cite MIC when present. Max **5**.

```text
You are ESR Scan Agent C — Handicaps & Matchup (max 5).
Real matchup reasons only. force_scan: only when justified.
Cite MIC when present. No p_model, packs, place. Output: outbox/scan_agent_c_YYYY-MM-DD.jsonl
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
No p_model, packs, place. Output: outbox/scan_agent_d_YYYY-MM-DD.jsonl
```

### Merge (A+B+C + D when active)

**Use `research scan-merge`.** Manual merge is allowed if CLI missing — same rules.

```powershell
python run_nt.py research scan-depth --odds <odds_file>
python run_nt.py research scan-merge --odds <odds_file> `
  --agent-a outbox/scan_agent_a_YYYY-MM-DD.jsonl `
  --agent-b outbox/scan_agent_b_YYYY-MM-DD.jsonl `
  --agent-c outbox/scan_agent_c_YYYY-MM-DD.jsonl
# or: --agents-dir outbox
# add --agent-d when D ran
```

| Rule | Detail |
|------|--------|
| Per agent | Truncate each to **5** |
| Agent A band | Drop A rows outside odds **[1.40, 1.90]** |
| Invalid | Off odds dump · empty reason → drop |
| Dedupe | By evidence_pair_key; union `scan_agents` (e.g. A+C, B+D) |
| Family | Each `market_family` ≤**2** after merge |
| Sport soft | Prefer ≤**3** per sport on multi-sport boards |
| Light KD16 | Multi-agent-only **hard light-fail → DROP** unless reason contains `force_scan:` |
| Size | Clamp shortlist **8–15**; engine top-up from `deep_queue` if &lt;8 |
| Coverage | `primary_worklist` = shortlist ∪ coverage_critical · cap **15** |
| Continuity | `form_continuity_risk` / anti-flip notes = **annotation only** after merge |
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

### Stage 1x hard top-up (after 1c)

```powershell
# Fill MIC for worklist matches still missing cards
python run_nt.py research match-intel --odds <odds_file>
# or per-match: --match "…" for each gap
```

Hard for **v1_sports** worklist seats (intent); best-effort for other sports. Do not deep football (v1) seats that still lack MIC when `require_for_deep` is true (PR6+). Until then: soft pressure only.

---

## 6) Stage 2 — Deep research on primary worklist only (MIC primary)

1. Invoke **`/deep-research` once** on the **primary worklist ≤15** (see `~/.grok/skills/deep-research/SKILL.md`).  
2. **MIC is primary input** — load `outbox/match_intel/{match_key}.json` before Exa/HQ; pack `data_coverage` / `evidence_quality` from MIC + both-sides checks.  
3. **Refuse** full-board / dump-wide deep.  
4. Scaffold only if needed for a worklist line:

```powershell
python run_nt.py research board --odds <odds_file> --write-scaffolds
python run_nt.py research scaffold --match "…" --selection "…" --sport darts --write
```

5. Packs: **atomic** `python scripts/write_deep_research_pack.py` (never bare `research write-pack` as final step). Honest `p_model`, both sides, form · H2H · rank · natural markets.  
6. Form-continuity / opposite-side / anti-flip fields: follow deep-research skill + engine soft rules — do not invent weak-phrase flips.  
7. **Exa optional** — use when MIC + free pages are thin; not mandatory for every line when MIC grade ≥ B.

**Pack minimum (not F):** `p_model` · `summary` · `failure_modes` · real sources (≈4+). Prefer `data_coverage` block.  
**Hard rejects only:** script/base-rate conflict · missing availability on sensitive markets · missing `p_model` · empty takeaways.  
**Never invent `p_model`.** Soft dog without edge → skip that line, not the whole philosophy.

Optional critique:

```powershell
python run_nt.py research critique evidence/<file>.json --odds 1.95
```

---

## 7) Stage 3 — Three Decision Agents → apply-quality-veto → engine recommend → annotate (+ expand once)

### KD-place-law (normative — highest risk; do not violate)

> **Engine `recommend` / `build_portfolio` remains the sole authority for the positive place set and all stakes.**  
> Decision Agents do **not** publish a competing positive place list.  
> Main Agent is the **narrative judge** only — never invents, adds, removes, or re-stakes after recommend.

#### Exception table

| Action | Binding? | Who / how |
|--------|----------|-----------|
| Positive place set + stakes | **Yes — engine only** | `recommend` / `build_portfolio` |
| **hard_veto** remove placeability **before** recommend | **Yes — Quality only** | Machine `outbox/quality_veto_*.json` + **CLI** `apply-quality-veto` mutates packs |
| soft_demote / Edge ranks / Guardian challenges | **No — advisory** | Markdown artifacts; near-miss notes |
| Main invents extra vetoes not in Challenger JSON | **Forbidden** | — |
| Post-recommend hand delete / hand add / restake | **Forbidden** | — |
| Edge/Guardian “preferred 2–6” as place list | **Forbidden** | KD-DD-wire spirit for Edge/Guardian |

**Constitutional note:** This **supersedes** Dual Decision Stage 3.1 as the sole Stage 3 protocol. Adaptive **scan** A/B/C(+D) is **unchanged**. Golden shape: **`docs/templates/TRI_DECISION_TEMPLATE.md`** (keep Dual template file for archive; skill uses TRI).

| Conflict | Rule |
|----------|------|
| Engine **drops** an agent want | Near-miss with **engine reject reason**; do not hand-force place |
| Engine **includes** a Guardian-challenged seat | **Still place** the engine pick; annotate — **do not hand-remove** |
| Quality hard_veto applied | Seat not placeable (null `p_model`); near-miss with veto reason |
| Agents agree on X, engine picks Y | Place **Y**; narrative explains disagreement |
| No agent artifacts (skip path) | PLACE_THESE as engine-only; omit agent tags |

**Order law:**

```text
deep packs ready
  → 3.1 Three Decision Agents ARGUE (Edge ∥ Guardian ∥ Quality)
  → 3.1z apply-quality-veto (CLI; applied marker required)
  → 3.2 engine recommend (SOLE positive place set)
  → 3.3 annotate PLACE_THESE from engine picks + agent cards
  → (optional once) 3.4 MIC top-up → deep → re-run 3.1–3.3 once
```

### Skip rules

| Session type | Decision agents |
|--------------|-----------------|
| Full `/daily-run` | Run **3.1 → 3.1z → 3.2 → 3.3** |
| Recommend-only / already-researched packs only | **Skip 3.1** unless `quality_veto_{today}.json` exists → still run **3.1z** before recommend |
| Empty deep-ready set | **Skip argue**; still run recommend path (may empty) |
| Skill kill-switch | Comment out Stage 3.1 in this skill + mirror (`decision_agents: skip` skill-text only; skills do not load YAML) |

### Stage 3.1 — Three Decision Agents ARGUE (before recommend)

**Speed law:** ≤ **10 minutes** wall-clock. Prefer Edge **∥** Guardian **∥** Quality.  
**Inputs only:** deep packs + MIC + shortlist reasons + open occupancy + Settlement Lessons soft notes.  
**Hard bans:** no new Exa · no new packs · no invent `p_model` · no soften min_EV · **no place** · no ledger write · no re-open full board · **no Main hand-edits of packs**.

#### Decision Agent 1 — Edge Maximiser (advisory)

**Mission:** Rank **3–6 wants** by honest +EV from deep-ready cards. Advisory only.

```text
Advisory only. Packs exist. No new research. Rank 3–6 wants by honest +EV.
You do NOT place bets. Output: outbox/decision_agent_edge_YYYY-MM-DD.md
```

**Output:** `outbox/decision_agent_edge_YYYY-MM-DD.md` — ranked wants + one-line why each. **Does NOT place.**

#### Decision Agent 2 — Portfolio Guardian (advisory)

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

#### Decision Agent 3 — Research Quality & Continuity Challenger

**Mission:** Emit machine-readable quality vetoes. Notes-only flags are **insufficient**. Real power = closed-enum **hard_veto** applied by **CLI** (not Main hand-edits).

```text
Emit quality_veto JSON. hard_veto reasons ONLY from closed enum.
CLI apply-quality-veto nulls p_model (engine-aligned). You do not place or edit stakes.
soft_demote is advisory only.
Output: outbox/decision_agent_quality_YYYY-MM-DD.md + outbox/quality_veto_YYYY-MM-DD.json
```

**Closed-enum hard_veto reasons only:**

```text
mic_missing | mic_grade_D | mic_grade_F |
opposite_side_thin | form_continuity_weak_flip | evidence_quality_insufficient
```

Any other reason string → CLI **rejects** that veto row. soft_demote may use free-text notes.

**Sport scope (PR6+):** `mic_missing` / `mic_grade_D` / `mic_grade_F` hard_veto only when seat `sport ∈ v1_sports`. Until then soft pressure is OK; CLI still accepts the enum.

**Outputs:**

- `outbox/decision_agent_quality_YYYY-MM-DD.md`
- `outbox/quality_veto_YYYY-MM-DD.json`

#### Draft reconciliation (pre-engine)

Write draft `outbox/TRI_DECISION_YYYY-MM-DD.md` with **wants / challenges / vetoes only** — **not** a place list. Golden shape: `docs/templates/TRI_DECISION_TEMPLATE.md`.

### Stage 3.1z — apply-quality-veto (**required** before recommend)

```powershell
python run_nt.py research apply-quality-veto --date YYYY-MM-DD
# optional: --dry-run | --veto-file path
```

| Check | Value |
|-------|--------|
| `outbox/quality_veto_applied_YYYY-MM-DD.json` | **must exist** after successful apply (**even if `n_vetoes=0`**) |
| Packs | hard_veto → null `p_model` + `research_quality` block (CLI only) |
| Undo | `outbox/quality_veto_undo_YYYY-MM-DD.jsonl` (may be empty) |
| Main | **Never** hand-edit packs or invent vetoes outside Challenger JSON |

**If 3.1z is skipped, Challenger power is zero.** skill_smoke proof = applied marker file.

If no `quality_veto_*.json` exists on full daily-run, still run apply (no-op / empty vetoes path when supported) or write empty veto JSON then apply so the **applied marker** lands.

### Stage 3.2 — Engine recommend (SOLE positive place set)

```powershell
python run_nt.py research ready --odds <odds_file>
python run_nt.py recommend --odds <odds_file>
# Coverage critical + explicit override only:
# python run_nt.py recommend --odds <odds_file> --allow-low-coverage
# dry-run ONLY if user asks
```

- Engine output = **sole** picked set + stakes + rejects.  
- Target **2–6** picks on large boards when honest EV exists.  
- When test cap active, expect ≤ **10 NOK** and `TEST_CAP:esr_data_v1` in notes.  
- Do not re-place already open tickets.  
- **No** `--prefer-keys` / agent pin in v1 — recommend API unchanged.

### Stage 3.3 — Annotate PLACE_THESE (post-engine only)

Main agent is **annotator**, not a second place list:

1. For each **engine-picked** row:
   - On both Edge and Guardian top lists → `decision: both`
   - Only Edge → `decision: edge_only` (or `edge_over_guardian` if Guardian challenged)
   - Only Guardian → `decision: guardian_only`
   - Quality pass / demote / prior hard_veto cleared by non-place → tag quality in `agents:`
   - On neither agent list → `decision: engine_only`
2. For each agent want **not** picked → near-miss with **engine reject reason** (not agent veto).
3. Hard_vetoes (pre-recommend) → near-miss with closed-enum reason.
4. **Never** hand-remove an engine pick because Guardian challenged it.
5. **Never** hand-add an agent want the engine did not pick.
6. Finalize PLACE_THESE reasoning + `outbox/TRI_DECISION_YYYY-MM-DD.md` **reconciliation** section (post-engine match table).
7. Provenance: `scan_agent:` when multi-agent shortlist was used; `decision:` / `agents:` **only after** recommend.

```markdown
### N. {Selection} @ {odds} · Grade · EV · stake
- **Why:** …
- **Support:** … (cite MIC)
- **Main risk:** …
- **Opposite side:** …
- **Form continuity:** …
- **MIC:** grade B · score …
- **Evidence quality:** adequate
- **scan_agent:** A+D
- **decision:** both | edge_only | guardian_only | edge_over_guardian | engine_only | …
- **agents:** maximiser_rank=#k · guardian_rank=#j · quality=pass|demote|veto
```

**Integrity:** Any claim of `both` requires the pick on **both** Edge and Guardian want lists **and** in engine picks. No pre-recommend `decision:` tags.

### Stage 3.4 — Expansion (optional, once) — MIC top-up + `re_expand_once`

**Token:** `re_expand_once` ∈ {`unused`, `consumed`}.

```text
IF re_expand_once == consumed: skip
IF not (large board & picks < 2): skip
1. Select next 5–8 light-pass lines (promo / next_tier_keys / expansion_needed)
2. MIC build for those expansion matches (hard for v1_sports; best-effort else)
3. Deep those lines
4. Three agents → apply-quality-veto → recommend → annotate
5. Set re_expand_once = consumed  (even if still <2 picks)
```

Large board: ≥15 matches or ≥80 lines.

```powershell
python run_nt.py research match-intel --odds <odds_file>   # expansion matches
# /deep-research on expansion tier
# re-run 3.1 → 3.1z → 3.2 → 3.3 once
```

Do **not** loop expansion further. Do not accept empty slip while next tier is unresearched — that is a process miss.

### What Decision Agents must not do

- Invent or edit `p_model` (except CLI apply-quality-veto for hard_veto)  
- Soften min_EV / haircut  
- Publish a place list separate from engine picks  
- Hand-remove or hand-add bets vs engine output  
- Main hand-mutate packs outside CLI  
- Re-open full odds board  
- Replace `build_portfolio`  
- Run &gt; ~10 minutes or nest deep-research inside argue  

---

## 8) Stage 4 — Place session

```powershell
python run_nt.py place-ack --ids <bet_id>[,<bet_id>...]
python run_nt.py abandon --ids <bet_id> --reason missed_prematch
python run_nt.py status
```

When test cap active, notes carry `TEST_CAP:esr_data_v1`.

## Exhaustive CLI map

| Stage | Command |
|-------|---------|
| Status | `python run_nt.py status` · `refresh` · `validate` |
| Capital | `capital status` · `capital segments` |
| Settle | `settle --draft` · `settle --results …` · `abandon` |
| **0b Can-bet** | `research assert-can-bet` · `risk assert-can-bet` |
| Learning | `learn` · `control-signals list` |
| Research 1a | `research market-scan` · `board` · `light` · `ready` · `scaffold` · `critique` |
| **1x MIC** | `research match-intel` |
| Research 1b | `research scan-merge` · `research scan-depth` |
| Stage 2 packs | `python scripts/write_deep_research_pack.py` · `/deep-research` skill |
| Decision 3.1 | three agents → `outbox/decision_agent_{edge,guardian,quality}_*.md` · `outbox/quality_veto_*.json` · `outbox/TRI_DECISION_*.md` |
| **3.1z** | `research apply-quality-veto --date YYYY-MM-DD` |
| Decision 3.2–4 | `recommend` · `place-ack` · `abandon` |
| Sims | `simulate --sport tennis\|football\|basketball …` (suggest only) |

## Deliverables (list paths in final reply)

1. Odds file: `inbox/…`
2. Can-bet: assert-can-bet result / halt note
3. Light: `outbox/light_research/…`
4. Deep queue SSOT: `data/state/deep_queue.json`
5. MIC: `outbox/match_intel/*.json`
6. Scan agents: `outbox/scan_agent_{a,b,c[,d]}_YYYY-MM-DD.jsonl`
7. Multi-agent shortlist / primary worklist: `outbox/MULTI_AGENT_SHORTLIST.md`
8. Evidence packs: `evidence/*.json`
9. Coverage Health: `data/state/coverage_health.json`
10. Three agents: `outbox/decision_agent_{edge,guardian,quality}_YYYY-MM-DD.md` · `outbox/quality_veto_YYYY-MM-DD.json` · `outbox/quality_veto_applied_YYYY-MM-DD.json` · `outbox/TRI_DECISION_YYYY-MM-DD.md` (or skip note)
11. Slip: **`outbox/PLACE_THESE.md`** (engine picks only; post-engine `decision:` / `agents:` tags)
12. Status: `data/state/status.md` · `risk.json`
13. Reasoning: why · support · main risk (+ near-misses + agent tags when agents ran)
14. Expansion done? (`re_expand_once` unused/consumed)
15. place-ack / abandon ids if place session ran
16. Agent D: spawned / skipped (max lines, budget) note

## Hard rules (do not break)

- Load AGENTS.md first every session.
- Live recommend by default; dry-run only on request.
- **0b can-bet halt** after refresh — stop research when `can_bet: false`.
- **1x MIC** before deep (board if n≤max; hard top-up after 1c; budget ≤8 min).
- **Stage 1b** A∥B∥C always; D only when any match ≥41 Candidate lines.
- **Primary worklist ≤15** drives Stage 2 when multi-agent shortlist exists; never full-board deep.
- Engine `deep_queue.json` is light baseline SSOT — multi-agent merge never rewrites it.
- Deep-research primary worklist (**MIC primary**); expand with MIC top-up before accepting empty on large boards.
- **ESR** — soft dogs not guilty by default; short 1.40–1.80 OK with support.
- **Exa optional** — free MIC/public pages first; sport-scoped `require_for_deep` only after exit criteria.
- FEH is **not** place law (shadow only).
- Empty slip only after expansion + no +EV.
- Coverage Health **critical** → soft-gate unless explicit `--allow-low-coverage`.
- Engines own bankroll/phase/risk; UI never invents stakes.
- **Do not change** capital_v2, phase ladder, secure bucket, unit sizing (10 NOK is post-size clip only).
- Form-continuity / anti-flip engine math unchanged; scan notes are soft annotations after merge.
- After place session: place-ack new Pending unless user says missed → abandon.
- Learning: no permanent hard-reject list growth.
- **KD-place-law:** engine sole **positive** place set + stakes; Quality **hard_veto** only via **CLI** pack mutation pre-recommend; Main never hand-edits packs; Edge/Guardian advisory; `decision:` tags **post-engine only**.
- **3.1z** must run after Quality agent and **before** recommend; **applied marker required**.
- Three agents argue ≤10 min; no new Exa; skip on recommend-only / empty deep-ready (still apply veto file if present).
- Test tag: **`esr_data_v1`**.
- Dual Decision is **not** sole Stage 3 — use TRI_DECISION + three agents + 3.1z.
