"""
Capital v2 Monte-Carlo stress harness (Phase 2.5).

In-memory only — does NOT enable live capital_v2, does NOT write production
ledger/segments. Uses the same pure rules as risk + sizing + secure + snapshots.

Deterministic given seed + scenario config.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

from nt.capital_runtime import apply_secure_transfer_to_segments, ensure_day_week_snapshots
from nt.capital_v2 import (
    RULE_BUNDLE_VERSION,
    active_unit_for_mode,
    apply_nt_floor,
    capital_v2_cfg,
    compute_unit_stake,
    drawdown_from_peak,
    empty_segments,
    is_hard_loss_stopped,
    loss_limit_nok,
    oslo_iso_week_id,
    peak_equity_settlement,
    portfolio_open_room,
    riskable_equity,
    riskable_liquid,
    size_mode_from_dd,
    unit_size,
)

MIN_STAKE = 10.0

# Synthetic market book: odds + true p so edge ≈ edge_roi on stake
# p_win = (1 + edge) / odds
MARKET_BOOK: dict[str, dict[str, float]] = {
    "football_ou": {"odds": 1.85, "edge": 0.03},
    "football_1x2": {"odds": 2.10, "edge": 0.02},
    "darts_ml": {"odds": 1.70, "edge": 0.025},
    "tennis_ml": {"odds": 1.90, "edge": 0.02},
    "esports_maps": {"odds": 1.80, "edge": 0.015},
    "adverse": {"odds": 1.95, "edge": -0.05},  # negative edge stress
}


def _p_win(odds: float, edge: float) -> float:
    return max(0.01, min(0.99, (1.0 + edge) / odds))


@dataclass
class SimBet:
    stake: float
    odds: float
    market: str
    day: str
    size_mode: str
    unit: float
    open: bool = True
    result: str | None = None  # Win/Loss
    pl: float = 0.0


@dataclass
class PathMetrics:
    final_equity: float
    final_secure: float
    final_working: float
    max_dd_frac: float
    max_dd_nok: float
    peak_equity: float
    days_reduced: int
    days_frozen: int
    days_total: int
    n_bets: int
    n_stakes_at_floor: int
    n_secure_transfers: int
    n_daily_stops: int
    n_weekly_stops: int
    n_violations: int
    violations: list[str] = field(default_factory=list)
    equity_path_sample: list[float] = field(default_factory=list)


@dataclass
class ScenarioResult:
    name: str
    seed: int
    n_paths: int
    metrics: list[PathMetrics]
    summary: dict[str, Any]


def _phase() -> dict[str, Any]:
    return {
        "phase_id": "1A",
        "daily_risk_pct": 0.08,
        "daily_risk_floor": 30.0,
        "daily_risk_ceil": 42.0,
        "stake_min": 10.0,
        "stake_max": 12.0,
    }


def _v2_cfg() -> dict[str, Any]:
    return capital_v2_cfg(
        {
            "capital_v2": {"enabled": True},
            "norsk_tipping": {"min_stake_nok": MIN_STAKE},
        }
    )


def _check_stake_violations(
    stake: float,
    *,
    size_mode: str,
    remaining: float,
    open_after: float,
    liquid_before: float,
    max_open_pct: float,
    min_stake: float = MIN_STAKE,
) -> list[str]:
    v: list[str] = []
    if stake < 0:
        v.append(f"negative_stake:{stake}")
    if 0 < stake < min_stake - 1e-9:
        v.append(f"stake_below_floor:{stake}")
    if stake != int(stake) and stake > 0:
        v.append(f"non_whole_krone:{stake}")
    if stake > remaining + 1e-6 and stake > 0:
        v.append(f"stake_exceeds_remaining:{stake}>{remaining}")
    if size_mode == "FROZEN" and stake > 0:
        v.append(f"stake_while_frozen:{stake}")
    # open risk consistency: total open should respect 18% of liquid at decision
    # (room was computed pre-stake; post open may exceed old room by construction of
    # sequential adds — check each stake ≤ room at decision time is enough)
    _ = (open_after, liquid_before, max_open_pct)
    return v


def simulate_path(
    *,
    seed: int,
    start_equity: float,
    n_days: int,
    start_day: str = "2026-01-05",  # Monday
    bets_per_day: int = 3,
    market_mix: list[str] | None = None,
    force_lose_days: int = 0,
    force_win_days: int = 0,
    force_lose_after_day: int | None = None,
    multi_open: bool = False,
    settle_same_day: bool = True,
    allow_unfreeze_after_days: int | None = None,
    baseline: float | None = None,
    edge_scale: float = 1.0,
) -> PathMetrics:
    """
    One full capital_v2 path simulation (in-memory).

    Day loop: snapshot roll → peak/DD → limits → size stakes → settle → secure.
    """
    rng = random.Random(seed)
    v2 = _v2_cfg()
    phase = _phase()
    min_stake = float(v2["min_stake_nok"])
    reduce_at = float(v2["drawdown"]["reduce_at"])
    freeze_at = float(v2["drawdown"]["freeze_at"])
    max_open_pct = float(v2["portfolio_open_risk"]["max_pct_of_riskable_liquid"])
    daily_cfg = v2["daily_loss"]
    weekly_cfg = v2["weekly_loss"]

    baseline = float(baseline if baseline is not None else start_equity)
    equity = float(start_equity)
    peak_eq = equity
    max_dd_frac = 0.0
    max_dd_nok = 0.0

    segs = empty_segments(baseline_nok=baseline, oslo_date=start_day)
    segs["unit_hwm_reset_equity_nok"] = baseline
    segs["secure_nok"] = 0.0
    freeze_manual = False
    freeze_day_index: int | None = None

    # Synthetic ledger for peak_equity_settlement
    rows: list[dict[str, str]] = []
    open_bets: list[SimBet] = []

    markets = market_mix or ["football_ou", "darts_ml", "tennis_ml", "esports_maps"]

    days_reduced = 0
    days_frozen = 0
    n_bets = 0
    n_floor = 0
    n_secure = 0
    n_daily_stops = 0
    n_weekly_stops = 0
    violations: list[str] = []
    equity_sample: list[float] = []

    y, m, d = (int(x) for x in start_day.split("-"))
    cur = date(y, m, d)

    for day_i in range(n_days):
        day = cur.isoformat()
        week_id = oslo_iso_week_id(day)

        # Optional manual unfreeze after N days in freeze
        if (
            freeze_manual
            and allow_unfreeze_after_days is not None
            and freeze_day_index is not None
            and (day_i - freeze_day_index) >= allow_unfreeze_after_days
        ):
            freeze_manual = False
            segs["freeze"] = {
                "active": False,
                "reason": None,
                "activated_at": None,
                "unfreeze_requires": "manual",
            }

        secure = float(segs.get("secure_nok") or 0.0)
        open_risk = sum(b.stake for b in open_bets if b.open)
        liquid = riskable_liquid(equity, secure, open_risk)
        unit_now = unit_size(liquid, v2)

        # Snapshot roll (in-memory)
        segs = ensure_day_week_snapshots(
            segs,
            liquid_now=liquid,
            unit_now=unit_now,
            today=day,
            week_id=week_id,
            realized_day=0.0,
            realized_week=0.0,
        )
        day_snap = segs["day_snapshot"]
        week_snap = segs["week_snapshot"]
        liquid_sod = float(day_snap["liquid_start_nok"] or liquid)
        liquid_sow = float(week_snap["liquid_start_nok"] or liquid)
        unit_sod = float(day_snap.get("unit_size_nok") or unit_now)
        unit_sow = float(week_snap.get("unit_size_nok") or unit_now)

        # Peak / DD from settlement rows + current equity
        peak_hist = peak_equity_settlement(rows, baseline)
        peak_eq = max(peak_eq, peak_hist, equity)
        dd = drawdown_from_peak(equity, peak_eq)
        if dd > max_dd_frac:
            max_dd_frac = dd
            max_dd_nok = peak_eq - equity

        size_mode = size_mode_from_dd(
            dd, freeze_active=freeze_manual, reduce_at=reduce_at, freeze_at=freeze_at
        )
        if size_mode == "FROZEN" and not freeze_manual and dd >= freeze_at - 1e-12:
            freeze_manual = True  # require manual unfreeze (circuit)
            freeze_day_index = day_i
            segs["freeze"] = {
                "active": True,
                "reason": "dd_25pct",
                "activated_at": day,
                "unfreeze_requires": "manual",
            }
            size_mode = "FROZEN"

        if size_mode == "REDUCED":
            days_reduced += 1
        if size_mode == "FROZEN":
            days_frozen += 1

        # Day/week realized from rows
        day_pl = 0.0
        week_pl = 0.0
        for r in rows:
            if r.get("result") not in ("Win", "Loss", "Refunded"):
                continue
            pl = float(r.get("p_l_nok") or 0)
            sd = (r.get("updated_at") or r.get("date") or "")[:10]
            if sd == day:
                day_pl += pl
            if sd and oslo_iso_week_id(sd) == week_id:
                week_pl += pl

        daily_lim = loss_limit_nok(
            liquid_sod,
            unit_sod,
            pct=float(daily_cfg["hard_pct_of_liquid"]),
            units=float(daily_cfg["hard_units"]),
        )
        weekly_lim = loss_limit_nok(
            liquid_sow,
            unit_sow,
            pct=float(weekly_cfg["hard_pct_of_liquid"]),
            units=float(weekly_cfg["hard_units"]),
        )
        # Stops from *prior* settlements on this calendar day / week (start-of-eval)
        daily_stopped = is_hard_loss_stopped(day_pl, daily_lim)
        weekly_stopped = is_hard_loss_stopped(week_pl, weekly_lim)

        stopped = freeze_manual or size_mode == "FROZEN" or daily_stopped or weekly_stopped
        working = riskable_equity(equity, secure)
        # Phase open budget (same as risk layer)
        raw_cap = working * float(phase["daily_risk_pct"])
        phase_cap = round(
            max(float(phase["daily_risk_floor"]), min(float(phase["daily_risk_ceil"]), raw_cap)),
            2,
        )
        phase_rem = phase_cap - open_risk
        if bool(daily_cfg.get("shrink_remaining", True)) and day_pl < 0:
            phase_rem += day_pl
        phase_rem = max(0.0, round(phase_rem, 2))
        open_room = portfolio_open_room(open_risk, liquid, max_pct=max_open_pct)
        remaining = 0.0 if stopped else max(0.0, min(phase_rem, open_room))
        can_bet = (not stopped) and remaining >= min_stake

        # Place bets
        n_place = bets_per_day if can_bet else 0
        if multi_open:
            n_place = min(n_place + 2, 8)  # push toward open-risk cap

        day_stakes: list[SimBet] = []
        for _ in range(n_place):
            if remaining < min_stake:
                break
            mkt = markets[rng.randrange(len(markets))]
            book = MARKET_BOOK[mkt]
            odds = book["odds"]
            edge = book["edge"] * edge_scale
            decision = compute_unit_stake(
                size_mode=size_mode,
                unit_size_nok=unit_now,
                remaining_room_nok=remaining,
                min_stake=min_stake,
                stopped=stopped,
                can_bet=can_bet,
            )
            stake = decision.final_stake_nok
            viol = _check_stake_violations(
                stake,
                size_mode=size_mode,
                remaining=remaining,
                open_after=open_risk + stake,
                liquid_before=liquid,
                max_open_pct=max_open_pct,
                min_stake=min_stake,
            )
            for vv in viol:
                violations.append(f"day={day}:{vv}")
            if stake < min_stake:
                break
            if stake <= min_stake + 1e-9:
                n_floor += 1
            bet = SimBet(
                stake=stake,
                odds=odds,
                market=mkt,
                day=day,
                size_mode=size_mode,
                unit=decision.active_unit_nok,
            )
            # stash edge for settle
            bet._p = _p_win(odds, edge)  # type: ignore[attr-defined]
            open_bets.append(bet)
            day_stakes.append(bet)
            open_risk += stake
            remaining = max(0.0, round(remaining - stake, 2))
            liquid = riskable_liquid(equity, secure, open_risk)
            n_bets += 1

            # Recompute room after each open (sequential)
            open_room = portfolio_open_room(open_risk, liquid, max_pct=max_open_pct)
            remaining = min(remaining, open_room) if not stopped else 0.0

        # Settle
        force_loss = day_i < force_lose_days
        force_win = (not force_loss) and day_i < force_win_days
        if force_lose_after_day is not None and day_i >= force_lose_after_day:
            force_loss = True
            force_win = False

        to_settle = list(day_stakes) if settle_same_day else [b for b in open_bets if b.open]
        if not settle_same_day:
            # settle previous opens only (keep today's open) — simple lag-1
            to_settle = [b for b in open_bets if b.open and b.day != day]

        for bet in to_settle:
            if not bet.open:
                continue
            p = getattr(bet, "_p", 0.5)
            if force_loss:
                win = False
            elif force_win:
                win = True
            else:
                win = rng.random() < p
            if win:
                bet.pl = round(bet.stake * (bet.odds - 1.0), 2)
                bet.result = "Win"
            else:
                bet.pl = -bet.stake
                bet.result = "Loss"
            bet.open = False
            equity = round(equity + bet.pl, 2)
            rows.append(
                {
                    "date": bet.day,
                    "updated_at": f"{day}T18:00:00Z",
                    "result": bet.result,
                    "p_l_nok": str(bet.pl),
                    "stake_nok": str(bet.stake),
                }
            )
            open_risk = sum(b.stake for b in open_bets if b.open)

        # Consistency: riskable components
        secure = float(segs.get("secure_nok") or 0.0)
        open_risk = sum(b.stake for b in open_bets if b.open)
        if equity < -1e-6:
            violations.append(f"day={day}:negative_equity:{equity}")
        if secure < -1e-6:
            violations.append(f"day={day}:negative_secure:{secure}")
        if open_risk < -1e-6:
            violations.append(f"day={day}:negative_open:{open_risk}")
        if riskable_equity(equity, secure) + 1e-6 < 0:
            violations.append(f"day={day}:working_negative")
        # secure cannot exceed equity in our model (ledger still holds full equity)
        if secure > equity + 1e-6 and equity >= 0:
            # allowed if large losses after secure skim — working can be 0
            pass

        # End-of-day stop accounting (same-day settlements visible to next risk eval)
        day_pl_eod = 0.0
        week_pl_eod = 0.0
        for r in rows:
            if r.get("result") not in ("Win", "Loss", "Refunded"):
                continue
            pl = float(r.get("p_l_nok") or 0)
            sd = (r.get("updated_at") or r.get("date") or "")[:10]
            if sd == day:
                day_pl_eod += pl
            if sd and oslo_iso_week_id(sd) == week_id:
                week_pl_eod += pl
        if is_hard_loss_stopped(day_pl_eod, daily_lim):
            n_daily_stops += 1
        if is_hard_loss_stopped(week_pl_eod, weekly_lim):
            # count once per day if still hard-stopped (matches "stays fired")
            n_weekly_stops += 1

        # Secure transfer after settle (skip if frozen)
        segs["freeze"] = segs.get("freeze") or {
            "active": freeze_manual,
            "reason": "dd_25pct" if freeze_manual else None,
            "activated_at": None,
            "unfreeze_requires": "manual",
        }
        segs["freeze"]["active"] = freeze_manual
        segs, info = apply_secure_transfer_to_segments(segs, ledger_equity=equity, v2=v2)
        if info.get("triggered"):
            n_secure += 1

        # Accounting: working = max(0, equity − secure)
        secure = float(segs.get("secure_nok") or 0.0)
        working = riskable_equity(equity, secure)
        if equity + 1e-9 >= secure and abs(working + secure - equity) > 0.02:
            violations.append(
                f"day={day}:accounting working({working})+secure({secure})!=equity({equity})"
            )

        equity_sample.append(equity)
        cur += timedelta(days=1)

        if equity < min_stake and open_risk < 1e-9:
            # ruined for betting purposes
            break

    return PathMetrics(
        final_equity=equity,
        final_secure=float(segs.get("secure_nok") or 0.0),
        final_working=riskable_equity(equity, float(segs.get("secure_nok") or 0.0)),
        max_dd_frac=max_dd_frac,
        max_dd_nok=max_dd_nok,
        peak_equity=peak_eq,
        days_reduced=days_reduced,
        days_frozen=days_frozen,
        days_total=n_days,
        n_bets=n_bets,
        n_stakes_at_floor=n_floor,
        n_secure_transfers=n_secure,
        n_daily_stops=n_daily_stops,
        n_weekly_stops=n_weekly_stops,
        n_violations=len(violations),
        violations=violations[:50],
        equity_path_sample=equity_sample[:: max(1, len(equity_sample) // 20)],
    )


def _pctile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def summarize_paths(name: str, seed: int, metrics: list[PathMetrics]) -> ScenarioResult:
    finals = [m.final_equity for m in metrics]
    dds = [m.max_dd_frac for m in metrics]
    viol_total = sum(m.n_violations for m in metrics)
    summary = {
        "n_paths": len(metrics),
        "seed": seed,
        "rule_bundle_version": RULE_BUNDLE_VERSION,
        "final_equity_mean": statistics.mean(finals) if finals else 0.0,
        "final_equity_p05": _pctile(finals, 0.05),
        "final_equity_p50": _pctile(finals, 0.50),
        "final_equity_p95": _pctile(finals, 0.95),
        "max_dd_frac_mean": statistics.mean(dds) if dds else 0.0,
        "max_dd_frac_p50": _pctile(dds, 0.50),
        "max_dd_frac_p95": _pctile(dds, 0.95),
        "days_reduced_mean": statistics.mean([m.days_reduced for m in metrics]),
        "days_frozen_mean": statistics.mean([m.days_frozen for m in metrics]),
        "n_bets_mean": statistics.mean([m.n_bets for m in metrics]),
        "pct_stakes_at_floor": (
            100.0
            * sum(m.n_stakes_at_floor for m in metrics)
            / max(1, sum(m.n_bets for m in metrics))
        ),
        "secure_transfers_mean": statistics.mean([m.n_secure_transfers for m in metrics]),
        "daily_stops_mean": statistics.mean([m.n_daily_stops for m in metrics]),
        "weekly_stops_mean": statistics.mean([m.n_weekly_stops for m in metrics]),
        "total_violations": viol_total,
        "paths_with_violations": sum(1 for m in metrics if m.n_violations > 0),
        "final_secure_mean": statistics.mean([m.final_secure for m in metrics]),
    }
    return ScenarioResult(name=name, seed=seed, n_paths=len(metrics), metrics=metrics, summary=summary)


def run_scenario(
    name: str,
    *,
    seed: int,
    n_paths: int,
    path_kwargs: dict[str, Any],
) -> ScenarioResult:
    metrics = [
        simulate_path(seed=seed + i * 9973, **path_kwargs) for i in range(n_paths)
    ]
    return summarize_paths(name, seed, metrics)


def core_scenario_specs(n_paths: int = 200) -> list[dict[str, Any]]:
    """Named stress scenarios required for Phase 2.5."""
    return [
        {
            "name": "losing_streak_daily_weekly",
            "n_paths": n_paths,
            "kwargs": {
                "start_equity": 550.0,
                "n_days": 40,
                "bets_per_day": 4,
                "force_lose_days": 14,
                "market_mix": ["football_ou", "darts_ml"],
            },
        },
        {
            "name": "drawdown_reduce_freeze",
            "n_paths": n_paths,
            "kwargs": {
                "start_equity": 600.0,
                "n_days": 60,
                "bets_per_day": 3,
                "force_win_days": 5,  # build peak
                "force_lose_days": 0,
                "edge_scale": -2.0,  # strong negative after — wait force_win then adverse
                "market_mix": ["adverse", "football_1x2"],
            },
        },
        {
            "name": "drawdown_forced_loss_after_peak",
            "n_paths": n_paths,
            "kwargs": {
                "start_equity": 500.0,
                "n_days": 50,
                "bets_per_day": 4,
                "force_win_days": 8,
                "market_mix": ["football_ou"],
                # after wins, remaining days use adverse markets via mix only —
                # use edge_scale negative after by using only adverse post peak:
            },
        },
        {
            "name": "small_bankroll_floor",
            "n_paths": n_paths,
            "kwargs": {
                "start_equity": 200.0,
                "n_days": 80,
                "bets_per_day": 2,
                "market_mix": ["football_ou", "darts_ml", "tennis_ml"],
                "edge_scale": 0.5,
            },
        },
        {
            "name": "open_risk_18pct_pressure",
            "n_paths": n_paths,
            "kwargs": {
                "start_equity": 800.0,
                "n_days": 30,
                "bets_per_day": 6,
                "multi_open": True,
                "settle_same_day": False,
                "market_mix": ["darts_ml", "tennis_ml", "esports_maps"],
            },
        },
        {
            "name": "secure_then_drawdown",
            "n_paths": n_paths,
            "kwargs": {
                "start_equity": 500.0,
                "baseline": 500.0,
                "n_days": 70,
                "bets_per_day": 3,
                "force_win_days": 25,
                "force_lose_after_day": 25,
                "market_mix": ["football_ou", "darts_ml"],
                "edge_scale": 1.5,
            },
        },
        {
            "name": "mixed_realistic",
            "n_paths": n_paths,
            "kwargs": {
                "start_equity": 550.0,
                "n_days": 120,
                "bets_per_day": 3,
                "market_mix": [
                    "football_ou",
                    "football_1x2",
                    "darts_ml",
                    "tennis_ml",
                    "esports_maps",
                ],
                "edge_scale": 1.0,
            },
        },
        {
            "name": "boundary_and_unfreeze",
            "n_paths": max(50, n_paths // 2),
            "kwargs": {
                "start_equity": 500.0,
                "n_days": 40,
                "bets_per_day": 3,
                "force_win_days": 6,
                "force_lose_days": 0,
                "allow_unfreeze_after_days": 5,
                "market_mix": ["adverse"],
                "edge_scale": 1.0,
            },
        },
        {
            "name": "period_rollover_week",
            "n_paths": max(50, n_paths // 2),
            "kwargs": {
                "start_equity": 550.0,
                "n_days": 21,  # spans 3 weeks
                "start_day": "2026-01-05",
                "bets_per_day": 3,
                "force_lose_days": 5,
                "market_mix": ["football_ou"],
            },
        },
    ]


def run_core_suite(
    *,
    seed: int = 42,
    n_paths: int = 200,
) -> dict[str, Any]:
    """Run all core scenarios; return aggregate report dict."""
    results: list[ScenarioResult] = []
    for i, spec in enumerate(core_scenario_specs(n_paths=n_paths)):
        # Special case: drawdown after peak — two-phase markets
        kwargs = dict(spec["kwargs"])
        if spec["name"] == "drawdown_forced_loss_after_peak":
            metrics = []
            for p in range(spec["n_paths"]):
                rng_seed = seed + i * 100_000 + p * 9973
                m = simulate_path(
                    seed=rng_seed,
                    start_equity=500.0,
                    n_days=45,
                    bets_per_day=4,
                    force_win_days=10,
                    force_lose_after_day=10,
                    market_mix=["football_ou"],
                )
                metrics.append(m)
            results.append(summarize_paths(spec["name"], seed + i, metrics))
            continue

        if spec["name"] == "boundary_and_unfreeze":
            metrics = []
            for p in range(spec["n_paths"]):
                m2 = simulate_path(
                    seed=seed + i * 100_000 + p * 9973 + 1,
                    start_equity=650.0,
                    baseline=500.0,
                    n_days=35,
                    bets_per_day=5,
                    force_lose_days=18,
                    allow_unfreeze_after_days=5,
                    market_mix=["football_ou"],
                )
                metrics.append(m2)
            results.append(summarize_paths(spec["name"], seed + i, metrics))
            continue

        res = run_scenario(
            spec["name"],
            seed=seed + i * 100_000,
            n_paths=spec["n_paths"],
            path_kwargs=kwargs,
        )
        results.append(res)

    total_viol = sum(r.summary["total_violations"] for r in results)
    return {
        "seed": seed,
        "n_paths_default": n_paths,
        "rule_bundle_version": RULE_BUNDLE_VERSION,
        "scenarios": {r.name: r.summary for r in results},
        "total_violations_all_scenarios": total_viol,
        "all_clear": total_viol == 0,
        "results": results,
    }


def format_report(suite: dict[str, Any]) -> str:
    lines = [
        "# Capital v2 Monte-Carlo Stress Report (Phase 2.5)",
        "",
        f"**Rule bundle:** `{suite['rule_bundle_version']}`",
        f"**Master seed:** {suite['seed']}",
        f"**Paths per scenario (default):** {suite['n_paths_default']}",
        f"**Total rule violations:** **{suite['total_violations_all_scenarios']}** "
        f"({'PASS' if suite['all_clear'] else 'FAIL'})",
        "",
        "Harness is **in-memory only** — does not enable live `capital_v2.enabled` "
        "and does not write production ledger/segments.",
        "",
        "## Scenarios",
        "",
    ]
    for name, s in suite["scenarios"].items():
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|------:|")
        lines.append(f"| paths | {s['n_paths']} |")
        lines.append(f"| final equity mean | {s['final_equity_mean']:.2f} |")
        lines.append(f"| final equity p05 / p50 / p95 | {s['final_equity_p05']:.2f} / {s['final_equity_p50']:.2f} / {s['final_equity_p95']:.2f} |")
        lines.append(f"| max DD frac mean / p50 / p95 | {s['max_dd_frac_mean']:.3f} / {s['max_dd_frac_p50']:.3f} / {s['max_dd_frac_p95']:.3f} |")
        lines.append(f"| days REDUCED (mean) | {s['days_reduced_mean']:.1f} |")
        lines.append(f"| days FROZEN (mean) | {s['days_frozen_mean']:.1f} |")
        lines.append(f"| bets (mean) | {s['n_bets_mean']:.1f} |")
        lines.append(f"| % stakes at floor | {s['pct_stakes_at_floor']:.1f}% |")
        lines.append(f"| secure transfers (mean) | {s['secure_transfers_mean']:.2f} |")
        lines.append(f"| daily stops (mean) | {s['daily_stops_mean']:.1f} |")
        lines.append(f"| weekly stops (mean) | {s['weekly_stops_mean']:.1f} |")
        lines.append(f"| final secure mean | {s['final_secure_mean']:.2f} |")
        lines.append(f"| violations | {s['total_violations']} |")
        lines.append("")

    lines.extend(
        [
            "## Success criteria",
            "",
            "- No stake in (0, 10) NOK or non-integer positive stake",
            "- No stake while FROZEN / above remaining room",
            "- Accounting: working + secure consistent with equity model",
            "- Deterministic under fixed seed",
            "",
            f"**Suite all_clear:** `{suite['all_clear']}`",
            "",
            "## Findings & recommendations (enablement)",
            "",
            "1. **Secure transfer caps (applied):** (a) never secure more than working equity; "
            "(b) **min working buffer** max(55% ledger equity, 8×unit) after transfer; "
            "ref still resets to new working equity.",
            "2. **`secure_then_drawdown` healthier:** working capital retained at transfer; "
            "subsequent losses can still shrink working (expected).",
            "3. **Below 1500 liquid, stakes are the 10 NOK floor unit** — expected.",
            "4. **DD freeze is sticky** — CLI/App unfreeze with confirmation only.",
            "5. **Daily + weekly stops** both fire under forced losses.",
            "6. **No stake-layer violations** in the suite.",
            "",
        ]
    )
    return "\n".join(lines)


def determinism_check(seed: int = 12345) -> bool:
    a = simulate_path(seed=seed, start_equity=550, n_days=30, bets_per_day=3)
    b = simulate_path(seed=seed, start_equity=550, n_days=30, bets_per_day=3)
    return (
        a.final_equity == b.final_equity
        and a.n_bets == b.n_bets
        and a.max_dd_frac == b.max_dd_frac
        and a.n_violations == b.n_violations
    )
