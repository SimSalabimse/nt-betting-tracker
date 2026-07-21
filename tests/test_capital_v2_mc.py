"""Phase 2.5 — capital_v2 Monte-Carlo harness tests (determinism + zero violations)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_mc import determinism_check, run_core_suite, run_scenario, simulate_path
from nt.capital_v2 import capital_v2_cfg
from nt.config import load_config


def test_live_config_capital_v2_enabled():
    """Production policy: capital_v2 is on; MC still must not violate floor."""
    assert capital_v2_cfg(load_config()).get("enabled") is True


def test_determinism():
    assert determinism_check(42) is True
    assert determinism_check(999) is True


def test_single_path_no_stake_below_floor():
    m = simulate_path(seed=7, start_equity=550, n_days=40, bets_per_day=3)
    assert m.n_violations == 0
    assert m.n_bets >= 0


def test_losing_streak_triggers_stops():
    m = simulate_path(
        seed=1,
        start_equity=550,
        n_days=20,
        bets_per_day=4,
        force_lose_days=15,
    )
    assert m.n_daily_stops > 0 or m.n_weekly_stops > 0 or m.n_bets == 0
    assert m.n_violations == 0


def test_drawdown_freeze_path():
    m = simulate_path(
        seed=2,
        start_equity=500,
        n_days=40,
        bets_per_day=5,
        force_win_days=8,
        force_lose_after_day=8,
    )
    # Should hit reduced and often frozen
    assert m.max_dd_frac >= 0.15 - 1e-9 or m.days_frozen > 0 or m.days_reduced > 0
    assert m.n_violations == 0


def test_small_bankroll_floor_heavy():
    m = simulate_path(seed=3, start_equity=180, n_days=50, bets_per_day=2)
    assert m.n_violations == 0
    if m.n_bets > 0:
        assert m.n_stakes_at_floor / m.n_bets >= 0.5


def test_secure_triggers_on_win_streak():
    m = simulate_path(
        seed=4,
        start_equity=500,
        baseline=500,
        n_days=30,
        bets_per_day=4,
        force_win_days=25,
    )
    assert m.n_secure_transfers >= 1
    assert m.final_secure > 0
    assert m.n_violations == 0


def test_mini_suite_zero_violations():
    suite = run_core_suite(seed=42, n_paths=30)
    assert suite["total_violations_all_scenarios"] == 0
    assert suite["all_clear"] is True
    assert "mixed_realistic" in suite["scenarios"]
