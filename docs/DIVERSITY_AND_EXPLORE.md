# Multi-sport & multi-market diversity (code-is-law)

## Problem this solves

Football has the largest sample and often the highest stake mults. Without hard rules:

1. Research boards collapse to **football ML / BTTS / O2.5**.
2. Recommend fills the slip with football only.
3. Tennis / NBA / esports / props **never get sample**, so learning never updates.

You cannot get more data for other sports without **trying** researched bets there.

## Rules (v7)

### Research board (`nt/board.py`)

| Rule | Default |
|------|---------|
| Market families include ML, O/U, BTTS, DNB, HC, **period (1H)**, **player props**, team totals, clean sheet, corners | first-class |
| Hard noise only (correct score spam, cards, 10-min HUB junk) | still blocked |
| `board_max_football_share` | **0.45** of shortlist when other sports present |
| `board_min_non_football` | **≥4** slots reserved for non-football when available |
| `board_max_props` | **5** prop-like lines on the board |
| Thin sports get **score boost** so they surface for research | automatic |

### Portfolio (`nt/portfolio.py`)

| Rule | Default |
|------|---------|
| `max_football_per_round` | **1** soft preference only — **never** leave empty seats |
| `min_non_football_per_round` | prefer non-football first |
| Fill-up pass | Non-football first → limited football → if seats remain, **take good football** (e.g. Racing BTTS Nei) up to `max_per_sport` |
| `prefer_explore_first` | thin/explore lines sorted ahead |
| `explore_min_ev` | **0.012** (lower bar for explore-flagged lines) |
| `max_per_match` | **1** open market per match (pending + slip) — blocks correlated stacks |
| Stake packing | min-stake seats first; reserve leftover for extra eligible seats; then EV top-up |
| Rejects | Full machine-readable `outbox/REJECTS_*.jsonl` (+ MD summary) |

### Learning (`nt/learning.py`)

| Rule | Default |
|------|---------|
| `explore_min_n` | **0** (virgin sports/markets get explore) |
| `explore_ev_boost` | **0.018** |
| `explore_virgin_ev_boost` | **0.022** |
| Extra boost for non-football thin sports + props/period markets | yes |

## Sport taxonomy (Phase 3)

All diversify / learning / forensic soft-match keys go through `nt.sport_taxonomy.normalize_sport`:

| Input (examples) | Canonical key |
|------------------|---------------|
| `Darts`, `darts` | `darts` |
| `nba`, `WNBA`, `Basketball` | `basketball` |
| `LoL`, `CS2`, `Counter-Strike` | `esports` |
| `Fotball`, `Football Rating 8` | `football` |
| `ishockey`, `NHL` (via hockey) | `ice_hockey` |

**Inference fixes** (`nt.odds_parse._infer_sport`):

1. Collector `Sport: …` tag is **authoritative**.
2. No bare `"game"` → tennis (too broad).
3. Comma `Last, First` names alone → `unknown` (not snooker).
4. `inkludert overtid` → `basketball` (not bare `straffer` / football ET).

Subtype `nba`/`wnba` is UI-only via `basketball_subtype()`; diversify never splits them.

## Rejects logging (Phase 2)

| Artifact | Role |
|----------|------|
| `outbox/REJECTS_YYYY-MM-DD.md` | Human summary (first 100 + total count) |
| `outbox/REJECTS_YYYY-MM-DD.jsonl` | **Full** machine-readable reject records |
| `outbox/REJECTS_LATEST.jsonl` | Pointer to latest full log |
| `outbox/REJECTS.md` | Latest MD summary pointer |

## What this is *not*

- Not free money: EV still must clear haircut + min EV (explore bar is lower, not zero).
- High-odds props still need **grade A**.
- Deep-red soft-blocked sports stay blocked (`block_roi_below`).
- **Not a soft-underdog place path.** Explore / virgin / diversity boosts are **research and sort** pressure so thin sports and mid-price lines get packs. They **never** bypass **Forced Evidence Hierarchy (FEH)** — side-first, anti-soft underdog, empty slip OK. Underdog @ 1.85–2.20 is **not** inherently attractive; preferred/mid band is **research-rank only**. See root `AGENTS.md` and [`FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md`](./FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md).

## Agent / human research checklist

When analyzing an odds file:

1. Run `python run_nt.py research board --odds …`
2. Check shortlist **sport mix** and **macro mix** in the report.
3. Research **every** shortlisted sport — not only football.
4. For each fixture, compare **all** viable markets (including player / 1H) **side-first** before locking p_models (favourite HC / natural totals before soft dog price).
5. `recommend` will prefer non-football explore when EV is comparable **and FEH allows** — explore never places anti-soft rejects.

## Config keys

See `config.yaml` → `learning.diversification` and `research.board_*`.
