from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.calibrate import analyze_calibration, record_from_settled_bet, rebuild_calibration
from nt.config import load_config
from nt.sim_football import (
    SimInputs,
    markets_from_matrix,
    p_model_for_selection,
    score_matrix,
    simulate_match,
)


def test_poisson_matrix_normalized():
    mat = score_matrix(1.5, 1.2, rho=-0.05, max_goals=8)
    total = sum(sum(row) for row in mat)
    assert abs(total - 1.0) < 1e-6
    m = markets_from_matrix(mat)
    assert abs(m["home_win"] + m["draw"] + m["away_win"] - 1.0) < 1e-5
    assert abs(m["over_2.5"] + m["under_2.5"] - 1.0) < 1e-5
    assert abs(m["btts_yes"] + m["btts_no"] - 1.0) < 1e-5


def test_higher_lambda_raises_over25():
    low = simulate_match(SimInputs(lambda_home=0.8, lambda_away=0.7, match="A vs B", home="A", away="B"))
    high = simulate_match(SimInputs(lambda_home=2.2, lambda_away=1.8, match="A vs B", home="A", away="B"))
    assert high.markets["over_2.5"] > low.markets["over_2.5"]
    assert high.markets["btts_yes"] > low.markets["btts_yes"]


def test_xg_path_and_selection_map():
    cfg = load_config()
    r = simulate_match(
        SimInputs(
            match="Home FC vs Away United",
            home="Home FC",
            away="Away United",
            home_xg_for=1.8,
            home_xg_against=1.0,
            away_xg_for=1.1,
            away_xg_against=1.3,
            source_quality="high",
        ),
        cfg,
    )
    assert r.lambda_home > 0 and r.lambda_away > 0
    p = p_model_for_selection(r, "BTTS Ja")
    assert p is not None and 0.1 < p < 0.95
    p2 = p_model_for_selection(r, "Totalt antall mål - Over/Under 2.5: Under 2.5")
    assert p2 is not None
    assert abs(p2 - r.markets["under_2.5"]) < 1e-6


def test_missing_inputs_raise():
    try:
        simulate_match(SimInputs(match="X vs Y"))
        assert False, "should raise"
    except ValueError as e:
        assert "lambda" in str(e).lower() or "missing" in str(e).lower()


def test_calibration_record_and_metrics():
    bet = {
        "bet_id": "abc123",
        "date": "2026-07-15",
        "match": "A vs B",
        "selection": "BTTS Ja",
        "decimal_odds": "1.85",
        "odds_band": "1.8-2.2",
        "result": "Win",
        "p_l_nok": "8.5",
        "sport": "football",
        "phase": "1A",
        "research_grade": "B",
        "notes": "",
    }
    dec = {"p_model": 0.58, "ev": 0.05}
    rec = record_from_settled_bet(bet, dec)
    assert rec is not None
    assert rec["y"] == 1.0
    assert rec["p_model"] == 0.58

    rows = [
        rec,
        {
            **rec,
            "bet_id": "x2",
            "y": 0.0,
            "result": "Loss",
            "p_model": 0.58,
            "brier": (0.58 - 0) ** 2,
            "log_loss": 0.1,
        },
    ]
    report = analyze_calibration(rows)
    assert report["n"] == 2
    assert report["brier"] is not None
    assert "reliability_bins" in report


def test_rebuild_calibration_smoke():
    cfg = load_config()
    # write=False path via analyze only if file missing — rebuild write true is ok (state only)
    report = rebuild_calibration(cfg, write=True)
    assert "n_written" in report
    assert report.get("path")
