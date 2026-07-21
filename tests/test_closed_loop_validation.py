"""Closed-loop + size_mode floor validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.closed_loop_validation import (
    replay_closed_loop,
    validate_size_mode_floor_invariant,
)
from nt.bets_io import load_bets
from nt.config import load_config, path_from_config
from nt.bankroll import compute_bankroll


def test_live_size_mode_floor_never_looser_than_capital():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(path_from_config(cfg, "bets"))
    inv = validate_size_mode_floor_invariant(
        cfg,
        equity=float(b["equity_nok"]),
        settled_count=int(b["settled_count"]),
        rows=rows,
    )
    assert inv["ok"] is True
    # Severity: effective >= capital
    order = {"NORMAL": 0, "REDUCED": 1, "FROZEN": 2}
    assert order.get(inv["size_mode"], 0) >= order.get(inv["size_mode_capital"], 0)


def test_replay_closed_loop_runs():
    cfg = load_config()
    report = replay_closed_loop(cfg, n=60)
    assert report["n_replayed"] >= 1
    assert report["n_replayed"] <= 60
    assert "process_error_class_losses" in report
    assert report["size_mode_invariant"]["ok"] is True
    assert report["pass"] is True


def test_synthetic_pe_gate_followon(tmp_path: Path):
    """Two losses: first PE, second same sport should count under gate."""
    from nt.bets_io import utc_now

    state = tmp_path / "state"
    state.mkdir()
    bets = tmp_path / "bets.csv"
    # settlement order by updated_at
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,notes,source,created_at,updated_at\n"
        "a,2026-07-01,M1,S,1.9,10,Loss,-10,0,B,1.8-2.2,tennis,,,feel:process_error,rec,2026-07-01T10:00:00Z,2026-07-01T12:00:00Z\n"
        "b,2026-07-02,M2,S,1.9,10,Loss,-10,0,B,1.8-2.2,tennis,,,,"
        "rec,2026-07-02T10:00:00Z,2026-07-02T12:00:00Z\n"
        "c,2026-07-03,M3,S,1.9,10,Win,9,19,B,1.8-2.2,football,,,,"
        "rec,2026-07-03T10:00:00Z,2026-07-03T12:00:00Z\n",
        encoding="utf-8",
    )
    rev = state / "settlement_reviews.jsonl"
    rev.write_text(
        json.dumps(
            {
                "bet_id": "a",
                "ts": "2026-07-01T12:00:00Z",
                "variance_class": "process_error",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "settlement_reviews_jsonl": str(rev),
        },
        "bankroll": {"baseline_nok": 500},
        "norsk_tipping": {"min_stake_nok": 10},
        "capital_v2": {"enabled": True},
        "phases": {
            "1A": {
                "label": "Protect",
                "enter_equity": 0,
                "enter_settled": 0,
                "stake_min": 10,
                "stake_max": 12,
                "max_bets_per_round": 4,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.08,
                "daily_risk_floor": 30,
                "daily_risk_ceil": 42,
                "next": "1B",
            }
        },
        "phase_stability": {
            "min_rolling_settled": 25,
            "min_rolling_roi": 0.0,
            "demote_if_rolling_roi_below": -0.10,
            "demote_min_settled": 25,
            "demote_drawdown_pct_of_peak": 0.12,
        },
        "phase_health": {"enabled": True},
        "risk": {},
        "learning": {"enabled": False},
    }
    report = replay_closed_loop(cfg, n=10)
    assert report["process_error_class_losses"] >= 1
    assert report["subsequent_tickets_under_temp_gate"] >= 1
