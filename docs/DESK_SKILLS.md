# Desk skills (Grok)

User-scope Grok skills for the NT capital desk. Skills live under **`%USERPROFILE%\.grok\skills\`** (not committed as binary agent state). This doc is the **repo pointer** + invoke cheat sheet.

Engines in `nt/` remain law. Skills encode **workflows**; they never invent `p_model`, bankroll equity, or hand-softened min_EV.

## Installed skills

| Slash | Directory | Role |
|-------|-----------|------|
| `/daily-run` | `~/.grok/skills/daily-run/` | Full day: results → odds → board+light → deep queue → scaffolds → recommend + Reasoning Chains (`## Reasoning` + `## Near-miss / Rejected`, empty/blocked too) → `PLACE_THESE.md` → place-ack |
| `/missed-audit` | `~/.grok/skills/missed-audit/` | Mid-band 1.80–2.20 out of deep; `promotion_score` components; cheapest fix; AH/tennis/snooker patterns |
| `/chain-explain` | `~/.grok/skills/chain-explain/` | Full Reasoning Chain for match/selection — light SSOT promo components + near-miss stage/reason |
| `/bankroll-tune` | `~/.grok/skills/bankroll-tune/` | Secure/phase/unit/regime proposal → MC (`mc_phase_progression.py`) + capital tools |
| `/learning-rootcause` | `~/.grok/skills/learning-rootcause/` | Taxonomy + `learning_weight` + ControlSignals; **safe** backfill (proposed file default; `--apply` for live) |

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

Copy from a machine that already has them, or recreate from this doc + `AGENTS.md` Desk skills section.

## PowerShell helpers (optional)

Repo scripts (run from tracker root):

```powershell
# Print skill paths + open SKILL.md in editor
.\scripts\skill_list.ps1

# Invoke reminder: print the /slash and first steps for a skill
.\scripts\skill_invoke.ps1 daily-run
.\scripts\skill_invoke.ps1 missed-audit
.\scripts\skill_invoke.ps1 chain-explain
.\scripts\skill_invoke.ps1 bankroll-tune
.\scripts\skill_invoke.ps1 learning-rootcause

# Smoke suite used by desk skill PR validation
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
# Safe taxonomy backfill: proposed only (default) — never live without --apply
python scripts/backfill_settlement_taxonomy.py --n 30
python scripts/backfill_settlement_taxonomy.py --n 30 --apply   # after review
python scripts/backfill_settlement_taxonomy.py --n 30 --dry-run # classify only
```

### `/daily-run` richer chain output

After `recommend`, always check:

- `outbox/PLACE_THESE.md` → `## Reasoning` (picks) **and** `## Near-miss / Rejected` (even empty slip / blocked)
- `data/state/reasoning_chains.jsonl` — kinds: `pick` · `near_miss` · `rejected_prefilter`
- Light join: each chain should carry `light.promotion_score` + components when light LATEST exists (not notes-only)

### `/chain-explain` richer output

When explaining a line / slip:

1. Prefer the latest chain row for that `(match, selection)` from `reasoning_chains.jsonl`
2. Surface `rejected_at_stage`, `reject_reason`, `promotion_score` + component top drivers
3. If light LATEST has the line and chain is thin, re-join via light SSOT (promo scorer)

### Safe taxonomy backfill

| Flag | Effect |
|------|--------|
| *(default)* | Write `data/state/settlement_reviews_backfill.jsonl` only — **never** mutates live reviews |
| `--apply` | Merge into live `settlement_reviews.jsonl` after operator review |
| `--dry-run` | Classify only — no write |

`/learning-rootcause` must default to proposed path; only pass `--apply` when the operator explicitly confirms.

## Deliverable paths (common)

| Artifact | Path |
|----------|------|
| Place slip | `outbox/PLACE_THESE.md` |
| Reasoning chains | `data/state/reasoning_chains.jsonl` |
| Light research | `outbox/light_research/` |
| Deep queue SSOT | `data/state/deep_queue.json` |
| Coverage Health | `data/state/coverage_health.json` |
| Status / risk | `data/state/status.md` · `risk.json` · `phase.json` |
| Evidence packs | `evidence/*.json` |
| Settlement reviews | `data/state/settlement_reviews.jsonl` |
| Taxonomy backfill (proposed) | `data/state/settlement_reviews_backfill.jsonl` |
| ControlSignals | `data/state/control_signals.jsonl` |
| Learning | `data/state/learning.json` |

## Related

| Doc | Role |
|-----|------|
| `AGENTS.md` | Desk law + skills section |
| `docs/RESEARCH_WORKFLOW.md` | Prefilter → deep → recommend |
| `docs/RESEARCH_GATES.md` | Gate fields |
| `docs/CAPITAL_HYBRID_PROGRESSION.md` | Half-steps + continuous unit + Variant A |
| `docs/SETTLEMENT_LEARNING.md` | Settle + learn loop |
| `docs/BANKROLL_PLAN.md` | Clean 500 era plan |
