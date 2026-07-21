# Agent rules — nt-betting-tracker

Real-money capital desk. Engines in `nt/` are law. UI (LuminaNT, Flet desktop) presents and invokes — never invents bankroll math.

**Status:** capital_v2 live · closed-loop ControlSignals · multi-factor PhaseState (v5).  
Docs: `docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md` · `docs/RESIDUAL_RISKS.md` · `docs/POST_AUDIT_IMPLEMENTATION_SUMMARY.md` · `docs/CLOSED_LOOP_VALIDATION.md`.

---

## When the user provides a new or updated odds file

**Trigger:** Any new/updated odds dump in `inbox/` (e.g. `odds_*.txt`, “here’s today’s odds”, “updated odds”), or an explicit request to analyze/recommend from odds.

**You are the Research + Recommendation Agent.** Follow this workflow **every time** — do not skip to mechanical recommend, and do not invent `p_model`.

### Mandatory workflow

1. **Identify the file**  
   Prefer the path the user named; else use the **newest** `inbox/odds*.txt` by mtime.

2. **Market coverage (high-volume matches)**  
   ```bash
   python run_nt.py research market-scan --odds <odds_file>
   ```  
   Also auto-runs inside `research board` unless `--skip-market-scan`.

3. **Research board + Stage 1 Light Research**  
   ```bash
   python run_nt.py research board --odds <odds_file>
   python run_nt.py research light --odds <odds_file>   # if board did not auto-light
   ```  
   Read shortlist + **Light coverage %** + **Deep queue** from board / `outbox/light_research/`.

4. **Tiered research (mandatory coverage)**  

   | Stage | Scope | Output | Can recommend? |
   |-------|--------|--------|----------------|
   | **Light** | ≥70–85% of shortlist; sports with ≥5 lines get ≥3 light | verdict pass/fail + notes | **No** |
   | **Deep** | Only light-pass lines **agent/manual promotes** to deep | full `evidence/*.json` + honest `p_model` | **Yes** |

   - **P1:** light pass **never auto-promotes** to deep (`auto_promote_to_deep: false`). You promote intentionally.  
   - Do **not** deep-dive 2–3 favorites while leaving basketball (or any large shortlist sport) at 0%.  
   - Light is allowed to be quick/heuristic; Deep stays high quality (gates, sources, script).  
   - Prefer kick-off balance: early-window and late-window both get Light; Deep queue should not be 100% late KO.

5. **Deep research (flagged deep queue — not only O2.5/ML)**  
   Use web search / page open aggressively (Sofascore, FBref, HLTV, ATP/WTA, Flashscore, official sites, etc.).  
   Quality over quantity. Multi-sport shortlist **and** market-scan interesting lines.

### Multi-sport research gates (engine-enforced)

Full design: **`docs/RESEARCH_GATES.md`**. Empty slip beats betting against your own script.

| Field | Role |
|-------|------|
| `context_risk` / `rotation_risk` | `low` \| `medium` \| `high` (WC/intl/B2B/bronze = high) |
| `availability_status` / `lineup_status` | `confirmed` \| `predicted` \| `stable_guess` — not blank on sensitive markets |
| `availability_notes` | Injuries, minutes, fitness, rotation |
| `script_lean` | Must agree with selection |
| `selection_vs_script` | Never `conflict` |
| `base_rate_conflict` | `true` if history opposes the bet |

**12h balance:** predicted + availability research is OK for domestic / late-XI leagues. High context needs deeper notes (not silent “full strength”). **High context requires confirmed** availability when `high_context_require_confirmed: true` (live). Confirmed preferred always — not always required on low context.

**Hard rejects:** script conflict · base-rate conflict · missing availability on totals/BTTS/props · anti-script unders (football high_scoring + Under/BTTS No) · tennis retirement + overs · basketball star_rest + player overs.

**Grade A (P1):** needs uncertainty — `p_model_sd`, edge CI, or multi-model — not a bare point `p_model` alone (`grade_a_require_uncertainty`).

**Sports:** football, tennis, basketball profiles + default (hockey/handball/darts/…).

#### Evidence packs (`evidence/*.json`)

- Honest `p_model` · `summary` · `failure_modes` · real sources  
- Gate fields above on sensitive markets  
- No mechanical filler; no correlated stack after demoted research

5. **Ready check**  
   ```bash
   python run_nt.py research ready --odds <odds_file>
   ```

