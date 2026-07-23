"""
PR-2: hybrid half-steps (1A+/1B+) + continuous unit / open-risk progress.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.phase import (
    continuous_open_risk_params,
    continuous_unit_size,
    evaluate_phase,
    hard_gate_fields,
    phase_continuous_cfg,
    progress_inside_phase,
    resolve_hard_phase_id,
)
from nt.risk import daily_risk_cap, evaluate_risk


def _minimal_rows() -> list[dict[str, str]]:
    """Empty ledger — peak = baseline, no demote/count noise."""
    return []


@pytest.fixture
def cfg_ladder(tmp_path: Path) -> dict:
    """Isolated ladder with half-steps + continuous (no live state side effects)."""
    state = tmp_path / "state"
    state.mkdir(parents=True, exist_ok=True)
    bets = tmp_path / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,"
        "payout_nok,research_grade,odds_band,sport,market_type,phase,notes,"
        "source,created_at,updated_at\n",
        encoding="utf-8",
    )
    return {
        "bankroll": {"baseline_nok": 500.0},
        "norsk_tipping": {"min_stake_nok": 10},
        "paths": {
            "state_dir": str(state),
            "bets": str(bets),
        },
        "phase_continuous": {"enabled": True, "scale_factor": 100.0},
        "phase_stability": {
            "min_rolling_settled": 25,
            "min_rolling_roi": 0.0,
            "demote_if_rolling_roi_below": -0.10,
            "demote_min_settled": 25,
            "demote_drawdown_pct_of_peak": 0.12,
        },
        "phase_health": {"enabled": False},
        "capital_v2": {"enabled": False},
        "risk": {
            "stop_day_loss_pct_of_equity": 0.08,
            "stop_day_loss_floor_nok": 40,
        },
        "phases": {
            "1A": {
                "label": "Protect",
                "enter_equity": 0,
                "enter_settled": 0,
                "stake_min": 10,
                "stake_max": 12,
                "max_bets_per_round": 5,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.08,
                "daily_risk_floor": 30,
                "daily_risk_ceil": 42,
                "next": "1A+",
            },
            "1A+": {
                "label": "Protect+",
                "enter_equity": 540,
                "enter_settled": 30,
                "stake_min": 12,
                "stake_max": 14,
                "max_bets_per_round": 5,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.085,
                "daily_risk_floor": 34,
                "daily_risk_ceil": 47,
                "hard_phase_id": "1A",
                "next": "1B",
            },
            "1B": {
                "label": "Stabilize",
                "enter_equity": 580,
                "enter_settled": 60,
                "stake_min": 12,
                "stake_max": 15,
                "max_bets_per_round": 4,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.09,
                "daily_risk_floor": 38,
                "daily_risk_ceil": 52,
                "next": "1B+",
            },
            "1B+": {
                "label": "Stabilize+",
                "enter_equity": 620,
                "enter_settled": 75,
                "stake_min": 13,
                "stake_max": 16,
                "max_bets_per_round": 4,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.095,
                "daily_risk_floor": 44,
                "daily_risk_ceil": 62,
                "hard_phase_id": "1B",
                "next": "2",
            },
            "2": {
                "label": "Build",
                "enter_equity": 750,
                "enter_settled": 90,
                "stake_min": 14,
                "stake_max": 18,
                "max_bets_per_round": 5,
                "max_doubles_per_round": 1,
                "daily_risk_pct": 0.10,
                "daily_risk_floor": 50,
                "daily_risk_ceil": 75,
                "next": "3",
            },
            "3": {
                "label": "Expand",
                "enter_equity": 1200,
                "enter_settled": 130,
                "stake_min": 16,
                "stake_max": 28,
                "max_bets_per_round": 6,
                "max_doubles_per_round": 2,
                "daily_risk_pct": 0.09,
                "daily_risk_floor": 70,
                "daily_risk_ceil": 140,
                "next": "4",
            },
            "4": {
                "label": "Mature",
                "enter_equity": 2500,
                "enter_settled": 180,
                "stake_min": 28,
                "stake_max": 45,
                "max_bets_per_round": 7,
                "max_doubles_per_round": 2,
                "daily_risk_pct": 0.07,
                "daily_risk_floor": 100,
                "daily_risk_ceil": 250,
                "next": "5",
            },
            "5": {
                "label": "Scale",
                "enter_equity": 5000,
                "enter_settled": 250,
                "stake_min": 45,
                "stake_max": 70,
                "max_bets_per_round": 8,
                "max_doubles_per_round": 3,
                "daily_risk_pct": 0.06,
                "daily_risk_floor": 120,
                "daily_risk_ceil": 400,
                "next": None,
            },
        },
    }


def test_live_config_phase_order_includes_half_steps():
    cfg = load_config()
    order = list(cfg["phases"].keys())
    assert "1A" in order and "1A+" in order and "1B" in order and "1B+" in order
    assert order.index("1A") < order.index("1A+") < order.index("1B") < order.index("1B+")
    assert order.index("1B+") < order.index("2")
    assert cfg["phases"]["1A"]["next"] == "1A+"
    assert cfg["phases"]["1A+"]["next"] == "1B"
    assert cfg["phases"]["1B"]["next"] == "1B+"
    assert cfg["phases"]["1B+"]["next"] == "2"
    assert cfg["phases"]["1A+"]["hard_phase_id"] == "1A"
    assert cfg["phases"]["1B+"]["hard_phase_id"] == "1B"
    pc = phase_continuous_cfg(cfg)
    assert pc["enabled"] is True
    assert pc["scale_factor"] == 100.0


def test_equity_540_selects_1a_plus(cfg_ladder):
    cfg = cfg_ladder
    rows = _minimal_rows()
    phase = evaluate_phase(cfg, equity=540.0, settled_count=0, rows=rows)
    assert phase["phase_id"] == "1A+"
    assert phase["equity_phase"] == "1A+"
    assert phase["label"] == "Protect+"
    assert phase["phase_hard_id"] == "1A"

    # Just below half-step stays 1A
    phase_lo = evaluate_phase(cfg, equity=539.0, settled_count=0, rows=rows)
    assert phase_lo["phase_id"] == "1A"


def test_progress_0_at_enter_near_1_at_next(cfg_ladder):
    cfg = cfg_ladder
    # 1A: enter 0 → next 540
    assert progress_inside_phase(cfg, "1A", 0.0) == 0.0
    assert abs(progress_inside_phase(cfg, "1A", 270.0) - 0.5) < 1e-9
    assert abs(progress_inside_phase(cfg, "1A", 540.0) - 1.0) < 1e-9

    # 1A+: enter 540 → next 580
    assert progress_inside_phase(cfg, "1A+", 540.0) == 0.0
    assert abs(progress_inside_phase(cfg, "1A+", 560.0) - 0.5) < 1e-9
    assert abs(progress_inside_phase(cfg, "1A+", 580.0) - 1.0) < 1e-9

    phase = evaluate_phase(cfg, equity=540.0, settled_count=0, rows=_minimal_rows())
    assert phase["progress_inside_phase"] == 0.0

    phase_mid = evaluate_phase(cfg, equity=560.0, settled_count=0, rows=_minimal_rows())
    assert phase_mid["phase_id"] == "1A+"
    assert abs(phase_mid["progress_inside_phase"] - 0.5) < 1e-6


def test_unit_increases_between_500_and_560(cfg_ladder):
    """
    Continuous unit rises with equity when the band has headroom.

    Formula: unit = floor(stake_min + (equity - enter) / scale_factor) clamped.
    scale_factor=100 → whole-krone step every 100 NOK of equity.
    """
    cfg = cfg_ladder
    rows = _minimal_rows()

    # Inside Phase 2: room above bridged stake_min 14 with scale 100
    u750 = continuous_unit_size(cfg, "2", 750.0)
    u850 = continuous_unit_size(cfg, "2", 850.0)
    assert u750 == 14.0  # bridged / carry floor from 1B+
    assert u850 == 15.0  # 14 + 100/100
    assert u850 > u750

    # Wide single band: 500 → 600 crosses a whole-krone step (560 still same floor)
    wide = {
        **cfg,
        "phases": {
            "1A": {
                "label": "Protect",
                "enter_equity": 0,
                "enter_settled": 0,
                "stake_min": 10,
                "stake_max": 20,
                "max_bets_per_round": 5,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.08,
                "daily_risk_floor": 30,
                "daily_risk_ceil": 42,
                "next": None,
            }
        },
    }
    u500 = continuous_unit_size(wide, "1A", 500.0)
    u560 = continuous_unit_size(wide, "1A", 560.0)
    u600 = continuous_unit_size(wide, "1A", 600.0)
    assert u500 == 15.0  # 10 + 500/100
    assert u560 == 15.0  # 10 + 5.6 → floor 15 (same whole krone)
    assert u600 == 16.0  # 10 + 6.0
    assert u600 > u500
    # Raw (pre-floor) still rises 500 → 560
    assert (10.0 + 560.0 / 100.0) > (10.0 + 500.0 / 100.0)

    # Half-step ladder: unit at 560 (1A+) >= unit at 500 (1A capped at 12)
    p500 = evaluate_phase(cfg, equity=500.0, settled_count=0, rows=rows)
    p560 = evaluate_phase(cfg, equity=560.0, settled_count=0, rows=rows)
    assert p500["phase_id"] == "1A"
    assert p560["phase_id"] == "1A+"
    assert p500["unit_size_nok"] == 12.0
    assert p560["unit_size_nok"] >= p500["unit_size_nok"]
    # Inside 1A before cap: 50 → 150 must rise
    assert continuous_unit_size(cfg, "1A", 150.0) > continuous_unit_size(cfg, "1A", 50.0)


def test_hard_gates_1a_plus_max_doubles_0(cfg_ladder):
    cfg = cfg_ladder
    rows = _minimal_rows()
    phase = evaluate_phase(cfg, equity=550.0, settled_count=0, rows=rows)
    assert phase["phase_id"] == "1A+"
    assert phase["phase_hard_id"] == "1A"
    assert phase["max_doubles_per_round"] == 0
    assert phase["max_bets_per_round"] == 5  # from hard 1A

    gates = hard_gate_fields(cfg, "1A+")
    assert gates["phase_hard_id"] == "1A"
    assert gates["max_doubles_per_round"] == 0

    phase_1b_plus = evaluate_phase(cfg, equity=630.0, settled_count=0, rows=rows)
    assert phase_1b_plus["phase_id"] == "1B+"
    assert phase_1b_plus["phase_hard_id"] == "1B"
    assert phase_1b_plus["max_doubles_per_round"] == 0  # still no doubles until 2

    phase_2 = evaluate_phase(cfg, equity=750.0, settled_count=0, rows=rows)
    assert phase_2["phase_id"] == "2"
    assert phase_2["phase_hard_id"] == "2"
    assert phase_2["max_doubles_per_round"] == 1


def test_demote_and_count_unlock_with_half_steps(cfg_ladder):
    cfg = cfg_ladder
    rows = _minimal_rows()
    order = list(cfg["phases"].keys())

    # Equity-only: 600 → 1B; count cannot skip more than +1 from equity phase
    p = evaluate_phase(cfg, equity=600.0, settled_count=200, rows=rows)
    eq_i = order.index(p["equity_phase"])
    chosen_i = order.index(p["phase_id"])
    assert chosen_i <= eq_i + 1
    assert p["equity_phase"] == "1B"

    # One-step advance cap vs previous stored phase
    p_cap = evaluate_phase(
        cfg,
        equity=1200.0,
        settled_count=200,
        rows=rows,
        current_phase="1A",
    )
    assert p_cap["phase_id"] == "1A+"  # only one step from 1A

    # Demote path: force deep-red rolling ROI with enough settled
    bad_rows = []
    for i in range(30):
        bad_rows.append(
            {
                "bet_id": f"b{i}",
                "date": "2026-07-01",
                "match": f"M{i}",
                "selection": "X",
                "decimal_odds": "1.90",
                "stake_nok": "10",
                "result": "Loss",
                "p_l_nok": "-10",
                "payout_nok": "0",
                "updated_at": "2026-07-20T12:00:00+00:00",
            }
        )
    # Equity 760 would be phase 2 by ladder; demote should drop one step → 1B+
    p_dem = evaluate_phase(cfg, equity=760.0, settled_count=30, rows=bad_rows)
    assert p_dem["phase_id"] == "1B+"
    assert any("demote" in r for r in p_dem["reasons"])


def test_open_risk_scales_with_progress(cfg_ladder):
    cfg = cfg_ladder
    # At enter of 1A: open params = 1A values
    p0 = continuous_open_risk_params(cfg, "1A", 0.0)
    assert p0["daily_risk_floor"] == 30.0
    assert p0["daily_risk_ceil"] == 42.0

    # Midway 1A → lerp toward 1A+
    p_mid = continuous_open_risk_params(cfg, "1A", 270.0)
    assert 30.0 < p_mid["daily_risk_floor"] < 34.0
    assert 42.0 < p_mid["daily_risk_ceil"] < 47.0

    # Near next enter: near 1A+ floors
    p_hi = continuous_open_risk_params(cfg, "1A", 540.0)
    assert abs(p_hi["daily_risk_floor"] - 34.0) < 0.01
    assert abs(p_hi["daily_risk_ceil"] - 47.0) < 0.01

    phase = evaluate_phase(cfg, equity=270.0, settled_count=0, rows=_minimal_rows())
    cap = daily_risk_cap(270.0, phase)
    assert phase["daily_risk_floor"] <= cap <= phase["daily_risk_ceil"]


def test_risk_emits_phase_hard_id_progress_unit(cfg_ladder):
    cfg = cfg_ladder
    rows = _minimal_rows()
    phase = evaluate_phase(cfg, equity=550.0, settled_count=0, rows=rows)
    risk = evaluate_risk(cfg, 550.0, phase, rows)
    assert risk["phase_id"] == "1A+"
    assert risk["phase_hard_id"] == "1A"
    assert risk.get("progress_inside_phase") is not None
    assert risk.get("unit_size_nok") is not None
    assert risk["unit_size_nok"] == phase["unit_size_nok"]
    assert risk.get("daily_risk_ceil") is not None


def test_resolve_hard_phase_id_aliases(cfg_ladder):
    cfg = cfg_ladder
    assert resolve_hard_phase_id(cfg, "1A+") == "1A"
    assert resolve_hard_phase_id(cfg, "1B+") == "1B"
    assert resolve_hard_phase_id(cfg, "1A") == "1A"
    assert resolve_hard_phase_id(cfg, "2") == "2"

    # inherits_hard_gates_from alias
    cfg2 = {
        **cfg,
        "phases": {**cfg["phases"], "1A+": {**cfg["phases"]["1A+"]}},
    }
    cfg2["phases"]["1A+"] = dict(cfg["phases"]["1A+"])
    cfg2["phases"]["1A+"]["inherits_hard_gates_from"] = "1A"
    del cfg2["phases"]["1A+"]["hard_phase_id"]
    assert resolve_hard_phase_id(cfg2, "1A+") == "1A"


def test_continuous_disabled_no_unit_override(cfg_ladder):
    cfg = {**cfg_ladder, "phase_continuous": {"enabled": False, "scale_factor": 100.0}}
    phase = evaluate_phase(cfg, equity=550.0, settled_count=0, rows=_minimal_rows())
    assert phase["phase_id"] == "1A+"
    assert phase.get("phase_continuous_enabled") is False
    assert "unit_size_nok" not in phase
    # Open risk stays at phase static (no lerp)
    assert phase["daily_risk_floor"] == 34.0
    assert phase["daily_risk_ceil"] == 47.0


def test_unit_non_decreasing_at_each_promotion_boundary(cfg_ladder):
    """
    R1/R2: unit at enter must be >= unit at enter − ε for every promotion.

    Covers half-steps and full phases (1B+→2, 2→3, 3→4, 4→5).
    """
    cfg = cfg_ladder
    rows = _minimal_rows()
    phases = cfg["phases"]
    order = list(phases.keys())
    eps = 0.01

    for i in range(1, len(order)):
        pid = order[i]
        enter = float(phases[pid].get("enter_equity") or 0.0)
        if enter <= 0:
            continue
        # Equity-only selection (settled=0) so phase_id tracks equity ladder
        pre = evaluate_phase(cfg, equity=enter - eps, settled_count=0, rows=rows)
        at = evaluate_phase(cfg, equity=enter, settled_count=0, rows=rows)
        assert pre["phase_id"] == order[i - 1], (
            f"pre-boundary at {enter - eps}: expected {order[i - 1]}, got {pre['phase_id']}"
        )
        assert at["phase_id"] == pid, (
            f"at boundary {enter}: expected {pid}, got {at['phase_id']}"
        )
        u_pre = float(pre["unit_size_nok"])
        u_at = float(at["unit_size_nok"])
        assert u_at >= u_pre, (
            f"unit drop at {order[i - 1]}→{pid} enter={enter}: "
            f"{u_pre} → {u_at}"
        )


def test_unit_non_decreasing_live_config_promotions():
    """Same boundary monotonicity on live config.yaml ladder."""
    cfg = load_config()
    assert phase_continuous_cfg(cfg).get("enabled")
    phases = cfg["phases"]
    order = list(phases.keys())
    eps = 0.01
    rows: list[dict[str, str]] = []

    # Isolated state so live phase.json sticky health does not interfere
    import tempfile
    from pathlib import Path as P

    with tempfile.TemporaryDirectory() as td:
        state = P(td) / "state"
        state.mkdir()
        cfg = {
            **cfg,
            "paths": {
                **(cfg.get("paths") or {}),
                "state_dir": str(state),
                "bets": str(P(td) / "bets.csv"),
            },
            "phase_health": {"enabled": False},
        }
        (P(td) / "bets.csv").write_text(
            "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,"
            "payout_nok,updated_at\n",
            encoding="utf-8",
        )
        for i in range(1, len(order)):
            pid = order[i]
            enter = float(phases[pid].get("enter_equity") or 0.0)
            if enter <= 0:
                continue
            pre = evaluate_phase(cfg, equity=enter - eps, settled_count=0, rows=rows)
            at = evaluate_phase(cfg, equity=enter, settled_count=0, rows=rows)
            assert pre["phase_id"] == order[i - 1]
            assert at["phase_id"] == pid
            assert float(at["unit_size_nok"]) >= float(pre["unit_size_nok"]), (
                f"live drop {order[i - 1]}→{pid} @ {enter}: "
                f"{pre['unit_size_nok']} → {at['unit_size_nok']}"
            )


def test_review_r1_measured_boundaries_no_drop(cfg_ladder):
    """Exact equities called out in PR-2 review R1 table."""
    cfg = cfg_ladder
    rows = _minimal_rows()
    cases = [
        (749.99, 750.0),
        (1199.99, 1200.0),
        (2499.99, 2500.0),
        (4999.99, 5000.0),
    ]
    for lo, hi in cases:
        p_lo = evaluate_phase(cfg, equity=lo, settled_count=0, rows=rows)
        p_hi = evaluate_phase(cfg, equity=hi, settled_count=0, rows=rows)
        assert p_hi["unit_size_nok"] >= p_lo["unit_size_nok"], (
            f"{lo}→{hi}: {p_lo['phase_id']}@{p_lo['unit_size_nok']} → "
            f"{p_hi['phase_id']}@{p_hi['unit_size_nok']}"
        )
