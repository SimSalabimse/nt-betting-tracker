# Forced Evidence Hierarchy — SUPERSEDED

> ### ⚠️ SUPERSEDED — 2026-07-25
>
> **This document describes the FEH non-bypassable place-law era and is no longer the desk philosophy.**
>
> **Authoritative replacement:**
> **[`docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](./RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md)** — Edge-Seeking Research (ESR) Stage 0–4.
>
> Also follow: root **`AGENTS.md`**, [`RESEARCH_WORKFLOW.md`](./RESEARCH_WORKFLOW.md), [`DESK_SKILLS.md`](./DESK_SKILLS.md).

---

## What changed

| FEH-era rule | ESR (live philosophy) |
|--------------|------------------------|
| FEH **NON-BYPASSABLE** place law | FEH place-owning **off** (`forced_hierarchy.enabled: false`, `shadow_mode: true`) — soft audit / demoted only |
| Anti-soft underdog hard reject → Grade F | Soft underdogs **not guilty by default**; place on matchup + honest EV + research_gates |
| Empty slip preferred over weak soft Grade B | Empty slip **rare** — only after full scan + expansion + no +EV |
| Preferred band 1.85–2.60 as research identity | Promise score = prior_ev / signal; no composition preferred floor |
| Short favourites high bar (Grade A + many sources) | Short 1.40–1.80 **allowed** at Grade B + core + EV (soft demote if thin matchup) |
| `FEH_TEST_CAP:feh_v1` 10 NOK | `TEST_CAP:esr_v1` 10 NOK first 10 placed (same safety intent, rebranded) |

## What is still true

- Engines in `nt/` own bankroll / phase / stake math (`capital_v2` untouched).
- Honest `p_model` required; never invent to fill seats.
- `research_gates` hard rejects for real nonsense (script conflict, base-rate, sensitive availability).
- Transparent reasoning + near-misses on `PLACE_THESE.md`.
- 10 NOK temporary stake ceiling on the first 10 test-tagged placed bets does **not** change unit formulas.

## Package history (retained for audit)

The 2026-07-24 FEH full-cleanup package introduced:

- Place-owning hierarchy (`nt/evidence_hierarchy/`)
- Anti-soft underdog hard path
- Sport research cards / SAEF coupling
- Temporary 10 NOK FEH-tagged stake cap
- Reasoning-chain FEH gate codes

Code may remain for **shadow / re-enable** and tests. **Do not treat FEH as place law** while ESR config is live. Operators and agents must load the Research Reset doc, not this file, for daily workflow.

## Migration pointer

| Need | Go to |
|------|--------|
| Daily research workflow | `docs/RESEARCH_WORKFLOW.md` + `AGENTS.md` |
| `/daily-run` skill | `docs/skills_mirror_daily-run.md` · `~/.grok/skills/daily-run/SKILL.md` |
| Exa usage | `docs/EXA_RESEARCH_USAGE.md` |
| Gates (soft vs hard) | `docs/RESEARCH_GATES.md` |
| Full ESR design | `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` |
