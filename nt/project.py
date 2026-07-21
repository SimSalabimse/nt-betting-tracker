from __future__ import annotations

"""
Long-horizon bankroll projection (Monte Carlo-style).

Does NOT touch data/bets.csv. For planning only — not a promise of returns.
"""

import random
from datetime import date
from typing import Any

from nt.bankroll import compute_bankroll
from nt.defaults import projection_cfg
from nt.config import path_from_config


def _phase_for_equity(cfg: dict[str, Any], equity: float) -> dict[str, Any]:
    """Equity-only phase snapshot (no demote/count) for simulation simplicity."""
    phases = cfg.get("phases") or {}
    order = list(phases.keys())
    chosen = order[0] if order else "1A"
    for pid in order:
        if equity >= float(phases[pid].get("enter_equity", 0)):
            chosen = pid
    p = phases.get(chosen) or {
        "stake_min": 10,
        "stake_max": 12,
        "daily_risk_pct": 0.08,
        "daily_risk_floor": 30,
        "daily_risk_ceil": 42,
    }
    return {"phase_id": chosen, **p}


def _daily_cap(equity: float, phase: dict[str, Any]) -> float:
    raw = equity * float(phase.get("daily_risk_pct", 0.08))
    floor = float(phase.get("daily_risk_floor", 30))
    ceil = float(phase.get("daily_risk_ceil", 42))
    return max(floor, min(ceil, raw))


