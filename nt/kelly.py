"""
P2: Fractional Kelly stake suggestion — gated on liquid + calibration Brier.

Never pure continuous Kelly; unit ladder remains floor. Fail-closed when
gates fail (returns None → caller keeps unit stake).
"""
from __future__ import annotations

from typing import Any


def full_kelly_fraction(p_model: float, odds: float) -> float:
    """
    Kelly fraction of bankroll for decimal odds (net odds b = odds-1).
    f* = (p*b - (1-p)) / b = (p*odds - 1) / (odds - 1)
    """
    p = float(p_model)
    o = float(odds)
    if o <= 1.01 or not (0.01 < p < 0.99):
        return 0.0
    b = o - 1.0
    return (p * o - 1.0) / b


def fractional_kelly_stake(
    *,
    p_model: float,
    odds: float,
    liquid: float,
    active_unit: float,
    min_stake: float,
    remaining_room: float,
    kelly_cfg: dict[str, Any] | None = None,
    brier: float | None = None,
    cal_n: int = 0,
) -> tuple[float | None, list[str]]:
    """
    Returns (stake_or_None, constraints).

    Stake is whole-krone, in [active_unit, min(max_units*unit, room)] when applied.
    None means do not override unit path.
    """
    cfg = dict(kelly_cfg or {})
    notes: list[str] = []

    if not bool(cfg.get("enabled", True)):
        notes.append("kelly_disabled")
        return None, notes

    liq_gate = float(cfg.get("enabled_above_liquid") or 1500.0)
    liquid = float(liquid)
    if liquid + 1e-9 < liq_gate:
        notes.append(f"kelly_liquid_below:{liq_gate}")
        return None, notes

    p = float(p_model)
    o = float(odds)
    if o <= 1.01 or not (0.01 < p < 0.99):
        notes.append("kelly_invalid_p_or_odds")
        return None, notes

    f_star = full_kelly_fraction(p, o)
    if f_star <= 0:
        notes.append("kelly_nonpositive_edge")
        return None, notes

    fraction_cap = float(cfg.get("fraction_cap") or 0.30)
    max_brier = float(cfg.get("max_brier") or 0.28)
    min_cal_n = int(cfg.get("min_calibration_n") or 30)
    soft = bool(cfg.get("brier_soft_scale", True))
    max_units = float(cfg.get("max_units") or 1.5)

    # Calibration gate
    if cal_n >= min_cal_n and brier is not None:
        if float(brier) > max_brier + 1e-12:
            notes.append(f"kelly_blocked_brier:{brier}>{max_brier}")
            return None, notes
        if soft:
            # scale down as Brier approaches max (0.18 → full, max_brier → 0.25×)
            lo, hi = 0.18, max_brier
            if hi > lo:
                t = (float(brier) - lo) / (hi - lo)
                t = max(0.0, min(1.0, t))
                scale = max(0.25, 1.0 - t)
            else:
                scale = 1.0
            fraction_cap = fraction_cap * scale
            notes.append(f"kelly_brier_scale:{scale:.2f}")
    else:
        # Fail-closed: no solid calibration → no Kelly
        notes.append(f"kelly_skip_thin_cal:n={cal_n}")
        return None, notes

    f = max(0.0, min(1.0, f_star)) * fraction_cap
    raw = liquid * f
    unit = max(0.0, float(active_unit))
    floor = float(min_stake)
    room = max(0.0, float(remaining_room))
    cap = min(unit * max_units, room) if unit > 0 else room

    # Kelly only lifts above unit; never below unit floor
    target = max(unit, raw)
    target = min(target, cap)
    stake = float(int(target))  # whole krone
    if stake + 1e-9 < floor:
        notes.append("kelly_below_floor")
        return None, notes
    if stake <= unit + 1e-9:
        notes.append("kelly_not_above_unit")
        return None, notes

    notes.append(f"kelly_f*:{f_star:.4f}")
    notes.append(f"kelly_f:{f:.4f}")
    notes.append(f"kelly_stake:{stake}")
    return stake, notes
