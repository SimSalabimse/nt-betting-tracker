"""
Basketball quant sim — suggestion only (never places bets).

Normal approximation for margin + total vs lines.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from nt.bets_io import utc_now


@dataclass
class BasketballSimInputs:
    match: str = ""
    home: str = ""
    away: str = ""
    # Expected home margin (positive = home favored)
    mean_margin: float = 0.0
    margin_sd: float = 12.0
    # Expected total points
    mean_total: float = 220.0
    total_sd: float = 18.0
    handicap_line: float | None = None  # home -line style (home gives points if negative)
    total_line: float | None = None
    source_quality: str = "medium"
    notes: str = ""
    selection: str | None = None
    odds_ref: float | None = None


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def p_home_covers(mean_margin: float, sd: float, line: float) -> float:
    """
    Home covers handicap line (e.g. line=-4.5 means home -4.5).
    Cover if margin_home > -line for negative line... use: home_margin + line > 0
    """
    sd = max(1.0, float(sd))
    # home_margin ~ N(mean, sd); covers if home_margin + line > 0
    z = (0.0 - (mean_margin + line)) / sd
    return max(0.01, min(0.99, 1.0 - _norm_cdf(z)))


def p_over(mean_total: float, sd: float, line: float) -> float:
    sd = max(1.0, float(sd))
    z = (line - mean_total) / sd
    return max(0.01, min(0.99, 1.0 - _norm_cdf(z)))


def simulate_basketball(inp: BasketballSimInputs) -> dict[str, Any]:
    warnings: list[str] = []
    if inp.margin_sd < 8 or inp.margin_sd > 20:
        warnings.append("margin_sd unusual — check inputs")
    if inp.mean_total < 160 or inp.mean_total > 260:
        warnings.append("mean_total outside typical NBA/Euro range")

    markets: dict[str, float] = {}
    p_out = 0.5
    sel = (inp.selection or "").lower()

    if inp.handicap_line is not None:
        ph = p_home_covers(inp.mean_margin, inp.margin_sd, float(inp.handicap_line))
        markets["home_covers"] = round(ph, 4)
        markets["away_covers"] = round(1.0 - ph, 4)
        p_out = ph
        if "away" in sel or (inp.away and inp.away.lower()[:5] in sel):
            p_out = 1.0 - ph

    if inp.total_line is not None:
        po = p_over(inp.mean_total, inp.total_sd, float(inp.total_line))
        markets["over"] = round(po, 4)
        markets["under"] = round(1.0 - po, 4)
        if "under" in sel:
            p_out = 1.0 - po
        elif "over" in sel or inp.handicap_line is None:
            p_out = po

    if not markets:
        # default: home ML from margin
        ph = p_home_covers(inp.mean_margin, inp.margin_sd, 0.0)
        markets["home_ml"] = round(ph, 4)
        markets["away_ml"] = round(1.0 - ph, 4)
        p_out = ph
        warnings.append("no line provided — using home ML from margin")

    conf = {"low": 0.35, "medium": 0.55, "high": 0.7}.get(
        (inp.source_quality or "medium").lower(), 0.5
    )
    if warnings:
        conf *= 0.8

    return {
        "sport": "basketball",
        "model": "normal_margin_total",
        "ts": utc_now(),
        "match": inp.match or f"{inp.home} vs {inp.away}",
        "inputs": asdict(inp),
        "p_model": round(float(p_out), 4),
        "confidence": round(conf, 3),
        "markets": markets,
        "warnings": warnings
        + [
            "SUGGESTION ONLY — does not place bets",
            "Fill evidence sources before grade A",
        ],
        "disclaimer": "Basketball sim is coarse Normal approx; human + research gates remain law.",
    }
