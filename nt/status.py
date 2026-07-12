from __future__ import annotations

from typing import Any

from nt.bets_io import band_roi_stats, fnum, load_bets
from nt.config import path_from_config


def generate_status(
    cfg: dict[str, Any],
    bankroll: dict[str, Any],
    phase: dict[str, Any],
    risk: dict[str, Any],
) -> str:
    rows = load_bets(path_from_config(cfg, "bets"))
    bands = band_roi_stats(rows)
    band_lines = []
    for b in sorted(bands.keys()):
        s = bands[b]
        band_lines.append(
            f"| {b} | {int(s['n'])} | {s['roi']*100:.1f}% | {s['pl']:+.1f} |"
        )

    pending = [r for r in rows if r.get("result") == "Pending"]
    pend_lines = (
        "\n".join(
            f"- {r['date']}: {r['match']} / {r['selection']} @ {r['decimal_odds']} "
            f"stake {r['stake_nok']}"
            for r in pending[:20]
        )
        or "_None_"
    )

    thr = cfg["selection"]["high_odds_threshold"]
    md = f"""# NT Status (auto-generated)

## Bankroll
- **Equity**: {bankroll['equity_nok']:.2f} NOK
- Realized P/L: {bankroll['realized_pl_nok']:+.2f} NOK (baseline {bankroll['baseline_nok']})
- Pending risk: {bankroll['pending_at_risk_nok']:.2f} NOK
- Liquid: {bankroll['liquid_nok']:.2f} NOK
- Ledger: {bankroll['total_bets']} bets ({bankroll['era_archive_bets']} archive + {bankroll['post_archive_bets']} later)

## Phase (auto)
- **{phase['phase_id']}** — {phase.get('label','')}
- Stake band: {phase['stake_min']:.0f}–{phase['stake_max']:.0f} NOK
- Max bets/round: {phase['max_bets_per_round']} | Max doubles: {phase['max_doubles_per_round']}
- Rolling ROI: {f"{phase['rolling_roi']*100:.1f}%" if phase.get('rolling_roi') is not None else "n/a"}

## Daily risk (auto — changes with equity/phase)
- Cap: **{risk['daily_risk_cap_nok']:.2f} NOK** (`{risk['formula']}`)
- Open pending: {risk['open_pending_risk_nok']:.2f}
- Remaining today: **{risk['remaining_risk_nok']:.2f} NOK**
- Today P/L: {risk['today_realized_pl_nok']:+.2f} | Stop if ≤ -{risk['stop_day_loss_limit_nok']:.2f}
- Can bet: **{risk['can_bet']}**

## High odds policy
- Odds **> {thr} are allowed** when evidence grade **A**, EV ≥ high-odds min after haircut, and stake uses high-odds multiplier.
- Historical bad band ROI raises the EV bar further — it does not hard-ban the band.

## ROI by odds band (this era ledger)
| Band | n | ROI | P/L |
|------|---|-----|-----|
{chr(10).join(band_lines) if band_lines else "| — | 0 | — | — |"}

## Open pending
{pend_lines}

## Your workflow
1. Put odds in `inbox/`
2. `python -m nt recommend --odds inbox/YOURFILE.csv`
3. Place bets from `outbox/PLACE_THESE.md`
4. Put results in `inbox/`
5. `python -m nt settle --results inbox/YOUR_RESULTS.yaml`

Updated: {bankroll.get('updated_at','')}
"""
    return md


def write_status(cfg: dict[str, Any], bankroll: dict[str, Any], phase: dict[str, Any], risk: dict[str, Any]) -> None:
    path = path_from_config(cfg, "status")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_status(cfg, bankroll, phase, risk), encoding="utf-8")
