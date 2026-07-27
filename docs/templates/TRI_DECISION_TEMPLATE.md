# Tri Decision — golden template (KD-place-law + Quality hard_veto)

| Field | Value |
|-------|--------|
| **Date** | YYYY-MM-DD |
| **Odds file** | `inbox/odds_….txt` |
| **Law** | **Engine** = sole **positive** place set + stakes. Main narrates only. |
| **Exception** | Quality **hard_veto** may remove placeability **before** recommend via CLI pack mutation (negative filter only; closed enum). |
| **Flow** | 3.1 ARGUE (Edge ∥ Guardian ∥ Quality) → **3.1z apply-quality-veto** → 3.2 engine recommend → 3.3 annotate (→ 3.4 expand once if needed) |

> **Do not** publish agent wants tables as a place list.  
> **Do not** hand-remove or hand-add engine picks after recommend.  
> **Do not** invent extra vetoes outside Challenger closed-enum JSON.  
> Write `decision:` tags **only after** recommend.

Related: design `data-first-esr-reset-and-intelligence` §4.2–4.6 · adaptive Dual Decision supersession (PR4) · `/daily-run` Stage 3.

---

## 0) Session header

| Item | Value |
|------|--------|
| Tri Decision ran? | yes / skip (recommend-only) / skip (empty deep-ready) / kill-switch |
| Wall-clock argue (min) | ≤10 |
| New Exa during argue? | **no** (hard ban) |
| `re_expand_once` | unused / consumed |
| **Quality apply (3.1z)** | **required** same day — see §1d |
| Engine recommend | live / dry-run (user asked) |

---

## 1) Stage 3.1 — ARGUE (pre-engine; not a place list)

### 1a Edge Maximiser wants

Source: `outbox/decision_agent_edge_YYYY-MM-DD.md`

| Rank | Match | Selection | Odds | Sport | market_family | One-line why (+EV) |
|------|-------|-----------|------|-------|---------------|--------------------|
| #1 | … | … | … | … | … | … |
| #2 | … | … | … | … | … | … |
| #3 | … | … | … | … | … | … |
| #4 | … | … | … | … | … | *(optional through #6)* |

**Maximiser does not place.**

### 1b Portfolio Guardian wants + challenges

Source: `outbox/decision_agent_guardian_YYYY-MM-DD.md`

| Rank | Match | Selection | Odds | Sport | market_family | One-line why |
|------|-------|-----------|------|-------|---------------|--------------|
| #1 | … | … | … | … | … | … |
| #2 | … | … | … | … | … | … |
| #3 | … | … | … | … | … | … |

**Challenges (P0 live always):**

| Type | Target | Note |
|------|--------|------|
| family concentration / max_per_market | … | … |
| max_per_match / same-match stack | … | … |
| sport pile | … | … |
| correlation | … | … |

**Challenges (P1 only when engine/pack notes present):**

| Type | Target | Note |
|------|--------|------|
| form_continuity | … | only if engine/pack notes present — do not invent soft-rejects |
| ranking-gap HC | … | only if engine/pack notes present |

**Guardian does not place.**

### 1c Research Quality & Continuity Challenger

Source markdown: `outbox/decision_agent_quality_YYYY-MM-DD.md`  
Source machine JSON: `outbox/quality_veto_YYYY-MM-DD.json`

**hard_veto reasons MUST be from the closed enum only:**

```text
mic_missing | mic_grade_D | mic_grade_F |
opposite_side_thin | form_continuity_weak_flip | evidence_quality_insufficient
```

Any other reason string is **rejected** by `apply-quality-veto` (row skipped).

#### quality_veto JSON schema

```json
{
  "schema_version": 1,
  "date": "YYYY-MM-DD",
  "vetoes": [
    {
      "match": "A vs B",
      "selection": "Over 2.5",
      "evidence_pair_key_str": "a vs b||over 2.5",
      "action": "hard_veto",
      "reasons": ["mic_grade_D", "evidence_quality_insufficient"]
    }
  ],
  "demotes": [
    {
      "match": "C vs D",
      "selection": "…",
      "evidence_pair_key_str": "…",
      "action": "soft_demote",
      "reasons": ["mic_grade_C"],
      "note": "injuries unchecked"
    }
  ]
}
```

