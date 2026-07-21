from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import load_bets
from nt.config import load_config
from nt.learning import (
    compute_learning,
    learning_adjustments,
    load_learning,
    run_learning,
)
from nt.portfolio import Candidate, build_portfolio
from nt.recommend import refresh_state


def test_compute_learning_has_sports():
    cfg = load_config()
    rows = load_bets(ROOT / "data/bets.csv")
    payload = compute_learning(rows, cfg)
    assert payload["enabled"] is True
    assert payload["summary"]["n_settled"] >= 1
    assert payload["sports"]
    # Multipliers stay clamped for any sport that has sample
    for sport, foot in (payload.get("sports") or {}).items():
        assert 0.5 <= float(foot.get("stake_mult") or 1.0) <= 1.5
        assert -0.10 <= float(foot.get("ev_boost") or 0.0) <= 0.10
    assert payload["lessons"] is not None


def test_run_learning_persists():
    cfg = load_config()
    payload = run_learning(cfg)
    loaded = load_learning(cfg)
    assert loaded.get("updated_at")
    assert loaded.get("sports")
    assert (ROOT / "data/state/learning.json").is_file()
    assert (ROOT / "data/state/edges_summary.md").is_file()
    assert payload["summary"]["n_settled"] == loaded["summary"]["n_settled"]


def test_learning_adjustments_apply():
    cfg = load_config()
    run_learning(cfg)
    learn = load_learning(cfg)
    adj = learning_adjustments(
        learn,
        sport="football",
        market="Match result",
        selection="Team to Win",
        band="1.8-2.2",
        enabled=True,
    )
    assert "stake_mult" in adj
    assert "ev_boost" in adj
    assert adj["stake_mult"] > 0


