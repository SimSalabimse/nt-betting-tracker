---
name: daily-run
description: >
  Full NT betting-desk daily run under Edge-Seeking Research (ESR) Stage 0–4:
  settle → Settlement Lessons (warn if missing/stale) → odds dump →
  market-scan → board+light → promising deep queue → Exa both-sides deep
  packs → recommend best +EV (hard max 2 market_family; similar-recent +
  lessons soft demotion; soft dogs not guilty; short 1.40–1.80 OK) → expand
  if large board & <2 picks → Reasoning (why · support · main risk) →
  PLACE_THESE.md → place-ack (10 NOK TEST_CAP:esr_v1 when active). Live
  ledger only — never history/archives or history/rounds. Use when the user
  runs /daily-run, says "daily run", "run the day", "today's desk", "full
  research day", or drops a new inbox/odds file for a complete session.
  Accepts optional kick-off window and odds filename.
metadata:
  short-description: "Full day ESR Stage 0–4 — lessons + diversify + live ledger"
---

# /daily-run — Full desk day (Edge-Seeking Research)

Real-money capital desk. **Engines in `nt/` are law.** Load project rules first; never invent `p_model` or soften min_EV by hand.

**ESR:** Find the best available edges. Soft underdogs are **not** guilty by default. Short favourites **1.40–1.80** are allowed when research supports them. Empty slip only after full scan + **expansion** + no honest +EV. FEH is **demoted / shadow only** — not place law.

**Automatic hardenings (every run):** Settlement Lessons after terminal settle · hard max **2** `market_family` · similar-recent + lessons soft demotion · **archive isolation** (never `history/archives/` or `history/rounds/`). ControlSignals, capital_v2, phase, secure, 10 NOK cap **unchanged**. See root `AGENTS.md` § Settlement Lessons + diversify + archive isolation.

**Exa** is the primary HQ search for every deep-queue line (both sides). Exa feeds packs and reasoning — it does **not** hard-reject and does not re-arm FEH. See `docs/EXA_RESEARCH_USAGE.md`.

> **Repo mirror:** keep `~/.grok/skills/daily-run/SKILL.md` in sync with `docs/skills_mirror_daily-run.md`. Desk pointer: `docs/DESK_SKILLS.md`. Philosophy: `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`. Diversify: `docs/DIVERSITY_AND_EXPLORE.md`. Lessons: `docs/SETTLEMENT_LEARNING.md`.

## 0) Bootstrap (mandatory)

1. `Read` the repo root **`AGENTS.md`** — especially **Edge-Seeking Research (ESR)** Stage 0–4.
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
| **1 Broad Scan** | market-scan → board → light → promising queue **8–15** (all lines scored) |
| **2 Deep** | Exa both-sides → `evidence/*.json` + honest `p_model` |
| **3 Select** | ready → recommend best +EV (gates + grade + EV) |
| **3b Expand** | Large board & **&lt;2** picks → deep next 5–8 → re-recommend |
| **4 Output** | PLACE_THESE + why/support/risk → place-ack |

- Soft underdog HC: place when **matchup + EV** support — mixed H2H is not automatic reject.
- Short **1.40–1.80**: welcome with form/rank support (Grade B + core + EV).
- Prefer **finding honest edges** over empty-slip culture. Empty only after expansion + no +EV.

### B) Sport research (cards optional aid)

- Sport cards / SAEF may inform notes; they are **not** FEH place law.
- Individual sports: H2H still high-value research — record polarity honestly.
- New/thin sports: research carefully; do not invent edges.

