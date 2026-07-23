# NT Betting Tracker v5 — Disciplined Betting OS

**Code is law.** Norsk Tipping Oddsen system for evidence-based value betting with full auditability, automatic phase/risk, and zero tolerance for undisciplined stakes.

You supply **odds** and **results**. The system owns stakes, phase, daily risk, portfolio construction, bankroll math, learning mults — and optionally assists research via templates + AI tools that **never bypass** the engines.

| Pillar | Meaning |
|--------|---------|
| **Code is law** | Phase, risk, EV bar, empty slip — engines decide |
| **Full audit** | `bets.csv` + decisions JSONL + edges + evidence + backups |
| **Empty slip = success** | No edge → no bet |
| **Human final approval** | Recommend proposes; you place. Agent never auto-bets |
| **Backward compatible** | v5 is additive — your ledger and LuminaNT desktop keep working |

Deep docs: [`docs/VISION.md`](docs/VISION.md) · [`docs/BANKROLL_PLAN.md`](docs/BANKROLL_PLAN.md) · [`docs/RESEARCH_WORKFLOW.md`](docs/RESEARCH_WORKFLOW.md) · [`docs/CAPITAL_HYBRID_PROGRESSION.md`](docs/CAPITAL_HYBRID_PROGRESSION.md) · [`docs/DESK_SKILLS.md`](docs/DESK_SKILLS.md) · [`docs/SETTLEMENT_LEARNING.md`](docs/SETTLEMENT_LEARNING.md) · [`docs/SOURCES.md`](docs/SOURCES.md) · [`docs/AGENT.md`](docs/AGENT.md) · [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md)

---

## 2-minute new-user / Grok flow

Clean-restart **500 NOK** desk with capital_v2 live. Engines in `nt/` are law — Grok skills encode workflow only.

### Daily path (preferred)

1. Drop Oddsen dump into `inbox/odds_*.txt` (or pass an explicit path).
2. In Grok (CWD = tracker root): **`/daily-run`**  
   → results draft → market-scan → board + light → engine deep queue → deep packs → `recommend` + **Reasoning Chains** → `outbox/PLACE_THESE.md` → `place-ack`.
3. Or CLI smoke (no ledger write):

```bash
python scripts/dry_run_daily_path.py
# or manually:
python run_nt.py research board --odds inbox/odds_YYYY-MM-DD.txt
python run_nt.py research light --odds inbox/odds_YYYY-MM-DD.txt
python run_nt.py recommend --odds inbox/odds_YYYY-MM-DD.txt --dry-run
```

### What is live (do not re-derive)

| Layer | Live default |
|-------|----------------|
| **Secure bucket Variant A** | Soft **1.25×** ref / **15%** skim · hard **1.50×** / **30%** (hard replaces soft, never stacked) |
| **Hybrid phases** | `1A → 1A+ → 1B → 1B+ → …` + **continuous unit** (`phase_continuous.enabled`) |
| **Coverage floor (A)** | Dynamic deep target + top-promo scaffold + sport rotation — **never invents `p_model`** |
| **`temp_ev_relax` (B)** | Safety net only: per-line ΔEV 1–2pp · stake ×0.80 · TTL 24h · blocked if process_gate active |
| **Settlement taxonomy** | Every settle: `predictability` + `variance_class` → **`learning_weight`**; ControlSignal temp_gate only if weight ≥ **0.5** |
| **Reasoning chains** | On recommend (dry-run OK): `data/state/reasoning_chains.jsonl` + `## Reasoning` in `PLACE_THESE.md` |

### Desk skills (Grok)

Full install + invoke: [`docs/DESK_SKILLS.md`](docs/DESK_SKILLS.md) · law: root [`AGENTS.md`](AGENTS.md).