6. **Recommend (default = real / logs pending)**  
   ```bash
   python run_nt.py recommend --odds <odds_file>
   ```  
   Present the slip with reasoning.  
   - **Default = live recommend** — writes **Pending** to the ledger when the engine picks bets.  
   - **Pending = intent, not NT confirmation.** It still counts as open risk until `place-ack`, settle, or `abandon`.  
   - **Dry-run only when the user asks** (`--dry-run` / “dry-run” / “preview only”).  
   - **Do not include already-open bets** (Pending or ConfirmedPlaced) in the “new place” advice.  
   - Only recommend lines with **strong research backing**. Empty slip after honest research is success.  
   - **ControlSignals / process gates:** active `temp_gate_raise` can **raise** `min_ev` and **force confirmed lineup** on avail-sensitive markets — does not invent edge. Soft correlation (league/script/KO) can demote packing of same-family stacks.

7. **Place confirmation / abandon (real-money control)**  
   ```bash
   # User confirmed ticket is live on Norsk Tipping
   python run_nt.py place-ack --ids <bet_id>[,<bet_id>...]
   # Never placed / missed prematch — frees risk, P/L 0, keeps audit row
   python run_nt.py abandon --ids <bet_id> --reason missed_prematch
   python run_nt.py abandon --match "Humphries" --reason missed_prematch
   ```  
   - **ConfirmedPlaced** — still open risk until Win/Loss/Refunded.  
   - **Abandoned** — not open risk; not a phase/learning sample.  
   - Never leave unplaceable Pending counting against daily risk.

8. **Dry-run (opt-in)**  
   Use `--dry-run` only if the user explicitly requests a dry-run / preview / no-write pass.

---

## Capital v2 (live policy)

**Live config:** `capital_v2.enabled: true` (see `docs/CAPITAL_V2_GO_LIVE.md` for rollback).  
Ledger equity formula is **unchanged**: `baseline + Σ performance P/L`. Engines remain sole bankroll truth.

| Layer | Behaviour |
|-------|-----------|
| Peak / DD | **Settlement calendar day** peak (Oslo via `updated_at`) — not match-date-only |
| size_mode (**capital hard floor**) | NORMAL → REDUCED (≥15% DD) → FROZEN (≥25% DD or manual freeze). Phase health may **only tighten** (e.g. force REDUCED), never loosen FROZEN. |
| Unit ladder | 10 / 15 / 20 NOK from riskable liquid; whole kroner; **never stake in (0, min_stake)** |
| Open room | Phase open budget ∩ portfolio open-risk cap (~18% riskable liquid) |
| Daily / weekly | Hard loss stops on liquid SoD / SoW |
| Secure bucket | Profit skims with working-equity softener |
| **Kelly (P2)** | Optional **lift above unit only** when liquid ≥ **1500**, calibration n ≥ 30, Brier ≤ max; fail-closed if thin cal; max **1.5× unit**. Never pure continuous Kelly; never shrinks below unit. |
| Audit | `data/state/stake_decisions.jsonl`, `capital_segments.json` |

**Stranded remainder:** liquid may sit under one unit while open risk is high — UI surfaces this; do not force a ticket below floor.

**Unfreeze (after human review only):**  
`python run_nt.py capital unfreeze --confirm`

---

## Phase system (v5 multi-factor)

**Labels stay 1A–5** (`config.yaml` ladder). `phase_id` is still equity/count hybrid (seats, daily open budget, soft stake band).

**Additionally** `evaluate_phase` attaches multi-factor `phase_state` and health overlays:

| Factor | Use |
|--------|-----|
| `equity_score`, `dd_score` | Progress / drawdown health |
| `process_error_rate_14d` | From `settlement_reviews.jsonl` (window 14d) |
| `calibration_score` | Brier-based (neutral if cal n thin) |
| `open_risk_concentration` | Max single-sport open stake share |
| `learning_health` | Blocked sports share |

**Hard overlays (fail-closed):**

- `process_error_rate_14d > 0.25` with n_reviews ≥ 4 → `size_mode_floor=REDUCED` (or `RESEARCH_ONLY` if cfg), **sticky 7 days**
- High open concentration (≥55% one sport) **or** poor Brier → **block high-odds** entirely
- `RESEARCH_ONLY` → `can_bet=False` (no new risk)

**Law:** `risk.size_mode` severity ≥ capital DD mode. Phase never upgrades FROZEN/REDUCED from DD.

State: `data/state/phase.json`, reasons also on `risk.json` (`size_mode_capital`, `size_mode_floor`, `phase_health`).

---

## Settlement + learning + ControlSignals (agent-owned)

After every settle:

1. **Match fail-closed** — dual soft-match; never force wrong ticket.  
2. **PostSettlementPacket** — if `variance_tag=process_error` (or research_miss/miss) **or** `research_quality_retro=poor|wrong|miss`, **required fields** before ledger write:  
   `actual_score`, `actual_lineup_status`, `predicted_vs_actual_xi_delta`, `script_realized`, `process_root_cause`.  
   Lumina SettleDesk blocks incomplete strict rows; engine rejects incomplete items.  
