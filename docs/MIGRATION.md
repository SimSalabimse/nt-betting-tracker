# Migration & Compatibility Guide (v5)

## Guarantee

Upgrading to v5 is **additive**. Existing ledgers, archives, evidence files, and CLI workflows continue to work without conversion scripts.

## What stays byte-compatible

| Asset | Status |
|-------|--------|
| `data/bets.csv` header (`BET_HEADER`) | Unchanged |
| Historical bet rows | Never rewritten by upgrade |
| `history/archives/*` | Untouched |
| `data/edges.jsonl` | Append-only; old lines still parse |
| `evidence/*.json` | Old minimal schema still grades |
| `python run_nt.py status\|recommend\|settle\|validate\|refresh\|learn` | Same flags |
| Desktop / LuminaNT file contracts | Same paths and engines |

## What is new (safe defaults)

| Addition | Default if missing in config |
|----------|------------------------------|
| `combos.*` | Singles-only behaviour (equivalent to off/conservative + phase caps) |
| `agent.*` | Disabled |
| `projection.*` | Built-in simulation defaults |
| `research.*` | Built-in source lists / templates |
| New CLI: `analyze`, `project`, `research`, `agent`, `edges` | Optional |
| Optional evidence fields | Ignored if absent |
| `data/state/agent_audit.jsonl` | Created only when agent used |

## Compatibility mode

If you want the **strict pre-v5 surface**:

```yaml
# config.yaml
combos:
  enabled: false
  aggressiveness: off
agent:
  enabled: false
learning:
  enabled: true   # pre-existing; leave as you prefer
```

Do not remove phase / selection / risk keys — those were already control-plane.

## Config merge behaviour

`nt.config.load_config` still returns the YAML mapping as-is. New modules call helpers that apply **defaults when keys are missing**, so an old `config.yaml` without `combos` / `agent` keeps working.

## Desktop / LuminaNT

| Integration | Action |
|-------------|--------|
| Equity / phase / risk panels | No change required |
| Recommend / settle buttons | Keep calling existing engines |
| New features | Optional: surface `analyze` report, combo notes, agent panel |
| `NT_PROJECT_ROOT` | Still supported |

If the GUI hard-codes command lists, add new subcommands as optional menu items — do not remove old ones.

## Rollback

1. Keep git history / tag before upgrade.
2. New modules can be deleted; engines for bankroll/phase/recommend remain.
3. Do not delete `data/` or `history/` when rolling back code.

## Validation after upgrade

```bash
python run_nt.py validate
python run_nt.py status
python run_nt.py refresh
python -m pytest tests/ -q
```

Equity and phase should match pre-upgrade expectations (within normal daily settle changes).

## v6 simulation / calibration (additive)

| Addition | Default |
|----------|---------|
| `simulation:` config block | Enabled; football-only |
| `nt simulate` | Optional research tool |
| `nt calibrate report\|rebuild` | Optional learning |
| `data/state/calibration.jsonl` | Created on settle/rebuild |
| `data/state/sim_audit.jsonl` | Created when sims run |
| Settle side-effect | Appends calibration row if p_model known |

Disable: `simulation.enabled: false` and/or `calibration_enabled: false`.

## Breaking changes

**None intentional.** If you find one, treat it as a bug: restore prior behaviour and gate the new path behind config.
