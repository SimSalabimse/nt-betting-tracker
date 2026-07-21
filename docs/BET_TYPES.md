# Bet Types, Combos & Systems

## Default: singles

**Singles are the system default** for discipline, clean attribution, and learning mults.

| Rule | Detail |
|------|--------|
| Preferred | One selection, one stake, one settle |
| Staking | Phase band × EV fraction × learning mult × high-odds mult |
| Evidence | Grade B+ (A if high odds) |
| Correlation | N/A |

Empty slip with zero singles is better than a forced double.

---

## Doubles / small accumulators

Allowed only when **all** of the following hold:

1. **Phase gate:** `max_doubles_per_round ≥ 1` (Phase 2+ in default ladder).
2. **Config gate:** `combos.enabled` true and aggressiveness allows doubles.
3. **Per-leg quality:** each leg would pass portfolio rules as a single (EV, grade, p_model, not soft-blocked).
4. **Leg count:** 2 legs for doubles; ≤ `norsk_tipping.max_legs_in_combo` (default 3).
5. **Correlation:** not same match; prefer different leagues / kickoff clusters (see scoring below).
6. **Stake:** reduced vs two independent singles — apply `combos.stake_multiplier` (default 0.55–0.70).
7. **Round cap:** count against `max_doubles_per_round`.
8. **Evidence:** either one combo pack referencing both legs, or grade B+ packs per leg.

### When doubles can make sense

- Two independent strong singles that individually clear the bar, and combined odds still within your process comfort.
- You have spare daily risk **and** would otherwise place only one of them due to slot limits (rare).

### When doubles are forbidden (process)

- Phase 1A / 1B (max doubles = 0).
- Either leg is high-odds (≥ threshold) unless `combos.allow_high_odds_legs` (default **false**).
- Same match multi-market “synthetic double”.
- Trying to “boost odds” on two mediocre legs.

---

## Higher combos / systems (patents, etc.)

| Type | Status in this OS |
|------|-------------------|
| Trebles+ | Only if phase allows, max_legs, and aggressiveness ≥ `aggressive`; **discouraged** |
| Patents / systems | **Not automated.** Manual logging only if you fully understand NT payout rules |
| “Lucky” / bonus paths | Out of scope — do not encode as edge |

If you place a system bet outside the engine, log it with clear `notes` and treat learning weight carefully.

---

## Correlation checks

`nt/combos.py` scores a candidate multi-leg set:

| Signal | Penalty |
|--------|---------|
| Same match | Hard reject |
| Same league + same day | Medium penalty |
| Shared team across legs | Hard reject |
| Same market family all legs | Soft penalty |
| Kickoffs within 2 hours same region | Soft penalty |

Reject if score below `combos.min_correlation_score` (higher = more independent).

---

## Staking adjustment

```
combo_stake = single_stake_proxy * combos.stake_multiplier
combo_stake = min(combo_stake, phase.stake_max, remaining_risk)
```

Combined EV uses independent approximation only when correlation is low:

```
p_joint ≈ ∏ p_adj_i   # independence assumption — invalid if correlated
EV_combo ≈ p_joint * odds_combo - 1
```

If independence is dubious → **do not place**.

---

## Aggressiveness presets (`config.yaml` → `combos.aggressiveness`)

| Preset | Doubles | Trebles | High-odds legs | Stake mult |
|--------|---------|---------|----------------|------------|
| `off` | never | never | n/a | n/a |
| `conservative` (default) | phase-gated, rare | never | no | 0.55 |
| `standard` | phase-gated | phase 4+ only | no | 0.65 |
| `aggressive` | more slots | up to max_legs | optional | 0.75 |

Engine still cannot exceed phase `max_doubles_per_round`.

---

## Logging combos in the ledger

NT often shows combo as one ticket. Log as **one row** with:

- `selection` describing both legs (e.g. `TeamA Win + TeamB Over 2.5`)
- `decimal_odds` = ticket odds
- `notes` include `COMBO legs=2` and leg identifiers
- `market_type` = `Combo` when possible

Decisions JSONL may store `legs: [...]` for attribution (optional).

---

## Integration points

| Component | Role |
|-----------|------|
| `config.yaml` `combos` | Policy knobs |
| `nt/combos.py` | Validate + score + stake |
| `nt/portfolio.py` | Enforces phase double caps; optional combo candidates |
| `nt recommend` | Singles-first; combo only if enabled and candidates tagged |
| Desktop GUI | Display notes / COMBO flag; no separate staking engine |

---

## Decision flowchart

```
Is phase max_doubles = 0? ──yes──► singles only
         │ no
combos.enabled? ──no──► singles only
         │ yes
Each leg clears single bar? ──no──► reject combo
         │ yes
Correlation OK? ──no──► reject combo
         │ yes
Stake fits remaining risk? ──no──► reject or reduce
         │ yes
Place as one ticket + log COMBO
```
