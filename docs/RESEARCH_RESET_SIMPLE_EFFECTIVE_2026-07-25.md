# Research Reset — Simple Effective Edge-Seeking Workflow (ESR)

| Field | Value |
|-------|--------|
| **Document title** | Research Reset: Simple Effective Philosophy (Edge-Seeking, Not Gate-Heavy) |
| **PLAN_ID** | `research-reset-simple-effective-2026-07-25` |
| **Date** | 2026-07-25 |
| **Status** | Authoritative philosophy (PR4 docs/skills) |
| **Supersedes (philosophy)** | FEH non-bypassable place law · anti-soft underdog hard reject · empty-slip-as-success culture · preferred-band soft-dog research identity as primary attractor |
| **Does not supersede** | `capital_v2`, phase ladder, secure bucket Variant A, unit sizing, odds collection, settlement ledger plumbing |

**Design source:** Edge-Seeking Research (ESR) Stage 0–4. Related engine/config work: PR1 config kill-switch · PR2 residual engines · PR3 tests · **PR4 this docs/skills rewrite**.

---

## Tagline

**Find the best available edges on the board.** Evidence first; price is a parameter, not a moral judgment.

---

## Core philosophy (ESR)

1. **Evidence and matchup quality come first** — form, H2H, ranking/strength, motivation/rest/injuries, style matchup, natural markets. Soft underdogs are **not** guilty by default.
2. **Lower odds (1.40–1.80) are allowed and often preferred** when research clearly supports them.
3. **Mid-odds (1.80–2.40) are fine** when there is a real edge (not because the price sits in a "preferred" band).
4. **High odds (>2.50)** need stronger justification via the high-odds path only (strict `>` threshold).
5. **The job is to find the best available edges**, not to reject everything that looks imperfect.
6. **Transparent reasoning is required** so the user can trust or correct decisions.
7. **Learning continues**, but must **not** create ever-growing hard reject rules that kill volume and edge.

### Operating maxims

| Maxim | Meaning |
|-------|---------|
| **Curious, not paranoid** | Investigate promising lines; do not pre-convict underdogs or short prices |
| **Honest EV** | Haircut stays; do not invent `p_model` to fill seats |
| **Best edges, not perfect packs** | Incomplete notes → soft downgrade / higher bar, not automatic F (unless missing `p_model` / hard research_gates conflict) |
| **Empty slip is rare** | OK only when board truly has no positive edge after Stage 2–3 **+ expansion** |
| **No price-led identity** | Neither "1.85–2.20 dog = good" nor "1.85–2.20 dog = bad" |

### Tone

Confident but not reckless · curious and edge-seeking · transparent · willing to take a good **1.55–1.80 favourite** when research supports it · willing to take a good mid-odds underdog when the matchup supports it · unwilling to force bets · also unwilling to reject everything.

---

## Stage 0–4 workflow

```
Stage 0  Collect     Oddsen dump → inbox/odds_*.txt
Stage 1  Broad Scan  market-scan → board → light → promising shortlist 8–15
Stage 2  Deep        Exa/HQ both-sides → evidence/*.json + honest p_model
Stage 3  Selection   ready → recommend (positive EV + soft band gates)
Stage 3b Expansion   large board & <2 picks → deep next tier → re-recommend
Stage 4  Output      PLACE_THESE + reasoning + near-misses → place-ack
```

| Stage | CLI / action | Artifacts |
|-------|--------------|-----------|
| **0 Collect** | Dump Oddsen for user timeframe | `inbox/odds_YYYY-MM-DD_*.txt` |
| **1 Broad Scan** | `research market-scan` → `research board` (+ light) | Shortlist, light report, `data/state/deep_queue.json` |
| **2 Deep** | Agent Exa + sport sites → packs | `evidence/*.json` |
| **3 Selection** | `research ready` → `recommend` | Pending ledger, portfolio audit |
| **4 Output** | Present slip | `outbox/PLACE_THESE.md`, `reasoning_chains.jsonl` |

No parallel research engine. Map ESR onto existing CLI.

### Stage 1 — promising shortlist (not anti-soft)

- Scan **ALL** lines; rank **8–15** most promising without anti-underdog guilt and without heavy short-chalk moralization.
- Promise scorer favors **prior_ev / soft value / natural totals / light signal** — not bare mid-band or bare HC family tags.
- Preferred composition quotas **disabled** under ESR (`deep_min_preferred_share: 0`, `deep_max_short_main_share: 1.0`); coverage must **not** re-arm preferred floor.
- Short favourites with structural prior may rank **above** bare soft +HC dogs with no signal.