### C) Exa search — every deep-queue line

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
```

Near-misses: one short line each (why not / what would change).

### G) Settlement Lessons + diversify + archive isolation (automatic)

| Rule | Detail |
|------|--------|
| **Settlement Lessons** | After settle with **≥1 terminal**: read + print `outbox/SETTLEMENT_LESSONS.md` / `data/state/settlement_lessons.json` **before** Stage 1 research. Missing or stale → **warn**, continue (not hard-stop). Soft awareness only (TTL); no permanent hard rejects. |
| **Hard max 2** `market_family` | Engine diversify on open+slip. Coarse family (line not in key). Expect family rejects on 3rd same family. |
| **similar-recent** | Soft `sort_ev` demotion + notes on live recent same sport/family/line — true EV honest. |
| **Lessons soft** | Independent portfolio demotion from Settlement Lessons soft_awareness. |
| **Archive isolation** | **FORBIDDEN** for memory/peers: `history/archives/`, `history/rounds/`, **and git stash/branch copies of `data/*`**. Use only live working-tree `data/bets.csv`, pending, latest results, current odds, `data/state/*`. |
| **Live desk SSOT** | Never `git checkout`/`restore`/`stash apply` onto `data/bets.csv` or `data/state/*` during engineering. Clean era: **era_start 2026-07-25**, baseline **500 NOK**. Verify with `python run_nt.py status` before research. |
| **Stage 1** | Do **not** hand-demote deep_queue by family/lessons — engine queue is research priority; diversify binds at recommend. |
| **Untouched** | No FEH/anti-soft revival · capital_v2/phase/secure/unit/10 NOK · ControlSignals contracts. |

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

## 2) Stage 1 — Market coverage + board + light

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
Queue rank = research priority, not automatic place pass.

## 3) Stage 2 — Deep queue research (Exa)

1. Work **engine deep_queue** first (promise score — not anti-chalk moralization only).  
2. Scaffold if needed:

```powershell
python run_nt.py research board --odds <odds_file> --write-scaffolds
python run_nt.py research scaffold --match "…" --selection "…" --sport darts --write
```

3. **Exa deep-research each queue line** — both sides, form · H2H · rank · natural markets.  
4. Write packs with honest `p_model`:

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
- If large board and **&lt;2** picks: deep next **5–8** light-pass by promo / `next_tier_keys` → **re-recommend**.  
- Present slip with **why · support · main risk**.  
- When test cap active, expect ≤ **10 NOK** and `TEST_CAP:…` in notes.  
- Do not re-advise already open tickets.  
- Expect **max 2** open+slip per coarse `market_family`; surface similar-recent / `lessons_soft` demotions in near-misses when present.

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
4. Deep queue: `data/state/deep_queue.json`
5. Evidence packs: `evidence/*.json`
6. Coverage Health: `data/state/coverage_health.json`
7. Slip: **`outbox/PLACE_THESE.md`**
8. Status: `data/state/status.md` · `risk.json`
9. Reasoning: why · support · main risk (+ near-misses; family/similar/lessons notes)
10. Expansion done? (if large board &lt;2 initially)
11. place-ack / abandon ids if place session ran

## Hard rules (do not break)

- Load AGENTS.md first every session.
- Live recommend by default; dry-run only on request.
- Deep-research engine queue; expand before accepting empty on large boards.
- **ESR** — soft dogs not guilty by default; short 1.40–1.80 OK with support.
- **Exa (or HQ fallback)** on every deep-queue line — both sides.
- FEH is **not** place law (shadow only). **Do not** revive anti-soft from losses.
- Empty slip only after expansion + no +EV.
- Coverage Health **critical** → soft-gate unless explicit `--allow-low-coverage`.
- Engines own bankroll/phase/risk; UI never invents stakes.
- **Do not change** capital_v2, phase ladder, secure bucket, unit sizing (10 NOK is post-size clip only). ControlSignals contracts unchanged.
- After place session: place-ack new Pending unless user says missed → abandon.
- Learning: no permanent hard-reject list growth.
- After settle ≥1 terminal: **print Settlement Lessons** before research; missing/stale = warn only.
- Hard max **2** `market_family`; respect similar-recent + lessons soft demotion (sort only).
- **FORBIDDEN memory:** `history/archives/`, `history/rounds/`, git stash/branch `data/*` — live working-tree `data/bets.csv` + pending + current odds/results only.
- **Never overwrite live desk SSOT** via git during `/execute-plan` or branch work. Clean era = **2026-07-25 / 500 NOK**.
