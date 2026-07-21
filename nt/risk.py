from __future__ import annotations

import json
from datetime import date
from typing import Any

from nt.bets_io import fnum, is_open_risk, is_performance_settled, load_bets, settlement_calendar_day
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
    """
    Realized P/L for the **settlement calendar day** (Europe/Oslo via updated_at).

    Before (buggy): filtered on ledger ``date`` (match kickoff date).
    After: uses ``settlement_calendar_day(row)`` so kill-switch tracks when
    outcomes were recorded, not when the match was scheduled.
    """
    day = day or date.today().isoformat()
    total = 0.0
    for r in rows:
        if is_open_risk(r.get("result")):
            continue
        if settlement_calendar_day(r) != day:
            continue
        # Win/Loss/Refunded only (Abandoned is terminal but never moves day P/L)
        if not is_performance_settled(r.get("result")):
            continue
        total += fnum(r.get("p_l_nok")) or 0.0
    return round(total, 2)


def week_realized_pl(rows: list[dict[str, str]], week_id: str | None = None) -> float:
    """
    Realized performance P/L for an ISO week (Europe/Oslo settlement days).

    ``week_id`` format: ``YYYY-Www`` (same as ``capital_v2.oslo_iso_week_id``).
    """
    from nt.capital_v2 import oslo_iso_week_id, oslo_today

    week_id = week_id or oslo_iso_week_id(oslo_today())
    total = 0.0
    for r in rows:
        if is_open_risk(r.get("result")):
            continue
        if not is_performance_settled(r.get("result")):
            continue
        d = settlement_calendar_day(r)
        if not d:
            continue
        if oslo_iso_week_id(d) != week_id:
            continue
        total += fnum(r.get("p_l_nok")) or 0.0
    return round(total, 2)


def day_pending_risk(rows: list[dict[str, str]], day: str | None = None) -> float:
    """
    Open risk against today's budget: all Pending + ConfirmedPlaced stakes.

    Multi-run days share one budget; match-date filter is intentionally not used
    (a tomorrow kickoff still consumes today's risk when logged open).
    """
    _ = day  # reserved for future day-scoped views; open risk is book-wide
    total = 0.0
    for r in rows:
        if not is_open_risk(r.get("result")):
            continue
        total += fnum(r.get("stake_nok")) or 0.0
    return round(total, 2)


def evaluate_risk(
    cfg: dict[str, Any],
    equity: float,
    phase: dict[str, Any],
    rows: list[dict[str, str]] | None = None,
    *,
    segments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Single risk entry point.

    When ``capital_v2.enabled`` is false (default): legacy behaviour only —
    phase daily cap, equity-% kill-switch, open-pending remaining.

    When true: fail-closed capital_v2 layers (manual freeze → DD freeze →
    weekly → daily → portfolio open-risk room), still exposing remaining_risk
    for downstream sizing (Phase 2.3).
    """
    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))

    from nt.capital_v2 import capital_v2_cfg

    v2 = capital_v2_cfg(cfg)
    if not bool(v2.get("enabled")):
        return _evaluate_risk_legacy(cfg, equity, phase, rows)

    return _evaluate_risk_capital_v2(cfg, equity, phase, rows, segments=segments, v2=v2)


def _evaluate_risk_legacy(
    cfg: dict[str, Any],
    equity: float,
    phase: dict[str, Any],
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Pre-capital_v2 risk evaluation — behaviour frozen for flag-off identity."""
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
        "formula": (
            "daily_cap = clamp(equity * phase.daily_risk_pct, floor, ceil); "
            "today_pl = sum(settled P/L by settlement calendar day from updated_at); "
            "open_risk = Pending + ConfirmedPlaced stakes"
        ),
    }