| Slash | Role |
|-------|------|
| `/daily-run` | Full day desk → place-ack |
| `/missed-audit` | Mid-band 1.80–2.20 out of deep queue |
| `/chain-explain` | Forensic Reasoning Chain for one line / slip |
| `/bankroll-tune` | Secure / phase / unit / regime + MC |
| `/learning-rootcause` | Taxonomy + `learning_weight` + ControlSignals |

```powershell
.\scripts\skill_list.ps1
.\scripts\skill_invoke.ps1 daily-run
.\scripts\skill_smoke.ps1
python scripts/dry_run_daily_path.py
```

### Capital + research pointers

- Hybrid half-steps + continuous unit + Variant A: [`docs/CAPITAL_HYBRID_PROGRESSION.md`](docs/CAPITAL_HYBRID_PROGRESSION.md)
- Prefilter → light → deep queue → packs: [`docs/RESEARCH_WORKFLOW.md`](docs/RESEARCH_WORKFLOW.md)
- Settle taxonomy + learning loop: [`docs/SETTLEMENT_LEARNING.md`](docs/SETTLEMENT_LEARNING.md)

---

## Your only jobs

1. Accept baseline bankroll in `config.yaml` (**500 NOK**, clean-restart era).
2. Research → evidence packs → paste **Oddsen** odds into `inbox/` → `recommend` → place `outbox/PLACE_THESE.md`.
3. Drop results in `inbox/` → `settle` → review with `analyze` / `learn` (taxonomy + ControlSignals auto).

---

## Quick start

```bash
cd nt-betting-tracker
python -m pip install -r requirements.txt

# Windows: package name `nt` can clash — use the helper:
python run_nt.py status
python run_nt.py validate
python run_nt.py recommend --odds inbox/odds_15-07.2026.txt --dry-run
python run_nt.py settle --results inbox/results_template.yaml
```

Linux/macOS: `python -m nt status` also works after bootstrap.

---

## CLI command map

### Core (unchanged contracts)

| Command | Purpose |
|---------|---------|
| `status` | Equity, phase, daily cap, can-bet |
| `validate` | Ledger integrity |
| `refresh` | Recompute `data/state/*` |
| `recommend --odds PATH [--dry-run]` | Portfolio → place slip |
| `settle --results PATH` | Settle + learning |
| `learn` | Recompute sport/market/band mults |
| `backfill-decisions` | Rebuild decisions JSONL from notes |

### v5 additions (optional)

| Command | Purpose |
|---------|---------|
| **`research board --odds …`** | **PRIMARY workflow:** shortlist + report (+ `--write-scaffolds`) |
| `research ready --odds …` | Gate check before recommend |
| `research write-pack --match … --selection … --p-model …` | Write filled evidence pack (gates + p_model) |
| `analyze` / `project` / `edges` | Attribution, simulation, lessons |
| `research sources` / `scaffold` / `p-model` / `critique` | Helpers |
| `place-ack` / `abandon` | Confirm placed or free phantom Pending risk |
| `agent ask "…"` | Assist-only AI |

### Collect odds (multi-sport)

```powershell
# Portable: collector uses repo root via Path(__file__). Optional dual-write:
# $env:NT_MIRROR = "D:\other\artifacts"
$env:NT_MIN_KO = "2026-07-21T07:00"
$env:NT_MAX_KO = "2026-07-21T17:00"
python artifacts\multi_sport_collector.py
# Prune raw API cache (dry-run default):
python scripts\prune_api_raw.py --days 7
```

### Correct daily path (do not skip research)

```bash
python run_nt.py research board --odds inbox/odds_YYYY-MM-DD.txt --write-scaffolds
# → outbox/RESEARCH_BOARD.md  +  evidence scaffolds for main markets
# → fill p_model + takeaways (internet research)
python run_nt.py research ready --odds inbox/odds_YYYY-MM-DD.txt
python run_nt.py recommend --odds inbox/odds_YYYY-MM-DD.txt --dry-run
python run_nt.py recommend --odds inbox/odds_YYYY-MM-DD.txt
```

