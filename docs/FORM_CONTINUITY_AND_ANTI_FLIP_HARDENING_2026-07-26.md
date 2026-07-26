# Form continuity + anti-flip hardening (pointer)

| Field | Value |
|-------|--------|
| **Status** | Pointer stub (full narrative may expand later) |
| **Date** | 2026-07-26 |
| **Live law** | Engine + portfolio — not place-law revival |

This path is referenced from `AGENTS.md` and related docs. **Authoritative live behaviour** lives in code and the diversity doc — not in this stub.

## Where to read

| Source | Role |
|--------|------|
| [`docs/DIVERSITY_AND_EXPLORE.md`](./DIVERSITY_AND_EXPLORE.md) | Operator summary: form continuity, ranking-gap HC soft max 1, explore `base_ev` gate, opposite-side |
| `nt/form_continuity.py` | Code law: live-ledger peers, heavy-fav HC window, strong-flip signals, soft-reject prefix **`form_continuity:` only** |
| `config.yaml` → `learning.diversification.form_continuity` | Live defaults (`enabled`, window hours/games, `weak_flip_action`) |
| [`docs/DEEP_RESEARCH_SKILL_ESR_2026-07-26.md`](./DEEP_RESEARCH_SKILL_ESR_2026-07-26.md) | Stage 2 pack fields that feed `build_evidence_snapshot` / flip signals |

## Hard constraints (do not re-litigate)

- **Narrow soft-reject class only:** reason prefix `form_continuity:` for weak opposite-side flips after successful heavy-fav HC within the fail-closed hours **AND** games window.
- **Not** FEH place law. **Not** anti-soft hard reject. Soft dogs remain not guilty by default.
- Continuity peers from **live** `data/bets.csv` only — never `history/archives/` or `history/rounds/`.
- Ranking-gap and explore gates are separate portfolio rules; see DIVERSITY doc.

Agents: surface near-misses and pack `why_flip` / opposite-side; do **not** hand-override weak flips without structural ≥2 strong signals.