def _evaluate_risk_capital_v2(
    cfg: dict[str, Any],
    equity: float,
    phase: dict[str, Any],
    rows: list[dict[str, str]],
    *,
    segments: dict[str, Any] | None,
    v2: dict[str, Any],
) -> dict[str, Any]:
    """
    Fail-closed capital_v2 risk stack (Phase 2.2).

    Order: L0 manual freeze → L1 DD freeze → L2 weekly hard stop →
    L3 daily hard stop → portfolio open-risk room + phase open budget.
    Does not size bets (2.3) or mutate segments/snapshots.
    """
    from nt.capital_segments import is_frozen, load_segments
    from nt.capital_v2 import (
        drawdown_from_peak,
        is_hard_loss_stopped,
        loss_limit_nok,
        oslo_iso_week_id,
        oslo_today,
        peak_equity_settlement,
        portfolio_open_risk_cap,
        portfolio_open_room,
        riskable_equity,
        riskable_liquid,
        size_mode_from_dd,
        unit_size,
    )

    min_stake = float(
        v2.get("min_stake_nok")
        or (cfg.get("norsk_tipping") or {}).get("min_stake_nok")
        or 10.0
    )
    today = oslo_today()
    week_id = oslo_iso_week_id(today)
    baseline = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)

    if segments is None:
        try:
            segments = load_segments(cfg, baseline_nok=baseline)
        except Exception:
            # Fail-closed segments: no freeze, no secure — still apply pure limits
            from nt.capital_v2 import empty_segments

            segments = empty_segments(baseline_nok=baseline, oslo_date=today)

    secure_nok = max(0.0, float(segments.get("secure_nok") or 0.0))
    freeze_manual = is_frozen(segments)

    open_pending = day_pending_risk(rows, today)
    working_eq = riskable_equity(equity, secure_nok)
    liquid_now = riskable_liquid(equity, secure_nok, open_pending)

    # Snapshots are read-only for 2.2 (no mutation). Missing → current liquid.
    day_snap = dict(segments.get("day_snapshot") or {})
    week_snap = dict(segments.get("week_snapshot") or {})
    if day_snap.get("oslo_date") == today and day_snap.get("liquid_start_nok") is not None:
        liquid_sod = max(0.0, float(day_snap["liquid_start_nok"]))
    else:
        liquid_sod = liquid_now
    if week_snap.get("week_id") == week_id and week_snap.get("liquid_start_nok") is not None:
        liquid_sow = max(0.0, float(week_snap["liquid_start_nok"]))
    else:
        liquid_sow = liquid_now

    unit_sod = float(day_snap.get("unit_size_nok") or 0.0) or unit_size(liquid_sod, v2)
    unit_sow = float(week_snap.get("unit_size_nok") or 0.0) or unit_size(liquid_sow, v2)
    unit_now = unit_size(liquid_now, v2)

    peak = peak_equity_settlement(rows, baseline)
    dd = drawdown_from_peak(equity, peak)
    dd_cfg = v2.get("drawdown") or {}
    reduce_at = float(dd_cfg.get("reduce_at") or 0.15)
    freeze_at = float(dd_cfg.get("freeze_at") or 0.25)
    size_mode = size_mode_from_dd(
        dd,
        freeze_active=freeze_manual,
        reduce_at=reduce_at,
        freeze_at=freeze_at,
    )
    dd_frozen = size_mode == "FROZEN"

    realized_day = day_realized_pl(rows, today)
    realized_week = week_realized_pl(rows, week_id)

    daily_cfg = v2.get("daily_loss") or {}
    weekly_cfg = v2.get("weekly_loss") or {}
    daily_limit = loss_limit_nok(
        liquid_sod,
        unit_sod,
        pct=float(daily_cfg.get("hard_pct_of_liquid") or 0.04),
        units=float(daily_cfg.get("hard_units") or 3.0),
    )
    weekly_limit = loss_limit_nok(
        liquid_sow,
        unit_sow,
        pct=float(weekly_cfg.get("hard_pct_of_liquid") or 0.08),
        units=float(weekly_cfg.get("hard_units") or 6.0),
    )
    daily_stopped = is_hard_loss_stopped(realized_day, daily_limit)
    weekly_stopped = is_hard_loss_stopped(realized_week, weekly_limit)

    # Phase open-risk budget (L4) on working equity for scale; legacy used full equity.
    phase_cap = daily_risk_cap(working_eq, phase)
    phase_remaining = round(phase_cap - open_pending, 2)
    if bool(daily_cfg.get("shrink_remaining", True)) and realized_day < 0:
        # Daily loss reduces remaining open-risk budget for the rest of the day
        phase_remaining = round(phase_remaining + realized_day, 2)
    phase_remaining = max(0.0, phase_remaining)

    por_cfg = v2.get("portfolio_open_risk") or {}
    max_open_pct = float(por_cfg.get("max_pct_of_riskable_liquid") or 0.18)
    open_cap = portfolio_open_risk_cap(liquid_now, max_pct=max_open_pct)
    open_room = portfolio_open_room(open_pending, liquid_now, max_pct=max_open_pct)

    remaining = min(phase_remaining, open_room)

    reasons: list[str] = []
    stopped = False  # hard stop (no new risk)

    # L0 manual freeze
    if freeze_manual:
        stopped = True
        remaining = 0.0
        reasons.append("L0 MANUAL FREEZE: capital_segments.freeze.active=true")

    # L1 DD freeze (25%) — size_mode FROZEN includes manual; only append DD if not manual
    if dd_frozen and not freeze_manual:
        stopped = True
        remaining = 0.0
        reasons.append(
            f"L1 DD FREEZE: drawdown {dd:.1%} from peak {peak:.2f} >= {freeze_at:.0%}"
        )
    elif size_mode == "REDUCED":
        reasons.append(
            f"L1 DD REDUCED: drawdown {dd:.1%} from peak {peak:.2f} >= {reduce_at:.0%} "
            f"(size_mode=REDUCED; sizing applies in 2.3)"
        )

    # L2 weekly hard stop
    if weekly_stopped:
        stopped = True
        remaining = 0.0
        reasons.append(
            f"L2 WEEKLY STOP: week P/L {realized_week:+.2f} <= -{weekly_limit:.2f} "
            f"(week {week_id})"
        )

    # L3 daily hard stop
    if daily_stopped:
        stopped = True
        remaining = 0.0
        reasons.append(
            f"L3 DAILY STOP: today P/L {realized_day:+.2f} <= -{daily_limit:.2f}"
        )

    # Portfolio open-risk / phase budget exhaustion (soft block via remaining)
    if not stopped:
        if open_room <= 0 and open_pending > 0:
            reasons.append(
                f"portfolio open-risk exhausted: open {open_pending:.2f} / "
                f"cap {open_cap:.2f} ({max_open_pct:.0%} of liquid {liquid_now:.2f})"
            )
        if phase_remaining <= 0:
            reasons.append(
                f"daily open budget exhausted: pending {open_pending:.2f} / "
                f"phase_cap {phase_cap:.2f}"
                + (
                    f" after realized {realized_day:+.2f}"
                    if realized_day < 0 and bool(daily_cfg.get("shrink_remaining", True))
                    else ""
                )
            )

    if stopped:
        remaining = 0.0
    else:
        remaining = max(0.0, round(remaining, 2))

    can_bet = (not stopped) and remaining >= min_stake

    # Legacy-compatible kill-switch fields: stopped if hard stop OR cannot bet
    # Preserve keys used by status/recommend; extend with v2 diagnostics.
    legacy_stop_lim = stop_day_loss_limit(cfg, equity)

    return {
        "date": today,
        "equity_nok": equity,
        "phase_id": phase["phase_id"],
        "daily_risk_cap_nok": phase_cap,
        "daily_risk_pct": phase["daily_risk_pct"],
        "open_pending_risk_nok": open_pending,
        "remaining_risk_nok": remaining,
        "today_realized_pl_nok": realized_day,
        "stop_day_loss_limit_nok": daily_limit,  # Set B daily limit (not legacy %)
        "stopped": stopped,
        "can_bet": can_bet,
        "reasons": reasons,
        "formula": (
            "capital_v2 fail-closed: L0 freeze → L1 DD(15% REDUCED/25% FROZEN) → "
            "L2 weekly(8%|6u) → L3 daily(4%|3u) → "
            "remaining=min(phase_cap−open[−day_loss], portfolio_open_room 18% liquid); "
            "settlement-day P/L Europe/Oslo; working=equity−secure"
        ),
        # capital_v2 diagnostics (downstream 2.3 sizing / App)
        "capital_v2_enabled": True,
        "rule_bundle_version": v2.get("rule_bundle_version"),
        "secure_nok": secure_nok,
        "working_equity_nok": working_eq,
        "riskable_liquid_nok": liquid_now,
        "liquid_start_of_day_nok": liquid_sod,
        "liquid_start_of_week_nok": liquid_sow,
        "unit_size_nok": unit_now,
        "unit_size_sod_nok": unit_sod,
        "peak_equity_nok": peak,
        "drawdown_from_peak": round(dd, 6),
        "size_mode": size_mode,
        "freeze_manual": freeze_manual,
        "dd_frozen": dd_frozen and not freeze_manual,
        "week_id": week_id,
        "week_realized_pl_nok": realized_week,
        "daily_loss_limit_nok": daily_limit,
        "weekly_loss_limit_nok": weekly_limit,
        "daily_hard_stopped": daily_stopped,
        "weekly_hard_stopped": weekly_stopped,
        "portfolio_open_risk_cap_nok": open_cap,
        "portfolio_open_room_nok": open_room,
        "portfolio_open_max_pct": max_open_pct,
        "phase_remaining_before_portfolio_nok": phase_remaining if not stopped else 0.0,
        "min_stake_nok": min_stake,
        "legacy_stop_day_loss_limit_nok": legacy_stop_lim,
    }


def write_risk_state(cfg: dict[str, Any], risk: dict[str, Any]) -> None:
    state_dir = path_from_config(cfg, "state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "risk.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(risk, f, indent=2)
        f.write("\n")