**`recommend` refuses boards with zero evidence/p_model** unless `--force-mechanical` (tests only).

### Football simulation & calibration (optional)

**Sim suggests `p_model` — it never places bets.** Engine haircut / EV / phase still rule. See [`docs/SIMULATION.md`](docs/SIMULATION.md).

```bash
# Scoreline model (Poisson + Dixon–Coles) from λ or xG inputs
python run_nt.py simulate --input inbox/sim_match_template.yaml
python run_nt.py simulate --home "Bodø/Glimt" --away "Brann" \
  --lambda-home 1.8 --lambda-away 1.1 --selection "BTTS Ja"

# Seed evidence pack (you still fill real sources)
python run_nt.py simulate --lambda-home 1.6 --lambda-away 1.2 \
  --match "A vs B" --selection "Totalt antall mål - Over/Under 2.5: Over 2.5" \
  --write-evidence

# Calibration: predicted p vs Win/Loss (from decisions + settle)
python run_nt.py calibrate rebuild
python run_nt.py calibrate report
```

| Helps | Avoid |
|-------|--------|
| Football O/U, BTTS, rough 1X2 with real xG/λ | Multi-sport “simulate everything” |
| Transparent p_model for evidence | Treating sim as ground truth |
| Learning via Brier/bias over time | Forcing p_model just to clear EV |

```bash
python run_nt.py analyze
python run_nt.py project --years 3 --roi 0.03 --bets-per-week 10
python run_nt.py agent ask "What sports are hurting my ROI?"
```

---

## Odds input

**Preferred:** paste Oddsen board → `inbox/odds_YYYY-MM-DD.txt` (HUB / Vinner blocks).

```bash
python run_nt.py recommend --odds inbox/odds_15-07.2026.txt
python run_nt.py recommend --odds inbox/odds_15-07.2026.txt --dry-run
```

CSV still works (`inbox/odds_template.csv`) with optional `p_model` column.

---

## Research workflow (best practice)

```
Idea → Data (FBref, Transfermarkt, Sofascore…) → p_model
    → evidence/*.json → grade → recommend → place → settle → analyze/learn
```

