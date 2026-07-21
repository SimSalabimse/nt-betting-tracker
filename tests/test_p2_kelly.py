"""P2 fractional Kelly gates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.kelly import fractional_kelly_stake, full_kelly_fraction


def test_full_kelly_positive_edge():
    f = full_kelly_fraction(0.55, 2.0)
    assert f > 0
    assert f < 1


def test_kelly_blocked_below_liquid():
    stake, notes = fractional_kelly_stake(
        p_model=0.60,
        odds=2.0,
        liquid=800.0,
        active_unit=10.0,
        min_stake=10.0,
        remaining_room=100.0,
        kelly_cfg={"enabled": True, "enabled_above_liquid": 1500, "fraction_cap": 0.3},
        brier=0.20,
        cal_n=50,
    )
    assert stake is None
    assert any("liquid" in n for n in notes)


def test_kelly_blocked_bad_brier():
    stake, notes = fractional_kelly_stake(
        p_model=0.60,
        odds=2.0,
        liquid=2000.0,
        active_unit=10.0,
        min_stake=10.0,
        remaining_room=100.0,
        kelly_cfg={
            "enabled": True,
            "enabled_above_liquid": 1500,
            "fraction_cap": 0.3,
            "max_brier": 0.28,
            "min_calibration_n": 30,
        },
        brier=0.35,
        cal_n=50,
    )
    assert stake is None
    assert any("brier" in n for n in notes)


def test_kelly_applies_above_unit():
    stake, notes = fractional_kelly_stake(
        p_model=0.58,
        odds=2.10,
        liquid=5000.0,
        active_unit=10.0,
        min_stake=10.0,
        remaining_room=200.0,
        kelly_cfg={
            "enabled": True,
            "enabled_above_liquid": 1500,
            "fraction_cap": 0.30,
            "max_units": 1.5,
            "max_brier": 0.28,
            "min_calibration_n": 30,
            "brier_soft_scale": False,
        },
        brier=0.20,
        cal_n=50,
    )
    assert stake is not None
    assert stake >= 10
    assert stake <= 15  # max 1.5 units
    assert any("kelly_applied" in n or "kelly_stake" in n for n in notes)


def test_kelly_thin_cal_skip():
    stake, notes = fractional_kelly_stake(
        p_model=0.60,
        odds=2.0,
        liquid=5000.0,
        active_unit=10.0,
        min_stake=10.0,
        remaining_room=100.0,
        kelly_cfg={"enabled": True, "enabled_above_liquid": 1500, "min_calibration_n": 30},
        brier=None,
        cal_n=5,
    )
    assert stake is None
    assert any("thin_cal" in n for n in notes)
