---
name: deep-research
description: >
  ESR Stage 2 deep research on the final primary worklist only (usually 8–15
  candidates, hard cap 15). Match Intelligence Cards (MIC) are the primary
  structured evidence input; optional Exa / free HQ web both-sides + optional
  Firecrawl fill thin gaps → structured evidence packs with form-continuity /
  opposite-side / ranking / data_coverage / evidence_quality via atomic pack
  writer (scripts/write_deep_research_pack.py). Use when user runs
  /deep-research, says "deep research shortlist", "Stage 2 packs", "research
  primary worklist", "MIC packs for candidates", or when /daily-run reaches
  Stage 2. Never on full odds board (refuse full-board / whole dump deep).
  Not for place-ack, multi-agent scan-only, or bare research write-pack finals.
metadata:
  short-description: "Stage 2 primary-worklist packs — MIC primary + optional Exa via atomic helper"
---

# /deep-research — Primary-worklist packs only (MIC primary)

> **Repo mirror:** keep `~/.grok/skills/deep-research/SKILL.md` in sync with
> `docs/skills_mirror_deep-research.md`. Desk pointer: `docs/DESK_SKILLS.md`.
> Design: `docs/DEEP_RESEARCH_SKILL_ESR_2026-07-26.md`. Exa: `docs/EXA_RESEARCH_USAGE.md`.
> Form continuity: `docs/FORM_CONTINUITY_AND_ANTI_FLIP_HARDENING_2026-07-26.md`.
> Daily order: `docs/skills_mirror_daily-run.md` (Stage 2 after 1x MIC).

Real-money capital desk. **Engines in `nt/` are law.** Never invent `p_model`.
Never bare `research write-pack` as the **final** pack step — always
`python scripts/write_deep_research_pack.py`.

## 0) Bootstrap (mandatory)

1. `Read` repo root **`AGENTS.md`** — ESR Stage 0–4 + form continuity + Stage 2 scope law + MIC.
2. Confirm CWD is **nt-betting-tracker** root (`run_nt.py` present).
3. Confirm input list is **primary worklist ≤15** only:
   - `outbox/MULTI_AGENT_SHORTLIST.md` → `## Primary worklist` (shortlist ∪ coverage_critical), **or**
   - Explicit named lines that are on that worklist / coverage_critical / Stage 3.4 expansion, **or**
   - Engine `deep_queue` head cap 15 **only** on multi-agent all-fail fallback.
4. **REFUSE** full-board / dump-wide deep (“deep the whole odds file”, 40+ unfiltered board rows). Stop and ask for primary worklist.
5. Force real tools: MIC load, optional Exa/HQ web, optional Firecrawl, CLI, helper script. Do not simulate packs.
6. **MIC readiness (primary):** for each worklist match, prefer `outbox/match_intel/{match_key}.json`. Multi-sport free pipeline covers `v1_sports` (football, tennis, esports, snooker, darts, baseball) when `--allow-network`. If missing and daily-run Stage 1x hard top-up was skipped, run:

```powershell
python run_nt.py research match-intel --match "Team A vs Team B" --sport football --allow-network
# or worklist-sized batch (live guidance ≤15 matches):
# python run_nt.py research match-intel --odds <odds_file> --allow-network
```

Until `require_for_deep: true` (only after exit criteria E1–E5 — **stays false** in skills/ops polish; **v1_sports only** when true): missing MIC → soft note `mic:missing` and continue with free/HQ research. When require_for_deep is true for `sport ∈ v1_sports`: missing/D/F MIC → **do not** deep that seat.

Read card `extraction.process_miss` / `process_miss_reason` when present: fetch/ops failures grade **F** with `process_miss: true` (e.g. `fetch_failed`, `playwright_not_installed`); true empty board → `thin_public` + `process_miss: false`. **Never invent** form/H2H to escape F.

7. **Live anchor recipe** (working-tree ledger only — never archives):

```powershell
python run_nt.py status
# Live bets only — never history/archives or history/rounds
# Prefer latest terminal Wins with handicap selections for team-pair names on worklist
```

Practical steps:

