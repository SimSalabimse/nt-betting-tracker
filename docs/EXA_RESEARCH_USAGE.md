# Exa research usage (ESR)

Exa is the **primary high-quality search tool** for deep-queue research under Edge-Seeking Research (ESR). It **feeds** evidence packs and reasoning — it does **not** hard-reject candidates and does **not** re-arm FEH place law.

**Philosophy:** [`RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](./RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md) · Operator law: root `AGENTS.md`.

---

## Role

| Does | Does not |
|------|----------|
| Both-sides form / results / H2H / rank / natural market profile | Override EV floors or invent `p_model` |
| Populate pack sources, summary, failure_modes, H2H notes | FEH anti-soft Condition A or checklist hard-F |
| Support **why · support · main risk** reasoning | Single-side price-led narratives as “research done” |
| Soft note when opposite side is thin | Auto-reject soft underdogs for incomplete Exa coverage |

**Missing opposite-side Exa hit → soft note / lower confidence, not automatic Grade F** (except hard `research_gates` conflicts: script / base-rate / sensitive availability).

---

## When to use Exa

**Mandatory for every deep-queue / Stage 2 line** when Exa (MCP / plugin / `/exa-search`) is available.

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

Always research **favourite and underdog** (or home/away) before locking selection. Soft underdogs are **not** guilty by default — still require honest matchup + EV, not price alone.

### Efficiency

- Prefer highlights/summaries for queue triage.
- Deeper Exa fetches for serious place candidates.
- Cite real sources in `evidence/*.json` takeaways.

---

## Coupling under ESR (not FEH)

```
Exa / HQ search
    → evidence pack fields (sources, H2H, form notes, natural market lean)
    → honest p_model + summary + failure_modes
    → grade_evidence (legacy path) + research_gates + EV + odds_confidence
    → recommend / PLACE_THESE reasoning
```

| Old FEH coupling | ESR |
|------------------|-----|
| Exa fills anti-soft Condition A or fail | No anti-soft hard path |
| Incomplete checklist → F | Soft downgrade / note |
| Feeds FEH gate codes in reasoning | Feeds **why · support · main risk** |

---

## Pack proof

Minimum signal that deep research happened:

- Sources/takeaways show HQ search for form + H2H (when relevant) + natural checks
- Both sides reflected in notes (or explicit “opposite thin” note)
- Honest `p_model` consistent with research narrative

Scaffold CLI (structure only — agent writes Exa content):

```bash
python run_nt.py research write-pack --match "…" --selection "…" --p-model 0.XX …
# then edit evidence/*.json with Exa findings
```

---

## Hard rules

- Never invent `p_model` from Exa snippets alone without a coherent matchup story.
- Never use Exa only to defend a mid-band price without testing the other side.
- Never claim Exa “cleared FEH” — FEH place-owning is **off** under ESR.
- Soft dog with negative H2H can still fail **EV** or honest grade — that is selection, not anti-soft ideology.
- capital_v2 / unit math unchanged.

---

## Related

| Doc | Role |
|-----|------|
| `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` | ESR philosophy |
| `docs/RESEARCH_WORKFLOW.md` | Stage 0–4 |
| `docs/skills_mirror_daily-run.md` | `/daily-run` Exa step |
| `docs/SOURCES.md` | Per-sport sites |
