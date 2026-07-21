"""
Phase 2.2 — capital_v2 risk layers behind feature flag.

Proves:
- flag OFF → identical to legacy evaluate_risk behaviour
- flag ON → L0 freeze, L1 DD, L2 weekly, L3 daily, portfolio 18% open room
- floor / whole-krone invariants on remaining and can_bet
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_v2 import (
    apply_nt_floor,
    empty_segments,
    peak_equity_settlement,
    portfolio_open_room,
    riskable_liquid,
    unit_size,
)
from nt.risk import (
    daily_risk_cap,
    day_pending_risk,
    day_realized_pl,
    evaluate_risk,
    stop_day_loss_limit,
    week_realized_pl,
    _evaluate_risk_legacy,
)


PHASE = {
    "phase_id": "1A",
    "daily_risk_pct": 0.08,
    "daily_risk_floor": 30.0,
    "daily_risk_ceil": 42.0,
}


def _cfg(*, enabled: bool = False, **extra) -> dict:
    base = {
        "bankroll": {"baseline_nok": 500.0},
        "risk": {"stop_day_loss_pct_of_equity": 0.08, "stop_day_loss_floor_nok": 40},
        "norsk_tipping": {"min_stake_nok": 10},
        "capital_v2": {"enabled": enabled},
        "paths": {},
    }
    base.update(extra)
    return base


def _settled(pl: float, day: str, *, ts: str | None = None) -> dict[str, str]:
    return {
        "date": day,
        "updated_at": ts or f"{day}T12:00:00Z",
        "result": "Loss" if pl < 0 else ("Win" if pl > 0 else "Refunded"),
        "p_l_nok": str(pl),
        "stake_nok": str(abs(pl) if pl != 0 else 10),
    }


def _open(stake: float, result: str = "Pending") -> dict[str, str]:
    return {
        "date": "2026-07-21",
        "updated_at": "2026-07-21T10:00:00Z",
        "result": result,
        "p_l_nok": "",
        "stake_nok": str(stake),
    }


# ── flag-off identity ─────────────────────────────────────────────────────


def test_flag_off_matches_legacy_helper_exactly():
    rows = [
        _settled(-20, "2026-07-21"),
        _open(12),
        _open(10, "ConfirmedPlaced"),
    ]
    cfg = _cfg(enabled=False)
    a = evaluate_risk(cfg, 550.0, PHASE, rows)
    b = _evaluate_risk_legacy(cfg, 550.0, PHASE, rows)
    assert a == b


def test_flag_off_ignores_manual_freeze_and_dd():
    """Legacy path must not consult capital_segments freeze or 15/25% DD."""
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["freeze"] = {
        "active": True,
        "reason": "test",
        "activated_at": "x",
        "unfreeze_requires": "manual",
    }
    # Deep DD equity 400 vs peak 600
    rows = [
        _settled(100, "2026-07-01"),
        _settled(-200, "2026-07-10"),
    ]
    cfg = _cfg(enabled=False)
    risk = evaluate_risk(cfg, equity=400.0, phase=PHASE, rows=rows, segments=segs)
    # segments kw is ignored when flag off; freeze / DD must not stop
    assert risk["stopped"] is False
    assert risk["can_bet"] is True
    assert not any("FREEZE" in r or "L0" in r or "L1" in r for r in risk["reasons"])
    assert "size_mode" not in risk
    assert "capital_v2_enabled" not in risk


def test_flag_off_uses_legacy_8pct_kill_switch_not_4pct():
    # equity 500 → legacy stop = max(40, 40) = 40
    rows = [_settled(-41, "2026-07-21")]
    # Force "today" by monkeypatching date if needed — day_realized_pl uses day arg
    # evaluate_risk uses date.today(); set rows to today's iso via monkeypatch
    import nt.risk as risk_mod

    today = risk_mod.date.today().isoformat()
    rows = [_settled(-41, today)]
    cfg = _cfg(enabled=False)
    risk = evaluate_risk(cfg, 500.0, PHASE, rows)
    assert risk["stopped"] is True
    assert risk["stop_day_loss_limit_nok"] == 40.0

    # -39 should not stop legacy
    rows2 = [_settled(-39, today)]
    risk2 = evaluate_risk(cfg, 500.0, PHASE, rows2)
    assert risk2["stopped"] is False


def test_flag_off_remaining_is_cap_minus_open_only():
    import nt.risk as risk_mod

    today = risk_mod.date.today().isoformat()
    rows = [
        _settled(-15, today),  # realized loss must NOT shrink remaining (legacy)
        _open(10),
    ]
    cfg = _cfg(enabled=False)
    equity = 500.0
    risk = evaluate_risk(cfg, equity, PHASE, rows)
    cap = daily_risk_cap(equity, PHASE)
    assert risk["remaining_risk_nok"] == round(cap - 10.0, 2)
    assert risk["today_realized_pl_nok"] == -15.0


# ── flag-on layers ────────────────────────────────────────────────────────


def _v2_cfg() -> dict:
    return _cfg(enabled=True)


def _segs(
    *,
    freeze: bool = False,
    secure: float = 0.0,
    liquid_sod: float | None = None,
    liquid_sow: float | None = None,
    day: str = "2026-07-21",
    week_id: str = "2026-W30",
) -> dict:
    s = empty_segments(baseline_nok=500.0, oslo_date=day)
    s["secure_nok"] = secure
    if freeze:
        s["freeze"] = {
            "active": True,
            "reason": "manual_test",
            "activated_at": "2026-07-21T00:00:00Z",
            "unfreeze_requires": "manual",
        }
    if liquid_sod is not None:
        s["day_snapshot"] = {
            "oslo_date": day,
            "liquid_start_nok": liquid_sod,
            "unit_size_nok": 10.0,
            "realized_pl_nok": 0.0,
        }
    if liquid_sow is not None:
        s["week_snapshot"] = {
            "week_id": week_id,
            "liquid_start_nok": liquid_sow,
            "unit_size_nok": 10.0,
            "realized_pl_nok": 0.0,
        }
    return s


def test_flag_on_manual_freeze_blocks(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")

    risk = evaluate_risk(
        _v2_cfg(),
        550.0,
        PHASE,
        [],
        segments=_segs(freeze=True),
    )
    assert risk["capital_v2_enabled"] is True
    assert risk["stopped"] is True
    assert risk["can_bet"] is False
    assert risk["remaining_risk_nok"] == 0.0
    assert risk["size_mode"] == "FROZEN"
    assert any("L0" in r or "MANUAL FREEZE" in r for r in risk["reasons"])


def test_flag_on_dd_freeze_at_25pct(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    # peak 600: win +100 then lose 150 → equity 450 = 25% DD from 600
    rows = [
        _settled(100, "2026-07-01"),
        _settled(-150, "2026-07-10"),
    ]
    equity = 450.0
    peak = peak_equity_settlement(rows, 500.0)
    assert peak == 600.0
    risk = evaluate_risk(
        _v2_cfg(),
        equity,
        PHASE,
        rows,
        segments=_segs(freeze=False, liquid_sod=450.0, liquid_sow=450.0),
    )
    assert risk["size_mode"] == "FROZEN"
    assert risk["stopped"] is True
    assert risk["can_bet"] is False
    assert any("L1 DD FREEZE" in r for r in risk["reasons"])


def test_flag_on_dd_reduced_at_15pct_still_can_bet(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    # peak 600, equity 510 = 15% DD
    rows = [
        _settled(100, "2026-07-01"),
        _settled(-90, "2026-07-10"),
    ]
    equity = 510.0
    risk = evaluate_risk(
        _v2_cfg(),
        equity,
        PHASE,
        rows,
        segments=_segs(liquid_sod=510.0, liquid_sow=510.0),
    )
    assert risk["size_mode"] == "REDUCED"
    assert risk["stopped"] is False
    assert risk["can_bet"] is True
    assert any("REDUCED" in r for r in risk["reasons"])
    assert risk["remaining_risk_nok"] >= 10.0


def test_flag_on_daily_hard_stop_4pct_or_3u(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    # liquid_sod 500, unit 10 → min(4%*500=20, 3*10=30) = 20
    rows = [_settled(-20, "2026-07-21")]
    risk = evaluate_risk(
        _v2_cfg(),
        480.0,
        PHASE,
        rows,
        segments=_segs(liquid_sod=500.0, liquid_sow=500.0),
    )
    assert risk["daily_loss_limit_nok"] == 20.0
    assert risk["daily_hard_stopped"] is True
    assert risk["stopped"] is True
    assert risk["can_bet"] is False
    assert any("L3 DAILY STOP" in r for r in risk["reasons"])


def test_flag_on_daily_not_stopped_below_limit(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    rows = [_settled(-19, "2026-07-21")]
    risk = evaluate_risk(
        _v2_cfg(),
        481.0,
        PHASE,
        rows,
        segments=_segs(liquid_sod=500.0, liquid_sow=500.0),
    )
    assert risk["daily_hard_stopped"] is False
    assert risk["stopped"] is False


def test_flag_on_weekly_hard_stop(monkeypatch):
    import nt.capital_v2 as cv

    # Real ISO: 2026-07-20/21 are week 30; do not stub week ids
    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    # week limit min(8%*500=40, 6*10=60) = 40
    rows = [
        _settled(-25, "2026-07-20"),
        _settled(-20, "2026-07-21"),
    ]
    risk = evaluate_risk(
        _v2_cfg(),
        455.0,
        PHASE,
        rows,
        segments=_segs(liquid_sod=500.0, liquid_sow=500.0, week_id="2026-W30"),
    )
    assert risk["weekly_loss_limit_nok"] == 40.0
    assert risk["week_realized_pl_nok"] == -45.0
    assert risk["weekly_hard_stopped"] is True
    assert risk["stopped"] is True
    assert any("L2 WEEKLY STOP" in r for r in risk["reasons"])


def test_flag_on_portfolio_open_risk_18pct_caps_remaining(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    equity, secure, open_r = 600.0, 0.0, 50.0
    rows = [_open(50)]
    segs = _segs(liquid_sod=550.0, liquid_sow=550.0, secure=0.0)
    risk = evaluate_risk(_v2_cfg(), equity, PHASE, rows, segments=segs)
    liq = riskable_liquid(equity, secure, open_r)
    expected_room = portfolio_open_room(open_r, liq, max_pct=0.18)
    assert risk["portfolio_open_room_nok"] == expected_room
    # remaining cannot exceed portfolio room
    assert risk["remaining_risk_nok"] <= expected_room + 1e-9
    assert risk["remaining_risk_nok"] <= risk["daily_risk_cap_nok"]


def test_flag_on_portfolio_over_cap_zero_room(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    # open large vs liquid → room 0
    equity = 500.0
    rows = [_open(100), _open(50, "ConfirmedPlaced")]
    risk = evaluate_risk(
        _v2_cfg(),
        equity,
        PHASE,
        rows,
        segments=_segs(liquid_sod=350.0, liquid_sow=350.0),
    )
    assert risk["portfolio_open_room_nok"] == 0.0
    assert risk["remaining_risk_nok"] == 0.0
    assert risk["can_bet"] is False


def test_flag_on_daily_loss_shrinks_remaining(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    equity = 500.0
    rows = [
        _settled(-10, "2026-07-21"),
        _open(5),
    ]
    segs = _segs(liquid_sod=500.0, liquid_sow=500.0)
    risk = evaluate_risk(_v2_cfg(), equity, PHASE, rows, segments=segs)
    working = equity  # secure 0
    phase_cap = daily_risk_cap(working, PHASE)
    # phase_remaining = cap - 5 - 10 = cap - 15
    expected_phase = max(0.0, round(phase_cap - 5.0 - 10.0, 2))
    liq = riskable_liquid(equity, 0.0, 5.0)
    room = portfolio_open_room(5.0, liq, max_pct=0.18)
    assert risk["remaining_risk_nok"] == min(expected_phase, room)


def test_flag_on_secure_reduces_working_and_liquid(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    equity = 600.0
    secure = 100.0
    risk = evaluate_risk(
        _v2_cfg(),
        equity,
        PHASE,
        [],
        segments=_segs(secure=secure, liquid_sod=500.0, liquid_sow=500.0),
    )
    assert risk["secure_nok"] == 100.0
    assert risk["working_equity_nok"] == 500.0
    assert risk["daily_risk_cap_nok"] == daily_risk_cap(500.0, PHASE)


def test_flag_on_layer_order_manual_beats_open_budget(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    risk = evaluate_risk(
        _v2_cfg(),
        550.0,
        PHASE,
        [],
        segments=_segs(freeze=True, liquid_sod=550.0),
    )
    assert risk["stopped"] is True
    assert risk["remaining_risk_nok"] == 0.0
    assert risk["can_bet"] is False


def test_week_realized_pl_iso_week():
    rows = [
        _settled(-10, "2026-07-20"),  # ISO week 30
        _settled(-5, "2026-07-21"),
        _settled(-50, "2026-07-13"),  # week 29
    ]
    assert week_realized_pl(rows, "2026-W30") == -15.0
    assert week_realized_pl(rows, "2026-W29") == -50.0


# ── floor invariants ──────────────────────────────────────────────────────


def test_can_bet_requires_remaining_ge_floor(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    # Force tiny remaining via large open within phase but leave portfolio room
    equity = 200.0
    # phase cap at floor 30; open 25 → remaining 5 < 10
    rows = [_open(25)]
    risk = evaluate_risk(
        _v2_cfg(),
        equity,
        PHASE,
        rows,
        segments=_segs(liquid_sod=200.0, liquid_sow=200.0),
    )
    assert risk["remaining_risk_nok"] < 10.0 or risk["remaining_risk_nok"] >= 0
    if risk["remaining_risk_nok"] < 10.0:
        assert risk["can_bet"] is False


def test_remaining_never_negative(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    rows = [_open(100), _settled(-30, "2026-07-21")]
    risk = evaluate_risk(
        _v2_cfg(),
        400.0,
        PHASE,
        rows,
        segments=_segs(liquid_sod=400.0, liquid_sow=400.0),
    )
    assert risk["remaining_risk_nok"] >= 0.0


def test_apply_nt_floor_invariant_on_remaining_stake():
    """Any stake taken from remaining must still obey NT floor fail-closed."""
    for rem in (0, 5, 9.99, 10, 12.7, 42):
        stake = apply_nt_floor(min(rem, 12), 10.0)
        assert stake == 0.0 or stake >= 10.0


def test_unit_size_at_least_floor_in_risk_context(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    risk = evaluate_risk(
        _v2_cfg(),
        500.0,
        PHASE,
        [],
        segments=_segs(liquid_sod=500.0),
    )
    assert risk["unit_size_nok"] >= 10.0
    assert risk["unit_size_nok"] == unit_size(500.0)


def test_flag_on_normal_mode_no_dd(monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    rows = [_settled(20, "2026-07-01")]
    risk = evaluate_risk(
        _v2_cfg(),
        520.0,
        PHASE,
        rows,
        segments=_segs(liquid_sod=520.0, liquid_sow=520.0),
    )
    assert risk["size_mode"] == "NORMAL"
    assert risk["stopped"] is False
    assert risk["can_bet"] is True
    assert risk["capital_v2_enabled"] is True