1. Read `data/state/status.md` for open tickets context.
2. From live `data/bets.csv` (or CLI that prints live rows only): find **Win** or open heavy-fav **minus HC** on same team-pair as any worklist HC dog.
3. If found within ~48h narrative: set `form_continuity.flip_risk_suspected=true` and `prior_anchor_note` to e.g. `"Live ledger bet_id=… selection=Brewers -1.5 result=Win"`.
4. If none: `flip_risk_suspected=false`, `prior_anchor_note=""`.
5. Engine still owns window/soft-reject; skill note is research awareness only.
6. **Forbidden:** `history/archives/`, `history/rounds/`, git stash copies of `data/*`.

## 1) Resolve worklist (fail-closed)

| Rule | Detail |
|------|--------|
| Source | Primary worklist from multi-agent merge, or engine fallback head |
| Odds | Drop any line not on current odds dump |
| Cap | Hard **15**; log dropped if truncated |
| coverage_critical | Never silently dropped |
| Empty | Empty without fallback → stop Stage 2 |
| Full-board request | **Refuse** — process stop |
| MIC | Load card per match when present; note grade/score in pack coverage |

## 2) Budget clock

| Bound | Value |
|-------|--------|
| Wall-clock **per line** | ≤ **4 min** standard · ≤ 2.5 min tight · ≤ 3 min expansion |
| Exa searches | **optional** 0–6 standard · 0–4 tight (prefer 0 when MIC grade ≥ B and free pages filled form/H2H) |
| Free / Firecrawl scrape | **0–2** pages (MIC multi-sport free pipeline already used free sources; top-up only). Firecrawl needs `FIRECRAWL_API_KEY`; Playwright SPA: `pip install playwright; python -m playwright install chromium` |
| Stage 2 batch | **≤ 45 min** hard for primary pass (soft target ≤ 35 min if parallel) |
| Stage 3.4 expansion | Separate ≤ 20 min; does not steal primary 45 |

**Degrade** when `remaining_candidates × 2.5 min > remaining_batch_budget`:

1. Switch remaining to **tight** profile.
2. Prefer multi-agent / coverage_critical first; demote pure top-up.
3. Tail: honest partial research **or** verdict **Weak** with `process_timeout:` / `budget_degrade:` in rationale — still fill opposite one_liner if any research ran; never invent p_model for Strong.
4. Do not skip write entirely without a batch row.
5. Parallel subagents preferred when host supports them (return packed ESR JSON only).

## 3) For each candidate (budget-capped)

### Research method (MIC primary)

1. Load candidate + opposite selection label.
2. **Load MIC** `outbox/match_intel/{match_key}.json` when present — use form, H2H, standings, injuries, competition, coverage.grade/score as **primary structured facts**. Note `process_miss` / `process_miss_reason` in `data_coverage.evidence_quality_notes` when hard_veto-relevant (F/D or thin).
3. Live anchor check (status + live bets).
4. **Optional Exa / HQ web** both sides when MIC thin (grade ≤ C, missing critical fields, `process_miss: true` after failed free fetch, or non-v1 sport skeleton): favourite **and** underdog / home **and** away — form, H2H, ranking, injuries/lineups.
5. Optional Firecrawl scrape 0–2 HQ pages when snippets thin (never for inventing MIC body retroactively without card write; never claim free MIC success when card is process_miss F).
6. Assemble **8 sections** + honest `p_model` + full ESR payload + **`data_coverage` / `evidence_quality`**.
7. **Atomic write only:**

```powershell
python scripts/write_deep_research_pack.py --payload outbox/deep_research/<slug>.payload.json --odds-ref <dec>
# stdout: {"ok": true, "path": "evidence/....json", "esr_keys_present": true, ...}
```

8. Optional human MD: `outbox/deep_research/<slug>.md` — **required** for Strong/Acceptable and any `flip_risk_suspected`.
9. Optional: `python run_nt.py research critique evidence/<file>.json --odds …`
10. Append `outbox/DEEP_RESEARCH_BATCH.md` row.

**Forbidden final step:** `python run_nt.py research write-pack …` alone. Re-research = edit payload → re-run helper. Never bare write-pack after helper (wipes ESR keys).

### MIC → pack mapping (primary)

