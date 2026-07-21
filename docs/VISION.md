# NT Betting OS — Strategic Vision

**Version:** 5.0 (2026-07-15)  
**Codename:** *Code is law, evidence is fuel, empty slip is success.*

## Executive summary

This repository is not a tip sheet. It is a **rules-enforced betting operating system** for Norsk Tipping Oddsen: bankroll math, phase ladder, daily risk, evidence grades, portfolio construction, learning mults, and full audit trail live in code and files.

The v5 overhaul adds:

1. A **best-in-class research workflow** (idea → evidence → grade → recommend → place → settle → learn).
2. **Source playbooks** for Eliteserien / football and other NT sports.
3. A **multi-year bankroll plan** from ~500 NOK with safe scaling.
4. **Explicit combo / multi-leg policy** (default singles; doubles only under strict gates).
5. **Optional AI agent** that assists research and analysis but **never bypasses** the engine.
6. **Analyze / project / edges / research** CLI tools for long-horizon operations.

**Non-negotiable:** 100% backward compatibility with `data/bets.csv`, archives, `edges.jsonl`, evidence JSON, CLI, `config.yaml` schema (additive only), and the LuminaNT / desktop companion app.

---

## Core philosophy (unchanged)

| Principle | Meaning |
|-----------|---------|
| **Code is law** | Phase, stake, risk, EV bar, empty slip — engines decide, not vibes. |
| **Full auditability** | Ledger + decisions JSONL + edges + evidence packs + backups. |
| **Disciplined risk** | Daily cap, kill-switch, phase demotion, high-odds haircut. |
| **Empty slip = success** | No edge → no bet. Volume is not a KPI. |
| **Human final approval** | Recommend proposes; you place. Agent proposes; you approve. |
| **Process over P/L** | Short-term variance is noise; learning mults and grades compound skill. |

---

## Long-term vision (3–5 years)

```
Year 0–1   Protect & Stabilize   equity ~500 → 750–1200   process mastery
Year 1–2   Build                 equity → 2–5k            selective doubles
Year 2–3   Expand / Mature       equity → 5–15k           full phase ladder
Year 3–5   Scale (if edge holds) equity → 15k+            still fractional risk
```

Realistic targets assume **modest positive expectancy** after costs (NT margin, haircut, human error). The system is designed so that **if edge is zero or negative**, risk shrinks and demotes — capital is protected while you learn.

There is **no profit guarantee**. The OS maximizes *disciplined +EV attempts* under NT constraints.

---

## Architecture (logical layers)

```
┌─────────────────────────────────────────────────────────────┐
│  Human / LuminaNT desktop / optional AI agent (assist only) │
└───────────────────────────┬─────────────────────────────────┘
                            │ inbox odds · evidence · results
┌───────────────────────────▼─────────────────────────────────┐
│  CLI (nt status|recommend|settle|analyze|project|agent|…)   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Engines (code is law)                                       │
│  bankroll · phase · risk · evidence · portfolio · learning   │
│  combos · research · analyze · project · agent tools         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Files (single source of operational truth)                  │
│  config.yaml · data/bets.csv · state/* · evidence/ · edges   │
│  inbox/ · outbox/ · history/                                 │
└─────────────────────────────────────────────────────────────┘
```

Desktop (Flet / LuminaNT) **reads the same files** and **invokes the same engines**. It never owns bankroll math.

---

## Compatibility contract

| Must remain stable | May change (additive) |
|--------------------|------------------------|
| `bets.csv` columns (`BET_HEADER`) | Optional config sections with defaults |
| `recommend` / `settle` / `status` / `validate` / `refresh` / `learn` CLI | New subcommands |
| Equity formula: `baseline + sum(settled P/L)` | Richer status markdown |
| Evidence grade A/B/C/F semantics | Optional evidence fields |
| Phase IDs 1A…5 | Docs, templates, agent audit log |
| Desktop state_service contracts | New state files under `data/state/` |

See [MIGRATION.md](./MIGRATION.md).

---

## What v5 deliberately does *not* do

- No live auto-betting against Norsk Tipping.
- No mandatory cloud AI or paid APIs.
- No rewrite of historical bet rows or archives.
- No Kelly-full staking at small bankrolls (variance would destroy process learning).
- No “guaranteed systems” / patents as default product — only gated multi-leg policy.

---

## Success metrics (process-first)

1. **Kill-switch and daily cap never silently ignored.**
2. **Empty-slip rate** healthy when board is thin.
3. **Grade A rate** on high-odds bets = 100% of those placed.
4. **Rolling ROI** used for phase unlock, not vanity volume.
5. **Every placed bet** has reconstructable evidence + decision meta.
6. **Agent outputs** stored as suggestions, never as silent ledger writes.
