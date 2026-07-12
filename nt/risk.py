from __future__ import annotations

import json
from datetime import date
from typing import Any

from nt.bets_io import fnum, load_bets
from nt.config import path_from_config


def daily_risk_cap(equity: float, phase: dict[str, Any]) -> float:
    """
    Dynamic daily risk budget.

    cap = clamp(equity * daily_risk_pct, floor, ceil)

    Changes automatically when equity or phase changes — no manual plan edit.
    """
    raw = equity * float(phase["daily_risk_pct"])
    floor = float(phase["daily_risk_floor"])
    ceil = float(phase["daily_risk_ceil"])
    return round(max(floor, min(ceil, raw)), 2)


def stop_day_loss_limit(cfg: dict[str, Any], equity: float) -> float:
    risk_cfg = cfg.get("risk", {})
    pct = float(risk_cfg.get("stop_day_loss_pct_of_equity", 0.08))
    floor = float(risk_cfg.get("stop_day_loss_floor_nok", 40))
    return round(max(floor, equity * pct), 2)


def day_realized_pl(rows: list[dict[str, str]], day: str | None = None) -> float:
    day = day or date.today().isoformat()
    total = 0.0
    for r in rows:
        if r.get("date") != day:
            continue
        if r.get("result") == "Pending":
            continue
        total += fnum(r.get("p_l_nok")) or 0.0
    return round(total, 2)


def day_pending_risk(rows: list[dict[str, str]], day: str | None = None) -> float:
    """Pending stakes for events logged today (or all open pending if day is None for portfolio)."""
    day = day or date.today().isoformat()
    total = 0.0
    for r in rows:
        if r.get("result") != "Pending":
            continue
        # Count all open pending against today's risk budget (multi-run days share one budget)
        total += fnum(r.get("stake_nok")) or 0.0
    return round(total, 2)


def evaluate_risk(
    cfg: dict[str, Any],
    equity: float,
    phase: dict[str, Any],
    rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))

    cap = daily_risk_cap(equity, phase)
    stop_lim = stop_day_loss_limit(cfg, equity)
    today = date.today().isoformat()
    realized = day_realized_pl(rows, today)
    open_pending = day_pending_risk(rows, today)
    remaining = round(cap - open_pending, 2)
    stopped = realized <= -stop_lim
    reasons = []
    if stopped:
        reasons.append(f"KILL-SWITCH: today P/L {realized:+.2f} <= -{stop_lim:.2f}")
    if remaining <= 0:
        reasons.append(f"daily risk exhausted: pending {open_pending:.2f} / cap {cap:.2f}")

    return {
        "date": today,
        "equity_nok": equity,
        "phase_id": phase["phase_id"],
        "daily_risk_cap_nok": cap,
        "daily_risk_pct": phase["daily_risk_pct"],
        "open_pending_risk_nok": open_pending,
        "remaining_risk_nok": max(0.0, remaining),
        "today_realized_pl_nok": realized,
        "stop_day_loss_limit_nok": stop_lim,
        "stopped": stopped,
        "can_bet": (not stopped) and remaining >= float(cfg["norsk_tipping"]["min_stake_nok"]),
        "reasons": reasons,
        "formula": "daily_cap = clamp(equity * phase.daily_risk_pct, floor, ceil)",
    }


def write_risk_state(cfg: dict[str, Any], risk: dict[str, Any]) -> None:
    state_dir = path_from_config(cfg, "state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "risk.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(risk, f, indent=2)
        f.write("\n")
