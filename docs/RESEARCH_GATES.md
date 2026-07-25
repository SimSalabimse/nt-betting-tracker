# Multi-Sport Research Gates

**Why this exists:** France vs England WC 2026 bronze — Under 3.5 and BTTS No were placed without treating **high rotation / international availability** seriously. EV math cleared; process did not.

**Principle under ESR:** Gates stop **betting against your own script** and inventing full-strength priors when availability is unknown. They are **not** volume killers and **not** FEH-style soft-underdog guilt lists. Empty slip is OK only when there is truly no edge after scan + expansion — not as a substitute for honest research.

Engine entry point: `nt.research_gates.evaluate_research_gates` → hard issues force **grade F** in `grade_evidence` → cannot place.

**Philosophy:** [`RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](./RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md) · Workflow: [`RESEARCH_WORKFLOW.md`](./RESEARCH_WORKFLOW.md).

---

## Soft checks vs volume killers

| Keep as **hard** | Treat as **soft** (notes / higher bar / stake demote) |
|------------------|--------------------------------------------------------|
| `selection_vs_script = conflict` | Thin but non-empty availability notes on low context |
| `base_rate_conflict = true` | Mixed H2H (allowed under ESR; may lower confidence) |
| Missing availability + no research on **sensitive** markets | Incomplete optional checklist fields |
| Anti-script unders (high_scoring + Under/BTTS No) | Soft underdog at mid-odds without perfect H2H packaging |
| Tennis retirement_risk + long overs | Short favourite without 8 sources (Grade B + core can place) |
| Basketball star_rest + player overs | Natural-market eval imperfect on HC sibling |

**Do not** layer FEH anti-soft, preferred-band guilt, or “empty slip over every imperfect Grade B” on top of these gates.

---

## Universal risk dimensions

1. Availability uncertainty (who plays / minutes / fitness)
2. Motivation / dead rubber
3. Rotation / rest / load management
4. Format & environment (BO3/BO5, surface, travel)
5. Base-rate conflict (fixture type vs selection)
6. Script vs selection
7. Market sensitivity (totals/props more fragile)
8. Data latency (12h board vs late announcement)
9. Same-event correlated stacking

---

## Evidence pack fields (all sports)

| Field | Values | Notes |
|-------|--------|-------|
| `context_risk` | `low` \| `medium` \| `high` | Or legacy `rotation_risk` |
| `availability_status` | `confirmed` \| `predicted` \| `stable_guess` \| `missing` | Alias: `lineup_status` (football), `fitness_status` (tennis) |
| `availability_notes` | text | Alias: `lineup_notes` |
| `script_lean` | sport vocabulary | See profiles |
| `selection_vs_script` | `agree` \| `conflict` \| `neutral` \| `unknown` | `conflict` always hard-fails |
| `base_rate_conflict` | bool | `true` hard-fails |

Nested `research_gates: { ... }` may mirror the same keys.

---

## Tiers

| Tier | Context | Availability for sensitive markets |
|------|---------|--------------------------------------|
| **T0/T1** | Stable domestic / late-data leagues | `predicted` / `stable_guess` + availability research |
| **T2** | Elevated (B2B, cup early, travel) | Predicted + stronger notes |
| **T3** | High rotation / dead rubber / intl | Predicted only with **substantive notes**, or confirmed |
| **T4** | Config strict | Confirmed only |

---

## Hard vs soft

**Hard (cannot place):** script conflict; base_rate conflict; missing availability with no research on sensitive markets; predicted without availability research (when enabled); T3 thin notes when high_context_stricter; optional confirmed-only.

**Soft (do not auto-kill volume):** high odds + predicted; prefer re-check when official availability drops; mixed H2H on underdogs; imperfect natural-market narrative; thin Exa opposite-side (note it).

---

## Sport profiles (summary)

### Football
- **High context:** WC, Euros, Nations League, friendlies, bronze/3rd, cup KO, playoffs  
- **Sensitive:** O/U, BTTS, team totals  
- **Script:** `high_scoring` / `low_scoring` / `one_sided` / `tight` / `neutral`  
- **Conflict:** high_scoring → no Under / BTTS No; low_scoring → no Over / BTTS Yes  

### Tennis
- **High context:** injury/retirement flags, prior long match, surface change, BO5 fatigue  
- **Sensitive:** games/sets totals, set handicaps, props  
- **Script:** `short_match` / `long_match` / `retirement_risk` / `competitive` / `dominant_favorite`  
- **Conflict:** retirement_risk / short_match → no long-match overs without notes  

### Basketball
- **High context:** B2B, 3-in-4, load management, summer league, star questionable  
- **Sensitive:** team totals, player props  
- **Script:** `high_pace` / `low_pace` / `blowout` / `star_rest` / `competitive`  
- **Conflict:** star_rest → no player overs; blowout scripts need prop caution  

### Default (hockey, handball, darts, …)
- Same universal hard gates  
- Sensitive: totals-like and props via selection text  
- High context markers: international, cup, back-to-back, stand-in, etc.  

---

## Config (`research.gates` + legacy aliases)

See `config.yaml`. Key knobs:

- `predicted_availability_ok` — default true (12h boards)
- `require_availability_research_if_predicted`
- `high_context_stricter_notes` / `high_context_min_notes_chars`
- `high_context_require_confirmed` — opt-in T4 for high risk only
- `strict_confirmed_only` — global T4
- `reject_script_conflict` / `reject_base_rate_conflict`
- Per-sport `sports.football|tennis|basketball|default.enabled`

Legacy keys (`predicted_lineup_ok_for_totals_btts`, etc.) still map in.

---

## ESR interaction

| Layer | Interaction with research_gates |
|-------|----------------------------------|
| FEH place-owning | **Off** — gates remain the main hard research rejects |
| Anti-soft underdog | **Off** — do not re-encode as gate ideology |
| Odds confidence bands | Soft demote / floors — separate from gates |
| Learning | Temp process gates OK; **no** permanent hard-reject lists grown from losses |
| Empty slip | Only after Stage 2–3 + expansion + no +EV — not “gates said pass nothing” on large boards without research |