| MIC field | Pack use |
|-----------|----------|
| `coverage.grade` / `score` | `data_coverage.mic_grade` · justify evidence_quality |
| `recent_form` / standings | `deep_research.recent_form` · ranking |
| `h2h` | `deep_research.h2h` |
| injuries / lineup notes | availability / lineup fields (gate-safe enums) |
| `sources[]` | pack sources takeaways (cite free publishers) |
| missing card | `data_coverage` notes `mic:missing`; evidence_quality thin/insufficient |
| `extraction.process_miss` / `process_miss_reason` | notes for Quality (e.g. `process_miss_reason=fetch_failed` vs `thin_public`); does **not** change grade math (KD-16) |

### data_coverage / evidence_quality (required on serious packs)

Prefer helper shape (`nt.research_quality_gate.build_data_coverage` when available):

```json
{
  "data_coverage": {
    "mic_grade": "B",
    "both_sides": true,
    "form": true,
    "h2h": true,
    "rank_or_table": true,
    "injuries_checked": false,
    "evidence_quality": "adequate",
    "evidence_quality_notes": "MIC B; injuries optional thin; form+table solid"
  }
}
```

| evidence_quality | When |
|------------------|------|
| **strong** | MIC A + both sides + form |
| **adequate** | MIC B + both sides |
| **thin** | MIC C or soft gaps |
| **insufficient** | MIC D/F, no both sides, or Quality hard_veto reasons likely |

Quality Challenger (Stage 3.1c) may hard_veto on closed-enum reasons including `evidence_quality_insufficient` / MIC grades — **CLI** applies mutation; this skill only writes honest coverage fields. When packs feed Quality, note **`process_miss_reason`** on grade F/D process misses (vs `thin_public`) so hard_veto notes can distinguish ops gap from empty public board.

### Eight research sections (map into `deep_research` + gates)

| # | Section | Pack home |
|---|---------|-----------|
| 1 | Match context | `deep_research.match_context` (+ MIC competition) |
| 2 | Recent form (both sides) | `deep_research.recent_form` + form_continuity recent fields |
| 3 | H2H | `deep_research.h2h` |
| 4 | Ranking / strength gap | `deep_research.ranking_strength_gap` + `feh_checklist` + `signals.ranking_seed` |
| 5 | Natural markets | `deep_research.natural_markets` |
| 6 | Key risks | `deep_research.key_risks` + `failure_modes` |
| 7 | Opposite-side check | `opposite_side_check` (**mandatory** evaluated + one_liner ≥20) |
| 8 | Final research verdict | `deep_research.verdict` (Strong / Acceptable / Weak / Reject) |

Also always: `summary`, sources with **non-empty takeaways** (≥4, ~≥8 chars each), honest `p_model`, prefer `data_coverage`.

### Form-continuity mapping (`build_evidence_snapshot`)

```text
pack.summary                          → snap.summary[:400]
pack.form_continuity.why_flip         → snap.why_flip[:300]   # primary
pack.opposite_side_check.one_liner    → snap.why_flip fallback  # must be weak-phrase clean
pack.feh_checklist.why_this_side…     → snap.why_flip fallback
pack.availability_status / notes      → snap.injury_or_lineup_break
pack.lineup_status / lineup_notes     → same (preferred S1: lineup_status changed + injury in notes)
pack.feh_checklist.higher_ranked_side → snap.higher_ranked_side
pack.feh_checklist.ranking_confidence → snap.ranking_confidence
pack.signals.ranking_seed             → snap.signals_rank_primary
pack.opposite_side_check              → snap.opposite_side_check
```

When flip risk: `form_continuity.checked=true`, structural `why_flip` ≥20 chars, claim only signals you actually document (S1/S2/S3/S4).

### Opposite side — mandatory

Every pack: `opposite_side_check.evaluated=true`, `opposite_selection` set, `one_liner` ≥20 chars explaining why not the other side. Process miss if missing (PLACE_THESE audit flag).

### Weak-phrase ban (even in negation)

