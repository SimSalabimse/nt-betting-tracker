# Research & Bet-Finding Workflow (Best-in-Class)

## Agent trigger (every odds dump)

When the user provides a **new or updated odds file** in `inbox/`, the agent **must** run the full research → recommend path (see root `AGENTS.md`). Defaults: **live recommend** (logs Pending when picks exist); **dry-run only if the user asks**; **do not re-advise already Pending tickets**; honest evidence only (no mechanical p_model unless explicitly ordered).

**Forced Evidence Hierarchy (FEH)** is **NON-BYPASSABLE** place law: side first, then price; anti-soft underdog; prefer empty slip over weak soft dogs. Deep-queue **preferred band (1.85–2.60)** is **research-rank only** — not place quality or inherent soft-dog attractiveness. Temporary **10 NOK** stake cap applies to the first 10 FEH-tagged placed bets. Design: [`FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md`](./FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md).

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
4. DEEP RESEARCH       only light-pass deep queue
        ↓              evidence/*.json + honest p_model (side-first)
5. READY CHECK         nt research ready --odds …
        ↓
6. VALIDATION          FEH + grade_evidence + portfolio + risk/phase
        ↓              (FEH F cannot be bypassed by promo/explore/temp_ev_relax)
7. DECISION            recommend → PLACE_THESE.md  (Deep only; empty slip OK)
        ↓
8. SETTLEMENT          results → settle → learning
        ↓
9. REVIEW              nt analyze / nt learn
```

### Tiered research (Light vs Deep)

| | **Light (Stage 1)** | **Deep (Stage 2)** |
|--|---------------------|--------------------|
| Scope | Most of shortlist (target 85%) | Promote queue (~8–12 lines) |
| Content | script lean, base-rate flag, odds/EV bar, strength/weakness notes | Full evidence pack + p_model + gates |
| Time | Fast / structured | Web research, quality bar |
| Recommend? | **No** | **Yes** (only these) |

```bash
python run_nt.py research board --odds inbox/current_odds_01.txt
python run_nt.py research light --odds inbox/current_odds_01.txt
# … deep packs for deep_queue …
python run_nt.py recommend --odds inbox/current_odds_01.txt
```

Config: `research.tiers` in `config.yaml` (`light_coverage_target`, `min_light_per_sport`, `deep_target_n`, …).

**SSOT export:** board/light writes engine composition + queue lines to **`data/state/deep_queue.json`** (`nt/deep_queue_state.py`) for Lumina preferred/short-main bars (D17).

**Preferred / mid band = research-rank only.** Composition targets (≥55% preferred, promo boosts for 1.85–2.60, handicaps, longer ML) decide *what gets deep packs* — they do **not** seal place quality. Soft underdog at 1.85–2.20 is **not** inherently attractive; FEH anti-soft + structured H2H own place.

### Coverage floor + temp_ev_relax safety net

Two permanent mechanisms keep high-volume boards from starving mid-price research **without** inventing `p_model` or casually softening EV.

| | **Mechanism A — coverage floor** | **Mechanism B — `temp_ev_relax`** |
|--|----------------------------------|-------------------------------------|
| Role | Quality-preserving research pressure | Auditable temporary EV soften (safety net) |
| Config | `research.coverage_floor` + `research.tiers.deep_target_*` | `learning.control_signals.temp_ev_relax` |
| Code | `dynamic_deep_target_n`, top-promo scaffold (~20%), sport rotation | `maybe_emit_temp_ev_relax*` → portfolio allowlist |
| Softens EV? | **No** | Yes, **only** on allowlisted lines (1–2pp) + stake ×0.80 · TTL 24h |
| Blocked when | Composition / short-main rules | `process_gate_raise` active on candidate; high-odds / grade C by default |
| vs FEH | Never invents place pass | **Never** overrides FEH F / anti-soft |

**Operator surface:** `python run_nt.py status` / `data/state/status.md` → **Coverage floor** section shows `deep_target_n_effective`, scaffold/rotation summary, and active `temp_ev_relax` (ΔEV, stake mult, expires, line_keys count). Soft-fails if light/signals files are missing.

**Verify (no live odds required):**

```bash
python scripts/verify_coverage_floor.py --synthetic-large
```

Full agent mandate: root `AGENTS.md` → **Coverage floor + temp_ev_relax**.


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

**Code is law at stages 6–7.** Research quality at 1–4 determines whether anything clears the bar.  
**Empty slip after research = success.** Empty slip *instead of* research = process failure (now refused).

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
```

Haircut (default 5%) absorbs NT margin + optimism bias.

### Guidelines

| Odds band | Typical p_model discipline |
|-----------|----------------------------|
| <1.50 | Need strong structural edge; small EV still needs volume control; FEH / short-odds bar high |
| 1.50–2.60 | **Research-rank** mid band — honest packs when queued; place only if **FEH + EV** clear (underdog HC ~1.70–2.20 is anti-soft territory, not a default long) |
| 2.50+ | Grade **A**, higher min EV, reduced stake mult (existing high-odds rules) |

**Do not** invent p_model = 1/odds + 0.05 to force EV. **Do not** treat mid-band underdog price alone as edge. The learning loop and your P/L will punish you.

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
  "summary": "…",
  "failure_modes": "…",
  "sources": [
    {"url": "https://…", "takeaway": "…", "kind": "stats"}
  ]
}
```

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

- Risk can_bet / remaining cap
- Min EV (standard vs high-odds)
- Grade floors (B+ standard; A high-odds)
- Learning soft-blocks and diversification
- Phase max bets / doubles policy
- Empty slip OK

---

## Stage 6–8 — Decision, settle, review

1. Place only what is on `outbox/PLACE_THESE.md`.
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
| **A** | Full sources (grade_A or high-odds threshold), p_model, summary, failure_modes | Yes; required for odds ≥ high_odds_threshold |
| **B** | Default source count met + core fields | Yes for standard odds |
| **C** | Partial credit | **No** (portfolio rejects) |
| **F** | Missing pack / critical fields | **No** |

Raise quality, don’t lower the bar in config for temporary volume.

---

## Time budget (practical)

| Slot | Activity |
|------|----------|
| 10–15 min | Parse board, shortlist 3–8 candidates |
| 15–40 min | Deep research on shortlist only |
| 5 min | Evidence JSON + recommend dry-run |
| 5 min | Place / archive slip |
| After events | Settle + one-line edge note if process lesson |

If you cannot afford Stage 2 for a selection → **skip it**.
