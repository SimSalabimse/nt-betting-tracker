from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
    assert b["post_archive_bets"] == 146
    assert b["total_bets"] == 193
    assert abs(b["realized_pl_nok"] - 47.57) < 0.02
    assert abs(b["equity_nok"] - 547.57) < 0.02


def test_phase_is_1b_not_4_at_current_equity():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    phase = evaluate_phase(cfg, b["equity_nok"], b["settled_count"], rows)
    assert phase["phase_id"] == "1B"
    assert phase["equity_phase"] == "1A"
    assert phase["count_phase"] == "4"


def test_daily_cap_in_1b_band():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    phase = evaluate_phase(cfg, b["equity_nok"], b["settled_count"], rows)
    cap = daily_risk_cap(b["equity_nok"], phase)
    assert 55 <= cap <= 80
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
        "p_model": 0.42,
        "summary": "longshot with data",
        "failure_modes": "variance",
        "sources": sources,
    }
    # p*odds - 1 with haircut: (0.42-0.05)*2.8 - 1 = 0.036 — may need higher p
    ev["p_model"] = 0.48  # (0.43)*2.8 - 1 = 0.204
    c = Candidate(
        date="2026-07-12",
        match="Longshot Cup",
        selection="Underdog ML",
        decimal_odds=2.80,
        p_model=0.48,
        evidence=ev,
    )
    grade, issues = grade_evidence(ev, cfg, 2.80)
    assert grade == "A", issues
    picked, rejects = build_portfolio(cfg, [c], phase, risk, [])
    assert len(picked) == 1, rejects
    assert picked[0].high_odds is True


def test_high_odds_rejected_without_grade_a():
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
    risk = {"can_bet": True, "remaining_risk_nok": 80.0, "reasons": []}
    c = Candidate(
        date="2026-07-12",
        match="Longshot Cup",
        selection="Underdog ML",
        decimal_odds=2.80,
        p_model=0.50,
        evidence=None,
    )
    picked, rejects = build_portfolio(cfg, [c], phase, risk, [])
    assert picked == []
    assert any("grade A" in str(r).lower() or "no p_model" in str(r).lower() or "grade" in str(r).lower() for r in rejects)


def test_pl_math():
    assert pl_from_payout(10, 0) == -10
    assert pl_from_payout(10, 10) == 0
    assert pl_from_payout(10, 25) == 15
    assert pl_from_outcome(10, 2.5, "win") == 15
    assert pl_from_outcome(10, 2.5, "loss") == -10


def test_validate_ledger():
    rows = load_bets(ROOT / "data/bets.csv")
    assert validate_bets(rows) == []


def test_odds_band():
    assert odds_band(1.4) == "<1.5"
    assert odds_band(2.6) == "2.5-3.0"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("all passed")
