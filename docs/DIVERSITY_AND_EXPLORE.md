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
| `prefer_explore_first` | thin/explore lines sorted ahead (tiebreak under composite `sort_ev` when configured) |
| `explore_min_ev` | **0.012** (lower bar for explore-flagged lines) |
| `explore_base_ev_min` | **0.005** — explore/virgin boost + explore floor only when **base_ev** clears this; dual EV in reasoning |
| `max_per_match` | **1** open market per match (pending + slip) — blocks correlated stacks |
| `form_continuity` | Soft demotion + **narrow** soft-reject (`form_continuity:` only) for weak opposite-side flips after successful heavy-fav HC within hours **AND** games window. Module: `nt/form_continuity.py`. True EV unchanged. |
| `ranking_gap_hc` | Soft max **1** ranking-gap HC per slip (EV-slack skip-then-fill; same-match non-HC preferred). Force-accept when only RG remain. |
| Stake packing | min-stake seats first; reserve leftover for extra eligible seats; then EV top-up |
| Rejects | Full machine-readable `outbox/REJECTS_*.jsonl` (+ MD summary); form_continuity near-misses use prefix `form_continuity:` |

### Learning (`nt/learning.py`)

| Rule | Default |
|------|---------|
| `explore_min_n` | **0** (virgin sports/markets get explore) |
| `explore_ev_boost` | **0.018** |
| `explore_virgin_ev_boost` | **0.022** |
| Extra boost for non-football thin sports + props/period markets | yes |
| Explore portion split | Virgin + explore + thin extras are the **explore** portion; withheld when `base_ev < explore_base_ev_min` |

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

## Form continuity + anti-flip (process soft-reject class)

**Code:** `nt/form_continuity.py` · config `learning.diversification.form_continuity` · design [`FORM_CONTINUITY_AND_ANTI_FLIP_HARDENING_2026-07-26.md`](./FORM_CONTINUITY_AND_ANTI_FLIP_HARDENING_2026-07-26.md).

| Piece | Default / behaviour |
|-------|---------------------|
| Trigger | Opposite-side HC after successful **heavy-fav** minus-HC on same team-pair |
| Window | Fail-closed **AND**: `hours_since ≤ max_hours` (**48**) **and** `games_in_pair ≤ max_games` (**2**) |
| Soft pen | Win base **0.035** on `sort_ev` (`continuity_penalty_weight`); pending anchors demote-only |
| Weak flip | Default `weak_flip_action: soft_reject` → reason prefix **`form_continuity:` only** (filters scored; `rec.ev` unchanged) |
| Strong flip | ≥2 positive signals (news/why_flip/`base_ev≥strong_flip_min_ev`+grade/structural) → demote only |
| Live ledger only | Continuity peers from live `data/bets.csv` via `filter_live_rows` — never archives |

**Not** an expansion of `similar_recent.hard_reject_if_count`. Similar-recent + Settlement Lessons stay **sort-only**. **No FEH / anti-soft place-law revival.**

### Ranking-gap HC soft cap

| Key | Default |
|-----|---------|
| `ranking_gap_hc.enabled` | **true** (PR4) |
| `max_per_slip` | **1** when competitive non-RG peers remain |
| `ev_slack` | **0.015** peer compare on `sort_ev` |
| Same-match non-HC | Soft-skip RG even for **first** RG seat when competitive non-HC exists (`max_per_match: 1`) |
| Pass 3 | Force-accept RG when peers gone — never empty seats solely due to this soft cap |

### Explore base-EV gate

| Key | Default |
|-----|---------|
| `explore_base_ev_min` | **0.005** |
| When `base_ev ≥ min` and explore portion &gt; 0 | Apply explore boost; `explored` effective; floor may use `explore_min_ev` |
| Else | **Withhold** explore portion; do **not** lower min_EV floor via explore alone |
| Reasoning | Always prefer dual display: `base_ev` · `explore_boost` (or `withheld`) · `placed_ev` |

## What this is *not*

- Not free money: EV still must clear haircut + min EV (explore bar is lower, not zero).
- High-odds props still need **grade A**.
- Deep-red soft-blocked sports stay blocked (`block_roi_below`).
- **Not FEH / anti-soft revival.** The only narrow process soft-reject class added here is **`form_continuity:`** weak flips. Soft dogs remain not guilty by default; short favs 1.40–1.80 still welcome with support.

## Agent / human research checklist

When analyzing an odds file:

1. Run `python run_nt.py research board --odds …`
2. Check shortlist **sport mix** and **macro mix** in the report.
3. Research **every** shortlisted sport — not only football.
4. For each fixture, compare **all** viable markets (including player / 1H) before locking p_models; evaluate **opposite side** and record it on the pack / PLACE_THESE.
5. `recommend` will prefer non-football explore when EV is comparable — and only apply explore boost when **base_ev** is clear+.
6. Expect `form_continuity:` near-misses on weak opposite-side flips after heavy-fav wins; do not hand-override without structural why_flip.

## Config keys

See `config.yaml` → `learning.diversification` (incl. `form_continuity`, `ranking_gap_hc`, `explore_base_ev_min`, `sort.continuity_penalty_weight`) and `research.board_*`.
