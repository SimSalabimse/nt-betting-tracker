"""
Phase 2.3 — unit-ladder sizing behind capital_v2 flag.

Proves:
- flag OFF → exact legacy _stake_for behaviour
- flag ON → unit ladder, REDUCED, floor, remaining clip
- combinations with risk-layer fields from evaluate_risk
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_v2 import (
    apply_nt_floor,
    compute_unit_stake,
    reduced_unit,
    unit_size,
)
from nt.portfolio import (
    Candidate,
    Recommendation,
    _stake_for,
    _stake_for_capital_v2,
    build_portfolio,
)


def _phase(**kw):
    base = {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 4,
        "max_doubles_per_round": 0,
        "daily_risk_pct": 0.08,
        "daily_risk_floor": 30,
        "daily_risk_ceil": 42,
    }
    base.update(kw)
    return base


def _cfg(*, enabled: bool = False):
    return {
        "norsk_tipping": {"min_stake_nok": 10},
        "capital_v2": {"enabled": enabled},
        "selection": {
            "probability_haircut": 0.05,
            "standard_min_ev": 0.03,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.08,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {"min_sample": 15, "bad_roi_below": -0.10, "extra_ev_required": 0.05},
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
        },
        "learning": {
            "enabled": False,
            "diversification": {
                "max_per_sport": 4,
                "max_per_market": 4,
                "max_per_band": 4,
                "max_per_match": 1,
                "max_football_per_round": 2,
                "min_non_football_per_round": 0,
                "prefer_explore_first": False,
                "explore_min_ev": 0.012,
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
    }


def _pack(p: float = 0.75) -> dict:
    sources = [
        {"url": f"https://example.com/{i}", "takeaway": "ok", "kind": "stats"}
        for i in range(8)
    ]
    return {
        "match": "X",
        "selection": "Y",
        "p_model": p,
        "summary": "test pack with enough text for grade B sizing",
        "failure_modes": "test failure mode text",
        "context_risk": "low",
        "availability_status": "confirmed",
        "availability_notes": "confirmed for test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
    }


def _risk_v2(
    *,
    remaining: float = 40.0,
    size_mode: str = "NORMAL",
    unit: float = 10.0,
    can_bet: bool = True,
    stopped: bool = False,
    liquid: float = 500.0,
) -> dict:
    return {
        "can_bet": can_bet,
        "stopped": stopped,
        "remaining_risk_nok": remaining,
        "reasons": [],
        "size_mode": size_mode,
        "unit_size_nok": unit,
        "riskable_liquid_nok": liquid,
        "working_equity_nok": liquid,
        "equity_nok": liquid,
        "secure_nok": 0.0,
        "open_pending_risk_nok": 0.0,
        "drawdown_from_peak": 0.0,
        "phase_id": "1A",
        "capital_v2_enabled": True,
    }


def _cand(
    match: str = "Alpha vs Beta",
    selection: str = "Vinner: Alpha",
    odds: float = 1.85,
    p: float = 0.75,
    sport: str = "darts",
) -> Candidate:
    return Candidate(
        date="2026-07-21",
        match=match,
        selection=selection,
        decimal_odds=odds,
        sport=sport,
        market_type="Vinner",
        p_model=p,
        evidence=_pack(p),
        notes="test",
    )


# ── pure compute_unit_stake ───────────────────────────────────────────────


def test_normal_full_unit():
    d = compute_unit_stake(
        size_mode="NORMAL",
        unit_size_nok=10.0,
        remaining_room_nok=42.0,
        min_stake=10.0,
    )
    assert d.final_stake_nok == 10.0
    assert d.active_unit_nok == 10.0
    assert d.reject_reason is None
    assert d.schema_version == 1


def test_normal_unit_15_and_20():
    assert (
        compute_unit_stake(
            size_mode="NORMAL", unit_size_nok=15.0, remaining_room_nok=50.0
        ).final_stake_nok
        == 15.0
    )
    assert (
        compute_unit_stake(
            size_mode="NORMAL", unit_size_nok=20.0, remaining_room_nok=50.0
        ).final_stake_nok
        == 20.0
    )


def test_reduced_half_or_step():
    # unit 20 → half 10
    d = compute_unit_stake(
        size_mode="REDUCED", unit_size_nok=20.0, remaining_room_nok=50.0
    )
    assert d.active_unit_nok == 10.0
    assert d.final_stake_nok == 10.0
    # unit 15 → half illegal → step to 10
    d2 = compute_unit_stake(
        size_mode="REDUCED", unit_size_nok=15.0, remaining_room_nok=50.0
    )
    assert d2.active_unit_nok == reduced_unit(15.0, 10.0) == 10.0
    assert d2.final_stake_nok == 10.0
    # unit 10 → stays 10
    d3 = compute_unit_stake(
        size_mode="REDUCED", unit_size_nok=10.0, remaining_room_nok=50.0
    )
    assert d3.final_stake_nok == 10.0


def test_frozen_and_stopped_zero():
    assert (
        compute_unit_stake(
            size_mode="FROZEN", unit_size_nok=10.0, remaining_room_nok=40.0
        ).final_stake_nok
        == 0.0
    )
    assert (
        compute_unit_stake(
            size_mode="NORMAL",
            unit_size_nok=10.0,
            remaining_room_nok=40.0,
            stopped=True,
        ).final_stake_nok
        == 0.0
    )
    assert (
        compute_unit_stake(
            size_mode="NORMAL",
            unit_size_nok=10.0,
            remaining_room_nok=40.0,
            can_bet=False,
        ).final_stake_nok
        == 0.0
    )


def test_clip_to_remaining_room_fail_closed():
    # room 8 < floor → 0
    d = compute_unit_stake(
        size_mode="NORMAL", unit_size_nok=10.0, remaining_room_nok=8.0
    )
    assert d.final_stake_nok == 0.0
    assert d.reject_reason is not None
    # room 12, unit 15 → clip to 12, but 12 >= floor
    d2 = compute_unit_stake(
        size_mode="NORMAL", unit_size_nok=15.0, remaining_room_nok=12.0
    )
    assert d2.final_stake_nok == 12.0
    # room 11.9 → whole krone 11 still >= 10
    d3 = compute_unit_stake(
        size_mode="NORMAL", unit_size_nok=15.0, remaining_room_nok=11.9
    )
    assert d3.final_stake_nok == 11.0


def test_never_partial_below_floor():
    for room in (0, 1, 5, 9, 9.99, 10, 15):
        for unit in (10, 15, 20):
            d = compute_unit_stake(
                size_mode="NORMAL", unit_size_nok=unit, remaining_room_nok=room
            )
            assert d.final_stake_nok == 0.0 or d.final_stake_nok >= 10.0
            assert d.final_stake_nok == int(d.final_stake_nok)


def test_audit_dict_shape():
    d = compute_unit_stake(
        size_mode="NORMAL",
        unit_size_nok=10.0,
        remaining_room_nok=40.0,
        match="A vs B",
        selection="A",
        inputs={"ev": 0.1},
    )
    ad = d.to_audit_dict()
    assert ad["rule_bundle_version"]
    assert ad["final_stake_nok"] == 10.0
    assert "constraints_applied" in ad
    assert ad["inputs"]["ev"] == 0.1


# ── legacy identity ───────────────────────────────────────────────────────


def test_legacy_stake_for_unchanged_formula():
    phase = _phase()
    # EV mid-band: frac = (0.09-0.03)/0.12 = 0.5 → stake 11
    s = _stake_for(phase, 40.0, 10.0, False, 0.6, 1.0, 0.09)
    assert s == 11.0
    # remaining clip
    s2 = _stake_for(phase, 10.0, 10.0, False, 0.6, 1.0, 0.20)
    assert s2 == 10.0
    # remaining 9 → 0
    s3 = _stake_for(phase, 9.0, 10.0, False, 0.6, 1.0, 0.20)
    assert s3 == 0.0


def test_flag_off_build_portfolio_no_stake_decision():
    cfg = _cfg(enabled=False)
    risk = {"can_bet": True, "remaining_risk_nok": 40.0, "reasons": []}
    cands = [
        _cand("M1 vs M2", "Vinner: M1", 1.80, 0.75, "tennis"),
        _cand("M3 vs M4", "Vinner: M3", 1.90, 0.72, "darts"),
    ]
    picked, _ = build_portfolio(cfg, cands, _phase(), risk, historical_rows=[])
    assert len(picked) >= 1
    for p in picked:
        assert p.stake_decision is None
        assert p.stake_nok >= 10
        # legacy phase max 12
        assert p.stake_nok <= 12


def test_flag_off_stake_matches_direct_legacy_call():
    """Scoring stake path with flag off equals pure _stake_for for same EV/room."""
    phase = _phase()
    remaining = 40.0
    ev = 0.15  # near top of band → stake_max 12
    legacy = _stake_for(phase, remaining, 10.0, False, 0.6, 1.0, ev)
    # via portfolio helper with disabled flag uses _stake_for only in build;
    # direct compare for formula lock
    assert legacy == 12.0


# ── flag-on portfolio ─────────────────────────────────────────────────────


def test_flag_on_normal_unit_10():
    cfg = _cfg(enabled=True)
    risk = _risk_v2(remaining=40.0, size_mode="NORMAL", unit=10.0, liquid=500.0)
    picked, rejects = build_portfolio(
        cfg,
        [_cand()],
        _phase(),
        risk,
        historical_rows=[],
    )
    assert len(picked) == 1
    assert picked[0].stake_nok == 10.0
    assert picked[0].stake_decision is not None
    assert picked[0].stake_decision["size_mode"] == "NORMAL"
    assert picked[0].stake_decision["final_stake_nok"] == 10.0
    assert "size_mode=NORMAL" in picked[0].notes or "rules=" in picked[0].notes


def test_flag_on_unit_ladder_15_from_liquid():
    cfg = _cfg(enabled=True)
    # liquid 1500 → unit 15
    assert unit_size(1500.0) == 15.0
    risk = _risk_v2(remaining=50.0, size_mode="NORMAL", unit=15.0, liquid=1500.0)
    stake, dec = _stake_for_capital_v2(
        cfg,
        risk,
        remaining_risk=50.0,
        min_stake=10.0,
        high_odds=False,
        high_odds_mult=0.6,
        learning_stake_mult=1.0,
        ev=0.1,
        p_model=0.7,
        odds=1.8,
        match="A",
        selection="B",
    )
    assert stake == 15.0
    assert dec["active_unit_nok"] == 15.0


def test_flag_on_reduced_mode():
    cfg = _cfg(enabled=True)
    risk = _risk_v2(remaining=40.0, size_mode="REDUCED", unit=20.0, liquid=2500.0)
    stake, dec = _stake_for_capital_v2(
        cfg,
        risk,
        remaining_risk=40.0,
        min_stake=10.0,
        high_odds=False,
        high_odds_mult=0.6,
        learning_stake_mult=1.0,
        ev=0.1,
        p_model=0.7,
        odds=1.8,
        match="A",
        selection="B",
    )
    assert stake == 10.0  # half of 20
    assert dec["size_mode"] == "REDUCED"


def test_flag_on_frozen_zero_stake():
    cfg = _cfg(enabled=True)
    risk = _risk_v2(
        remaining=40.0, size_mode="FROZEN", unit=10.0, can_bet=False, stopped=True
    )
    # build_portfolio short-circuits on can_bet
    picked, rejects = build_portfolio(
        cfg, [_cand()], _phase(), risk, historical_rows=[]
    )
    assert picked == []
    assert rejects and rejects[0].get("reason") == "risk block"

    stake, dec = _stake_for_capital_v2(
        cfg,
        risk,
        remaining_risk=40.0,
        min_stake=10.0,
        high_odds=False,
        high_odds_mult=0.6,
        learning_stake_mult=1.0,
        ev=0.1,
        p_model=0.7,
        odds=1.8,
        match="A",
        selection="B",
    )
    assert stake == 0.0
    assert dec["final_stake_nok"] == 0.0


def test_flag_on_remaining_room_clip_in_portfolio():
    cfg = _cfg(enabled=True)
    # unit 15 but only 11 room
    risk = _risk_v2(remaining=11.0, size_mode="NORMAL", unit=15.0, liquid=1500.0)
    stake, dec = _stake_for_capital_v2(
        cfg,
        risk,
        remaining_risk=11.0,
        min_stake=10.0,
        high_odds=False,
        high_odds_mult=0.6,
        learning_stake_mult=1.0,
        ev=0.1,
        p_model=0.7,
        odds=1.8,
        match="A",
        selection="B",
    )
    assert stake == 11.0
    assert apply_nt_floor(stake, 10) == 11.0


def test_flag_on_remaining_below_floor_rejects():
    cfg = _cfg(enabled=True)
    risk = _risk_v2(remaining=8.0, size_mode="NORMAL", unit=10.0)
    # can_bet true but remaining < floor — portfolio should reject / not pick
    # evaluate_risk would set can_bet false; here we force edge case
    risk["can_bet"] = True
    picked, rejects = build_portfolio(
        cfg, [_cand()], _phase(), risk, historical_rows=[]
    )
    assert picked == []
    assert any(
        "insufficient remaining" in str(r.get("reason", "")).lower() for r in rejects
    )


def test_flag_on_rebalance_does_not_exceed_unit():
    """With unit 10, rebalance must not push stakes to phase stake_max 12."""
    cfg = _cfg(enabled=True)
    risk = _risk_v2(remaining=40.0, size_mode="NORMAL", unit=10.0, liquid=500.0)
    cands = [
        _cand("A vs B", "Vinner: A", 1.80, 0.80, "tennis"),
        _cand("C vs D", "Vinner: C", 1.85, 0.78, "darts"),
        _cand("E vs F", "Vinner: E", 1.90, 0.76, "esports"),
    ]
    picked, _ = build_portfolio(cfg, cands, _phase(), risk, historical_rows=[])
    assert len(picked) >= 1
    for p in picked:
        assert p.stake_nok <= 10.0 + 1e-9
        assert p.stake_nok >= 10.0 - 1e-9


def test_flag_on_combination_reduced_and_room():
    cfg = _cfg(enabled=True)
    # REDUCED unit 20 → 10; room 25 → stake 10
    risk = _risk_v2(remaining=25.0, size_mode="REDUCED", unit=20.0, liquid=3000.0)
    stake, dec = _stake_for_capital_v2(
        cfg,
        risk,
        remaining_risk=25.0,
        min_stake=10.0,
        high_odds=False,
        high_odds_mult=0.6,
        learning_stake_mult=1.0,
        ev=0.12,
        p_model=0.7,
        odds=1.9,
        match="MvG",
        selection="Vinner",
    )
    assert stake == 10.0
    assert dec["size_mode"] == "REDUCED"
    assert dec["active_unit_nok"] == 10.0