**Never** place weak-phrase substrings in `form_continuity.why_flip`, `opposite_side_check.one_liner` / `why_not_opposite`, `summary`, or `feh_checklist.why_this_side_not_opposite` — **even when negating** (“not because X is easier”). If `why_flip` is missing, snapshot falls back to `one_liner`; weak blob still fails S2.

Weak list includes (non-exhaustive): easier line, +2.5 is easier, softer number, public on favourite/favorite/fav, public chalk, sharp lean, sharp other way, steam other side, fade the favourite/favorite, bounce back, enklere linje, mykere linje, publikum på favoritt, fade favoritt, tilbakefall.

**Rewrite:** say what **is** true (“SP downgrade is material; rest advantage favors dog RL”) — do not name the weak idiom.

Helper **warns** on weak phrases; skill **must** fix before shipping Strong/Acceptable on a flip.

### S1 gate-safe (injury / lineup)

| Field | Rule |
|-------|------|
| `availability_status` | **Only** `confirmed` \| `predicted` \| `stable_guess` \| `missing` |
| `lineup_status` | May be `changed` or `uncertain` for material lineup/injury |
| Notes | Put tokens: `"injury"`, `"lineup change"`, `"scratched"`, `"out for"` in availability_notes / lineup_notes / pack notes |
| **Do not** | Set availability_status to `changed` / `out` / `doubtful` |

### Brewers strong-flip vs weak-flip (example)

**Scenario:** Live ledger won Brewers −1.5. Today Rockies +2.5.

**Strong (good):** gate-canonical `availability_status=predicted`, `lineup_status=changed`, injury/lineup language in notes, structural `why_flip` / one_liner about SP change + rest — **no** weak idioms. Verdict Acceptable/Strong only with honest p_model.

**Weak anti-pattern (do not write):**  
`why_flip` / one_liner / summary containing: *"Rockies +2.5 is an easier line after Brewers already won; fade the favourite; bounce back"* → S2 fails; skill verdict **Reject** or **Weak**.

Full strong payload shape: design doc example in `docs/DEEP_RESEARCH_SKILL_ESR_2026-07-26.md` § Example.

## 4) Batch summary + recap

1. Write/update `outbox/DEEP_RESEARCH_BATCH.md` — table: match, selection, verdict, p_model, mic_grade, evidence_quality, form_continuity_triggered, opposite one-liner, tooling.
2. Recap: packs written this batch have `(match, selection)` ⊆ primary worklist keys; extras = process miss.
3. Hand back to `/daily-run` Stage **3.1** three agents → **3.1z apply-quality-veto** → **3.2** `research ready` → `recommend` (not recommend-first).

## Hard rules

- **MIC primary** structured evidence (multi-sport free pipeline for v1_sports when allow_network); Exa **optional** fill when MIC/free pages thin or process_miss.
- Soft dogs not guilty; short 1.40–1.80 OK with form/rank support.
- FEH checklist is **shadow only** — no FEH place reject codes.
- form_continuity: engine soft-reject only; do not hand-override weak flips without structural why_flip.
- **Never** bare write-pack as final pack step — **only** `scripts/write_deep_research_pack.py`.
- Live ledger only for continuity narrative anchors.
- Never invent `p_model` or force Strong on timeout.
- Refuse full-board deep.
- Prefer pack `data_coverage` / `evidence_quality` for Quality Challenger consumption; include `process_miss_reason` when MIC process_miss.
- `require_for_deep` **stays false** until exit criteria E1–E5; when true, hard-blocks **v1_sports only** on missing/D/F MIC — non-v1 remain Exa/HQ optional.

## Deliverable paths

| Artifact | Path |
|----------|------|
| MIC (input) | `outbox/match_intel/*.json` |
| Evidence packs | `evidence/*.json` via helper only |
| Payload (optional retain) | `outbox/deep_research/*.payload.json` |
| Human MD view | `outbox/deep_research/*.md` |
| Batch index | `outbox/DEEP_RESEARCH_BATCH.md` |

## CLI helper reminder

```powershell
python run_nt.py research match-intel --help
python scripts/write_deep_research_pack.py --help
python scripts/write_deep_research_pack.py --payload outbox/deep_research/slug.payload.json --odds-ref 1.85
Get-Content payload.json | python scripts/write_deep_research_pack.py --stdin
```
