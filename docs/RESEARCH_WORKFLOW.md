# Research & Bet-Finding Workflow — Edge-Seeking Research (ESR)

## Agent trigger (every odds dump)

When the user provides a **new or updated odds file** in `inbox/`, the agent **must** run the full **Stage 0–4** path (see root `AGENTS.md`). Defaults: **live recommend** (logs Pending when picks exist); **dry-run only if the user asks**; **do not re-advise already Pending tickets**; honest evidence only (no mechanical `p_model` unless explicitly ordered).

**Philosophy:** **Edge-Seeking Research (ESR)** — find the best available +EV edges. Soft underdogs are **not** guilty by default. Short favourites **1.40–1.80** are allowed when research supports them. Empty slip only after full scan + **expansion** + no honest edge.

Authoritative design: [`RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](./RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md).  
FEH non-bypassable place law is **SUPERSEDED** — see [`FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md`](./FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md).

---

## Stage 0–4 (mandatory order)

```
0. COLLECT             Oddsen dump → inbox/odds_*.txt
        ↓              (if prior settle ≥1 terminal: print Settlement Lessons first)
1. BROAD SCAN          market-scan → board → light → promising queue 8–15
        ↓              (all lines scored; no anti-soft filter; no family demote of queue)
2. DEEP RESEARCH       Exa both-sides on shortlist → evidence/*.json
        ↓
3. SELECTION           ready → recommend (gates + EV + soft bands)
        ↓              hard max 2 market_family · similar-recent + lessons soft demote
        ↓              if large board & <2 picks → EXPANSION (deep next tier)
4. OUTPUT              PLACE_THESE + why/support/risk + near-miss → place-ack
        ↓
   SETTLE / LEARN      results → taxonomy → Settlement Lessons (soft TTL)
                       → print lessons before next Stage 1 (warn if missing/stale)
```

### Automatic desk law (lessons · diversify · archive isolation)

| Rule | Behaviour |
|------|-----------|
| **Settlement Lessons** | After settle with ≥1 terminal: print `outbox/SETTLEMENT_LESSONS.md` + `data/state/settlement_lessons.json` **before** next Stage 1. Missing/stale → **warn**, not hard-stop. Soft `sort_ev` only. |
| **Hard max 2** `market_family` | Portfolio open+slip (coarse family; line not in key). Diversify binds at recommend — not Stage 1 queue demote. |
| **similar-recent + lessons soft** | Visible demotion on notes / near-misses; true EV stays honest. |
| **Archive isolation** | **Never** seed peers from `history/archives/` or `history/rounds/`. Live only: `data/bets.csv` · pending · latest results · current odds · `data/state/*`. |
| **Untouched** | capital_v2 · phase · secure · unit · **10 NOK** · ControlSignals · FEH stays demoted |

Full law: root `AGENTS.md` § Settlement Lessons + diversify + archive isolation · [`SETTLEMENT_LEARNING.md`](./SETTLEMENT_LEARNING.md) · [`DIVERSITY_AND_EXPLORE.md`](./DIVERSITY_AND_EXPLORE.md).

### CLI map

```bash
# Stage 0 — collect (agent dump or user file)
# Stage 1
python run_nt.py research market-scan --odds inbox/odds_….txt
python run_nt.py research board --odds inbox/odds_….txt
python run_nt.py research light --odds inbox/odds_….txt   # if not auto

# Stage 2 — agent Exa + write packs
python run_nt.py research write-pack --match "…" --selection "…" --p-model 0.XX …

# Stage 3
python run_nt.py research ready --odds inbox/odds_….txt
python run_nt.py recommend --odds inbox/odds_….txt

# Stage 4
python run_nt.py place-ack --ids …
```

| Stage | Scope | Output | Can recommend? |
|-------|--------|--------|----------------|
| **Prefilter** | Noise screens + classical prior | discard hopeless; `prior_ev` rank-only | **No** |
| **Light** | ≥70–85% shortlist | pass/fail + notes | **No** |
| **Deep queue** | Engine promise ranking ~8–15 | worklist | **No** until packs |
| **Deep packs** | Honest `p_model` + sources | gradeable | **Yes** |
| **Expand** | Next 5–8 light-pass if &lt;2 picks | more packs | Re-recommend |

Config: `research.tiers` (`deep_target_*`, promo weights, composition **off** under ESR).

**SSOT export:** `data/state/deep_queue.json` (may include `expansion_needed` / `next_tier_keys`).

### Coverage floor + temp_ev_relax

| | **Mechanism A — coverage floor** | **Mechanism B — `temp_ev_relax`** |
|--|----------------------------------|-------------------------------------|
| Role | Research pressure (dynamic target, scaffold, rotation) | Auditable temporary EV soften |
| Softens EV? | **No** | Allowlisted lines only (1–2pp) + stake ×0.80 |
| Place law | Never invents place pass | Never invents `p_model` |

```bash
python scripts/verify_coverage_floor.py --synthetic-large
```

### Market coverage (high-volume matches)

```bash
python run_nt.py research market-scan --odds inbox/current_odds_01.txt
```

| Tier | Contents |
|------|----------|
| T1 | ML, draw, O/U, BTTS, HC, team totals |
| T2 | Player props, goalscorer, player stats |
| T3 | Corners, cards, halves/periods |
| T4 | Specials & SGPs |

`research board` runs market-scan automatically unless `--skip-market-scan`.

### Wrong path (blocked by default)

```bash
python run_nt.py recommend --odds inbox/odds_….txt
# → BLOCKED if zero evidence/p_model on the board
```

Override only for tests/emergency: `--force-mechanical`.

### Right path

```bash
python run_nt.py research board --odds inbox/odds_….txt --write-scaffolds
# deep research queue with Exa → evidence/*.json
python run_nt.py research ready --odds inbox/odds_….txt
python run_nt.py recommend --odds inbox/odds_….txt
# expansion if large board & <2 picks, then re-recommend
```

**Code is law at selection.** Research quality at Stages 1–2 determines whether edges clear.  
**Empty slip after full scan + expansion + no +EV = OK.** Empty slip *instead of* research or expansion = process failure.

---

## Stage 1 — Broad scan (promising shortlist)

**Primary input:** Norsk Tipping Oddsen paste → `inbox/odds_*.txt`

Go through **ALL** lines. Rank **8–15** most promising **without** anti-underdog filters and **without** heavy short-chalk moralization.

| Signal | Direction |
|--------|-----------|
| Rough prior EV | ↑↑ |
| Soft value vs ref (when real soft odds present) | ↑ |
| Natural totals | ↑ |
| Light form/rank notes | mild ↑ |
| Mid-band alone | neutral / mild |
| Bare HC with no signal | **no** family boost |
| Soft dog with no light signal | **neutral** (not guilt, not promo) |

Short favourite @ 1.55 with prior_ev should rank **above** bare soft +HC @ 1.95 with no notes.

**Research and recommend are multi-sport.** Always shortlist across sports on the dump.

```bash
python run_nt.py research checklist --sport football
python run_nt.py research scaffold --match "Bodø/Glimt vs Brann" --selection "Bodø/Glimt to Win"
```

---

## Stage 2 — Deep research (shortlist only)

### Research gates

**Canonical:** [`RESEARCH_GATES.md`](./RESEARCH_GATES.md)

Hard failures → grade F → cannot place. Soft issues → notes / higher bar — **not** stacked volume killers.

| Field | Domestic / late data | High context |
|-------|----------------------|--------------|
| `availability_status` | predicted / stable_guess OK | notes or confirmed |
| `context_risk` | low / medium | **high** |
| `script_lean` | must not conflict | same |

**Hard rejects:** script conflict · base_rate · blank availability on sensitive markets · football high_scoring+Under/BTTS No · tennis retirement+overs · basketball star_rest+player overs.

### Exa / HQ search

Primary tool: Exa. Both sides · form · H2H · rank · natural markets. Feeds packs — **not** FEH hard reject. See [`EXA_RESEARCH_USAGE.md`](./EXA_RESEARCH_USAGE.md).

### Sources (football example)

| Tier | Sources |
|------|---------|
| Core | FBref, Transfermarkt, Sofascore, Flashscore, official/club news |
| Depth | Understat, WhoScored, odds history (soft signal), motivation table |

Per-sport lists: [SOURCES.md](./SOURCES.md).

---

## Stage 3 — Model / edge / selection

### p_model & EV

```
implied = 1 / decimal_odds
p_adj   = clamp(p_model - probability_haircut, 0.01, 0.99)
EV      = p_adj * odds - 1
```

Haircut default **3pp** (High-Volume v2). Do **not** invent `p_model = 1/odds + ε`.

| Odds | ESR stance |
|------|------------|
| **1.40–1.80** | Allowed at Grade B + core + EV; soft demote stake if matchup thin |
| **1.80–2.40** | Fine with real edge — not “preferred band identity” |
| **>2.50** | High-odds path only (strict `>`): higher min EV, stake mult |

Soft underdog HC: place when matchup + EV support; **mixed H2H is not automatic F**.

```bash
python run_nt.py research p-model --odds 1.85 --p 0.58
```

### Evidence packaging

Minimum viable pack:

```json
{
  "match": "Team A vs Team B",
  "selection": "Team A DNB",
  "p_model": 0.62,
  "summary": "…",
  "failure_modes": "…",
  "sources": [
    {"url": "https://…", "takeaway": "…", "kind": "stats"}
  ]
}
```

Scaffold:

```bash
python run_nt.py research write-pack \
  --match "Rosenborg vs Viking" \
  --selection "Over 2.5" \
  --p-model 0.58
```

### Engine validation (`recommend`)

`attach_evidence` → `grade_evidence` (legacy path under ESR) → `odds_confidence` → `build_portfolio`:

- Risk can_bet / remaining cap  
- Min EV (standard vs high-odds **>** threshold)  
- Grade floors  
- Learning soft-blocks and diversification  
- Phase max bets / doubles  
- Empty slip OK **after** expansion check  

FEH place-owning is **off** (`forced_hierarchy.enabled: false`).

### Expansion (Stage 3b)

Large board + &lt;2 picks after primary deep → deep next 5–8 light-pass → re-recommend.  
Empty with `expansion_needed` and next tier unresearched = **process miss**.

---

## Stage 4 — Output, place, settle

### Reasoning format

```markdown
## Reasoning

### 1. Humphries −2.5 @ 1.62 · Grade B · EV +3.1% · stake 12 NOK
- **Why:** Clear ranking + form gap; opponent cold last 3.
- **Support:** ranking delta; last-5 averages; H2H 4–1.
- **Main risk:** single-set variance.

## Near-miss / Rejected
- Smith +2.5 @ 1.85 — form favours other side; EV ~0.4% after haircut.
```

1. Place only what is on `outbox/PLACE_THESE.md` (after user places on NT → `place-ack`).  
2. Settle via results + `nt settle`.  
3. Review with `learn` / `analyze` / taxonomy — **no hard-reject list growth**.  
4. If settle wrote ≥1 terminal: **print Settlement Lessons** before the next research board; missing/stale = warn only. Soft awareness only — never seed peers from `history/archives/` or `history/rounds/`.

---

## research_grade in practice

| Grade | Meaning | Placeable? |
|-------|---------|------------|
| **A** | Full sources + uncertainty when required | Yes; high-odds path may require stronger bar |
| **B** | Default source count + core fields | Yes for standard odds under ESR |
| **C** | Partial | Placeable when `grade_c_placeable` + core reason |
| **F** | Missing pack / hard gate conflict | **No** |

Raise quality; do not re-arm FEH ideology for temporary volume control.

---

## Time budget (practical)

| Slot | Activity |
|------|----------|
| 10–15 min | Parse board, shortlist 8–15 promising |
| 15–40 min | Deep research on shortlist (Exa both-sides) |
| 5 min | Evidence JSON + recommend |
| +expand | If &lt;2 picks on large board — next tier deep |
| 5 min | Place / place-ack |
| After events | Settle + taxonomy |

If you cannot afford Stage 2 for a selection → **skip that line**, not the whole board scan.

---

## Large vs thin boards

| Board | Stage 1 shortlist | Deep | Target bets | Empty slip |
|-------|-------------------|------|-------------|------------|
| **Large** (≥15 matches) | 12–15 | Full queue + expand if &lt;2 | **2–6** | Rare; only after expansion + no +EV |
| **Medium** | 8–12 | Full | 1–4 | Uncommon |
| **Thin** (&lt;8 matches) | All viable | All light-pass | 0–2 | Acceptable if no edge |

---

## Related

| Doc | Role |
|-----|------|
| `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` | ESR philosophy |
| `docs/RESEARCH_GATES.md` | Gate fields |
| `docs/EXA_RESEARCH_USAGE.md` | Exa usage |
| `docs/DESK_SKILLS.md` | Skills |
| `docs/SETTLEMENT_LEARNING.md` | Settlement Lessons v1 |
| `docs/DIVERSITY_AND_EXPLORE.md` | max 2 family · similar-recent · archive isolation |
| Root `AGENTS.md` | Operator law · lessons + diversify + archive isolation |
