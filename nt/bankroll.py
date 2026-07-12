from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nt.bets_io import fnum, load_bets, pending_stake_total, settled_count, settled_pl_sum, utc_now
from nt.config import path_from_config


def compute_bankroll(cfg: dict[str, Any], bets_path: Path | None = None) -> dict[str, Any]:
    """
    Equity = baseline + sum(settled P/L) over the full era ledger (data/bets.csv).

    The era ledger intentionally includes bankroll_archive_up_to_2026_07_01 rows
    (source=era_archive) plus all later bets. Pre-restart history lives under history/
    and does NOT affect equity unless migrated into data/bets.csv.
    """
    path = bets_path or path_from_config(cfg, "bets")
    rows = load_bets(path)
    baseline = float(cfg["bankroll"]["baseline_nok"])
    realized = settled_pl_sum(rows)
    equity = round(baseline + realized, 2)
    pending = pending_stake_total(rows)
    liquid = round(equity - pending, 2)
    n_settled = settled_count(rows)
    n_pending = sum(1 for r in rows if r.get("result") == "Pending")
    n_archive = sum(1 for r in rows if r.get("source") == "era_archive")
    n_live = sum(1 for r in rows if r.get("source") != "era_archive")

    return {
        "baseline_nok": baseline,
        "realized_pl_nok": realized,
        "equity_nok": equity,
        "pending_at_risk_nok": pending,
        "liquid_nok": liquid,
        "settled_count": n_settled,
        "pending_count": n_pending,
        "era_archive_bets": n_archive,
        "post_archive_bets": n_live,
        "total_bets": len(rows),
        "era_start": cfg["bankroll"].get("era_start"),
        "updated_at": utc_now(),
        "formula": "equity = baseline + sum(settled P/L in data/bets.csv); archive+live included",
    }


def write_bankroll_state(cfg: dict[str, Any], bankroll: dict[str, Any]) -> None:
    state_dir = path_from_config(cfg, "state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    json_path = state_dir / "bankroll.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(bankroll, f, indent=2)
        f.write("\n")

    md_path = path_from_config(cfg, "bankroll_md")
    md = f"""# Current Bankroll (generated — do not hand-edit)

**Baseline**: {bankroll['baseline_nok']:.2f} NOK (era start {bankroll.get('era_start')})

**Equity**: **{bankroll['equity_nok']:.2f} NOK**

**Realized P/L**: {bankroll['realized_pl_nok']:+.2f} NOK

**Pending at Risk**: {bankroll['pending_at_risk_nok']:.2f} NOK ({bankroll['pending_count']} bets)

**Liquid**: {bankroll['liquid_nok']:.2f} NOK

**Ledger**: {bankroll['total_bets']} bets total \
({bankroll['era_archive_bets']} from era archive + {bankroll['post_archive_bets']} later)

**Formula**: `{bankroll['formula']}`

**Updated**: {bankroll['updated_at']}
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
