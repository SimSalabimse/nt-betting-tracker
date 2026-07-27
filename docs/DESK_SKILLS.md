# Desk skills (Grok)

User-scope Grok skills for the NT capital desk. Skills live under **`%USERPROFILE%\.grok\skills\`** (not committed as binary agent state). This doc is the **repo pointer** + invoke cheat sheet.

Engines in `nt/` remain law. Skills encode **workflows**; they never invent `p_model`, bankroll equity, or hand-softened min_EV.

**Edge-Seeking Research (ESR)** is the research + recommend philosophy. Stage 0–4 **data-first**: settle → **0b assert-can-bet halt** → odds → **1a** engine baseline → **1x MIC** → **1b** adaptive multi-agent scan (A/B/C always + conditional D) → primary worklist ≤15 → MIC hard top-up → deep research (**MIC primary**) → **three Decision Agents** → **3.1z apply-quality-veto** → engine `recommend` (sole **positive** place set; **KD-place-law**) → annotate PLACE_THESE → expand once (MIC + `re_expand_once`) if needed. Soft underdogs are **not** guilty by default. Short favourites **1.40–1.80** allowed. Empty slip only after full scan + expansion. FEH is **demoted / shadow only** — not place law. Test tag: **`TEST_CAP:esr_data_v1`**.

Authoritative: [`RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md`](./RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md) · Workflow: [`RESEARCH_WORKFLOW.md`](./RESEARCH_WORKFLOW.md) · Repo mirror of daily-run: [`skills_mirror_daily-run.md`](./skills_mirror_daily-run.md) · deep-research: [`skills_mirror_deep-research.md`](./skills_mirror_deep-research.md).

**Adaptive scan (still valid) + Stage 3 three agents (supersedes Dual):** Stage 1b A/B/C + conditional Agent D unchanged; Stage **3.1–3.1z–3.3** three agents + Quality hard_veto CLI — see live `/daily-run` skill + root `AGENTS.md`. Design scan: [`ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md`](./ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md) (Stage 3 Dual **superseded**). Golden template: [`templates/TRI_DECISION_TEMPLATE.md`](./templates/TRI_DECISION_TEMPLATE.md). Multi-agent stub pointer: [`ESR_MULTI_AGENT_SCAN_2026-07-25.md`](./ESR_MULTI_AGENT_SCAN_2026-07-25.md).

## Installed skills

| Slash | Directory | Role |
|-------|-----------|------|
| `/daily-run` | `~/.grok/skills/daily-run/` | Full day: settle → **assert-can-bet halt** → odds → 1a → **1x MIC** → **1b adaptive A/B/C(+D)** → primary ≤15 → MIC top-up → `/deep-research` (MIC primary) → **three agents** → **apply-quality-veto** → engine recommend (sole positive place set) → annotate PLACE_THESE → expand once (MIC + `re_expand_once`) → place-ack (`TEST_CAP:esr_data_v1` when active) |
| `/deep-research` | `~/.grok/skills/deep-research/` | Stage 2 primary-worklist packs only — **MIC primary** + optional Exa; atomic pack writer |
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
  deep-research\SKILL.md
  missed-audit\SKILL.md
  chain-explain\SKILL.md
  bankroll-tune\SKILL.md
  learning-rootcause\SKILL.md
```

Grok reloads skills when files change on disk (slash menu updates within a few seconds).

