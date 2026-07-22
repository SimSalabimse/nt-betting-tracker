"""
Phase 2.1 foundation — pure unit tests.

Covers: unit ladder, NT 10 NOK floor, REDUCED half-unit, peak/DD
(settlement-day), secure transfer + ref reset to working equity,
portfolio open-risk 18%, capital_segments I/O, freeze helpers.

No live risk/sizing wiring — capital_v2.enabled stays false.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_segments import (
    ensure_segments_file,
    is_frozen,
    load_segments,
    save_segments,
    segments_path,
    set_freeze,
)
from nt.capital_v2 import (
    RULE_BUNDLE_VERSION,
    apply_nt_floor,
    capital_v2_cfg,
    compute_secure_transfer,
    drawdown_from_peak,
    empty_segments,
    is_hard_loss_stopped,
    loss_limit_nok,
    oslo_iso_week_id,
    peak_equity_settlement,
    portfolio_open_risk_cap,
    portfolio_open_room,
    reduced_unit,
    riskable_equity,
    riskable_liquid,
    size_mode_from_dd,
    unit_size,
    whole_krone,
)
from nt.defaults import capital_v2_defaults


# ── config defaults ───────────────────────────────────────────────────────


def test_capital_v2_cfg_disabled_by_default():
    v2 = capital_v2_cfg({})
    assert v2["enabled"] is False
    assert v2["rule_bundle_version"] == RULE_BUNDLE_VERSION
    assert v2["min_stake_nok"] == 10.0
    assert v2["portfolio_open_risk"]["max_pct_of_riskable_liquid"] == 0.18
    assert v2["kelly"]["fraction_cap"] == 0.30
    assert v2["drawdown"]["reduce_at"] == 0.15
    assert v2["drawdown"]["freeze_at"] == 0.25


def test_capital_v2_defaults_reexport_matches_cfg():
    cfg = {"capital_v2": {"enabled": False, "min_stake_nok": 10}}
    assert capital_v2_defaults(cfg)["enabled"] is False
    assert capital_v2_defaults(cfg)["min_stake_nok"] == 10.0


def test_capital_v2_cfg_merges_nested_and_respects_nt_floor_override():
    cfg = {
        "norsk_tipping": {"min_stake_nok": 12},
        "capital_v2": {
            "portfolio_open_risk": {"max_pct_of_riskable_liquid": 0.20},
            "kelly": {"fraction_cap": 0.25},
        },
    }
    v2 = capital_v2_cfg(cfg)
    assert v2["min_stake_nok"] == 12.0
    assert v2["portfolio_open_risk"]["max_pct_of_riskable_liquid"] == 0.20
    # nested merge keeps defaults for other keys
    assert v2["portfolio_open_risk"].get("max_pct_of_riskable_liquid") == 0.20
    assert v2["kelly"]["enabled_above_liquid"] == 1500.0
    assert v2["kelly"]["fraction_cap"] == 0.25


# ── NT floor / whole krone ────────────────────────────────────────────────


def test_whole_krone_floors_positive():
    assert whole_krone(10.9) == 10.0
    assert whole_krone(10.0) == 10.0
    assert whole_krone(0) == 0.0
    assert whole_krone(-5) == 0.0


def test_apply_nt_floor_fail_closed():
    assert apply_nt_floor(0, 10) == 0.0
    assert apply_nt_floor(5, 10) == 0.0  # illegal partial → 0
    assert apply_nt_floor(9.99, 10) == 0.0
    assert apply_nt_floor(10, 10) == 10.0
    assert apply_nt_floor(15.7, 10) == 15.0  # whole krone
    assert apply_nt_floor(10.1, 10) == 10.0


def test_never_recommend_stake_below_floor():
    """Invariant: apply_nt_floor never returns value in (0, min_stake)."""
    for stake in (0.1, 1, 5, 9, 9.99, 10, 10.5, 20, 100.9):
        out = apply_nt_floor(stake, 10.0)
        assert out == 0.0 or out >= 10.0
        assert out == int(out) or out == 0.0


# ── Unit ladder ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "liquid,expected",
    [
        (0, 12.0),  # High-Volume v2 base unit
        (500, 12.0),
        (1499.99, 12.0),
        (1500, 15.0),
        (2499.99, 15.0),
        (2500, 20.0),
        (10000, 20.0),
    ],
)
def test_unit_size_ladder(liquid, expected):
    assert unit_size(liquid) == expected


def test_unit_size_always_at_least_floor():
    v2 = capital_v2_cfg({"capital_v2": {"min_stake_nok": 10}})
    assert unit_size(100, v2) >= 10.0
    # custom ladder still respects floor
    v2b = capital_v2_cfg(
        {
            "capital_v2": {
                "min_stake_nok": 10,
                "unit_ladder": [{"max_liquid_exclusive": None, "unit": 5.0}],
            }
        }
    )
    assert unit_size(1000, v2b) == 10.0


# ── REDUCED half-unit ─────────────────────────────────────────────────────


def test_reduced_unit_exactly_half_when_legal():
    assert reduced_unit(20.0, 10.0) == 10.0
    assert reduced_unit(30.0, 10.0) == 15.0


def test_reduced_unit_steps_down_when_half_below_floor():
    # unit 15 → half 7 < 10 → next lower ladder step 12 (High-Volume v2)
    assert reduced_unit(15.0, 10.0) == 12.0


def test_reduced_unit_at_floor_stays_at_floor():
    # unit 10 → half 5 illegal → no lower step → floor (never below 10)
    assert reduced_unit(10.0, 10.0) == 10.0


def test_reduced_unit_never_below_floor():
    for u in (10, 15, 20, 25, 40):
        r = reduced_unit(float(u), 10.0)
        assert r >= 10.0


# ── Size mode from DD ─────────────────────────────────────────────────────


def test_size_mode_from_dd_thresholds():
    assert size_mode_from_dd(0.0) == "NORMAL"
    assert size_mode_from_dd(0.149) == "NORMAL"
    assert size_mode_from_dd(0.15) == "REDUCED"
    assert size_mode_from_dd(0.20) == "REDUCED"
    assert size_mode_from_dd(0.25) == "FROZEN"
    assert size_mode_from_dd(0.50) == "FROZEN"


def test_size_mode_manual_freeze_overrides():
    assert size_mode_from_dd(0.0, freeze_active=True) == "FROZEN"
    assert size_mode_from_dd(0.10, freeze_active=True) == "FROZEN"


# ── Peak equity & drawdown (settlement-day) ───────────────────────────────


def _row(
    *,
    result: str,
    pl: str,
    match_date: str,
    updated_at: str,
) -> dict[str, str]:
    return {
        "date": match_date,
        "updated_at": updated_at,
        "result": result,
        "p_l_nok": pl,
        "stake_nok": "10",
    }


def test_peak_equity_empty_is_baseline():
    assert peak_equity_settlement([], 500.0) == 500.0


def test_peak_equity_ignores_pending_and_abandoned():
    rows = [
        _row(result="Pending", pl="", match_date="2026-07-01", updated_at="2026-07-01T12:00:00Z"),
        _row(result="Abandoned", pl="0", match_date="2026-07-01", updated_at="2026-07-01T13:00:00Z"),
        _row(result="ConfirmedPlaced", pl="", match_date="2026-07-01", updated_at="2026-07-01T14:00:00Z"),
    ]
    assert peak_equity_settlement(rows, 500.0) == 500.0


def test_peak_equity_settlement_day_not_match_date():
    """
    Match on 2026-07-19, settled Oslo morning 2026-07-20 (UTC evening 19th).
    Peak must follow settlement path, not match date.
    """
    rows = [
        # Win +20 settled 2026-07-20 Oslo (2026-07-19T22:30Z = 00:30 CEST 20th)
        _row(
            result="Win",
            pl="20",
            match_date="2026-07-19",
            updated_at="2026-07-19T22:30:00Z",
        ),
        # Loss -10 settled later same Oslo day
        _row(
            result="Loss",
            pl="-10",
            match_date="2026-07-19",
            updated_at="2026-07-20T10:00:00Z",
        ),
    ]
    # path: 500 → 520 → 510; peak = 520
    assert peak_equity_settlement(rows, 500.0) == 520.0


def test_peak_equity_tracks_running_high():
    rows = [
        _row(result="Win", pl="50", match_date="2026-07-01", updated_at="2026-07-01T12:00:00Z"),
        _row(result="Loss", pl="-30", match_date="2026-07-02", updated_at="2026-07-02T12:00:00Z"),
        _row(result="Win", pl="10", match_date="2026-07-03", updated_at="2026-07-03T12:00:00Z"),
    ]
    # 500 → 550 → 520 → 530; peak 550
    assert peak_equity_settlement(rows, 500.0) == 550.0


def test_peak_equity_includes_refunded():
    rows = [
        _row(result="Refunded", pl="0", match_date="2026-07-01", updated_at="2026-07-01T12:00:00Z"),
        _row(result="Win", pl="15", match_date="2026-07-02", updated_at="2026-07-02T12:00:00Z"),
    ]
    assert peak_equity_settlement(rows, 500.0) == 515.0


def test_drawdown_from_peak():
    assert drawdown_from_peak(500, 500) == 0.0
    assert abs(drawdown_from_peak(425, 500) - 0.15) < 1e-9
    assert abs(drawdown_from_peak(375, 500) - 0.25) < 1e-9
    assert drawdown_from_peak(600, 500) == 0.0  # equity above peak → 0
    assert drawdown_from_peak(100, 0) == 0.0
    assert drawdown_from_peak(0, 500) == 1.0


def test_size_mode_at_15_and_25_pct_dd():
    peak = 600.0
    # 15% DD → equity 510
    eq_reduce = peak * (1 - 0.15)
    assert size_mode_from_dd(drawdown_from_peak(eq_reduce, peak)) == "REDUCED"
    # 25% DD → equity 450
    eq_freeze = peak * (1 - 0.25)
    assert size_mode_from_dd(drawdown_from_peak(eq_freeze, peak)) == "FROZEN"


# ── Riskable liquid & portfolio open risk ─────────────────────────────────


def test_riskable_equity_and_liquid():
    assert riskable_equity(600, 50) == 550.0
    assert riskable_equity(600, 700) == 0.0  # floor at 0
    assert riskable_liquid(600, 50, 100) == 450.0
    assert riskable_liquid(600, 0, 700) == 0.0


def test_portfolio_open_risk_cap_18_pct():
    # L = 500 free liquid → cap = 90
    assert portfolio_open_risk_cap(500.0, max_pct=0.18) == 90.0
    assert portfolio_open_risk_cap(0.0) == 0.0


def test_portfolio_open_room():
    # L=500, open=30 → cap=90 → room=60
    assert portfolio_open_room(30.0, 500.0, max_pct=0.18) == 60.0
    # over cap → room 0
    assert portfolio_open_room(100.0, 500.0, max_pct=0.18) == 0.0
    # open zero → full cap
    assert portfolio_open_room(0.0, 514.0, max_pct=0.18) == round(514.0 * 0.18, 2)


def test_portfolio_open_risk_uses_riskable_liquid_base():
    """18% of (equity − secure − open), not of full equity."""
    equity, secure, open_r = 600.0, 40.0, 36.0
    liq = riskable_liquid(equity, secure, open_r)  # 524
    cap = portfolio_open_risk_cap(liq)
    assert cap == round(524.0 * 0.18, 2)
    room = portfolio_open_room(open_r, liq)
    assert room == max(0.0, round(cap - open_r, 2))


# ── Loss limit helpers (pure stubs for 2.2) ───────────────────────────────


def test_loss_limit_min_of_pct_and_units():
    # liquid 500, unit 10: 4% = 20, 3u = 30 → min 20
    assert loss_limit_nok(500, 10, pct=0.04, units=3) == 20.0
    # liquid 1000, unit 10: 4% = 40, 3u = 30 → min 30
    assert loss_limit_nok(1000, 10, pct=0.04, units=3) == 30.0
    # weekly: 8% of 500 = 40, 6u = 60 → 40
    assert loss_limit_nok(500, 10, pct=0.08, units=6) == 40.0


def test_is_hard_loss_stopped():
    assert is_hard_loss_stopped(-20, 20) is True
    assert is_hard_loss_stopped(-20.01, 20) is True
    assert is_hard_loss_stopped(-19.99, 20) is False
    assert is_hard_loss_stopped(5, 20) is False
    assert is_hard_loss_stopped(-10, 0) is False


# ── Secure bucket transfer ────────────────────────────────────────────────


def test_secure_transfer_below_trigger_noop():
    # ref 500, trigger 650; equity 600 → no transfer
    r = compute_secure_transfer(
        ledger_equity=600,
        secure_nok=0,
        ref_hwm=500,
        trigger_multiple=1.30,
        transfer_fraction=0.40,
    )
    assert r.triggered is False
    assert r.transferred == 0.0
    assert r.secure_after == 0.0
    assert r.ref_hwm_after == 500.0
    assert r.working_equity_after == 600.0


def test_secure_transfer_40pct_and_reset_ref_to_working_equity():
    """
    Binding clarification:
    - transfer 40% of profit above ref
    - reset ref HWM to new working equity (ledger − secure after transfer)
    - secure permanently removed from riskable
    - min working buffer max(55% equity, 8×unit) respected
    """
    # ref 500, trigger 650; equity 700 → profit_above 200 → raw 80
    # min working = max(0.55*700=385, 8*10=80) = 385 → max xfer = 700-385=315 → 80 OK
    r = compute_secure_transfer(
        ledger_equity=700,
        secure_nok=0,
        ref_hwm=500,
        trigger_multiple=1.30,
        transfer_fraction=0.40,
        unit_size_nok=10.0,
    )
    assert r.triggered is True
    assert r.transferred == 80.0  # whole_krone(0.4 * 200)
    assert r.secure_after == 80.0
    assert r.working_equity_after == 620.0  # 700 - 80
    assert r.ref_hwm_after == 620.0  # reset to working equity, not ledger equity
    assert r.working_equity_after + 1e-9 >= 0.55 * 700


def test_secure_transfer_stacks_with_existing_secure():
    r = compute_secure_transfer(
        ledger_equity=800,
        secure_nok=50,
        ref_hwm=500,
        trigger_multiple=1.30,
        transfer_fraction=0.40,
        unit_size_nok=10.0,
    )
    # profit_above = 300 → raw 120; min work max(440, 80)=440; max xfer=800-50-440=310
    assert r.triggered is True
    assert r.transferred == 120.0
    assert r.secure_after == 170.0
    assert r.working_equity_after == 630.0
    assert r.ref_hwm_after == 630.0


def test_secure_transfer_respects_min_working_buffer():
    """Working after transfer must be ≥ max(55% equity, 8×unit)."""
    # Large raw transfer would drain working — buffer caps it
    r = compute_secure_transfer(
        ledger_equity=1000,
        secure_nok=0,
        ref_hwm=100,  # far below so trigger fires hard
        trigger_multiple=1.30,
        transfer_fraction=0.40,
        unit_size_nok=10.0,
    )
    # raw = 0.4*(1000-100)=360; min work = max(550, 80)=550; max xfer=450
    assert r.triggered is True
    assert r.transferred == 360.0  # 360 < 450, buffer not binding
    assert r.working_equity_after >= 550.0 - 1e-9

    r2 = compute_secure_transfer(
        ledger_equity=1000,
        secure_nok=0,
        ref_hwm=100,
        trigger_multiple=1.30,
        transfer_fraction=0.90,  # aggressive
        unit_size_nok=10.0,
    )
    # raw = 0.9*900=810; max by buffer = 1000-550=450
    assert r2.triggered is True
    assert r2.transferred == 450.0
    assert r2.transfer_capped_by_buffer is True
    assert r2.working_equity_after >= 550.0 - 1e-9
    assert r2.secure_after <= 1000.0


def test_secure_transfer_exactly_at_trigger():
    # equity == ref * 1.30 → triggers
    r = compute_secure_transfer(
        ledger_equity=650,
        secure_nok=0,
        ref_hwm=500,
        trigger_multiple=1.30,
        transfer_fraction=0.40,
    )
    assert r.triggered is True
    assert r.transferred == whole_krone(0.40 * 150)  # 60
    assert r.working_equity_after == 650 - r.transferred
    assert r.ref_hwm_after == r.working_equity_after


def test_secure_reduces_riskable_liquid():
    equity, secure, open_r = 700.0, 80.0, 20.0
    assert riskable_liquid(equity, secure, open_r) == 600.0
    # without secure would be 680
    assert riskable_liquid(equity, 0, open_r) == 680.0


# ── ISO week / Oslo ───────────────────────────────────────────────────────


def test_oslo_iso_week_id():
    # 2026-07-21 is Tuesday of ISO week 30
    assert oslo_iso_week_id("2026-07-21") == "2026-W30"
    # ISO week boundary: 2026-12-28 is week 53 of 2026
    assert oslo_iso_week_id("2026-12-28").startswith("2026-W")
    # Monday 2026-01-05 is week 2
    assert oslo_iso_week_id("2026-01-05") == "2026-W02"


# ── empty_segments structure ──────────────────────────────────────────────


def test_empty_segments_schema():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    assert segs["schema_version"] == 1
    assert segs["rule_bundle_version"] == RULE_BUNDLE_VERSION
    assert segs["secure_nok"] == 0.0
    assert segs["secure_transfers"] == []
    assert segs["unit_hwm_reset_equity_nok"] == 500.0
    assert segs["freeze"]["active"] is False
    assert segs["freeze"]["unfreeze_requires"] == "manual"
    assert segs["day_snapshot"]["oslo_date"] == "2026-07-21"
    assert segs["week_snapshot"]["week_id"] == "2026-W30"
    assert "realized_pl_nok" in segs["day_snapshot"]
    assert "realized_pl_nok" in segs["week_snapshot"]


# ── capital_segments I/O ──────────────────────────────────────────────────


def _tmp_cfg(tmp_path: Path) -> dict:
    state = tmp_path / "state"
    state.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {
            "state_dir": str(state),
            "capital_segments": str(state / "capital_segments.json"),
        },
        "bankroll": {"baseline_nok": 500.0},
    }


def test_load_segments_missing_returns_empty(tmp_path: Path):
    cfg = _tmp_cfg(tmp_path)
    segs = load_segments(cfg)
    assert segs["secure_nok"] == 0.0
    assert segs["unit_hwm_reset_equity_nok"] == 500.0
    assert not segments_path(cfg).is_file()


def test_save_and_load_segments_roundtrip(tmp_path: Path):
    cfg = _tmp_cfg(tmp_path)
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["secure_nok"] = 80.0
    segs["unit_hwm_reset_equity_nok"] = 620.0
    path = save_segments(cfg, segs)
    assert path.is_file()
    loaded = load_segments(cfg)
    assert loaded["secure_nok"] == 80.0
    assert loaded["unit_hwm_reset_equity_nok"] == 620.0
    assert loaded["rule_bundle_version"] == RULE_BUNDLE_VERSION
    assert "updated_at" in loaded


def test_ensure_segments_file_creates_once(tmp_path: Path):
    cfg = _tmp_cfg(tmp_path)
    a = ensure_segments_file(cfg, baseline_nok=500.0)
    b = ensure_segments_file(cfg, baseline_nok=500.0)
    assert segments_path(cfg).is_file()
    assert a["schema_version"] == b["schema_version"] == 1


def test_load_segments_corrupt_json_fail_closed(tmp_path: Path):
    cfg = _tmp_cfg(tmp_path)
    p = segments_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not-json", encoding="utf-8")
    segs = load_segments(cfg, baseline_nok=500.0)
    assert segs["secure_nok"] == 0.0
    assert segs["freeze"]["active"] is False


def test_set_freeze_and_is_frozen(tmp_path: Path):
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    assert is_frozen(segs) is False
    frozen = set_freeze(segs, active=True, reason="dd_25pct")
    assert is_frozen(frozen) is True
    assert frozen["freeze"]["reason"] == "dd_25pct"
    assert frozen["freeze"]["activated_at"] is not None
    assert frozen["freeze"]["unfreeze_requires"] == "manual"
    # original not mutated
    assert is_frozen(segs) is False
    unfrozen = set_freeze(frozen, active=False)
    assert is_frozen(unfrozen) is False
    assert unfrozen["freeze"]["reason"] is None
    assert unfrozen["freeze"]["activated_at"] is None


def test_load_fills_missing_keys(tmp_path: Path):
    cfg = _tmp_cfg(tmp_path)
    p = segments_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"secure_nok": 12.5}), encoding="utf-8")
    segs = load_segments(cfg, baseline_nok=500.0)
    assert segs["secure_nok"] == 12.5
    assert "freeze" in segs
    assert "day_snapshot" in segs
    assert "week_snapshot" in segs


# ── integration-ish pure chain (no live risk) ─────────────────────────────


def test_dd_reduced_then_stake_floor_chain():
    """
    Simulated path: peak 600, equity 510 (15% DD) → REDUCED half unit.
    Liquid 510 → unit 12 → reduced 10 (floor). Floor handling remains fail-closed.
    """
    peak = 600.0
    equity = 510.0
    dd = drawdown_from_peak(equity, peak)
    mode = size_mode_from_dd(dd)
    assert mode == "REDUCED"
    u = unit_size(equity)
    assert u == 12.0
    stake_unit = reduced_unit(u, 10.0)
    # half of 12 = 6 < floor → step to 10
    assert stake_unit == 10.0
    assert apply_nt_floor(stake_unit, 10.0) == 10.0
    assert apply_nt_floor(5.0, 10.0) == 0.0


def test_open_risk_layer_before_sizing_numbers():
    """Portfolio open room is independent pure input for later L4-ish stack."""
    equity, secure, open_r = 550.0, 0.0, 40.0
    liq = riskable_liquid(equity, secure, open_r)
    room = portfolio_open_room(open_r, liq, max_pct=0.18)
    # cannot size a stake larger than room without violating 18% rule
    assert room == max(0.0, round(0.18 * liq - open_r, 2))
    assert apply_nt_floor(room, 10.0) == 0.0 or apply_nt_floor(room, 10.0) >= 10.0