1. **Shortlist** from the board (don't research everything).
2. **Gather** sources — Eliteserien: FBref + Transfermarkt + Sofascore + Flashscore + official.
3. **Package** evidence (see `evidence/example.json`, `evidence/example_v5.json`, `evidence/templates/`).
4. **Validate** with `research critique` / engine grade A/B/C/F.
5. **Decide** via `recommend` — empty slip is success.
6. **Review** with `analyze`, `learn`, `edges`.

Full playbook: [`docs/RESEARCH_WORKFLOW.md`](docs/RESEARCH_WORKFLOW.md) · sources: [`docs/SOURCES.md`](docs/SOURCES.md).

### Evidence JSON (minimal — still fully supported)

```json
{
  "match": "Team A vs Team B",
  "selection": "Team A DNB",
  "p_model": 0.62,
  "summary": "Form + H2H + lineup support",
  "failure_modes": "Red card; key striker out late",
  "sources": [
    {"url": "https://fbref.com/...", "takeaway": "xG edge"},
    {"url": "https://...", "takeaway": "no injuries"}
  ]
}
```

Optional v5 fields: `league`, `checklist`, `confidence`, `model_name`, `sources[].kind` — ignored safely by older graders.

---

## Bankroll & phase

```
Equity = 500 + sum(settled P/L in data/bets.csv)
daily_cap = clamp(equity × phase.daily_risk_pct, floor, ceil)
```

| Phase | Label | Enter equity | Stake | Doubles |
|-------|--------|--------------|-------|---------|
| 1A | Protect | 0 | 10–12 | 0 |
| 1B | Stabilize | 580 | 10–15 | 0 |
| 2 | Build | 750 | 12–18 | 1 |
| 3 | Expand | 1200 | 15–28 | 2 |
| 4 | Mature | 2500 | 18–45 | 2 |
| 5 | Scale | 5000 | 20–70 | 3 |

Hybrid unlock: equity primary; settled count may +1 phase if rolling ROI ≥ 0%. Demote on deep red or peak drawdown. Details: [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md) · multi-year plan: [`docs/BANKROLL_PLAN.md`](docs/BANKROLL_PLAN.md).

**Kill-switch:** today P/L ≤ −max(40, 8% equity) → no new bets.  
**Loss streak:** after 3 consecutive losses → grade **A** only.

---

## Bet types

| Type | Policy |
|------|--------|
| **Singles** | Default. Always preferred for attribution. |
| **Doubles** | Phase ≥ 2 **and** `combos.enabled` **and** correlation OK |
| **Trebles+ / systems** | Discouraged; gated; not automated patents |

```yaml
combos:
  enabled: false
  aggressiveness: conservative  # off | conservative | standard | aggressive
```

See [`docs/BET_TYPES.md`](docs/BET_TYPES.md).

---

## High odds (> 2.5)

**Not banned.** Require grade **A**, elevated EV, reduced stake mult, round cap. Historical bad band ROI raises the EV bar further.

---

## Optional AI agent

Assist-only. Tools: status, ledger, edges, learning, grade evidence, dry-run recommend, EV calc, projection.

```yaml
agent:
  enabled: false   # set true + XAI_API_KEY or OPENAI_API_KEY for LLM
```

```bash
python run_nt.py agent tools
python run_nt.py agent ask "Summarize my last 40 settled bets"
# Without keys: offline brief from the same tools
```

Never writes `bets.csv`. Audit log: `data/state/agent_audit.jsonl`.  
Guide: [`docs/AGENT.md`](docs/AGENT.md).

---

## Desktop app (LuminaNT / local desk OS)

Same files and engines as CLI. No cloud required.

```bash
python -m pip install -r requirements-desktop.txt
python run_desktop.py
```

| Mode | Job |
|------|-----|
| **Desk** | Live risk, pending, settle, place slip, rejects |
| **Book** | Analytics + tickets blotter |
| **Lab** | Learning mults, lessons, edges |
| **Setup** | Paths, CLI cheat-sheet |

Set `NT_PROJECT_ROOT` if the project is not the cwd.  
v5 integration notes for GUI builders: optional panels for `analyze`, `project`, combo policy, agent — **never** a second bankroll engine. See [`docs/MIGRATION.md`](docs/MIGRATION.md) and `desktop/AGENTS.md`.

---

## Layout

| Path | Role |
|------|------|
| `config.yaml` | Rules & numbers (single control-plane) |
| `nt/` | CLI + engines |
| `desktop/` | Local UI (optional) |
| `data/bets.csv` | Era ledger (immutable columns) |
| `data/state/` | Generated bankroll, phase, risk, learning, status |
| `data/edges.jsonl` | Append-only lessons |
| `evidence/` | Research packs + `templates/` |
| `inbox/` · `outbox/` | I/O |
| `history/` | Archives, old rounds, legacy docs |
| `docs/` | Vision, bankroll, research, agent, migration |

---

## Design principles

1. **Code is law** — phase, risk, P/L, empty slips.
2. **Empty slip is success** when nothing clears the bar.
3. **Full history preserved** — era in `data/bets.csv`, rest in `history/`.
4. **No profit guarantee** — process maximizes disciplined +EV attempts under NT rules.
5. **Additive evolution** — new features degrade gracefully; never rewrite history.

---

## Compatibility mode

```yaml
combos:
  enabled: false
agent:
  enabled: false
```

Core v3/v4 workflows unchanged. Migration guide: [`docs/MIGRATION.md`](docs/MIGRATION.md).

---

## Tests

```bash
python -m pytest tests/ -q
```

---

## Disclaimer

Sports betting involves risk of loss. This software enforces process discipline; it does **not** guarantee profit. Use only where legal and with bankroll you can afford to lose.