Copy from a machine that already has them, or recreate from this doc + `AGENTS.md` Desk skills section + `docs/skills_mirror_daily-run.md` + `docs/skills_mirror_deep-research.md`.

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
python run_nt.py refresh
python run_nt.py research assert-can-bet          # Stage 0b halt if can_bet false
python run_nt.py research market-scan --odds <odds>
python run_nt.py research board --odds <odds>
python run_nt.py research light --odds <odds>
python run_nt.py research match-intel --odds <odds>   # Stage 1x MIC
python run_nt.py research scan-depth --odds <odds>
python run_nt.py research scan-merge --odds <odds> --agents-dir outbox
# after three agents write quality_veto JSON:
python run_nt.py research apply-quality-veto --date YYYY-MM-DD
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
| Stage 0–4 data-first | 0a settle → 0b can-bet halt → 0c odds → 1a → 1x MIC → 1b A/B/C(+D) → 1c → MIC top-up → deep → three agents → 3.1z → recommend → annotate → expand once |
| Stage 0b | `research assert-can-bet` / `risk.json` `can_bet` — halt research if false |
| Stage 1x MIC | Free structured facts; ≤8 min; board if n≤max else defer; hard top-up after shortlist |
| Stage 1b | A favourites/HUB · B totals/props · C HC/matchup · D long-tail if any match ≥41 Candidate lines |
| Agent D | `scan-depth` or manual line-count; skip if sequential A+B+C ≥10 min of 12 min budget |
| Primary worklist | shortlist ∪ coverage_critical, cap 15 — drives Stage 2 when multi-agent shortlist exists |
| Soft underdogs | Not guilty by default; place on matchup + EV |
| Short 1.40–1.80 | Allowed when research supports (Grade B + core + EV); Agent A prefers ≥1.70 + HUB mandate |
| Empty slip | Only after full deep + expansion + no +EV — process miss if next tier unresearched |
| FEH | Shadow/demoted — not place law |
| KD-place-law | Engine sole **positive** place set + stakes; Quality **hard_veto** via CLI pack mutation only; Edge/Guardian advisory |
| Three agents + 3.1z | Stage **3.1–3.1z–3.3**: Edge ∥ Guardian ∥ Quality → `apply-quality-veto` (applied marker required) → engine recommend → annotate; never hand-remove engine picks |
| Exa | **Optional** pack fill; MIC primary; `require_for_deep` sport-scoped to v1_sports after exit criteria |
| Coverage / temp_ev_relax | Expand research or rare EV soften — never invent p_model |
| 10 NOK test cap | First 10 place-acked `TEST_CAP:esr_data_v1` seats ≤ 10 NOK |

### `/daily-run` reasoning output

After three agents + apply-quality-veto + `recommend`, always check:

- `outbox/decision_agent_edge_*.md` · `guardian_*.md` · `quality_*.md` · `quality_veto_*.json` · `quality_veto_applied_*.json` · `TRI_DECISION_*.md` (or skip note)
- `outbox/match_intel/*.json`
- `outbox/PLACE_THESE.md` → `## Reasoning` (**why · support · main risk**) + post-engine **`decision:` / `agents:`** tags **and** `## Near-miss / Rejected` (short)
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
| MIC | `outbox/match_intel/*.json` |
| Three agents / TRI | `outbox/decision_agent_{edge,guardian,quality}_*.md` · `quality_veto_*.json` · `quality_veto_applied_*.json` · `TRI_DECISION_*.md` |
| Tri Decision template | `docs/templates/TRI_DECISION_TEMPLATE.md` |
| Dual template (legacy) | `docs/templates/DUAL_DECISION_TEMPLATE.md` |
| Reasoning chains | `data/state/reasoning_chains.jsonl` |
| Light research | `outbox/light_research/` |
| Deep queue SSOT | `data/state/deep_queue.json` |
| Scan agents / shortlist | `outbox/scan_agent_{a,b,c[,d]}_*.jsonl` · `outbox/MULTI_AGENT_SHORTLIST.md` |
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
| `AGENTS.md` | Desk law + ESR Stage 0–4 data-first + Stage 1b + **three agents + KD-place-law** |
| `docs/RESEARCH_RESET_SIMPLE_EFFECTIVE_2026-07-25.md` | ESR philosophy |
| `docs/ESR_ADAPTIVE_SCAN_AND_DUAL_DECISION_2026-07-27.md` | Adaptive multi-agent **scan** (still valid); Stage 3 Dual **superseded** |
| `docs/templates/TRI_DECISION_TEMPLATE.md` | Golden three-agent Stage 3 artifact |
| `docs/ESR_MULTI_AGENT_SCAN_2026-07-25.md` | Stub → adaptive design + live skill |
| `docs/RESEARCH_WORKFLOW.md` | Stage map |
| `docs/EXA_RESEARCH_USAGE.md` | Exa optional; MIC primary |
| `docs/skills_mirror_daily-run.md` | Live daily-run skill mirror |
| `docs/skills_mirror_deep-research.md` | Live deep-research skill mirror |
| `docs/EXA_RESEARCH_USAGE.md` | Exa feeds research |
| `docs/skills_mirror_daily-run.md` | Committed daily-run skill text |
| `docs/RESEARCH_GATES.md` | Hard vs soft gates |
| `docs/CAPITAL_HYBRID_PROGRESSION.md` | Capital hybrid |
| `docs/SETTLEMENT_LEARNING.md` | Settle + learn |
| `docs/FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md` | **SUPERSEDED** |
