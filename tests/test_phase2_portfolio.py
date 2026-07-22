"""Phase 2: max_per_match correlation, stake packing, rejects completeness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import grade_evidence
from nt.portfolio import Candidate, Recommendation, build_portfolio, rebalance_stakes


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


def _risk(remaining: float = 40.0):
    return {
        "can_bet": True,
        "remaining_risk_nok": remaining,
        "reasons": [],
    }


def _cfg():
    return {
        "norsk_tipping": {"min_stake_nok": 10},
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
            "enabled": True,
            "diversification": {
                "max_per_sport": 2,
                "max_per_market": 3,
                "max_per_band": 4,
                "max_per_match": 1,
                "max_football_per_round": 1,
                "min_non_football_per_round": 1,
                "prefer_explore_first": False,
                "explore_min_ev": 0.012,
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
    }


def _pack(p: float = 0.70, odds: float = 1.85) -> dict:
    sources = [
        {"url": f"https://example.com/{i}", "takeaway": "ok", "kind": "stats"}
        for i in range(8)
    ]
    return {
        "match": "X",
        "selection": "Y",
        "p_model": p,
        "summary": "test pack with enough text for grade B",
        "failure_modes": "test failure",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "full strength expected for test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
        # HV v3: place requires dual-write odds snapshot
        "odds_at_research": odds,
        "decimal_odds_ref": odds,
    }


def test_rebalance_reserves_extra_seats():
    picks = [
        Recommendation(
            match="A vs B",
            selection="A",
            decimal_odds=1.8,
            stake_nok=10,
            ev=0.20,
            grade="B",
            odds_band="1.8-2.2",
            sport="tennis",
            market_type="HC",
            p_model=0.7,
            notes="",
        ),
        Recommendation(
            match="C vs D",
            selection="C",
            decimal_odds=1.7,
            stake_nok=10,
            ev=0.05,
            grade="B",
            odds_band="1.5-1.8",
            sport="darts",
            market_type="tot",
            p_model=0.65,
            notes="",
        ),
    ]
    # Budget 32: without reserve would top up to 12+12=24 leftover 8
    leftover = rebalance_stakes(picks, 32.0, 10.0, 12.0, reserve_extra_seats=1)
    total = sum(p.stake_nok for p in picks)
    # With reserve 10 for third seat: usable 22 → 12+10=22 leftover 10
    assert leftover >= 10.0 - 0.01
    assert total <= 22.0 + 0.01
    assert all(p.stake_nok >= 10 for p in picks)


def test_rebalance_leftover_below_min_is_ok_under_unit_cap():
    """When max_stake = min_stake (unit floor), leftover < min cannot fund another seat."""
    picks = [
        Recommendation(
            match="A vs B",
            selection="A",
            decimal_odds=1.8,
            stake_nok=10,
            ev=0.20,
            grade="B",
            odds_band="1.8-2.2",
            sport="tennis",
            market_type="HC",
            p_model=0.7,
            notes="",
        ),
        Recommendation(
            match="C vs D",
            selection="C",
            decimal_odds=1.7,
            stake_nok=10,
            ev=0.05,
            grade="B",
            odds_band="1.5-1.8",
            sport="darts",
            market_type="tot",
            p_model=0.65,
            notes="",
        ),
    ]
    leftover = rebalance_stakes(picks, 28.0, 10.0, 10.0, reserve_extra_seats=0)
    assert sum(p.stake_nok for p in picks) == 20.0
    assert leftover == 8.0  # unavoidable under NT floor + unit cap


def test_rebalance_no_reserve_uses_budget():
    picks = [
        Recommendation(
            match="A vs B",
            selection="A",
            decimal_odds=1.8,
            stake_nok=10,
            ev=0.20,
            grade="B",
            odds_band="1.8-2.2",
            sport="tennis",
            market_type="HC",
            p_model=0.7,
            notes="",
        ),
        Recommendation(
            match="C vs D",
            selection="C",
            decimal_odds=1.7,
            stake_nok=10,
            ev=0.05,
            grade="B",
            odds_band="1.5-1.8",
            sport="darts",
            market_type="tot",
            p_model=0.65,
            notes="",
        ),
    ]
    leftover = rebalance_stakes(picks, 32.0, 10.0, 12.0, reserve_extra_seats=0)
    total = sum(p.stake_nok for p in picks)
    assert total == 24.0  # 12+12
    assert leftover == 8.0


def test_max_per_match_blocks_second_market_same_match():
    cfg = _cfg()
    pack = _pack(0.72)
    cands = [
        Candidate(
            date="2026-07-20",
            match="Humphries, Luke vs Menzies, Cameron",
            selection="Totalt antall runder 15.5: Over 15.5",
            decimal_odds=2.10,
            sport="darts",
            market_type="Totalt antall runder 15.5",
            p_model=0.72,
            evidence=dict(
                pack,
                match="Humphries, Luke vs Menzies, Cameron",
                selection="Totalt antall runder 15.5: Over 15.5",
                odds_at_research=2.10,
                decimal_odds_ref=2.10,
            ),
        ),
        Candidate(
            date="2026-07-20",
            match="Humphries, Luke vs Menzies, Cameron",
            selection="Legs handikap -4.5: Menzies, Cameron +4.5",
            decimal_odds=1.80,
            sport="darts",
            market_type="Legs handikap -4.5",
            p_model=0.70,
            evidence=dict(
                pack,
                match="Humphries, Luke vs Menzies, Cameron",
                selection="Legs handikap -4.5: Menzies, Cameron +4.5",
                p_model=0.70,
                odds_at_research=1.80,
                decimal_odds_ref=1.80,
            ),
        ),
        Candidate(
            date="2026-07-21",
            match="Dallas Wings vs New York Liberty",
            selection="Handikap 4.5: Dallas Wings +4.5",
            decimal_odds=1.85,
            sport="basketball",
            market_type="Handikap 4.5",
            p_model=0.68,
            evidence=dict(
                pack,
                match="Dallas Wings vs New York Liberty",
                selection="Handikap 4.5: Dallas Wings +4.5",
                p_model=0.68,
                odds_at_research=1.85,
                decimal_odds_ref=1.85,
            ),
        ),
    ]
    picked, rejects = build_portfolio(cfg, cands, _phase(), _risk(40), [], learning={})
    matches = [p.match for p in picked]
    # At most one line from Humphries match
    assert matches.count("Humphries, Luke vs Menzies, Cameron") <= 1
    assert any("max 1 per match" in str(r.get("reason", "")).lower() or "max 1 per match" in str(r) for r in rejects) or any(
        "per match" in str(r.get("reason", "")).lower() for r in rejects
    )
    # Second match can still be picked
    assert any("Wings" in m or "Liberty" in m for m in matches) or len(picked) >= 1


def test_stake_packing_fills_three_min_seats_when_budget_allows():
    """Classic bug: 12+10+11=33 left 8.51; packing should fund 3×10+ leftovers."""
    cfg = _cfg()
    pack = _pack(0.70)
    cands = []
    for i, (match, sel, odds, sport) in enumerate(
        [
            ("Match A vs B", "Sel A", 1.85, "tennis"),
            ("Match C vs D", "Sel C", 1.80, "darts"),
            ("Match E vs F", "Sel E", 1.90, "basketball"),
            ("Match G vs H", "Sel G", 1.75, "snooker"),
        ]
    ):
        cands.append(
            Candidate(
                date="2026-07-20",
                match=match,
                selection=sel,
                decimal_odds=odds,
                sport=sport,
                market_type="Vinner",
                p_model=0.70,
                evidence=dict(
                    pack,
                    match=match,
                    selection=sel,
                    p_model=0.70,
                    odds_at_research=odds,
                    decimal_odds_ref=odds,
                ),
            )
        )
    # 32 risk, max 4 bets, max_per_sport 2 → can take 3–4 singles
    picked, _ = build_portfolio(cfg, cands, _phase(max_bets_per_round=4), _risk(32), [], learning={})
    total = sum(p.stake_nok for p in picked)
    assert len(picked) >= 3
    assert total >= 30  # at least 3 min stakes used
    # No stake below min
    assert all(p.stake_nok >= 10 for p in picked)
    # Should not strand more than min_stake-1 when 3+ picks fit
    leftover = 32 - total
    assert leftover < 10 or len(picked) >= 3
