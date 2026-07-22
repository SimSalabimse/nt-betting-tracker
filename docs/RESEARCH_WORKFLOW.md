# Research & Bet-Finding Workflow (Best-in-Class)

## Agent trigger (every odds dump)

When the user provides a **new or updated odds file** in `inbox/`, the agent **must** run the full research → recommend path (see root `AGENTS.md`). Defaults: **live recommend** (logs Pending when picks exist); **dry-run only if the user asks**; **do not re-advise already Pending tickets**; honest evidence only (**never invent `p_model`** unless explicitly ordered).

## End-to-end stages (mandatory order)

```
0. SETTLE              results first if any pending
        ↓
1. MARKET COVERAGE     nt research market-scan --odds …
        ↓
2. BOARD SHORTLIST     nt research board --odds …
        ↓              (auto Stage-1 Light Research)
3. LIGHT RESEARCH      ≥70–85% shortlist · sport minimums
        ↓              outbox/light_research/*.md
4. DEEP RESEARCH       clearability deep queue (~8 target)
        ↓              evidence/*.json + honest p_model + odds snapshot
5. SECOND-PASS         if packs present, mid covered, zero EV clears
        ↓              research second-pass → re-deep new queue lines
6. READY CHECK         nt research ready --odds …
        ↓
7. VALIDATION          grade_evidence + portfolio + risk/phase + soft pack
        ↓
8. DECISION            recommend → PLACE_THESE.md  (Deep only; place-capable)
        ↓
9. SETTLEMENT          results → settle → learning
        ↓
10. REVIEW             nt analyze / nt learn
```

### Tiered research (Light vs Deep)

| | **Light (Stage 1)** | **Deep (Stage 2)** |
|--|---------------------|--------------------|
| Scope | Most of shortlist (target 85%) | Clearability promote queue (**~8** target / max 12) |
| Content | script lean, base-rate flag, odds/EV bar, strength/weakness notes | Full evidence pack + honest p_model + dual-write odds snapshot + gates |
| Time | Fast / structured | Web research, quality bar |
| Recommend? | **No** | **Yes** (only these) |

```bash
python run_nt.py research board --odds inbox/current_odds_01.txt
python run_nt.py research light --odds inbox/current_odds_01.txt
# … deep packs for deep_queue …
# if Coverage ok / mid covered but recommend empty (all EV fail):
python run_nt.py research second-pass --odds inbox/current_odds_01.txt
# … re-deep new queue lines with honest packs …
python run_nt.py recommend --odds inbox/current_odds_01.txt
```

Config: `research.tiers` in `config.yaml` (`light_coverage_target`, `min_light_per_sport`, `deep_target_n: 8`, `short_chalk_odds: 1.70`, clearability + second-pass knobs, …).

**SSOT export:** board/light writes engine composition + queue lines to **`data/state/deep_queue.json`** (`nt/deep_queue_state.py`) for Lumina preferred/short-main bars (D17). Refresh mode after second-pass sets `mode=refresh` / `second_pass_*` flags used by `starvation_kind`.

### HV v3 — clearability, second-pass, place-capable runs

| Concept | Law |
|---------|-----|
| **Clearability ranking** | Relative prior + batch rank + demote coin-flip; **research-rank only** — never auto-fills `p_model` or softens haircut/min-EV |
| **Short chalk** | Odds &lt; **1.70** heavily demoted / Stage1 drop (config `short_chalk_odds`) |
| **Deep target** | **`deep_target_n: 8`** (max 12); preferred ≥55% / short-main ≤25% |
| **Second-pass** | `python run_nt.py research second-pass --odds <file>` — EV-fail refresh + dump alt inject (cap 12). Then agent re-deeps; engine does not invent edge |
| **`starvation_kind`** | `clearability_miss` = deep present, mid covered, zero raw EV clears, second-pass not done → incomplete. `honest_no_edge` = second-pass done, still zero → empty slip OK |
| **Odds snapshot** | Packs dual-write `odds_at_research` + `decimal_odds_ref` + `researched_at`; place **fail-closed** if missing/inferred |
| **Soft pack** | Under phase **1A** (and exploration flag): prefer ~**3 × unit** seats when ≥3 clear under remaining risk (e.g. remaining **40** → 12+12+12), not two fat seats |
| **Place-capable vs research-only** | **Research runs** (board/light/second-pass/packs) may run **3–4×/day**. Under Phase **1A** with remaining ~**40**, after one successful ~3×unit slip, room is spent → further same-day recommends are **research-only / empty** until settle or abandon. Ops expectation: **≈1 place-capable recommend/day** under 1A remaining 40 |
| **Ship KPI** | Funnel (clearable share, n_raw_ev_pass, second-pass ran) + honest empty when no edge — **not** “must place 3 every run” |


### Market Coverage Agent (high-volume matches)

For matches with **many lines** (default ≥40; internationals often 100+):

```bash
python run_nt.py research market-scan --odds inbox/current_odds_01.txt
python run_nt.py research market-scan --odds inbox/current_odds_01.txt --match "Frankrike"
```

**Tiers**