### Stage 2 — deep research (shortlist only)

Both sides form · H2H (honest polarity; mixed allowed) · rank/strength · motivation/rest/injuries · natural markets · honest `p_model` under **3pp** haircut.

**Pack minimum (placeable, not F):** `p_model` in (0.01, 0.99) · `summary` · `failure_modes` · sources (default **4** under ESR). Soft/recommended: structured H2H/form/rank notes.

### Stage 3 — selection

Target **2–6** quality bets on large boards when honest EV exists. Phase `max_bets` still binds. Singles primary; doubles Phase 2+. Stake = capital_v2 (unchanged).

**Place law under ESR:** legacy grade path (`p_model` + sources + **research_gates** hard conflicts + EV + odds_confidence soft/band floors). FEH place-owning is **off** (`forced_hierarchy.enabled: false`, `shadow_mode: true`).

| Price | ESR stance |
|-------|------------|
| **1.40–1.80** short | Allowed at Grade B + core + EV; thin matchup may soft-demote stake, not auto-reject |
| **1.80–2.40** mid | Fine with real edge — not "preferred band identity" |
| **>2.50** high | High-odds path only (strict `>`): higher min EV, stake mult |

### Stage 3b — expansion (large board)

If large board (≥15 matches) and recommend yields **&lt; 2** picks after full deep of primary queue:

1. Deep next **5–8** light-pass lines by promo score.
2. Re-recommend.
3. Empty slip with unresearched next tier = **process miss**, not success.

### Stage 4 — reasoning format

For each pick:

- **Why** this bet  
- **Strongest support**  
- **Main risk**  

Near-misses short (why not / what would change).

```markdown
## Reasoning

### 1. Humphries −2.5 @ 1.62 · Grade B · EV +3.1% · stake 12 NOK
- **Why:** Clear ranking + form gap; Price cold last 3; H2H favours Humphries on this format.
- **Support:** PDC ranking delta; last-5 avg 98 vs 91; H2H 4–1 recent.
- **Main risk:** Single-set variance / checkout swing.

## Near-miss / Rejected
- Smith +2.5 @ 1.85 — form/rank favour Price; H2H mixed; EV after haircut ~0.4% (below floor).
```

---

## What is removed vs kept

### Disable / demote

| Item | ESR role |
|------|----------|
| FEH place ownership | **Off** — shadow / soft audit only |
| Anti-soft hard reject | **Off** — soft dogs judged on matchup + EV |
| Preferred ≥55% / short-main ≤25% | **Off** — pure promo ranking |
| Empty slip as success culture | Empty only after full scan + expansion + no +EV |
| Mid-band identity as place quality | Neutral — edge quality owns place |

### Keep

| Item | Notes |
|------|-------|
| capital_v2 / phase / secure / unit | **Hard constraint — do not change** |
| Odds collection | Unchanged |
| research_gates hard nonsense | Script conflict · base-rate · availability on sensitive markets |
| Haircut 3pp + EV floors | Keep |
| Coverage floor (research pressure) | Keep; no composition re-arm |
| Exa deep research | Keep; feeds packs/reasoning, not FEH hard reject |
| 10 NOK test cap first 10 | Retagged `TEST_CAP:esr_v1` (not FEH-branded) |
| Settlement + soft learning mults | No hard-reject list growth |

---

## Learning constraint

**Allowed:** stake_mult / ev_boost clamps; process_gate temp raises; taxonomy + learning_weight.  
**Forbidden:** auto hard reject config; re-enable anti_soft from settlement; block lists from single-loss anecdotes.

---

## Success criteria (process)

| Metric | Target |
|--------|--------|
| Picks per large-board run | **2–6** regularly when EV exists |
| Empty slip on large boards | Only after expansion + no +EV |
| Short-price (1.40–1.80) share | Material when form/rank supports |
| Soft-dog hard auto-reject | ~0 |
| Capital math | Unchanged |

---

## Related

| Doc | Role |
|-----|------|
| [`RESEARCH_WORKFLOW.md`](./RESEARCH_WORKFLOW.md) | Stage map + CLI |
| [`RESEARCH_GATES.md`](./RESEARCH_GATES.md) | Soft/hard gate fields |
| [`EXA_RESEARCH_USAGE.md`](./EXA_RESEARCH_USAGE.md) | Exa feeds research |
| [`DESK_SKILLS.md`](./DESK_SKILLS.md) | `/daily-run` and siblings |
| [`FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md`](./FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md) | **SUPERSEDED** FEH design (historical) |
| Root `AGENTS.md` | Operator law |
