"""
HV Research Regime v3 PR4 — explore boost hygiene.

T8: explore_virgin_stack false → at most one virgin boost (≤0.022+ε)
T9: raw_ev −0.10 → portfolio zeros explore boost → no place (audit fields)
T9b: boundary raw_ev just below −0.015 + band prior — gate is load-bearing
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import ev_after_haircut
from nt.learning import diversification_limits, learning_adjustments
from nt.portfolio import Candidate, build_portfolio


def _learn_cfg(**div_extra) -> dict:
    return {
        "enabled": True,
        "diversification": {
            "explore_min_n": 0,
            "explore_max_n": 14,
            "explore_ev_boost": 0.018,
            "explore_virgin_ev_boost": 0.022,
            "explore_virgin_stack": False,
            "explore_boost_min_raw_ev": -0.015,
            "explore_stake_floor": 0.92,
            "explore_min_roi": -0.15,
            "explore_min_ev": 0.012,
            "prefer_explore_first": False,
            "max_per_sport": 2,
            "max_per_market": 3,
            "max_per_band": 4,
            "max_per_match": 1,
            **div_extra,
        },
    }


def _portfolio_cfg() -> dict:
    return {
        "norsk_tipping": {"min_stake_nok": 10},
        "selection": {
            "probability_haircut": 0.03,
            "standard_min_ev": 0.02,
            "strong_min_ev": 0.015,
            "absolute_min_ev": 0.01,
            "strong_min_sources": 8,
            "grade_c_placeable": True,
            "grade_c_require_core_reason": True,
            "grade_c_min_sources": 4,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.05,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {"min_sample": 15, "bad_roi_below": -0.10, "extra_ev_required": 0.05},
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
            "grade_a_require_uncertainty": True,
        },
        "learning": _learn_cfg(),
        "risk": {"loss_streak_grade_a_only": 99},
        "capital_v2": {"enabled": False},
        "phases": {
            "1A": {
                "stake_min": 10,
                "stake_max": 12,
                "max_bets_per_round": 5,
            }
        },
        "recommend": {"max_run_stake_pct_of_equity": 0.20},
    }


def _phase():
    return {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 4,
        "max_doubles_per_round": 0,
    }


def _risk(remaining: float = 80.0):
    return {
        "can_bet": True,
        "remaining_risk_nok": remaining,
        "reasons": [],
    }


def _virgin_learning() -> dict:
    """Empty sports/markets → both groups are virgin (n=0)."""
    return {"enabled": True, "sports": {}, "markets": {}, "bands": {}}


def test_t8_virgin_stack_false_boost_at_most_one():
    """T8: explore_virgin_stack false → boost ≤ virgin_boost + ε (no sport+market stack)."""
    learn = _virgin_learning()
    cfg = _learn_cfg(explore_virgin_stack=False)
    adj = learning_adjustments(
        learn,
        sport="darts",
        market="Totals",
        selection="Over 5.5",
        band="1.8-2.2",
        enabled=True,
        learn_cfg=cfg,
    )
    virgin = float(cfg["diversification"]["explore_virgin_ev_boost"])
    assert adj["explored"] is True
    assert float(adj["ev_boost"]) <= virgin + 1e-9
    assert float(adj["ev_boost"]) == virgin
    # Prefer market virgin when both are empty
    notes = " ".join(adj.get("notes") or [])
    assert "explore virgin market:" in notes
    assert "explore virgin sport:" not in notes

    # Stack on: legacy double virgin still possible
    cfg_stack = _learn_cfg(explore_virgin_stack=True)
    adj_stack = learning_adjustments(
        learn,
        sport="darts",
        market="Totals",
        selection="Over 5.5",
        band="1.8-2.2",
        enabled=True,
        learn_cfg=cfg_stack,
    )
    assert float(adj_stack["ev_boost"]) == 2 * virgin

    # diversification_limits exposes SSOT keys
    lim = diversification_limits({"learning": cfg})
    assert lim["explore_virgin_stack"] is False
    assert float(lim["explore_boost_min_raw_ev"]) == -0.015


def test_t9_raw_ev_deep_negative_zeros_boost_no_place():
    """T9: raw_ev ≈ −0.10 with explore path → boost blocked → reject, no place."""
    # p_adj = p - 0.03; EV = p_adj * odds - 1 = -0.10
    # → p_adj * odds = 0.90 → with odds=2.0 → p_adj=0.45 → p_model=0.48
    odds = 2.0
    p_model = 0.48
    haircut = 0.03
    raw = ev_after_haircut(p_model, odds, haircut)
    assert abs(raw - (-0.10)) < 1e-9
    assert raw < -0.015  # below explore_boost_min_raw_ev

    cfg = _portfolio_cfg()
    sources = [
        {"url": f"https://example.com/{i}", "takeaway": "stats ok", "kind": "stats"}
        for i in range(8)
    ]
    evidence = {
        "p_model": p_model,
        "summary": "Honest thin-sport total research with transparent failure modes listed.",
        "failure_modes": "small sample; line noise",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "expected full strength for unit test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
    }
    c = Candidate(
        date="2026-07-22",
        match="Darts Ace vs Blade",
        selection="Over 5.5",
        decimal_odds=odds,
        sport="darts",
        market_type="Totals",
        p_model=p_model,
        evidence=evidence,
    )
    learn = _virgin_learning()
    # Confirm learning would have applied a virgin boost without the gate
    adj = learning_adjustments(
        learn,
        sport="darts",
        market="Totals",
        selection="Over 5.5",
        band="1.8-2.2",
        enabled=True,
        learn_cfg=cfg["learning"],
    )
    assert adj["explored"] is True
    assert float(adj["ev_boost"]) > 0

    picked, rejects = build_portfolio(
        cfg, [c], _phase(), _risk(80.0), historical_rows=[], learning=learn
    )
    assert picked == [], f"deep-negative raw_ev must not place: {picked}"
    assert rejects, "expected EV reject"
    r0 = rejects[0]
    assert float(r0.get("raw_ev")) < -0.015
    # Learning boost zeroed by portfolio gate
    assert float(r0.get("learning_ev_boost") or 0.0) == 0.0
    assert r0.get("boost_applied") is False
    assert r0.get("boost_blocked_reason") == "raw_ev_below_explore_boost_min"
    assert "EV" in str(r0.get("reason", ""))


def test_t9b_boundary_raw_ev_gate_is_load_bearing():
    """
    T9b (M1): raw_ev just below explore_boost_min_raw_ev with production-like
    band prior — without the gate, virgin boost + prior would clear explore
    min_ev; with the gate, boost is zeroed and build_portfolio rejects.
    """
    odds = 2.0  # band 1.8-2.2
    haircut = 0.03
    floor = -0.015
    band_prior = 0.015  # production-like selection.band_prior_boost["1.8-2.2"]
    # raw_ev = (p - haircut)*odds - 1 ≈ -0.016 (strictly < floor)
    p_model = 0.522
    raw = ev_after_haircut(p_model, odds, haircut)
    assert raw < floor
    assert abs(raw - (-0.016)) < 1e-9

    cfg = _portfolio_cfg()
    cfg["selection"]["band_prior_boost"] = {"1.8-2.2": band_prior}
    # Keep explore bar explicit so counterfactual is stable
    cfg["learning"]["diversification"]["explore_min_ev"] = 0.012

    sources = [
        {"url": f"https://example.com/{i}", "takeaway": "stats ok", "kind": "stats"}
        for i in range(8)
    ]
    evidence = {
        "p_model": p_model,
        "summary": "Boundary virgin-sport total: near-miss raw EV with honest sources.",
        "failure_modes": "model noise; thin sample",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "expected full strength for unit test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
    }
    c = Candidate(
        date="2026-07-22",
        match="Boundary Darts vs Control",
        selection="Over 5.5",
        decimal_odds=odds,
        sport="darts",
        market_type="Totals",
        p_model=p_model,
        evidence=evidence,
    )
    learn = _virgin_learning()
    adj = learning_adjustments(
        learn,
        sport="darts",
        market="Totals",
        selection="Over 5.5",
        band="1.8-2.2",
        enabled=True,
        learn_cfg=cfg["learning"],
    )
    assert adj["explored"] is True
    boost = float(adj["ev_boost"] or 0.0)
    assert boost > 0.0
    explore_min = float(cfg["learning"]["diversification"]["explore_min_ev"])

    # Counterfactual: if boost were applied, EV would clear explore min_ev
    counterfactual_ev = float(raw) + band_prior + boost
    assert counterfactual_ev + 1e-12 >= explore_min, (
        f"fixture not load-bearing: with boost EV={counterfactual_ev:.4f} "
        f"< explore_min={explore_min}"
    )
    # Gated path: zero boost → EV fails
    gated_ev = float(raw) + band_prior + 0.0
    assert gated_ev + 1e-12 < explore_min

    picked, rejects = build_portfolio(
        cfg, [c], _phase(), _risk(80.0), historical_rows=[], learning=learn
    )
    assert picked == [], (
        f"gate must block place when raw_ev < floor; got picks={picked} "
        f"(counterfactual EV would have been {counterfactual_ev:.4f})"
    )
    assert rejects
    r0 = rejects[0]
    assert float(r0.get("raw_ev")) < floor
    assert float(r0.get("learning_ev_boost") or 0.0) == 0.0
    assert r0.get("boost_applied") is False
    assert r0.get("boost_blocked_reason") == "raw_ev_below_explore_boost_min"
    assert "EV" in str(r0.get("reason", ""))
