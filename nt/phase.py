from __future__ import annotations

import json
from typing import Any

from nt.bets_io import fnum, is_performance_settled, load_bets
from nt.config import path_from_config


def _rolling_roi(rows: list[dict[str, str]], n: int) -> float | None:
    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    if not settled:
        return None
    window = settled[-n:]
    stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in window)
    pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in window)
    if stake <= 0:
        return None
    return pl / stake


def _peak_equity(rows: list[dict[str, str]], baseline: float) -> float:
    """Max end-of-day equity on the settled curve (Win/Loss/Refunded only)."""
    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    if not settled:
        return baseline
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or r.get("created_at") or ""))
    peak = baseline
    cum = 0.0
    by_date: dict[str, float] = {}
    for r in settled:
        cum += fnum(r.get("p_l_nok")) or 0.0
        d = r.get("date") or ""
        by_date[d] = baseline + cum
    for eq in by_date.values():
        if eq > peak:
            peak = eq
    return round(peak, 2)


def _phase_order(cfg: dict[str, Any]) -> list[str]:
    return list(cfg["phases"].keys())


def evaluate_phase(
    cfg: dict[str, Any],
    equity: float,
    settled_count: int,
    rows: list[dict[str, str]] | None = None,
    current_phase: str | None = None,
) -> dict[str, Any]:
    """
    Phase selection (v4 safe hybrid):

    1. equity_phase  = highest phase whose enter_equity is met
    2. count_phase   = highest phase whose enter_settled is met
    3. count may advance at most one step above equity_phase **only if**
       rolling ROI >= min_rolling_roi (default 0% — no advance while red)
    4. demote one step if rolling ROI deeply negative
    5. demote one step if equity is in a large drawdown vs peak equity
    6. at most one step advance vs previous written phase
    """
    phases = cfg["phases"]
    order = _phase_order(cfg)
    stability = cfg.get("phase_stability", {})
    min_roll = int(stability.get("min_rolling_settled", 25))
    min_roi = float(stability.get("min_rolling_roi", 0.0))
    demote_roi = float(stability.get("demote_if_rolling_roi_below", -0.10))
    demote_n = int(stability.get("demote_min_settled", 25))
    dd_pct = float(stability.get("demote_drawdown_pct_of_peak", 0.12))

    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))

    baseline = float(cfg.get("bankroll", {}).get("baseline_nok", 500.0))
    peak = _peak_equity(rows, baseline)
    roll = _rolling_roi(rows, min_roll)
    stable_enough = roll is None or roll >= min_roi

    equity_phase = order[0]
    for pid in order:
        if equity >= float(phases[pid].get("enter_equity", 0)):
            equity_phase = pid

    count_phase = order[0]
    for pid in order:
        if settled_count >= int(phases[pid].get("enter_settled", 0)):
            count_phase = pid

    eq_i = order.index(equity_phase)
    count_i = order.index(count_phase)
    reasons = [
        f"equity_phase={equity_phase} (equity {equity:.2f})",
        f"count_phase={count_phase} (settled {settled_count})",
        f"peak_equity={peak:.2f}",
    ]

    if stable_enough:
        allowed_i = min(count_i, eq_i + 1)
        reasons.append(f"count unlock capped at equity+1 → {order[allowed_i]}")
    else:
        allowed_i = eq_i
        roi_s = f"{roll:.1%}" if roll is not None else "n/a"
        reasons.append(f"count unlock blocked: rolling ROI {roi_s} < stability {min_roi:.1%}")

    chosen_i = max(eq_i, allowed_i)
    chosen = order[chosen_i]
    demoted = False

    # Demote if deep red on rolling window
    if roll is not None and roll < demote_roi and settled_count >= demote_n:
        if chosen_i > 0:
            chosen_i -= 1
            chosen = order[chosen_i]
            demoted = True
            reasons.append(f"demote for rolling ROI {roll:.1%} < {demote_roi:.1%}")

    # Demote if large drawdown from peak (does not stack a second drop same evaluation)
    if not demoted and peak > 0 and settled_count >= demote_n:
        dd = (peak - equity) / peak
        if dd >= dd_pct and chosen_i > 0:
            chosen_i -= 1
            chosen = order[chosen_i]
            demoted = True
            reasons.append(f"demote for drawdown {dd:.1%} of peak (limit {dd_pct:.0%})")

    # One-step advance vs previously stored phase
    if current_phase and current_phase in phases:
        cur_i = order.index(current_phase)
        if chosen_i > cur_i + 1:
            chosen_i = cur_i + 1
            chosen = order[chosen_i]
            reasons.append(f"one-step advance cap from {current_phase} → {chosen}")

    p = phases[chosen]
    return {
        "phase_id": chosen,
        "label": p.get("label", chosen),
        "stake_min": float(p["stake_min"]),
        "stake_max": float(p["stake_max"]),
        "max_bets_per_round": int(p["max_bets_per_round"]),
        "max_doubles_per_round": int(p["max_doubles_per_round"]),
        "daily_risk_pct": float(p["daily_risk_pct"]),
        "daily_risk_floor": float(p["daily_risk_floor"]),
        "daily_risk_ceil": float(p["daily_risk_ceil"]),
        "next": p.get("next"),
        "equity_phase": equity_phase,
        "count_phase": count_phase,
        "rolling_roi": roll,
        "peak_equity_nok": peak,
        "drawdown_from_peak_pct": round((peak - equity) / peak, 4) if peak > 0 else 0.0,
        "reasons": reasons,
        "equity_nok": equity,
        "settled_count": settled_count,
    }


def write_phase_state(cfg: dict[str, Any], phase: dict[str, Any]) -> None:
    state_dir = path_from_config(cfg, "state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "phase.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(phase, f, indent=2)
        f.write("\n")


def load_phase_state(cfg: dict[str, Any]) -> dict[str, Any] | None:
    path = path_from_config(cfg, "state_dir") / "phase.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
