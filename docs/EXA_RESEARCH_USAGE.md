# Exa research usage (ESR) — optional pack fill

Exa is an **optional** high-quality search tool for deep-queue research under Edge-Seeking Research (ESR). It **feeds** evidence packs and reasoning when free Match Intelligence Cards (MIC) and public pages are thin — it does **not** hard-reject candidates, does **not** re-arm FEH place law, and is **not** used for MIC body extraction.

**Long-term posture:** free sources (Norsk Tipping → Flashscore → FotMob → other public) + MIC are primary. Exa is a **short optional transition** with measurable exit criteria (flip to `exa_mode: off` + sport-scoped `require_for_deep`).

**Philosophy:** [`RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](./RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md) · Operator law: root `AGENTS.md` · MIC + daily order: `docs/skills_mirror_daily-run.md`.

---

## Role

| Does | Does not |
|------|----------|
| Optional both-sides form / results / H2H / rank / natural market fill when MIC thin | Override EV floors or invent `p_model` |
| Populate pack sources, summary, failure_modes, H2H notes | FEH anti-soft Condition A or checklist hard-F |
| Support **why · support · main risk** reasoning | Single-side price-led narratives as “research done” |
| Soft note when opposite side is thin | Auto-reject soft underdogs for incomplete Exa coverage |
| | **MIC body** extraction (`research.match_intel.exa_fill: false`) |

**Missing opposite-side Exa hit → soft note / lower confidence, not automatic Grade F** (except hard `research_gates` conflicts: script / base-rate / sensitive availability).

---

## Config (live defaults)

```yaml
research:
  exa_mode: optional          # optional | off
  match_intel:
    require_for_deep: false   # true only after exit criteria (E1–E5)
    require_for_deep_sports: null   # null → same as v1_sports (never implicit all-sports)
    v1_sports: [football]
    exa_fill: false           # never Exa for MIC body
```

| Mode | Meaning |
|------|---------|
| **`optional`** (current) | Prefer MIC + free pages; use Exa/HQ web when grade thin or non-v1 skeleton |
| **`off`** (after exit criteria) | Default narrative path without Exa; free/HQ web only if needed |

### Sport-scoped `require_for_deep` (after exit criteria / PR6)

When `require_for_deep: true`:

- Seats with `sport ∈ v1_sports` (default **football**): missing MIC or grade D/F → **cannot deep** that seat.
- Seats with `sport ∉ v1_sports`: **not** hard-blocked by MIC alone; Exa/HQ web remain allowed; Quality may still soft_demote/hard_veto on pack `evidence_quality` / continuity (closed enum), but **not** solely `mic_missing` for non-v1 until that sport joins `v1_sports`.

**Skill rule:** Empty slip on multi-sport boards must not be blamed on football-only MIC hard-blocks for non-football seats.

### Exit criteria (measurable — flip config + docs in same PR)

| # | Gate |
|---|------|
| **E1** | ≥80% of primary-worklist matches with `sport ∈ v1_sports` have MIC grade ≥ C on **3 consecutive** full `/daily-run` days with at least one such match |
| **E2** | Offline parse fixtures green for every sport in `v1_sports` |
| **E3** | ≥1 full daily-run with `exa_mode: optional` where v1_sports packs did not require Exa-only fields to pass ready |
| **E4** | skill + this doc + `AGENTS.md` updated in same PR as config flip |
| **E5** | Quality `apply-quality-veto` + can-bet halt exercised at least once in those days |

Until then: keep `exa_mode: optional`, `require_for_deep: false` (MIC still built for football; soft pressure only).

---

## When to use Exa

**Optional** for Stage 2 / primary-worklist lines when:

1. MIC is missing, grade ≤ C, or critical fields thin, **or**
2. Sport is outside full free pipeline (non-v1), **or**
3. Operator explicitly wants HQ narrative top-up

**Not required** when MIC grade ≥ B and free pages already filled form/H2H/both-sides.

Fallback if Exa unavailable: high-quality `web_search` + sport-correct sites (same both-sides rules). Note fallback in pack summary.

### Intent queries (prefer natural language)

```
"[A] current form and recent results 2026"
"[A] vs [B] head to head record"
"[A] and [B] scoring / 180s / xG profile"   # sport-equivalent
"Reasons [Favourite] should cover the handicap"
"Reasons [Underdog] might cover the handicap"
"[Team] injuries lineup rotation [competition]"
```

### Both sides

When Exa/HQ is used, always research **favourite and underdog** (or home/away) before locking selection. Soft underdogs are **not** guilty by default — still require honest matchup + EV, not price alone.

### Efficiency

- Prefer MIC first; Exa only for gaps.
- Prefer highlights/summaries for triage.
- Deeper Exa fetches for serious place candidates with thin free coverage.
- Cite real sources in `evidence/*.json` takeaways.

---

## Coupling under ESR (not FEH)

```
MIC (primary free facts)
    → optional Exa / HQ web fill
    → evidence pack fields (sources, H2H, form notes, data_coverage, evidence_quality)
    → honest p_model + summary + failure_modes
    → grade_evidence (legacy path) + research_gates + EV + odds_confidence
    → Quality apply-quality-veto (may null p_model) → recommend / PLACE_THESE
```

| Old FEH coupling | ESR data-first |
|------------------|----------------|
| Exa fills anti-soft Condition A or fail | No anti-soft hard path |
| Incomplete checklist → F | Soft downgrade / note; Quality closed-enum hard_veto via CLI |
| Feeds FEH gate codes in reasoning | Feeds **why · support · main risk** + MIC citation |
| Exa mandatory every line | Exa **optional**; MIC primary |

---

## Pack proof

Minimum signal that deep research happened:

- MIC grade/score reflected in `data_coverage` when card present
- Sources/takeaways show free and/or HQ search for form + H2H (when relevant) + natural checks
- Both sides reflected in notes (or explicit “opposite thin” note)
- Honest `p_model` consistent with research narrative
- `evidence_quality` set when possible (strong / adequate / thin / insufficient)

Scaffold CLI (structure only — agent writes content):

```bash
python run_nt.py research write-pack --match "…" --selection "…" --p-model 0.XX …
# then edit evidence/*.json — prefer scripts/write_deep_research_pack.py as final write
```

---

## Hard rules

- Never invent `p_model` from Exa snippets alone without a coherent matchup story.
- Never use Exa only to defend a mid-band price without testing the other side.
- Never claim Exa “cleared FEH” — FEH place-owning is **off** under ESR.
- Never use Exa to write MIC body (`exa_fill: false`).
- Soft dog with negative H2H can still fail **EV** or honest grade — that is selection, not anti-soft ideology.
- capital_v2 / unit math unchanged.
- `require_for_deep` (when true) is **sport-scoped** to `v1_sports` — not all sports.

---

## Related

| Doc | Role |
|-----|------|
| `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` | ESR philosophy |
| `docs/skills_mirror_daily-run.md` | Full `/daily-run` order (MIC + optional Exa) |
| `docs/skills_mirror_deep-research.md` | Stage 2 MIC-primary packs |
| `docs/templates/TRI_DECISION_TEMPLATE.md` | Quality hard_veto + Stage 3 |
| root `AGENTS.md` | Operator law |
