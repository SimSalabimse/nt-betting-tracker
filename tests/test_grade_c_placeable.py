"""
HV Research Regime v3 PR4 — Grade C placeable via full build_portfolio.

T10: Grade C + core reason + EV clear → place
T11: Grade C missing core reason → reject
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import grade_evidence, has_core_reason
from nt.portfolio import Candidate, build_portfolio


def _cfg() -> dict:
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
        "learning": {
            "enabled": False,
            "diversification": {
                "max_per_sport": 2,
                "max_per_market": 3,
                "max_per_band": 4,
                "max_per_match": 1,
                "prefer_explore_first": False,
                "explore_min_ev": 0.012,
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
        "capital_v2": {"enabled": False},
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


def _grade_c_pack(
    *,
    summary: str,
    p_model: float = 0.60,
    n_sources: int = 6,
    odds: float = 2.0,
) -> dict:
    """
    Pack that grades C: enough sources + p_model, but missing failure_modes.
    Core reason controlled via summary length.
    Dual-writes odds snapshot for PR3 fail-closed place path.
    """
    return {
        "p_model": p_model,
        "summary": summary,
        # intentionally omit failure_modes → grade C (not F when sources ≥ need)
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "expected full strength for unit test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": [
            {
                "url": f"https://example.com/{i}",
                "takeaway": "t",
                "kind": "injury" if i == 0 else "stats",
            }
            for i in range(n_sources)
        ],
        "odds_at_research": float(odds),
        "decimal_odds_ref": float(odds),
        "researched_at": "2026-07-20T12:00:00Z",
        "odds_snapshot_inferred": False,
    }


def test_t10_grade_c_with_core_reason_places_via_build_portfolio():
    """T10: Grade C + written core reason + EV clear → full build_portfolio place."""
    cfg = _cfg()
    odds = 2.0
    p_model = 0.60  # raw_ev = (0.57)*2 - 1 = 0.14 >> 2% floor
    summary = "Clear mid-band under with injury-driven script lean and multi-source support."
    pack = _grade_c_pack(summary=summary, p_model=p_model, odds=odds)
    grade, issues = grade_evidence(
        pack, cfg, odds, selection="Under 2.5", sport="football"
    )
    assert grade == "C", f"expected grade C, got {grade}: {issues}"
    assert has_core_reason(pack)

    c = Candidate(
        date="2026-07-22",
        match="Alpha FC vs Beta United",
        selection="Under 2.5",
        decimal_odds=odds,
        sport="football",
        market_type="Totals",
        p_model=p_model,
        evidence=pack,
    )
    picked, rejects = build_portfolio(
        cfg, [c], _phase(), _risk(80.0), historical_rows=[], learning={}
    )
    assert len(picked) == 1, f"expected place, got rejects={rejects}"
    assert picked[0].grade == "C"
    assert picked[0].stake_nok >= 10.0
    assert float(picked[0].ev) >= 0.02


def test_t11_grade_c_missing_core_reason_rejects():
    """T11: Grade C without clear core reason → reject (not place)."""
    cfg = _cfg()
    odds = 2.0
    p_model = 0.60
    pack = _grade_c_pack(summary="too short", p_model=p_model, odds=odds)
    grade, issues = grade_evidence(
        pack, cfg, odds, selection="Under 2.5", sport="football"
    )
    assert grade == "C", f"expected grade C, got {grade}: {issues}"
    assert not has_core_reason(pack)

    c = Candidate(
        date="2026-07-22",
        match="Gamma FC vs Delta United",
        selection="Under 2.5",
        decimal_odds=odds,
        sport="football",
        market_type="Totals",
        p_model=p_model,
        evidence=pack,
    )
    picked, rejects = build_portfolio(
        cfg, [c], _phase(), _risk(80.0), historical_rows=[], learning={}
    )
    assert picked == [], f"must not place without core reason: {picked}"
    assert any(
        "core reason" in str(r.get("reason", "")).lower() for r in rejects
    ), f"expected core-reason reject, got {rejects}"
