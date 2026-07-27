# Football Simulation & Calibration

**Version:** 6.0 · Optional research tools · Never bypass engine rules

## Strategic rationale

| Choice | Why |
|--------|-----|
| Football-only (Poisson + Dixon–Coles) | Highest ROI for Oddsen; O/U + BTTS + 1X2 map cleanly to scorelines |
| Not multi-sport | Depth beats breadth; tennis/NBA later only if calibration is strong |
| Suggest p_model, don't auto-bet | Garbage-in prevention; human + evidence remain law |
| Calibration log | Highest-value learning after honest p_model tracking |
| Separate from `nt project` | Bankroll path sim ≠ match outcome model |

At ~500–2 000 NOK, **process + calibrated probabilities** beat a flashy universal simulator.

---

## When simulation helps

- Football **Over/Under 1.5–3.5**, **BTTS**, rough **1X2 / DNB**
- You have **credible λ or xG inputs** (FBref sample, not vibes)
- You want a **transparent** probability before writing evidence
- You will still **haircut** via engine and require **grade B+** packs

## When to avoid / distrust sim

- Thin xG samples, cup chaos with no data
- Markets sim doesn't model well (player props, correct score as primary bet, cards/corners)
- Using sim to **force** EV over the bar
- Treating fair odds from sim as "surely +EV vs NT"
- Non-football sports (out of scope for this module)

---

## Model (short)

1. Expected goals λ_home, λ_away  
   - Direct, or from xG for/against × league avg × home advantage × soft multipliers  
2. Scoreline matrix: independent Poisson × Dixon–Coles τ(ρ) on 0-0/1-0/0-1/1-1  
3. Aggregate → market probabilities  
4. Human reviews warnings → picks selection → evidence pack → recommend  

**Confidence** is degraded by low source quality, extreme multipliers, or incomplete xG.

---

## CLI

### Simulate

```bash
# From template
python run_nt.py simulate --input inbox/sim_match_template.yaml

# Direct lambdas
python run_nt.py simulate --home "Bodø/Glimt" --away "Brann" \
  --lambda-home 1.85 --lambda-away 1.05 --league Eliteserien

# xG building blocks
python run_nt.py simulate --match "Home vs Away" \
  --home-xg-for 1.7 --home-xg-against 1.0 \
  --away-xg-for 1.2 --away-xg-against 1.4 \
  --selection "BTTS Ja" --write-evidence

# JSON only
python run_nt.py simulate --lambda-home 1.5 --lambda-away 1.2 --json
```

Outputs:

- Terminal markdown + `outbox/SIM_*.md` / `SIM_LATEST.md`
- Optional seeded `evidence/*.json` (**TODO sources still required**)
- Audit line in `data/state/sim_audit.jsonl`

### Calibrate

```bash
python run_nt.py calibrate rebuild   # from bets.csv + decisions
python run_nt.py calibrate report    # Brier, bias, bins → outbox/CALIBRATION.md
```

On every settle with known `p_model`, a row is appended to `data/state/calibration.jsonl`.

Metrics:

| Metric | Meaning |
|--------|---------|
| **Brier** | Mean (p−y)² — lower better |
| **Bias p−y** | >0 overconfident; <0 underconfident |
| **Reliability bins** | Mean p vs empirical win rate by p bucket |
| **By band/market/phase** | Where your p_model fails |

---

## Workflow integration

```
research board
    → (optional) simulate football match
    → write/fill evidence with p_model from sim + real sources
    → research ready
    → recommend   # haircut, EV, phase, risk
    → place
    → settle      # calibration row if p_model known
    → calibrate report
```

**Empty slip after research still success.** Sim never forces a bet.

---

## Config (`simulation:`)

```yaml
simulation:
  enabled: true
  calibration_enabled: true
  audit_sims: true
  football:
    default_league_avg_xg: 1.35
    default_home_advantage: 1.08
    default_rho: -0.05
    max_goals: 10
  sport_scope: [football]
```

Set `enabled: false` to hard-disable simulate.

### Optional lake-backed λ priors (`data_platform.sim_features`)

When the sibling **`nt-data-platform`** package is installed and both flags are on:

```yaml
data_platform:
  enabled: true
  lake_root: null          # or absolute path; env NT_DATA_LAKE wins
  sim_features: true       # default false — required for lake λ
```

then `nt/sim_football.py` may call `DataClient.suggest_lambdas` to fill **missing** `lambda_home` / `lambda_away` from goals-based form + league rates (`sim_inputs_compat`).

| Rule | Behaviour |
|------|-----------|
| Default | **Off** (`enabled: false`, `sim_features: false`) — no lake call |
| Explicit λ | User-supplied `lambda_home`/`lambda_away` **win**; lake not called |
| Thin sample | Lake returns null λ → no invent; still need manual λ/xG |
| Warnings | Include **`goals_based_proxy`** (goals rates proxy, not true xG) + `lake_lambda_prior` |
| Evidence | **Never** auto-written — still needs `--write-evidence` + human sources |
| Tennis / basketball | **Untouched** — no lake priors in those modules |

See also `docs/SOURCES.md` (adapter) and the platform design for `suggest_lambdas` contracts.

---

## LuminaNT GUI

Safe surfaces:

- Lab: open `outbox/SIM_LATEST.md`, `outbox/CALIBRATION.md`
- Show calibration Brier/bias chips (read `data/state/calibration.jsonl` or CLI JSON)
- **Do not** auto-run recommend from sim alone
- Seed evidence only with user confirm

---

## Future (not now)

- Tennis Elo sim — only after football calibration n≥50 and process is stable  
- Full bivariate Poisson estimation from league data dumps  
- Auto λ from scraped FBref (ToS/legal review required)  
- Tennis/basketball lake auto-priors (only after football `sim_features` path is proven)

---

## Compatibility

- No changes to `bets.csv` columns  
- Calibration/sim audit are new append-only state files  
- Recommend/settle contracts unchanged (settle gains optional calibration side-effect)