def test_portfolio_uses_learning_without_crash():
    cfg = load_config()
    bankroll, phase, risk = refresh_state(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    learn = load_learning(cfg)
    # Minimal candidate with p_model so it can score if risk allows
    c = Candidate(
        date="2026-07-14",
        match="Test FC vs Other FC",
        selection="Test FC to Win",
        decimal_odds=1.70,
        sport="football",
        market_type="HUB",
        p_model=0.70,
        evidence={
            "p_model": 0.70,
            "summary": "unit test",
            "failure_modes": "test",
            "sources": [{"url": f"https://example.com/{i}", "takeaway": "t"} for i in range(6)],
        },
    )
    picked, rejects = build_portfolio(cfg, [c], phase, risk, rows, learning=learn)
    # Either picked or rejected for risk/EV — must not throw
    assert isinstance(picked, list)
    assert isinstance(rejects, list)


def test_diversify_counts_open_pending_sport():
    """max_per_sport includes already-open Pending, not only this slip."""
    cfg = load_config()
    bankroll, phase, risk = refresh_state(cfg)
    # Force can_bet path with plenty of room
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 100.0
    risk["daily_risk_cap_nok"] = 100.0

    pending = [
        {
            "match": "A vs B",
            "selection": "A to Win",
            "sport": "football",
            "result": "Pending",
            "decimal_odds": "1.70",
            "odds_band": "1.5-1.8",
            "market_type": "HUB",
        },
        {
            "match": "C vs D",
            "selection": "C to Win",
            "sport": "football",
            "result": "Pending",
            "decimal_odds": "1.80",
            "odds_band": "1.8-2.2",
            "market_type": "HUB",
        },
    ]
    cand = Candidate(
        date="2026-07-15",
        match="E vs F",
        selection="E to Win",
        decimal_odds=1.75,
        sport="football",
        market_type="HUB",
        p_model=0.72,
        evidence={
            "p_model": 0.72,
            "summary": "unit test diversify",
            "failure_modes": "test",
            "sources": [{"url": f"https://example.com/{i}", "takeaway": "t"} for i in range(6)],
        },
    )
    picked, rejects = build_portfolio(cfg, [cand], phase, risk, pending, learning={})
    assert picked == []
    assert any("diversify" in str(r.get("reason", "")).lower() and "football" in str(r.get("reason", "")).lower() for r in rejects)


def _ev_cand(
    match: str,
    selection: str,
    odds: float,
    sport: str,
    p: float,
    market_type: str = "HUB",
) -> Candidate:
    return Candidate(
        date="2026-07-16",
        match=match,
        selection=selection,
        decimal_odds=odds,
        sport=sport,
        market_type=market_type,
        p_model=p,
        evidence={
            "p_model": p,
            "summary": "unit test pack with gates for portfolio fill",
            "failure_modes": "test",
            "context_risk": "low",
            "availability_status": "predicted",
            "availability_notes": "expected full strength for unit test",
            "script_lean": "competitive",
            "selection_vs_script": "agree",
            "base_rate_conflict": False,
            "sources": [
                {"url": f"https://example.com/{i}", "takeaway": "t", "kind": "stats"}
                for i in range(8)
            ],
        },
    )


def test_soft_football_fillup_takes_second_football_when_slots_remain():
    """
    max_football_per_round=1 is a soft preference only.

    If non-football cannot fill remaining seats, good football (e.g. Racing
    BTTS Nei) must still be selected up to max_per_sport — never leave empty
    seats just because one football bet was already taken.
    """
    cfg = load_config()
    _, phase, risk = refresh_state(cfg)
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 100.0
    risk["daily_risk_cap_nok"] = 100.0
    phase = dict(phase)
    phase["max_bets_per_round"] = 3
    phase["max_stake_nok"] = 25

    # Two *different* football matches (max_per_match=1 blocks dual markets on one fixture)
    cands = [
        _ev_cand(
            "Houston Rockets vs Brooklyn Nets",
            "Totalt 182.5 (inkludert overtid): Over 182.5",
            1.80,
            "nba",  # normalized to basketball on Recommendation
            0.64,
            "Totals",
        ),
        _ev_cand(
            "Racing Club Avellaneda vs Defensa y Justicia",
            "Racing Club Avellaneda to Win",
            1.92,
            "football",
            0.60,
            "HUB",
        ),
        _ev_cand(
            "Boca Juniors vs River Plate",
            "BTTS Nei",
            1.62,
            "football",
            0.70,
            "Begge lag scorer",
        ),
    ]
    picked, _rejects = build_portfolio(cfg, cands, phase, risk, [], learning={})
    sports = [p.sport for p in picked]
    sels = [p.selection for p in picked]
    assert len(picked) == 3, f"expected full slip, got {len(picked)}: {sels}"
    assert sports.count("football") == 2, f"soft fill should take 2 football: {sels}"
    assert sports.count("basketball") == 1, f"nba→basketball expected: {sports}"
    assert any("BTTS" in s for s in sels), f"BTTS Nei must fill seat: {sels}"


def test_soft_football_prefers_non_football_first_then_fills():
    """Non-football is preferred first; empty seats still take football."""
    cfg = load_config()
    _, phase, risk = refresh_state(cfg)
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 100.0
    risk["daily_risk_cap_nok"] = 100.0
    phase = dict(phase)
    phase["max_bets_per_round"] = 3
    phase["max_stake_nok"] = 25

    cands = [
        _ev_cand("Tennis A vs B", "Vinner: A", 1.75, "tennis", 0.65, "Vinner"),
        _ev_cand("F1 vs F2", "F1 to Win", 1.80, "football", 0.66, "HUB"),
        _ev_cand("F3 vs F4", "BTTS Nei", 1.70, "football", 0.68, "BTTS"),
        _ev_cand("F5 vs F6", "Under 2.5", 1.85, "football", 0.64, "Totals"),
    ]
    picked, _rejects = build_portfolio(cfg, cands, phase, risk, [], learning={})
    assert len(picked) == 3
    assert picked[0].sport == "tennis"
    assert sum(1 for p in picked if p.sport == "football") == 2
    # Soft max_football=1 would only allow 1 football; fill-up must allow 2
    # (hard ceiling remains max_per_sport, which is 2).