- **hard_veto** → machine pack mutation (null `p_model`) only after CLI apply  
- **soft_demote** → narrative / near-miss only; **no** pack mutation  
- Store both raw `match`/`selection` and `evidence_pair_key_str`

#### Pack `data_coverage` / `evidence_quality` (deep packs)

Deep packs should include optional structured coverage (helpers: `nt.research_quality_gate.build_data_coverage`):

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
    "evidence_quality_notes": "Injuries optional thin; form+table solid"
  },
  "research_quality": null
}
```

When hard-vetoed after 3.1z:

```json
{
  "p_model": null,
  "research_quality": {
    "action": "hard_veto",
    "reasons": ["mic_grade_D"],
    "veto_date": "YYYY-MM-DD",
    "prior_p_model": 0.58,
    "applied_by": "apply-quality-veto",
    "resolved_path": "evidence/some_pack.json"
  }
}
```

### 1d Stage 3.1z — APPLY (code; **required** before recommend)

```text
python run_nt.py research apply-quality-veto --date YYYY-MM-DD
# optional: --dry-run | --veto-file path
```

| Check | Value |
|-------|--------|
| `outbox/quality_veto_applied_YYYY-MM-DD.json` exists? | **must** (even if `n_vetoes=0`) |
| Packs null `p_model` for hard_vetoes? | yes / n/a |
| Undo log | `outbox/quality_veto_undo_YYYY-MM-DD.jsonl` (may be empty) |

**If 3.1z is skipped, Challenger power is zero.** skill_smoke proof = applied marker file, not non-empty undo log.

Recommend-only sessions: if `quality_veto_{today}.json` exists, still run apply before recommend.

---

## 2) Stage 3.2 — Engine recommend (SOLE place set)

```text
python run_nt.py research ready --odds <odds_file>
python run_nt.py recommend --odds <odds_file>
```

| Engine pick # | Match | Selection | Odds | Grade | EV | Stake | Reject peers (short) |
|---------------|-------|-----------|------|-------|-----|-------|----------------------|
| 1 | … | … | … | … | … | … | … |
| 2 | … | … | … | … | … | … | … |

Empty / blocked recommend: still write near-misses; omit place list.

**KD-place-law:** only this table (from engine output) is the place set. Agents never override stakes.

---

## 3) Stage 3.3 — Reconciliation (post-engine only)

### 3a Engine picks × agent tags

| Engine pick | Edge rank | Guardian | Quality | Tag |
|-------------|-----------|----------|---------|-----|
| … | #k / — | want / challenge / — | hard_veto / demote / — | agree / edge-lean / guardian-challenge / quality-cleared |

### 3b Near-misses

Include: hard_vetoes (pre-recommend), soft demotes, engine rejects, form_continuity soft-rejects.

| Match | Selection | Why near-miss |
|-------|-----------|---------------|
| … | … | … |

### 3c Main narrative (no place theater)

2–6 bullets on process quality; **never** invent places or restake.

---

## 4) Stage 3.4 — Expansion (at most once)

| Token | Value |
|-------|--------|
| `re_expand_once` | unused → consumed after one cycle |

```text
IF re_expand_once == unused AND large board AND picks < 2:
  next tier → MIC top-up → deep → re-3.1–3.1z–3.3 → set consumed
ELSE skip. Never re-enter while consumed.
```

---

## 5) Can-bet early exit (pre-research; Stage 0b)

```text
python run_nt.py refresh
python run_nt.py research assert-can-bet
# alias: python run_nt.py risk assert-can-bet
```

If `can_bet=false`: write PLACE_THESE capital halt; **stop** — no odds / MIC / scan / deep / recommend.

---

## Artifact checklist

| Artifact | Path |
|----------|------|
| Edge agent | `outbox/decision_agent_edge_YYYY-MM-DD.md` |
| Guardian agent | `outbox/decision_agent_guardian_YYYY-MM-DD.md` |
| Quality agent | `outbox/decision_agent_quality_YYYY-MM-DD.md` |
| Quality veto JSON | `outbox/quality_veto_YYYY-MM-DD.json` |
| Veto applied marker | `outbox/quality_veto_applied_YYYY-MM-DD.json` (**always** after 3.1z) |
| Veto undo | `outbox/quality_veto_undo_YYYY-MM-DD.jsonl` |
| This reconciliation | `outbox/TRI_DECISION_YYYY-MM-DD.md` |
| Engine place | `outbox/PLACE_THESE.md` |
