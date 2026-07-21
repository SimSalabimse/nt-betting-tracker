# Multi-Sport Research Gates

**Why this exists:** France vs England WC 2026 bronze — Under 3.5 and BTTS No were placed without treating **high rotation / international availability** seriously. EV math cleared; process did not.

**Principle:** Empty slip beats betting against your own script or inventing a full-strength prior when availability is unknown. Gates must work for a **12-hour** research window (PL XIs ~1h before KO; many leagues never publish early).

Engine entry point: `nt.research_gates.evaluate_research_gates` → hard issues force **grade F** in `grade_evidence` → cannot place.

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

**Hard (cannot place):** script conflict; base_rate conflict; missing availability with no research on sensitive markets; predicted without availability research (when enabled); T3 thin notes; optional confirmed-only.

**Soft:** high odds + predicted; prefer re-check when official availability drops.

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

## Workflow placement

```
Research → fill pack fields
grade_evidence()  ← gates run here (hard → F)
build_portfolio() ← rejects F
```

---

## Examples

| Scenario | Result |
|----------|--------|
| Domestic + predicted + injuries + Under + low_scoring | Allow |
| Bronze + no availability research + BTTS No | **Block** |
| Confirmed rotated defence + high_scoring + Under | **Block** |
| Same + Over if EV clears | Allow |
| NBA B2B player prop, no minutes note | **Block** |
| Tennis games over, no fitness, high fatigue context | **Block** |

Full design origin: session plan + `outbox/POSTMORTEM_FRA_ENG_2026-07-18.md`.
