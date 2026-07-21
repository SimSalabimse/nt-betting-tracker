# Capital v2 — Go-Live Checklist

**Status:** Ready for operator enable (default remains **OFF**)  
**Rule bundle:** `br_v2.0.0`  
**Last MC suite:** seed 42, 0 stake-rule violations (after secure buffer softener)

---

## What you are enabling

When `capital_v2.enabled = true` (or env override), the engine uses the **fail-closed** stack:

| Layer | Behaviour |
|-------|-----------|
| L0 | Manual freeze (`capital_segments.freeze`) |
| L1 | DD ≥15% → `size_mode=REDUCED`; ≥25% → `FROZEN` (manual unfreeze) |
| L2 | Weekly hard stop: min(8% liquid SoW, 6 units) |
| L3 | Daily hard stop: min(4% liquid SoD, 3 units) |
| Open room | Phase open budget + **18%** portfolio open-risk on riskable liquid |
| L6 sizing | Unit ladder 10/15/20; REDUCED half/step; never stake in (0, 10) |
| Secure | 40% of profit above ref×1.30, **capped** so working ≥ max(55% equity, 8×unit); ref → working equity |
| Audit | `stake_decisions.jsonl` + `capital_segments.json` |

Ledger equity formula is **unchanged** (engine remains sole bankroll truth).

---

## Preconditions (before first enable)

1. [ ] Phase 2.1–2.5 checkpoints accepted  
2. [ ] Secure buffer softener MC re-run clean (`scripts/run_capital_v2_mc.py`)  
3. [ ] Backup `data/bets.csv` and `data/state/`  
4. [ ] LuminaNT connected to this tracker root; strip shows engine risk after `refresh`  
5. [ ] You know how to **unfreeze**:  
   `python run_nt.py capital unfreeze --confirm`  
   or App **Unfreeze** (confirm dialog)  
6. [ ] Daily time for 1–2 days of **shadow** observation (flag on, small unit stakes)

---

## Enable steps

### Option A — config (persistent)

1. Edit `config.yaml` — ensure block exists:

```yaml
capital_v2:
  enabled: true   # was false — set only when you intend live capital_v2
```

2. Run:

```bash
python run_nt.py refresh
python run_nt.py capital status
```

3. Confirm JSON shows `"capital_v2_enabled": true` and `size_mode` present.

4. Restart / refresh LuminaNT — strip should show **SECURE**, **size_mode**, **OPEN ROOM**, optional **Unfreeze**.

### Option B — environment (session / CI)

```powershell
$env:CAPITAL_V2_ENABLED = "true"
# or: NT_CAPITAL_V2_ENABLED=1
python run_nt.py refresh
python run_nt.py capital status
```

Unset env to restore config default:

```powershell
Remove-Item Env:CAPITAL_V2_ENABLED -ErrorAction SilentlyContinue
```

**Default remains false** if neither config nor env enables it.

---

## Rollback steps (immediate)

1. Set `capital_v2.enabled: false` in `config.yaml` **and** clear env overrides.  
2. `python run_nt.py refresh`  
3. Confirm `capital status` → `capital_v2_enabled: false` and risk JSON has **no** `size_mode`.  
4. Legacy phase stake band + 8% kill-switch resume.  
5. Optional: leave `capital_segments.json` in place (ignored when flag off) or archive it.

---

## Monitoring checklist (first 48h after enable)

| Check | How | Expect |
|-------|-----|--------|
| Flag on | `capital status` | `capital_v2_enabled: true` |
| Secure ≤ equity | segments / strip SECURE | Always |
| Working buffer | after any secure transfer | working ≥ 55% equity (at transfer time) |
| Floor | any recommend | No stake in (0, 10) |
| Freeze | after large DD | `size_mode=FROZEN`, Bet STOP; Unfreeze only after review |
| Audit | `data/state/stake_decisions.jsonl` | Grows on recommend under flag |
| Snapshots | day/week in segments | Roll at Oslo midnight / ISO week |
| App strip | Lumina DeskStrip | SECURE / MODE / rooms when v2 risk fields present |

---

## Operator commands

```bash
python run_nt.py capital status
python run_nt.py capital segments
python run_nt.py capital unfreeze --confirm --actor YOU --reason "reviewed DD"
python run_nt.py refresh
python scripts/run_capital_v2_mc.py 42 50   # optional re-stress (offline)
```

---

## Residual risks (honest)

1. **Sticky freeze** — requires explicit unfreeze; do not automate away.  
2. **Secure still reduces riskable capital** — buffer prevents *near-zero working at transfer*, but subsequent losses can still shrink working.  
3. **Unit 15/20** rare until liquid ≥1500.  
4. **App Unfreeze** needs Tauri + live repo (not demo browser).  
5. First live day: prefer dry-run recommend before logging Pending.

---

## Explicit non-action

This document does **not** enable the flag. Operator must set `enabled: true` or env deliberately after accepting this go-live pack.
