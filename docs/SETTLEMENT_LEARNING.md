# Settlement & layered learning

## Goals

1. Richer settle input (score, variance vs skill, research retro)
2. Auto-fetch results (multi-sport — see `docs/RESULT_FETCHERS.md`)
3. Automatic post-settlement analysis
4. Layered learning (short / medium / long) + **proposals** (accept/reject)
5. **ControlSignals closed loop** (primary process control — see below)

### ControlSignals (primary closed loop)

On `process_error` / poor research retro, the engine emits `temp_gate_raise` to
`data/state/control_signals.jsonl` (even n=1). Effects: raised `min_ev` for sport/market,
force confirmed lineup on avail-sensitive markets, TTL 7–14 days.

PostSettlementPacket is **mandatory** for process_error / poor retro (score, XI status,
xi_delta, script_realized, process_root_cause). Incomplete strict settles are rejected.

```bash
python run_nt.py control-signals list --json
python run_nt.py control-signals emit --sport football --source force_review --reason "…"
python run_nt.py control-signals revoke --sport football
```

Learning mult full-delta only when n≥8 and conf≥0.40. Mults can be recomputed away;
**ControlSignals are the durable process actuator.** Full map: `docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md`.

## Ledger result states

| Result | Meaning | Open risk? | Equity P/L | Phase sample? |
|--------|---------|:----------:|:----------:|:-------------:|
| **Pending** | Recommend *intent* — not confirmed on NT | Yes | — | No |
| **ConfirmedPlaced** | User confirmed ticket live on NT | Yes | — | No |
| **Win** / **Loss** / **Refunded** | Terminal settled outcomes | No | Yes | Yes |
| **Abandoned** | Never placed / voided intent | **No** | 0 | **No** |

```bash
# Confirm open tickets are live on Norsk Tipping
python run_nt.py place-ack --ids <bet_id>[,...]
# Never placed / missed prematch — frees risk, keeps audit row
python run_nt.py abandon --ids <bet_id> --reason missed_prematch
```

## CLI

```bash
# Draft open bets + optional auto-fetch (no write)
python run_nt.py settle --draft
python run_nt.py settle --draft --no-fetch

# Classic file settle (still supported; now runs analysis + proposals)
python run_nt.py settle --results inbox/results.yaml

# Rich JSON from LuminaNT Settle desk
python run_nt.py settle --items-json inbox/_settle_items.json

# Learning proposals (auto-applied when learning.auto_apply_proposals: true)
python run_nt.py learn --proposals
python run_nt.py learn --accept "sport:football:2026-07-18T18"
python run_nt.py learn --reject "market:Totals Over:..."
```

## Rich result fields

| Field | Meaning |
|-------|---------|
| `outcome` / `payout_nok` | Win / loss / refund (required path) |
| `score` | e.g. `2-1` |
| `variance_tag` | `expected` · `variance` · `process_error` |
| `research_quality_retro` | `good` · `ok` · `poor` |
| `confidence_retro` | 0–1 |
| `key_events` | Free text |
| `auto_fetched` | Suggestion came from auto-fetch |

**Risk day P/L / kill-switch** use **settlement calendar day** from `updated_at` (Europe/Oslo), not match kickoff `date`.

## Artifacts

| Path | Role |
|------|------|
| `outbox/SETTLEMENT_RECEIPT.md` | What settled |
| `outbox/SETTLEMENT_ANALYSIS.md` | Post-settlement narrative |
| `outbox/SETTLEMENT_LESSONS.md` | Per-batch main reason / driver / soft notes (overwrite) |
| `data/state/settlement_lessons.json` | Machine SSOT schema v1 (soft_awareness TTL) |
| `data/state/settlement_reviews.jsonl` | Per-bet reviews |
| `data/state/learning_proposals.json` | Pending mult proposals |
| `data/state/learning.json` | Live multipliers (layers + blend) |

### Settlement Lessons v1 (ESR)

After every settle batch with ≥1 terminal, the engine writes Settlement Lessons:

- **`main_reason`** always non-empty (engine auto-template when agent packet is thin; `settle{…}` blobs stripped)
- **`outcome_driver`** heuristic enum (`research_quality`, `variance`, `total_line_miss`, …)
- **Pattern peers** = last ~12 **live settled** (Win/Loss/Refunded) via `filter_live_rows` — no `era_archive`. Open tickets do not push losses out of the window. `cluster_same_family` may note open same-family seats but **soft_awareness is only emitted for loss-linked patterns** (repeat losses / batch multi-loss).
- **Soft awareness** with TTL (`learning.settlement_lessons.ttl_hours`, default 72h) — never permanent hard rejects; `max_soft_notes` keeps **freshest** notes
- **`live_ledger_only`**: always enforced (informational in config — cannot re-enable archive peers)
- Portfolio applies `lessons_soft:` sort demotion **independent** of similar-recent hits (`Recommendation.lessons_soft_reason` + combined `soft_demotion_reason`)

Config: `learning.settlement_lessons.*`. Failures are logged; settle never blocks.

## LuminaNT

- **Ops → Smart settle**: load pending, auto-fetch, batch outcomes, rich tags, submit
- **Research → Learnings**: review proposals after settle (when not auto-applied)

## Auto-apply (engine truth)

Config key: `learning.auto_apply_proposals` (default **true** in `config.yaml`).

| Mode | Behavior |
|------|----------|
| `true` (current default) | After settle / `nt learn`, proposals are **applied automatically** into `learning.json` sport/market/band mults. Still logged for audit. |
| `false` | Proposals land in `data/state/learning_proposals.json` only; operator must `nt learn --accept` / `--reject`. |

`AGENTS.md` and the engine follow config — not a hard “never auto-apply” rule. Set `auto_apply_proposals: false` if you want a human gate.
