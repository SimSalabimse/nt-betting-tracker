# Desk skills (Grok)

User-scope Grok skills for the NT capital desk. Skills live under **`%USERPROFILE%\.grok\skills\`** (not committed as binary agent state). This doc is the **repo pointer** + invoke cheat sheet.

Engines in `nt/` remain law. Skills encode **workflows**; they never invent `p_model`, bankroll equity, or hand-softened min_EV.

**Edge-Seeking Research (ESR)** is the research + recommend philosophy. Stage 0–4: Collect → engine board/light → **multi-agent Stage 1b** (A/B/C ≤5) → shortlist 8–15 → primary worklist (cap 15) → deep once → pick best +EV → expand if needed. Soft underdogs are **not** guilty by default. Short favourites **1.40–1.80** allowed. Empty slip only after full scan + expansion. FEH is **demoted / shadow only** — not place law.

Authoritative: [`RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](./RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md) · Multi-agent scan: [`ESR_MULTI_AGENT_SCAN_2026-07-25.md`](./ESR_MULTI_AGENT_SCAN_2026-07-25.md) · Workflow: [`RESEARCH_WORKFLOW.md`](./RESEARCH_WORKFLOW.md) · Repo mirror of daily-run: [`skills_mirror_daily-run.md`](./skills_mirror_daily-run.md).

## Installed skills

| Slash | Directory | Role |
|-------|-----------|------|
| `/daily-run` | `~/.grok/skills/daily-run/` | Full day: results → **Settlement Lessons** (warn if stale) → odds → Stage 1a board/light → **1b multi-agent A/B/C** (max 5) → primary worklist → ESR packs once (Exa both-sides) → expand if &lt;2 on large board → recommend (max 2 family / similar soft) + **why · support · main risk** → `PLACE_THESE.md` → place-ack (10 NOK cap when active) · live ledger only |
| `/missed-audit` | `~/.grok/skills/missed-audit/` | Promising lines out of deep; promo components; cheapest fix — **edge-seeking, not soft-dog guilt** |
| `/chain-explain` | `~/.grok/skills/chain-explain/` | Simple chain: why · strongest support · main risk (+ EV/stake when useful) |
| `/bankroll-tune` | `~/.grok/skills/bankroll-tune/` | Secure/phase/unit/regime proposal → MC + capital tools |
| `/learning-rootcause` | `~/.grok/skills/learning-rootcause/` | Taxonomy + `learning_weight` + ControlSignals; **must not grow hard reject lists** |

Each skill **must** load root `AGENTS.md` first and use real CLI/tools.

## Grok invoke

From a Grok session with CWD = tracker root:

```text
/daily-run
/daily-run inbox/odds_2026-07-23.txt

/missed-audit
/missed-audit -- focus Bodø Glimt -1.5

/chain-explain Match Name | Selection @ 2.05
/bankroll-tune secure soft trigger
/learning-rootcause last settle batch
```

Also: TUI `/skills <name>` · auto-invoke when the skill `description` matches user intent.

### Install / refresh (user scope)

Skills are plain directories:

```
%USERPROFILE%\.grok\skills\
  daily-run\SKILL.md
  missed-audit\SKILL.md
  chain-explain\SKILL.md
  bankroll-tune\SKILL.md
  learning-rootcause\SKILL.md
```

Grok reloads skills when files change on disk (slash menu updates within a few seconds).

Copy from a machine that already has them, or recreate from this doc + `AGENTS.md` Desk skills section + `docs/skills_mirror_daily-run.md`.

## PowerShell helpers (optional)

Repo scripts (run from tracker root):

```powershell
.\scripts\skill_list.ps1
.\scripts\skill_invoke.ps1 daily-run
.\scripts\skill_invoke.ps1 missed-audit
.\scripts\skill_invoke.ps1 chain-explain
.\scripts\skill_invoke.ps1 bankroll-tune
.\scripts\skill_invoke.ps1 learning-rootcause
.\scripts\skill_smoke.ps1
```

These scripts **do not** replace Grok skills — they list paths and run engine smokes.

## Exhaustive CLI (daily desk)

See also `AGENTS.md` and `docs/RESEARCH_WORKFLOW.md`.

```powershell
python run_nt.py status
python run_nt.py settle --draft
python run_nt.py research market-scan --odds <odds>
python run_nt.py research board --odds <odds>
python run_nt.py research light --odds <odds>
python run_nt.py research ready --odds <odds>
python run_nt.py recommend --odds <odds>
python run_nt.py place-ack --ids <id>
python run_nt.py abandon --ids <id> --reason missed_prematch
python run_nt.py capital status
python run_nt.py control-signals list --json
python run_nt.py learn --proposals

python scripts/verify_coverage_floor.py --synthetic-large
python scripts/verify_chain_residuals.py
python scripts/mc_phase_progression.py --paths 50
python scripts/backfill_settlement_taxonomy.py --n 30
python scripts/backfill_settlement_taxonomy.py --n 30 --apply   # after review
```