| Tier | Contents |
|------|----------|
| T1 | ML, draw, O/U, BTTS, HC, team totals |
| T2 | Player props, goalscorer, player stats |
| T3 | Corners, cards, halves/periods |
| T4 | Specials & SGPs |

Output: `outbox/market_scans/*.md` + coverage confidence %.  
`research board` runs this automatically and injects flagged interesting lines into the shortlist.


### Wrong path (blocked by default)

```bash
python run_nt.py recommend --odds inbox/odds_….txt
# → BLOCKED if zero evidence/p_model on the board
```

Override only for tests/emergency: `--force-mechanical`.

### Right path

```bash
python run_nt.py research board --odds inbox/odds_….txt --write-scaffolds
# optional: football sim for O/U / BTTS / 1X2 p_model suggestions
python run_nt.py simulate --input inbox/sim_match_template.yaml --selection "BTTS Ja"
# research shortlist → fill evidence packs (sim is not enough alone)
python run_nt.py research ready --odds inbox/odds_….txt
python run_nt.py recommend --odds inbox/odds_….txt --dry-run
python run_nt.py recommend --odds inbox/odds_….txt
# after settle:
python run_nt.py calibrate report
```

**Code is law at stages 7–8.** Research quality at 1–5 determines whether anything clears the bar.  
**Empty slip after honest deep research + second-pass** (`honest_no_edge`) **= success.**  
**Empty with `clearability_miss`** (no second-pass yet) = process incomplete — run second-pass.  
**Empty slip *instead of* research** = process failure (now refused).

---

## Stage 1 — Idea generation

**Primary input:** Norsk Tipping Oddsen paste → `inbox/odds_*.txt`

Optional filters (discipline aids, not bans):

| Priority | Focus |
|----------|--------|
| High | Any sport on the **actual NT board** you can research well (football, tennis, NBA/WNBA, etc.) |
| Medium | Secondary markets on those same events (totals, handicaps) with data |
| Low | Ultra-thin markets without lineups/stats; do not default to “football only” |

**Important:** Football-focused *simulation* (`nt simulate`) is a tool for scorelines.  
**Research and recommend are multi-sport.** Always shortlist across sports on the dump.

**CLI helpers**

```bash
python run_nt.py research checklist --sport football
python run_nt.py research scaffold --match "Bodø/Glimt vs Brann" --selection "Bodø/Glimt to Win"
```

Empty board after research → **empty slip**. That is success.

---

## Stage 2 — Data gathering (Eliteserien / football)

### Research gates (engine) — multi-sport, balanced for 12h boards

**Canonical doc:** [`docs/RESEARCH_GATES.md`](RESEARCH_GATES.md)

We research many events **hours before** official availability (PL ~1h; small leagues rarely publish early). Confirmed is ideal, not mandatory.

Gates apply to **football, tennis, basketball**, plus a **default** profile (hockey, handball, darts, esports…). Hard failures → grade F → cannot place.

| Field | Domestic / late data | High context (WC, intl, B2B, bronze) |
|-------|----------------------|--------------------------------------|
| `availability_status` | `predicted` / `stable_guess` OK | Predicted + substantive notes, or confirmed |
| Availability research | Injuries / load / fitness | Required + who replaces whom / minutes |
| `context_risk` | `low` / `medium` | **`high`** |
| `script_lean` | Must not conflict with selection | Same (often open/high-scoring for bronze) |

**Hard rejects:** script conflict · base_rate conflict · blank availability on sensitive markets · football high_scoring+Under/BTTS No · tennis retirement+overs · basketball star_rest+player overs.

Config: `research.gates` in `config.yaml` (legacy flat keys still aliased).

### Tier 1 (required for grade B+)

