#!/usr/bin/env python3
"""
Monte-Carlo projection: hybrid phase ladder + continuous unit + Variant A secure skim.

Read-only / offline — does NOT write ledger, segments, or outbox.

Purpose
-------
Illustrate time-to-milestone under a simple, documented betting model after
PR-1 (Variant A secure bucket) + PR-2 (half-steps 1A+/1B+ + continuous unit).

This is **not** a live risk engine stress suite (see scripts/run_capital_v2_mc.py
and nt/capital_mc.py). It answers operator questions:

  - How does unit evolve at equity 500 → 750 under live config?
  - Median bets / calendar days to +100 NOK, equity 540, 580?
  - Soft vs hard skim interaction along the path?

Assumptions (documented — change flags in main() / CLI if needed)
-----------------------------------------------------------------
* Start equity = bankroll.baseline_nok (500), ref_hwm = 500, secure = 0.
* Each sim day places up to ``bets_per_day`` independent singles at fixed odds.
* Stake = continuous unit from evaluate_phase (phase_continuous primary).
  Whole kroner; never below norsk_tipping.min_stake_nok.
* Daily open-risk budget = phase daily_risk_cap (lerp when continuous on).
  Also capped by bankroll_regime exploration/survival open_risk_cap when equity
  and settled_count still inside those regimes (mirrors early-bankroll binding).
* Win probability p_win = (1 + edge) / odds  (edge after 3pp haircut narrative).
* Default market: odds=1.95, edge=+0.025 (~2.5% ROI on stake in expectation).
* Settlements same day (no open overnight risk carry) — optimistic for open-cap
  turnover; pessimistic for multi-day Pending. Documented trade-off.
* Variant A secure skim checked after each day: soft 1.25×/15%, hard 1.50×/30%
  (hard replaces soft). Liquid floor = phase daily_risk_ceil. ref → working after.
* No DD freeze / no process_error size_mode floor / no Kelly lift.
* No demote / count-unlock (equity path only) — milestones are pure equity.
* Paths stop at max_days or when equity hits stop_equity (default 900).
* Ruin: equity < min_stake → path ends (cannot bet).

Usage
-----
  python scripts/mc_phase_progression.py
  python scripts/mc_phase_progression.py --paths 2000 --seed 42 --json
  python scripts/mc_phase_progression.py --odds 2.05 --edge 0.02 --bets-per-day 2

Exit 0 always (projection, not a gate).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bankroll_regime import evaluate_bankroll_regime
from nt.capital_v2 import compute_secure_transfer_variant_a, whole_krone
from nt.config import load_config
from nt.phase import (
    continuous_open_risk_params,
    continuous_unit_size,
    phase_continuous_cfg,
    progress_inside_phase,
    resolve_hard_phase_id,
)
from nt.risk import daily_risk_cap

# Equity checkpoints for unit trajectory printout (operator-facing).
UNIT_EQUITY_POINTS = (500, 520, 540, 560, 580, 620, 750)

# Milestone targets relative to start.
MILESTONE_KEYS = (
    "hit_plus_100",  # equity >= start + 100
    "hit_540",
    "hit_580",
    "hit_620",
    "hit_750",
)


@dataclass
class PathResult:
    final_equity: float
    final_secure: float
    final_working: float
    n_bets: int
    n_days: int
    n_wins: int
    n_losses: int
    n_soft_skims: int
    n_hard_skims: int
    total_skimmed: float
    ruined: bool
    # first day index (1-based) and bet count when milestone first hit; None if never
    first_day: dict[str, int | None] = field(default_factory=dict)
    first_bets: dict[str, int | None] = field(default_factory=dict)
    equity_at_end_of_milestones: dict[str, float | None] = field(default_factory=dict)


def _p_win(odds: float, edge: float) -> float:
    return max(0.01, min(0.99, (1.0 + float(edge)) / float(odds)))


def _equity_phase_id(cfg: dict[str, Any], equity: float) -> str:
    """Highest phase whose enter_equity is met (equity path only — no demote/count)."""
    phases = cfg["phases"]
    order = list(phases.keys())
    chosen = order[0]
    for pid in order:
        if float(equity) + 1e-9 >= float(phases[pid].get("enter_equity") or 0):
            chosen = pid
    return chosen


def phase_snapshot(cfg: dict[str, Any], equity: float) -> dict[str, Any]:
    """
    Fast sizing snapshot for MC (equity ladder + continuous unit/open-risk).

    Intentionally omits demote / count-unlock / peak / phase_health — this
    projection is pure equity progression (documented in module docstring).
    """
    pid = _equity_phase_id(cfg, equity)
    pc = phase_continuous_cfg(cfg)
    open_p = continuous_open_risk_params(cfg, pid, equity)
    unit = (
        continuous_unit_size(cfg, pid, equity)
        if pc.get("enabled")
        else float((cfg["phases"][pid].get("stake_min") or 10))
    )
    snap = {
        "phase_id": pid,
        "phase_hard_id": resolve_hard_phase_id(cfg, pid),
        "unit_size_nok": unit,
        "daily_risk_pct": open_p["daily_risk_pct"],
        "daily_risk_floor": open_p["daily_risk_floor"],
        "daily_risk_ceil": open_p["daily_risk_ceil"],
        "progress_inside_phase": progress_inside_phase(cfg, pid, equity),
        "phase_continuous_enabled": bool(pc.get("enabled")),
    }
    return snap


def _regime_open_cap(cfg: dict[str, Any], equity: float, settled: int) -> float | None:
    """Return regime pending open cap if exploration/survival binds; else None."""
    reg = evaluate_bankroll_regime(cfg, equity=equity, settled_count=settled)
    if not reg.get("enabled", True):
        return None
    rid = str(reg.get("id") or "").lower()
    if rid not in ("exploration", "survival", "calibration"):
        return None
    cap = reg.get("open_risk_cap_nok")
    if cap is None:
        return None
    return float(cap)


def unit_trajectory(cfg: dict[str, Any], equities: tuple[int, ...] = UNIT_EQUITY_POINTS) -> list[dict[str, Any]]:
    """Static continuous-unit / phase snapshot at fixed equities (no skim)."""
    out: list[dict[str, Any]] = []
    for eq in equities:
        phase = phase_snapshot(cfg, float(eq))
        cap = daily_risk_cap(float(eq), phase)
        out.append(
            {
                "equity": eq,
                "phase_id": phase["phase_id"],
                "phase_hard_id": phase.get("phase_hard_id") or phase["phase_id"],
                "unit_size_nok": phase.get("unit_size_nok"),
                "daily_risk_nok": cap,
                "daily_risk_floor": phase["daily_risk_floor"],
                "daily_risk_ceil": phase["daily_risk_ceil"],
                "progress_inside_phase": phase.get("progress_inside_phase"),
            }
        )
    return out


def _before_snapshot(equity: float) -> dict[str, Any]:
    """
    Pre-hybrid (pre half-steps / continuous) narrative numbers.

    Old ladder: 1A until 580, static daily_risk clamp 8%/30–42, unit ladder 12
    under 1500 liquid (High-Volume v2). No continuous lerp.
    """
    # Old 1A band
    if equity < 580:
        phase_id = "1A"
        pct, floor, ceil = 0.08, 30.0, 42.0
        unit = 12.0  # capital_v2 High-Volume base unit
    elif equity < 750:
        phase_id = "1B"
        pct, floor, ceil = 0.09, 38.0, 52.0
        unit = 12.0
    else:
        phase_id = "2"
        pct, floor, ceil = 0.10, 50.0, 75.0
        unit = 12.0
    raw = equity * pct
    daily = round(max(floor, min(ceil, raw)), 2)
    return {
        "equity": equity,
        "phase_id": phase_id,
        "unit_size_nok": unit,
        "daily_risk_nok": daily,
        "open_risk_note": "phase daily cap only (no continuous lerp)",
        "secure_skim": "Variant A already live post-PR1; no skim below 1.25×ref",
    }


def before_after_table(cfg: dict[str, Any], start: float = 500.0, end: float = 550.0) -> list[dict[str, Any]]:
    """Side-by-side before (pre-hybrid) vs after (live config) at start and end equity."""
    rows_out: list[dict[str, Any]] = []
    for eq in (start, end):
        before = _before_snapshot(eq)
        phase = phase_snapshot(cfg, float(eq))
        after_cap = daily_risk_cap(float(eq), phase)
        # Secure at these levels with ref=start baseline
        skim = compute_secure_transfer_variant_a(
            ledger_equity=float(eq),
            secure_nok=0.0,
            ref_hwm=float(start),
            unit_size_nok=float(phase.get("unit_size_nok") or 12),
            phase_daily_risk_ceil=float(phase["daily_risk_ceil"]),
            open_risk=0.0,
        )
        rows_out.append(
            {
                "equity": eq,
                "before_phase": before["phase_id"],
                "after_phase": phase["phase_id"],
                "before_unit": before["unit_size_nok"],
                "after_unit": phase.get("unit_size_nok"),
                "before_daily_risk": before["daily_risk_nok"],
                "after_daily_risk": after_cap,
                "after_open_floor": phase["daily_risk_floor"],
                "after_open_ceil": phase["daily_risk_ceil"],
                "secure_tier": skim.tier,
                "secure_xfer": skim.transferred,
            }
        )
    return rows_out


def simulate_path(
    cfg: dict[str, Any],
    *,
    rng: random.Random,
    start_equity: float,
    odds: float,
    edge: float,
    bets_per_day: int,
    max_days: int,
    stop_equity: float,
    apply_secure: bool,
    apply_regime_cap: bool,
) -> PathResult:
    min_stake = float((cfg.get("norsk_tipping") or {}).get("min_stake_nok") or 10.0)
    equity = float(start_equity)
    secure = 0.0
    ref_hwm = float(start_equity)
    settled = 0
    n_bets = n_wins = n_losses = 0
    n_soft = n_hard = 0
    total_skim = 0.0
    p = _p_win(odds, edge)

    targets = {
        "hit_plus_100": start_equity + 100.0,
        "hit_540": 540.0,
        "hit_580": 580.0,
        "hit_620": 620.0,
        "hit_750": 750.0,
    }
    first_day: dict[str, int | None] = {k: None for k in targets}
    first_bets: dict[str, int | None] = {k: None for k in targets}

    def _mark_milestones(day_i: int) -> None:
        for k, thr in targets.items():
            if first_day[k] is None and equity + 1e-9 >= thr:
                first_day[k] = day_i
                first_bets[k] = n_bets

    _mark_milestones(0)

    ruined = False
    day_i = 0
    for day_i in range(1, max_days + 1):
        if equity + 1e-9 >= stop_equity:
            break
        if equity < min_stake:
            ruined = True
            break

        phase = phase_snapshot(cfg, equity)
        unit = float(phase.get("unit_size_nok") or min_stake)
        unit = max(min_stake, whole_krone(unit) or min_stake)
        day_cap = daily_risk_cap(equity, phase)
        if apply_regime_cap:
            rcap = _regime_open_cap(cfg, equity, settled)
            if rcap is not None:
                day_cap = min(day_cap, rcap)

        # Same-day settle: open risk frees immediately; pack bets until budget spent
        spent = 0.0
        for _ in range(max(1, bets_per_day)):
            if equity < min_stake:
                break
            if spent + unit > day_cap + 1e-9:
                break
            # Also keep working liquid able to fund stake
            working = equity - secure
            if working + 1e-9 < unit:
                break

            win = rng.random() < p
            n_bets += 1
            spent += unit
            if win:
                pl = unit * (odds - 1.0)
                equity = round(equity + pl, 2)
                n_wins += 1
            else:
                equity = round(equity - unit, 2)
                n_losses += 1
            settled += 1
            _mark_milestones(day_i)

        if apply_secure and equity >= ref_hwm * 1.25 - 1e-9:
            phase2 = phase_snapshot(cfg, equity)
            unit2 = float(phase2.get("unit_size_nok") or unit)
            skim = compute_secure_transfer_variant_a(
                ledger_equity=equity,
                secure_nok=secure,
                ref_hwm=ref_hwm,
                unit_size_nok=unit2,
                phase_daily_risk_ceil=float(phase2["daily_risk_ceil"]),
                open_risk=0.0,  # same-day settle assumption
            )
            if skim.triggered and skim.transferred >= 1.0:
                secure = skim.secure_after
                ref_hwm = skim.ref_hwm_after
                total_skim = round(total_skim + skim.transferred, 2)
                if skim.tier == "soft":
                    n_soft += 1
                elif skim.tier == "hard":
                    n_hard += 1

        if equity < min_stake:
            ruined = True
            break

    working = round(max(0.0, equity - secure), 2)
    return PathResult(
        final_equity=equity,
        final_secure=secure,
        final_working=working,
        n_bets=n_bets,
        n_days=day_i if day_i else 0,
        n_wins=n_wins,
        n_losses=n_losses,
        n_soft_skims=n_soft,
        n_hard_skims=n_hard,
        total_skimmed=total_skim,
        ruined=ruined,
        first_day=first_day,
        first_bets=first_bets,
    )


def _median_or_none(xs: list[float | int]) -> float | None:
    if not xs:
        return None
    return float(statistics.median(xs))


def _pct(xs: list[bool]) -> float:
    if not xs:
        return 0.0
    return 100.0 * sum(1 for x in xs if x) / len(xs)


def run_suite(
    cfg: dict[str, Any],
    *,
    n_paths: int,
    seed: int,
    start_equity: float,
    odds: float,
    edge: float,
    bets_per_day: int,
    max_days: int,
    stop_equity: float,
    apply_secure: bool = True,
    apply_regime_cap: bool = True,
) -> dict[str, Any]:
    rng = random.Random(seed)
    paths: list[PathResult] = []
    for _ in range(n_paths):
        paths.append(
            simulate_path(
                cfg,
                rng=rng,
                start_equity=start_equity,
                odds=odds,
                edge=edge,
                bets_per_day=bets_per_day,
                max_days=max_days,
                stop_equity=stop_equity,
                apply_secure=apply_secure,
                apply_regime_cap=apply_regime_cap,
            )
        )

    def mil_stats(key: str) -> dict[str, Any]:
        days = [p.first_day[key] for p in paths if p.first_day.get(key) is not None]
        bets = [p.first_bets[key] for p in paths if p.first_bets.get(key) is not None]
        # day 0 means already at/above at start — count as hit, 0 bets/days
        hit_rate = _pct([p.first_day.get(key) is not None for p in paths])
        days_f = [float(d) for d in days if d is not None]
        bets_f = [float(b) for b in bets if b is not None]
        return {
            "hit_rate_pct": round(hit_rate, 1),
            "median_days": _median_or_none(days_f),
            "median_bets": _median_or_none(bets_f),
            "p25_days": float(statistics.quantiles(days_f, n=4)[0]) if len(days_f) >= 4 else None,
            "p75_days": float(statistics.quantiles(days_f, n=4)[2]) if len(days_f) >= 4 else None,
            "p25_bets": float(statistics.quantiles(bets_f, n=4)[0]) if len(bets_f) >= 4 else None,
            "p75_bets": float(statistics.quantiles(bets_f, n=4)[2]) if len(bets_f) >= 4 else None,
        }

    finals = [p.final_equity for p in paths]
    secures = [p.final_secure for p in paths]
    return {
        "n_paths": n_paths,
        "seed": seed,
        "assumptions": {
            "start_equity": start_equity,
            "odds": odds,
            "edge": edge,
            "p_win": round(_p_win(odds, edge), 4),
            "expected_roi_on_stake": round(edge, 4),
            "bets_per_day": bets_per_day,
            "max_days": max_days,
            "stop_equity": stop_equity,
            "apply_secure_variant_a": apply_secure,
            "apply_regime_open_cap": apply_regime_cap,
            "same_day_settle": True,
            "notes": (
                "Expectation-positive toy book; real desk has research gates, "
                "empty slips, haircut EV bars, and Pending carry."
            ),
        },
        "unit_trajectory": unit_trajectory(cfg),
        "before_after_500_550": before_after_table(cfg, 500.0, 550.0),
        "milestones": {k: mil_stats(k) for k in MILESTONE_KEYS},
        "terminal": {
            "median_final_equity": round(statistics.median(finals), 2),
            "mean_final_equity": round(statistics.mean(finals), 2),
            "p10_final_equity": round(sorted(finals)[max(0, int(0.10 * len(finals)) - 1)], 2),
            "p90_final_equity": round(sorted(finals)[min(len(finals) - 1, int(0.90 * len(finals)))], 2),
            "median_final_secure": round(statistics.median(secures), 2),
            "ruin_rate_pct": round(_pct([p.ruined for p in paths]), 2),
            "mean_soft_skims": round(statistics.mean(p.n_soft_skims for p in paths), 2),
            "mean_hard_skims": round(statistics.mean(p.n_hard_skims for p in paths), 2),
            "mean_total_skimmed": round(statistics.mean(p.total_skimmed for p in paths), 2),
            "mean_bets": round(statistics.mean(p.n_bets for p in paths), 1),
        },
    }


def format_report(suite: dict[str, Any]) -> str:
    a = suite["assumptions"]
    lines: list[str] = []
    lines.append("# Hybrid phase progression — Monte-Carlo projection")
    lines.append("")
    lines.append("## Assumptions")
    lines.append("")
    lines.append(f"- paths={suite['n_paths']}  seed={suite['seed']}")
    lines.append(
        f"- start={a['start_equity']}  odds={a['odds']}  edge={a['edge']}  "
        f"p_win={a['p_win']}  bets/day≤{a['bets_per_day']}  max_days={a['max_days']}"
    )
    lines.append(
        f"- secure Variant A={a['apply_secure_variant_a']}  "
        f"regime open-cap={a['apply_regime_open_cap']}  same-day settle={a['same_day_settle']}"
    )
    lines.append(f"- note: {a['notes']}")
    lines.append("")
    lines.append("## Unit trajectory (static, continuous phase unit)")
    lines.append("")
    lines.append("| Equity | Phase | Hard | Unit | Daily risk | Floor–Ceil | Progress |")
    lines.append("|-------:|:-----:|:----:|-----:|-----------:|:-----------|---------:|")
    for row in suite["unit_trajectory"]:
        prog = row.get("progress_inside_phase")
        prog_s = f"{prog:.2f}" if isinstance(prog, (int, float)) else "—"
        lines.append(
            f"| {row['equity']} | {row['phase_id']} | {row['phase_hard_id']} | "
            f"{row['unit_size_nok']} | {row['daily_risk_nok']} | "
            f"{row['daily_risk_floor']}–{row['daily_risk_ceil']} | {prog_s} |"
        )
    lines.append("")
    lines.append("## Before / after 500 → 550")
    lines.append("")
    lines.append(
        "| Equity | Before phase | After phase | Before unit | After unit | "
        "Before daily risk | After daily risk | Secure skim |"
    )
    lines.append("|-------:|:------------:|:-----------:|------------:|-----------:|------------------:|-----------------:|:------------|")
    for row in suite["before_after_500_550"]:
        skim = (
            f"{row['secure_tier']} {row['secure_xfer']}"
            if row["secure_tier"]
            else "none"
        )
        lines.append(
            f"| {row['equity']} | {row['before_phase']} | {row['after_phase']} | "
            f"{row['before_unit']} | {row['after_unit']} | "
            f"{row['before_daily_risk']} | {row['after_daily_risk']} | {skim} |"
        )
    lines.append("")
    lines.append("## Milestone medians (among all paths; hit_rate includes never-hit as miss)")
    lines.append("")
    lines.append("| Milestone | Hit % | Median days | Median bets | P25–P75 days |")
    lines.append("|:----------|------:|------------:|------------:|:-------------|")
    labels = {
        "hit_plus_100": "+100 NOK (→600)",
        "hit_540": "Equity 540 (1A+)",
        "hit_580": "Equity 580 (1B)",
        "hit_620": "Equity 620 (1B+)",
        "hit_750": "Equity 750 (2)",
    }
    for key, lab in labels.items():
        m = suite["milestones"][key]
        p25, p75 = m.get("p25_days"), m.get("p75_days")
        band = f"{p25}–{p75}" if p25 is not None and p75 is not None else "—"
        lines.append(
            f"| {lab} | {m['hit_rate_pct']} | {m['median_days']} | "
            f"{m['median_bets']} | {band} |"
        )
    lines.append("")
    t = suite["terminal"]
    lines.append("## Terminal summary")
    lines.append("")
    lines.append(
        f"- median final equity **{t['median_final_equity']}** "
        f"(p10={t['p10_final_equity']}, p90={t['p90_final_equity']})"
    )
    lines.append(
        f"- median final secure **{t['median_final_secure']}** · "
        f"mean skimmed **{t['mean_total_skimmed']}** "
        f"(soft skims/path ~{t['mean_soft_skims']}, hard ~{t['mean_hard_skims']})"
    )
    lines.append(f"- ruin rate **{t['ruin_rate_pct']}%** · mean bets **{t['mean_bets']}**")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paths", type=int, default=1500, help="Monte-Carlo paths (default 1500)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--odds", type=float, default=1.95)
    ap.add_argument("--edge", type=float, default=0.025, help="Expected ROI on stake (e.g. 0.025 = +2.5%)")
    ap.add_argument("--bets-per-day", type=int, default=2)
    ap.add_argument("--max-days", type=int, default=400)
    ap.add_argument("--stop-equity", type=float, default=900.0)
    ap.add_argument("--no-secure", action="store_true", help="Disable Variant A skim in sim")
    ap.add_argument("--no-regime-cap", action="store_true", help="Ignore exploration/survival open cap")
    ap.add_argument("--json", action="store_true", help="Also print JSON blob after markdown")
    args = ap.parse_args(argv)

    cfg = load_config()
    start = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)

    suite = run_suite(
        cfg,
        n_paths=max(1, args.paths),
        seed=args.seed,
        start_equity=start,
        odds=args.odds,
        edge=args.edge,
        bets_per_day=max(1, args.bets_per_day),
        max_days=max(1, args.max_days),
        stop_equity=args.stop_equity,
        apply_secure=not args.no_secure,
        apply_regime_cap=not args.no_regime_cap,
    )
    report = format_report(suite)
    print(report)
    if args.json:
        print(json.dumps(suite, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