### `/daily-run` ESR bar

| Rule | Detail |
|------|--------|
| Stage 0–4 | Collect → 1a board/light → **1b multi-agent A/B/C** → primary worklist (cap 15) → deep once → best +EV → expand if needed |
| Multi-agent 1b | A favourites 1.40–1.90 · B totals/props · C HC/matchup dogs · max 5 each · merge family ≤2 · deliverable `MULTI_AGENT_SHORTLIST.md` |
| Soft underdogs | Not guilty by default; place on matchup + EV |
| Short 1.40–1.80 | Allowed when research supports (Grade B + core + EV) |
| Empty slip | Only after full deep + expansion + no +EV — process miss if next tier unresearched |
| FEH | Shadow/demoted — not place law; **no** anti-soft revival |
| Coverage / temp_ev_relax | Expand research or rare EV soften — never invent p_model |
| 10 NOK test cap | First 10 place-acked `TEST_CAP:esr_v1` seats ≤ 10 NOK |
| Settlement Lessons | After settle ≥1 terminal: print before research; missing/stale = **warn** only |
| Diversify triad | Engine queue not family-demoted · shortlist soft family ≤2 · portfolio hard max 2 at place |
| Archive isolation | **Never** `history/archives/` or `history/rounds/` for memory — live only: `data/bets.csv` · pending · latest results · current odds · `data/state/*` |
| Untouched | capital_v2 · phase · secure · unit · **10 NOK** · ControlSignals · FEH stays demoted |

### `/daily-run` reasoning output

After `recommend`, always check:

- `outbox/PLACE_THESE.md` → `## Reasoning` (**why · support · main risk**) **and** `## Near-miss / Rejected` (short)
- `data/state/reasoning_chains.jsonl`
- `data/state/status.md` → ESR / coverage floor sections
- `data/state/deep_queue.json` → `expansion_needed` if present

### `/chain-explain` output

1. Prefer latest chain row for `(match, selection)`  
2. Lead with **why · strongest support · main risk**  
3. Add EV / stake / light promo only as supporting detail — less FEH gate-code archaeology  

### `/missed-audit` stance

Edge-seeking: which promising lines never got deep packs? Cheapest fix is usually **research them now** — not “soft dogs are bad.”

### `/learning-rootcause` stance

Taxonomy + weights + temp ControlSignals. **Forbidden:** proposing permanent hard-reject lists, re-enabling anti_soft/FEH place-owning from anecdotes.

### Safe taxonomy backfill

| Flag | Effect |
|------|--------|
| *(default)* | Write `data/state/settlement_reviews_backfill.jsonl` only |
| `--apply` | Merge into live after operator review |
| `--dry-run` | Classify only — no write |

## Deliverable paths (common)

| Artifact | Path |
|----------|------|
| Place slip | `outbox/PLACE_THESE.md` |
| Multi-agent shortlist | `outbox/MULTI_AGENT_SHORTLIST.md` (+ optional `outbox/scan_agent_{a,b,c}_*.jsonl`) |
| Reasoning chains | `data/state/reasoning_chains.jsonl` |
| Light research | `outbox/light_research/` |
| Deep queue SSOT | `data/state/deep_queue.json` |
| Coverage Health | `data/state/coverage_health.json` |
| Status / risk | `data/state/status.md` · `risk.json` · `phase.json` |
| Evidence packs | `evidence/*.json` |
| Settlement reviews | `data/state/settlement_reviews.jsonl` |
| Settlement Lessons | `outbox/SETTLEMENT_LESSONS.md` · `data/state/settlement_lessons.json` |
| Taxonomy backfill (proposed) | `data/state/settlement_reviews_backfill.jsonl` |
| ControlSignals | `data/state/control_signals.jsonl` |
| Learning | `data/state/learning.json` |

## Related

| Doc | Role |
|-----|------|
| `AGENTS.md` | Desk law + ESR Stage 0–4 · lessons + diversify + multi-agent Stage 1b |
| `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` | ESR philosophy |
| `docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md` | Multi-agent Stage 1b design |
| `docs/RESEARCH_WORKFLOW.md` | Stage map |
| `docs/EXA_RESEARCH_USAGE.md` | Exa feeds research |
| `docs/skills_mirror_daily-run.md` | Committed daily-run skill text (dual-write) |
| `docs/RESEARCH_GATES.md` | Hard vs soft gates |
| `docs/CAPITAL_HYBRID_PROGRESSION.md` | Capital hybrid |
| `docs/SETTLEMENT_LEARNING.md` | Settle + learn · Settlement Lessons v1 |
| `docs/DIVERSITY_AND_EXPLORE.md` | max 2 family · similar-recent · archive isolation |
| `docs/FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md` | **SUPERSEDED** |