| Source | Use for |
|--------|---------|
| **FBref** | xG, form, shooting, historical tables |
| **Transfermarkt** | injuries, suspensions, squad value, absences |
| **Sofascore** | form, ratings, predicted **and** confirmed lineups when live |
| **Flashscore** | H2H, live context, kickoff, cards streaks |
| **Official / NFF / club** | competition context, weather postponements |
| **Team news (BBC/Sky/L'Équipe etc.)** | absences, late XI leaks, rotation, farewell starts |

### Tier 2 (grade A / high-odds)

| Source | Use for |
|--------|---------|
| **Understat** (where covered) | shot quality / xG maps |
| **WhoScored** | event trends, referee-adjacent patterns |
| **OddsPortal / odds history** | line movement (soft signal only) |
| **League table depth** | motivation (relegation, title, mid-table dead rubber) |

### Efficient use (no illegal scraping required)

1. Keep a browser bookmark folder: `NT Research / Eliteserien`, `NT Research / Injuries`, etc.
2. Fill the evidence template fields as you open each tab (URL + one-line takeaway).
3. Prefer **manual** confirmation of lineups within ~1–2h of kickoff for grade A.
4. Automation helpers (`scripts/`, `nt research`) only produce **templates and checklists** — you still own takeaways.

See [SOURCES.md](./SOURCES.md) for per-sport lists.

---

## Stage 3 — Model / edge estimation

### p_model

Your subjective (or model) probability that the selection wins, **before** haircut.

```
implied = 1 / decimal_odds
p_adj   = clamp(p_model - probability_haircut, 0.01, 0.99)
EV      = p_adj * odds - 1
p_needed(min_ev) = (1 + min_ev) / odds + haircut
```

Haircut (live **3pp** / `probability_haircut: 0.03`) absorbs NT margin + optimism bias. Stage2 classical / **relative prior is rank-only** for deep-queue ordering — **never** paste prior as place `p_model`.

### Guidelines

| Odds band | Typical p_model discipline |
|-----------|----------------------------|
| <1.50 | Need strong structural edge; small EV still needs volume control |
| 1.50–2.20 | Sweet spot for most singles if research is real |
| 2.50+ | Grade **A**, higher min EV, reduced stake mult |

**Do not** invent p_model = 1/odds + 0.05 (or any mechanical lift) to force EV. Claim edge only with named quantitative factors. If you cannot justify p ≥ p_needed, write honest p (optional `expected_reject: true`). The learning loop and your P/L will punish overclaim.

Optional: import model probs via odds CSV column `p_model` or evidence JSON.

```bash
python run_nt.py research p-model --odds 1.85 --p 0.58
# shows implied, haircut EV, min-EV gate status
```

---

## Stage 4 — Evidence packaging

Minimum viable pack (`evidence/example.json`):

```json
{
  "match": "Team A vs Team B",
  "selection": "Team A DNB",
  "p_model": 0.62,
  "odds_at_research": 1.95,
  "decimal_odds_ref": 1.95,
  "researched_at": "2026-07-22T12:00:00+00:00",
  "summary": "…",
  "failure_modes": "…",
  "sources": [
    {"url": "https://…", "takeaway": "…", "kind": "stats"}
  ]
}
```

**Fail-closed place:** missing or inferred odds snapshot rejects place (`missing_odds_snapshot` / `odds_snapshot_inferred`). Rewrite the pack with real dual-write — do not stamp board odds as research baseline.

### Optional v5 fields (additive; grader ignores unknowns safely)

| Field | Purpose |
|-------|---------|
| `requested_grade` | `"A"` raises source threshold |
| `league` | e.g. Eliteserien |
| `kickoff` | ISO datetime |
| `confidence` | 1–5 research confidence |
| `checklist` | completed research checklist keys |
| `correlation_tags` | for combo risk (`same_match`, `same_league_round`) |
| `model_name` / `model_version` | if p_model from external model |
| `sources[].kind` | stats / injury / lineup / news / odds / official |
| `sources[].accessed_at` | ISO date of research |

Scaffold:

```bash
python run_nt.py research scaffold \
  --match "Rosenborg vs Viking" \
  --selection "Over 2.5" \
  --p-model 0.58 \
  --league Eliteserien
```

---

## Stage 5 — Validation (engine)

`nt recommend` → `attach_evidence` → `grade_evidence` → `build_portfolio`:

- Risk can_bet / remaining cap (min'd with 20% equity run stake)
- Min EV (standard vs high-odds; regime floor under Exploration/Survival)
- Grade floors (B+ standard; A high-odds; Grade C placeable with core reason)
- Fail-closed odds snapshot integrity
- Soft pack under 1A / exploration when ≥3 clear (target_bets_per_run ≈ 3 × unit)
- Learning soft-blocks and diversification
- Phase max bets / doubles policy
- Empty slip OK (`honest_no_edge` after second-pass; not before)

---

## Stage 6–8 — Decision, settle, review

1. Place only what is on `outbox/PLACE_THESE.md` from a **place-capable** run (room remaining).
2. Settle via `inbox/results_*.yaml` + `nt settle`.
3. Review with:

```bash
python run_nt.py learn
python run_nt.py analyze
python run_nt.py edges --last 20
```

Optional agent (never auto-places):

```bash
python run_nt.py agent ask "What patterns hurt ROI in the last 40 settled bets?"
```

---

## research_grade in practice

| Grade | Meaning | Placeable? |
|-------|---------|------------|
| **A** | Full sources (grade_A or high-odds threshold), p_model, summary, failure_modes, uncertainty for Grade A policy | Yes; required for odds ≥ high_odds_threshold |
| **B** | Default source count met + core fields | Yes for standard odds |
| **C** | Partial credit + core reason + source floor (HV) | **Yes** when policy allows (not free EV) |
| **F** | Missing pack / critical fields / snapshot fail | **No** |

Raise quality, don’t lower the bar in config for temporary volume.

---

## Time budget (practical)

| Slot | Activity |
|------|----------|
| 10–15 min | Parse board, shortlist / clearability queue (~8) |
| 15–40 min | Deep research on deep_queue only |
| 10–20 min | Second-pass + re-deep if first recommend empty / clearability_miss |
| 5 min | Evidence JSON dual-write + ready + recommend |
| 5 min | Place / place-ack / archive slip (if place-capable room) |
| After events | Settle + one-line edge note if process lesson |

Same-day **research-only** passes after a full place-capable slip: delta odds, second-pass, pack refresh — not a second 3-bet book under 1A remaining 40.

If you cannot afford deep research for a selection → **skip it**.
