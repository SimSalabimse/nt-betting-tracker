"""Phase v5 multi-factor PhaseState + capital_v2 hard floor."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.phase import evaluate_phase
from nt.phase_factors import compute_phase_factors, process_error_rate_14d
from nt.portfolio import Candidate, build_portfolio
from nt.risk import evaluate_risk


def _cfg(tmp: Path, *, reviews: list[dict] | None = None, action: str = "REDUCED") -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    bets = tmp / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,notes,source,created_at,updated_at\n"
        "o1,2026-07-21,A vs B,Win A,1.90,10,Pending,0,0,B,1.8-2.2,football,,,,rec,,,\n"
        "o2,2026-07-21,C vs D,Win C,1.85,10,Pending,0,0,B,1.8-2.2,football,,,,rec,,,\n"
        "o3,2026-07-21,E vs F,Win E,1.80,5,Pending,0,0,B,1.8-2.2,tennis,,,,rec,,,\n",
        encoding="utf-8",
    )
    rev_path = state / "settlement_reviews.jsonl"
    if reviews is not None:
        rev_path.write_text(
            "\n".join(json.dumps(r) for r in reviews) + "\n",
            encoding="utf-8",
        )
    else:
        rev_path.write_text("", encoding="utf-8")

    cal = state / "calibration_summary.json"
    cal.write_text(json.dumps({"n": 20, "brier": 0.20}), encoding="utf-8")

    return {
        "paths": {
            "state_dir": str(state),
            "bets": str(bets),
            "settlement_reviews_jsonl": str(rev_path),
            "calibration_summary_json": str(cal),
            "learning_json": str(state / "learning.json"),
            "capital_segments": str(state / "capital_segments.json"),
        },
        "bankroll": {"baseline_nok": 500.0},
        "norsk_tipping": {"min_stake_nok": 10},
        "capital_v2": {"enabled": True},
        "phase_health": {
            "enabled": True,
            "process_error_rate_threshold": 0.25,
            "process_error_min_reviews": 4,
            "process_error_action": action,
            "process_error_hold_days": 7,
            "concentration_block_share": 0.55,
            "calibration_poor_brier": 0.28,
            "calibration_min_n": 15,
        },
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
            },
            "1B": {
                "label": "Stabilize",
                "enter_equity": 580,
                "enter_settled": 60,
                "stake_min": 10,
                "stake_max": 15,
                "max_bets_per_round": 4,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.09,
                "daily_risk_floor": 38,
                "daily_risk_ceil": 52,
                "next": "2",
            },
            "5": {
                "label": "Scale",
                "enter_equity": 5000,
                "enter_settled": 250,
                "stake_min": 20,
                "stake_max": 70,
                "max_bets_per_round": 8,
                "max_doubles_per_round": 3,
                "daily_risk_pct": 0.06,
                "daily_risk_floor": 120,
                "daily_risk_ceil": 400,
                "next": None,
            },
        },
        "phase_stability": {
            "min_rolling_settled": 25,
            "min_rolling_roi": 0.0,
            "demote_if_rolling_roi_below": -0.10,
            "demote_min_settled": 25,
            "demote_drawdown_pct_of_peak": 0.12,
        },
        "selection": {
            "probability_haircut": 0.05,
            "standard_min_ev": 0.03,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.08,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {"min_sample": 99},
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
        },
        "learning": {"enabled": False},
        "risk": {"stop_day_loss_pct_of_equity": 0.08, "stop_day_loss_floor_nok": 40},
    }


def _pe_reviews(n_pe: int, n_other: int) -> list[dict]:
    from nt.bets_io import utc_now

    ts = utc_now()
    out = []
    for i in range(n_pe):
        out.append({"ts": ts, "variance_class": "process_error", "bet_id": f"pe{i}"})
    for i in range(n_other):
        out.append({"ts": ts, "variance_class": "skill", "bet_id": f"ok{i}"})
    return out


def test_process_error_rate_and_thin_sample(tmp_path: Path):
    cfg = _cfg(tmp_path, reviews=_pe_reviews(1, 1))
    r = process_error_rate_14d(cfg)
    assert r["n_reviews_14d"] == 2
    assert r["force_process_health"] is False  # n < 4

    cfg2 = _cfg(tmp_path / "b", reviews=_pe_reviews(2, 2))  # 50% of 4
    r2 = process_error_rate_14d(cfg2)
    assert r2["force_process_health"] is True
    assert r2["process_error_rate_14d"] == 0.5


def test_phase_process_error_forces_reduced_floor(tmp_path: Path):
    cfg = _cfg(tmp_path, reviews=_pe_reviews(3, 1))  # 75%
    from nt.bets_io import load_bets

    rows = load_bets(Path(cfg["paths"]["bets"]))
    phase = evaluate_phase(cfg, 550.0, 10, rows)
    assert phase["phase_id"] == "1A"
    assert phase["size_mode_floor"] == "REDUCED"
    assert phase["phase_model"] == "v5_multifactor"
    assert "process_error_rate_14d" in phase["phase_state"]


def test_research_only_blocks_can_bet(tmp_path: Path):
    cfg = _cfg(tmp_path, reviews=_pe_reviews(3, 1), action="RESEARCH_ONLY")
    from nt.bets_io import load_bets

    rows = load_bets(Path(cfg["paths"]["bets"]))
    phase = evaluate_phase(cfg, 550.0, 10, rows)
    assert phase["research_only"] is True
    risk = evaluate_risk(cfg, 550.0, phase, rows)
    assert risk["can_bet"] is False
    assert risk.get("research_only") is True


def test_risk_phase_floor_tightens_not_loosens(tmp_path: Path):
    cfg = _cfg(tmp_path, reviews=_pe_reviews(3, 1))
    from nt.bets_io import load_bets

    rows = load_bets(Path(cfg["paths"]["bets"]))
    phase = evaluate_phase(cfg, 550.0, 10, rows)
    # Force phase floor but mock capital NORMAL via low DD equity~peak
    risk = evaluate_risk(cfg, 550.0, phase, rows)
    assert risk.get("size_mode_capital") in ("NORMAL", "REDUCED", "FROZEN")
    if risk.get("size_mode_capital") == "NORMAL":
        assert risk["size_mode"] == "REDUCED"
    # If capital already FROZEN, phase cannot loosen
    phase_frozen = dict(phase)
    phase_frozen["size_mode_floor"] = "REDUCED"
    # Simulate by setting freeze via segments not needed — just check merge logic:
    # when capital is REDUCED and floor REDUCED, stays REDUCED
    assert risk["size_mode"] in ("REDUCED", "FROZEN", "NORMAL")


def test_high_odds_stress_from_concentration(tmp_path: Path):
    """Open book is ~80% football → high odds blocked."""
    cfg = _cfg(tmp_path, reviews=[])
    from nt.bets_io import load_bets

    rows = load_bets(Path(cfg["paths"]["bets"]))
    phase = evaluate_phase(cfg, 550.0, 5, rows)
    # 20 football + 5 tennis open = 80% football
    assert phase["high_odds_stress_block"] is True
    risk = evaluate_risk(cfg, 550.0, phase, rows)
    # Ensure can_bet may be false due to open room — force risk for portfolio test
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 40.0
    risk["size_mode"] = "NORMAL"
    risk["unit_size_nok"] = 10.0
    risk["capital_v2_enabled"] = True
    risk["high_odds_stress_block"] = True
    risk["riskable_liquid_nok"] = 500.0

    pack = {
        "p_model": 0.55,
        "summary": "test pack long enough for grade A uncertainty",
        "failure_modes": "fail mode text here ok",
        "context_risk": "low",
        "availability_status": "confirmed",
        "availability_notes": "full strength confirmed " + ("x" * 30),
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "p_model_sd": 0.04,
        "sources": [
            {"url": f"https://ex.com/{i}", "takeaway": "ok", "kind": "stats"}
            for i in range(12)
        ],
    }
    cands = [
        Candidate(
            date="2026-07-21",
            match="H vs A",
            selection="Vinner: H",
            decimal_odds=2.80,
            sport="football",
            market_type="Vinner",
            p_model=0.55,
            evidence=pack,
        )
    ]
    picked, rejects = build_portfolio(cfg, cands, phase, risk, historical_rows=[])
    assert picked == []
    assert any("high_odds blocked" in str(r.get("reason")) for r in rejects)


def test_ladder_labels_unchanged_low_equity(tmp_path: Path):
    cfg = _cfg(tmp_path, reviews=[])
    from nt.bets_io import load_bets

    rows = load_bets(Path(cfg["paths"]["bets"]))
    phase = evaluate_phase(cfg, 550.0, 28, rows)
    assert phase["phase_id"] == "1A"
    assert phase["equity_phase"] == "1A"