def simulate_paths(
    cfg: dict[str, Any],
    *,
    start_equity: float | None = None,
    years: float | None = None,
    sims: int | None = None,
    roi: float | None = None,
    bets_per_week: float | None = None,
    avg_odds: float | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Simulate weekly P/L paths with simple Bernoulli outcomes.

    Edge model: each bet has fair win rate implied by avg_odds adjusted so that
    expected ROI ≈ `roi` (on stake). Variance is high at small bankrolls.
    """
    pc = projection_cfg(cfg)
    years = float(years if years is not None else pc["default_years"])
    sims = int(sims if sims is not None else pc["default_sims"])
    roi = float(roi if roi is not None else pc["default_roi"])
    bets_per_week = float(bets_per_week if bets_per_week is not None else pc["default_bets_per_week"])
    avg_odds = float(avg_odds if avg_odds is not None else pc["default_avg_odds"])
    seed = int(seed if seed is not None else pc["seed"])

    if start_equity is None:
        start_equity = float(compute_bankroll(cfg)["equity_nok"])

    # Win probability such that E[P/L]/stake ≈ roi
    # E = p*(odds-1) - (1-p) = p*odds - 1  => p = (1+roi)/odds
    p_win = max(0.01, min(0.99, (1.0 + roi) / avg_odds))
    weeks = max(1, int(round(years * 52)))
    rng = random.Random(seed)

    finals: list[float] = []
    max_dds: list[float] = []
    ruin = 0  # equity < 0.5 * start or < min stake * 3
    phase_end: dict[str, int] = {}

    for _ in range(sims):
        eq = float(start_equity)
        peak = eq
        max_dd = 0.0
        for _w in range(weeks):
            phase = _phase_for_equity(cfg, eq)
            cap = _daily_cap(eq, phase)
            # approximate weekly risk budget as ~4 active days * fraction of daily cap
            week_budget = min(eq * 0.25, cap * 4.0)
            n_bets = max(0, int(round(bets_per_week + rng.uniform(-2, 2))))
            if n_bets == 0 or week_budget < 10:
                continue
            stake = max(10.0, min(float(phase.get("stake_max", 12)), week_budget / n_bets))
            week_pl = 0.0
            for _b in range(n_bets):
                if eq < 30:
                    break
                st = min(stake, eq * 0.05 + 10)  # soft clamp
                st = max(10.0, float(int(st)))
                if rng.random() < p_win:
                    week_pl += st * (avg_odds - 1.0)
                else:
                    week_pl -= st
            eq = round(eq + week_pl, 2)
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > max_dd:
                max_dd = dd
            if eq < max(30.0, start_equity * 0.4):
                ruin += 1
                break
        finals.append(eq)
        max_dds.append(max_dd)
        pid = _phase_for_equity(cfg, eq)["phase_id"]
        phase_end[pid] = phase_end.get(pid, 0) + 1

    finals_sorted = sorted(finals)
    n = len(finals_sorted)

    def pct(p: float) -> float:
        if n == 0:
            return 0.0
        i = min(n - 1, max(0, int(p * (n - 1))))
        return finals_sorted[i]

    return {
        "start_equity": start_equity,
        "years": years,
        "weeks": weeks,
        "sims": sims,
        "assumptions": {
            "roi": roi,
            "bets_per_week": bets_per_week,
            "avg_odds": avg_odds,
            "p_win": round(p_win, 4),
            "seed": seed,
        },
        "final_equity": {
            "mean": round(sum(finals) / n, 2) if n else 0.0,
            "p05": round(pct(0.05), 2),
            "p25": round(pct(0.25), 2),
            "p50": round(pct(0.50), 2),
            "p75": round(pct(0.75), 2),
            "p95": round(pct(0.95), 2),
            "min": round(finals_sorted[0], 2) if n else 0.0,
            "max": round(finals_sorted[-1], 2) if n else 0.0,
        },
        "max_drawdown_mean": round(sum(max_dds) / len(max_dds), 2) if max_dds else 0.0,
        "stress_hit_rate": round(ruin / sims, 4) if sims else 0.0,
        "phase_at_end_hist": phase_end,
        "disclaimer": "Illustrative simulation only. Not a forecast. Edge may be zero or negative.",
    }


def render_projection_md(result: dict[str, Any]) -> str:
    a = result["assumptions"]
    f = result["final_equity"]
    lines = [
        f"# Bankroll Projection — {date.today().isoformat()}",
        "",
        f"Start equity: **{result['start_equity']:.2f} NOK** · Horizon: **{result['years']}y** ({result['weeks']} weeks) · Sims: {result['sims']}",
        "",
        "## Assumptions",
        f"- Target ROI on stake: {a['roi']*100:.1f}%",
        f"- Bets/week: {a['bets_per_week']}",
        f"- Avg odds: {a['avg_odds']}",
        f"- Implied p_win (for that ROI): {a['p_win']}",
        f"- Seed: {a['seed']}",
        "",
        "## Final equity distribution",
        f"| pct | equity NOK |",
        f"|-----|------------|",
        f"| p05 | {f['p05']:.2f} |",
        f"| p25 | {f['p25']:.2f} |",
        f"| **p50** | **{f['p50']:.2f}** |",
        f"| p75 | {f['p75']:.2f} |",
        f"| p95 | {f['p95']:.2f} |",
        f"| mean | {f['mean']:.2f} |",
        "",
        f"Mean max drawdown (path): {result['max_drawdown_mean']:.2f} NOK",
        f"Stress hit rate (equity collapse path): {result['stress_hit_rate']*100:.1f}%",
        "",
        f"Phase at end (hist): {result.get('phase_at_end_hist')}",
        "",
        f"> {result['disclaimer']}",
        "",
        "See also: `docs/BANKROLL_PLAN.md`",
        "",
    ]
    return "\n".join(lines)


def run_project(cfg: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    write = bool(kwargs.pop("write_outbox", True))
    result = simulate_paths(cfg, **kwargs)
    md = render_projection_md(result)
    result["markdown"] = md
    if write:
        outbox = path_from_config(cfg, "outbox")
        outbox.mkdir(parents=True, exist_ok=True)
        path = outbox / f"PROJECTION_{date.today().isoformat()}.md"
        path.write_text(md, encoding="utf-8")
        result["path"] = str(path)
    return result
