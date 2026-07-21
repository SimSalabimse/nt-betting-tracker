from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import load_bets, odds_band, validate_bets
from nt.bankroll import compute_bankroll
from nt.config import load_config
from nt.evidence import ev_after_haircut, grade_evidence
from nt.phase import evaluate_phase
from nt.pl import pl_from_outcome, pl_from_payout
from nt.portfolio import Candidate, build_portfolio
from nt.risk import daily_risk_cap, evaluate_risk


def test_equity_includes_archive_and_live():
    cfg = load_config()
    b = compute_bankroll(cfg)
    assert b["era_archive_bets"] == 47
    assert b["post_archive_bets"] >= 146
    assert b["total_bets"] == b["era_archive_bets"] + b["post_archive_bets"]
    assert b["settled_count"] >= 193
    # Equity = baseline + realized; must be consistent
    assert abs(b["equity_nok"] - (b["baseline_nok"] + b["realized_pl_nok"])) < 0.02
    assert b["equity_nok"] >= 500.0


def test_phase_safe_hybrid_not_max_from_count_alone():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    phase = evaluate_phase(cfg, b["equity_nok"], b["settled_count"], rows)
    # Equity ladder primary; count may unlock at most +1 phase if stable
    order = list(cfg["phases"].keys())
    eq_i = order.index(phase["equity_phase"])
    chosen_i = order.index(phase["phase_id"])
    assert chosen_i <= eq_i + 1
    assert phase["phase_id"] != "4" or b["equity_nok"] >= 2500
    # Near ~580–750 band: equity phase should be 1A or 1B (not mature)
    if b["equity_nok"] < 750:
        assert phase["equity_phase"] in ("1A", "1B")
        assert phase["phase_id"] in ("1A", "1B", "2")


def test_daily_cap_matches_phase_clamp():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    phase = evaluate_phase(cfg, b["equity_nok"], b["settled_count"], rows)
    cap = daily_risk_cap(b["equity_nok"], phase)
    floor = float(phase["daily_risk_floor"])
    ceil = float(phase["daily_risk_ceil"])
    assert floor <= cap <= ceil
    risk = evaluate_risk(cfg, b["equity_nok"], phase, rows)
    assert risk["daily_risk_cap_nok"] == cap


def test_high_odds_allowed_with_grade_a():
    cfg = load_config()
    phase = {
        "phase_id": "1B",
        "stake_min": 12,
        "stake_max": 20,
        "max_bets_per_round": 5,
        "max_doubles_per_round": 1,
        "daily_risk_pct": 0.12,
        "daily_risk_floor": 55,
        "daily_risk_ceil": 80,
    }
    risk = {
        "can_bet": True,
        "remaining_risk_nok": 80.0,
        "reasons": [],
    }
    sources = [{"url": f"https://example.com/{i}", "takeaway": "ok"} for i in range(12)]
    ev = {
        "p_model": 0.48,
        "summary": "longshot with data",
        "failure_modes": "variance",
        "sources": sources,
    }
    c = Candidate(
        date="2026-07-12",
        match="Longshot Cup",
        selection="Underdog ML",
        decimal_odds=2.80,
        sport="football",
        p_model=0.48,
        evidence=ev,
    )
    picked, rejects = build_portfolio(cfg, [c], phase, risk, [])
    # May pick or reject on EV; must not hard-ban high odds solely for odds>2.5
    reasons = " ".join(str(r) for r in rejects)
    assert "banned" not in reasons.lower()


def test_pl_math():
    assert pl_from_outcome(10, 2.0, "win") == 10.0
    assert pl_from_outcome(10, 2.0, "loss") == -10.0
    assert pl_from_payout(10, 0) == -10.0
    assert pl_from_payout(10, 19) == 9.0


def test_odds_band():
    assert odds_band(1.4) == "<1.5"
    assert odds_band(1.9) == "1.8-2.2"
    assert odds_band(3.1) == ">=3.0"


def test_validate_current_ledger():
    rows = load_bets(ROOT / "data/bets.csv")
    assert validate_bets(rows) == []
