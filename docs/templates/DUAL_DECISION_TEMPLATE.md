# Dual Decision — golden template (KD-DD-wire)

| Field | Value |
|-------|--------|
| **Date** | YYYY-MM-DD |
| **Odds file** | `inbox/odds_….txt` |
| **Law** | **Advisory only** — place set + stakes come **exclusively** from engine `recommend` / `build_portfolio` |
| **Flow** | 3.1 ARGUE → 3.2 engine recommend → 3.3 annotate (→ 3.4 expand once if needed) |

> **Do not** publish the wants tables below as a place list.  
> **Do not** hand-remove engine picks because Guardian challenged them.  
> Write `decision:` tags **only after** recommend.

Related: `docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md` · `/daily-run` skill Stage 3 · `AGENTS.md` Stage 3.1–3.4.

---

## 0) Session header

| Item | Value |
|------|--------|
| Dual Decision ran? | yes / skip (recommend-only) / skip (empty deep-ready) / kill-switch |
| Wall-clock argue (min) | ≤8 |
| New Exa during argue? | **no** (hard ban) |
| `re_dual_once` | unused / consumed |
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

### 1c Agreement snapshot (pre-engine — informational only)

| Selection | Maximiser rank | Guardian rank | Notes |
|-----------|----------------|---------------|-------|
| … | #k | #j | agree / edge-only want / guardian-only want / challenged |

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

---

## 3) Stage 3.3 — Reconciliation (post-engine only)

### 3a Engine picks × dual-decision tags

| Engine pick | maximiser_rank | guardian_rank | **decision** | dual_decision note |
|-------------|----------------|---------------|--------------|--------------------|
| … | #k / — | #j / — | both \| edge_only \| guardian_only \| edge_over_guardian \| engine_only | … |

**Tag rules:**

| Tag | Meaning |
|-----|---------|
| `both` | On **both** agent want lists **and** engine-picked |
| `edge_only` | Maximiser wanted; Guardian did not rank/want |
| `guardian_only` | Guardian wanted; Maximiser did not |
| `edge_over_guardian` | Maximiser wanted; Guardian **challenged** — still place (engine included) |
| `engine_only` | Engine picked; on **neither** agent top list |

### 3b Dual wants **not** in engine set (near-misses — not dual veto)

| Want source | Selection | Engine reject reason |
|-------------|-----------|----------------------|
| maximiser #k | … | EV / gates / diversify / … |
| guardian #j | … | … |

### 3c Integrity checklist (KD-DD-wire)

- [ ] No hand-removed engine picks  
- [ ] No hand-added dual wants  
- [ ] No preferred 2–6 published as place list  
- [ ] `decision:` tags written **after** recommend only  
- [ ] PLACE_THESE stakes match engine output  

---

## 4) Stage 3.4 — Expansion (optional once)

| Item | Value |
|------|--------|
| Triggered? | no / yes (large board & &lt;2 picks) |
| Expansion deep lines | 5–8 … |
| Re-ran 3.1–3.3? | yes once / n/a |
| `re_dual_once` | consumed / unused |

---

## 5) PLACE_THESE provenance snippet (copy into slip)

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

---

## 6) Artifact paths

| Artifact | Path |
|----------|------|
| Edge Maximiser | `outbox/decision_agent_edge_YYYY-MM-DD.md` |
| Portfolio Guardian | `outbox/decision_agent_guardian_YYYY-MM-DD.md` |
| This reconciliation | `outbox/DUAL_DECISION_YYYY-MM-DD.md` |
| Place slip | `outbox/PLACE_THESE.md` |

*End of golden template — advisory only; engine recommend is sole place-set law.*