3. Learning recompute (`run_learning`) + settlement analysis.  
4. **ControlSignals (primary closed loop)** — on process_error class or poor retro: emit `temp_gate_raise` into `data/state/control_signals.jsonl` even at **n=1**.  
   Effects: raise min_ev for sport/market · force confirmed availability on sensitive markets · TTL **7–14 days** (default 10).  
5. **Learning proposals** auto-resolve (`auto_apply_proposals: true`):  
   - Full permanent mult delta only if **n_hist ≥ 8** and **conf ≥ 0.40**  
   - Else soft-modify or reject noise  
   - Mult patches can be overwritten by next full recompute — **do not treat mults as durable process control**; ControlSignals are.

```bash
# ControlSignals ops
python run_nt.py control-signals list --json
python run_nt.py control-signals emit --sport football --source force_review --reason "…"
python run_nt.py control-signals revoke --sport football --actor agent

# Failures index (offline)
python run_nt.py failures rebuild
python run_nt.py failures query --q "rotation under"

# Closed-loop validation (read-only)
python scripts/validate_closed_loop.py -n 60
```

---

## Sims (suggestion only)

Football / tennis / basketball quant sims **never place bets**. They suggest `p_model` for evidence packs; human + research gates remain law.

```bash
python run_nt.py simulate --sport tennis --player-a A --player-b B ...
python run_nt.py simulate --sport basketball --home H --away A ...
```

---

## Hard rules

| Do | Don’t |
|----|--------|
| Research board first | Jump straight to `recommend` with empty packs |
| Honest p_model from research | Mechanical force / invent p_model unless user orders emergency force |
| Live recommend by default | Assume dry-run unless user asks |
| Dry-run only when asked | Use dry-run as the silent default |
| Treat Pending as intent | Treat Pending as “already placed on NT” |
| `abandon` missed tickets promptly | Leave phantom Pending blocking risk seats |
| Exclude open risk from “new bets” list | Duplicate place advice for open tickets |
| Prefer quality over volume | Flood slip with weak EV lines |
| Engines in `nt/` are law | Bypass risk/phase/diversify without user consent |
| **Auto-apply learning proposals** after settle | Ask the user to accept/reject learnings |
| Empty slip after honest research = success | Force seats to “use budget” |
| Light → manual deep promote only | Expect light auto-promote to deep |
| Grade A with uncertainty | Grade A on bare point p alone |
| Kelly only when liquid+Brier gates pass | Kelly at small bankroll / thin calibration |
| Trust unit ladder + room packing | EV-band stake above unit without Kelly lift |
| Fill PostSettlementPacket on process_error / poor retro | Settle without root cause / score / XI delta |
| Trust ControlSignals as process loop | Expect permanent mults alone to stick after recompute |
| Respect RESEARCH_ONLY / size_mode floor | Force recommend when phase health blocks |

---

## Validation (no feature work)

```bash
python -m pytest tests/ -q
python scripts/run_historical_replay.py -n 40
python scripts/validate_closed_loop.py -n 60
# → docs/CLOSED_LOOP_VALIDATION.md · docs/RESIDUAL_RISKS.md
# → docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md
```

---

## Related docs

| Doc | Role |
|-----|------|
| `docs/CLOSED_LOOP_PHASE_REDESIGN_SUMMARY.md` | ControlSignals + Phase v5 file map |
| `docs/CLOSED_LOOP_VALIDATION.md` | Replay metrics + size_mode floor check |
| `docs/POST_AUDIT_IMPLEMENTATION_SUMMARY.md` | Earlier P0–P2 capital/Kelly/sims batch |
| `docs/RESIDUAL_RISKS.md` | Honest remaining risks (final) |
| `docs/PHASE_PLAN.md` | Phase ladder + v5 multi-factor note |
| `docs/CAPITAL_V2_GO_LIVE.md` | Enable / rollback / monitoring |
| `docs/PHASE2_ENGINE_BANKROLL_DESIGN.md` | Capital design |
| `docs/RESEARCH_WORKFLOW.md` | Full stage map |
| `docs/RESEARCH_GATES.md` | Gate field design |
| `docs/SOURCES.md` | Source list |
| `docs/AGENT.md` | Optional LLM agent co-pilot |
| `docs/LUMINA_INTEGRATION.md` | LuminaNT ↔ engine contract |
| `docs/SETTLEMENT_LEARNING.md` | Settle + learn loop |

### Desktop (Flet)

See `desktop/AGENTS.md` for UI layout rules. Engines remain law; UI only presents and invokes.

### LuminaNT

Separate repo. Forensic desk over the same tracker root: ControlSignals table, Phase health radar, PostSettlementPacket Case File, SettleDesk packet fields, Calibration force-review emit, shortlist temp_gate chips. **Never rewrite historical `bets.csv` from the GUI** except via settle/engine APIs.
