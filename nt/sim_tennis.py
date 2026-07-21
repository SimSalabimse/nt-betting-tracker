"""
Tennis quant sim — suggestion only (never places bets).

Simple hold-based match-win model for BO3 / BO5 style markets.
Garbage-in → low confidence + warnings.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from nt.bets_io import utc_now


@dataclass
class TennisSimInputs:
    match: str = ""
    player_a: str = ""
    player_b: str = ""
    # Serve hold probabilities (0-1). Default ~ATP average-ish.
    hold_a: float = 0.78
    hold_b: float = 0.78
    best_of: int = 3  # 3 or 5
    elo_diff: float | None = None  # optional A - B elo
    source_quality: str = "medium"  # low|medium|high
    notes: str = ""
    selection: str | None = None
    odds_ref: float | None = None


def _clamp01(x: float) -> float:
    return max(0.01, min(0.99, float(x)))


def p_game_hold(hold: float) -> float:
    return _clamp01(hold)


def p_set_from_holds(hold_a: float, hold_b: float) -> float:
    """
    Very coarse: set win ≈ f(break opportunity).
    P(A wins set) ~ logistic of hold advantage.
    """
    ha, hb = p_game_hold(hold_a), p_game_hold(hold_b)
    edge = (ha - hb) * 4.0 + (ha - 0.75) * 0.5
    return _clamp01(1.0 / (1.0 + math.exp(-edge * 3.0)))


def p_match_from_set(p_set: float, best_of: int) -> float:
    """Independent sets: BO3 need 2, BO5 need 3."""
    p = _clamp01(p_set)
    q = 1.0 - p
    if best_of >= 5:
        # P(A wins BO5) = p^3 + C(3,1)p^3 q + C(4,2)p^3 q^2
        return (
            p**3
            + 3 * p**3 * q
            + 6 * p**3 * q**2
        )
    # BO3
    return p**2 + 2 * p**2 * q


def simulate_tennis(inp: TennisSimInputs) -> dict[str, Any]:
    warnings: list[str] = []
    ha, hb = float(inp.hold_a), float(inp.hold_b)
    if not (0.5 <= ha <= 0.95) or not (0.5 <= hb <= 0.95):
        warnings.append("hold% outside typical 50–95% range — low confidence")
    if inp.elo_diff is not None:
        # blend tiny elo into holds
        d = float(inp.elo_diff) / 400.0
        ha = _clamp01(ha + d * 0.03)
        hb = _clamp01(hb - d * 0.03)
        warnings.append("elo_diff soft-blended into holds")

    p_set = p_set_from_holds(ha, hb)
    p_match = p_match_from_set(p_set, int(inp.best_of or 3))
    conf = {"low": 0.35, "medium": 0.55, "high": 0.7}.get(
        (inp.source_quality or "medium").lower(), 0.5
    )
    if warnings:
        conf *= 0.75

    markets = {
        "match_win_a": round(p_match, 4),
        "match_win_b": round(1.0 - p_match, 4),
        "set_win_a": round(p_set, 4),
    }
    # Map selection if looks like A/B winner
    p_out = p_match
    sel = (inp.selection or "").lower()
    if inp.player_b and inp.player_b.lower()[:6] in sel:
        p_out = 1.0 - p_match
    elif "vinner" in sel or "to win" in sel:
        if inp.player_a and inp.player_a.lower()[:6] in sel:
            p_out = p_match

    return {
        "sport": "tennis",
        "model": "hold_logistic_sets",
        "ts": utc_now(),
        "match": inp.match or f"{inp.player_a} vs {inp.player_b}",
        "inputs": asdict(inp),
        "p_model": round(p_out, 4),
        "confidence": round(conf, 3),
        "markets": markets,
        "warnings": warnings
        + [
            "SUGGESTION ONLY — does not place bets",
            "Fill evidence sources before grade A",
        ],
        "disclaimer": "Tennis sim is coarse; human + research gates remain law.",
    }
