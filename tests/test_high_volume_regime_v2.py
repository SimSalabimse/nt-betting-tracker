"""
High-Volume Research Regime v2 — success-criteria proof suite.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_v2 import (
    capital_v2_cfg,
    compute_secure_transfer,
    compute_unit_stake,
    grade_stake_multiplier,
    unit_size,
)
from nt.evidence import ev_after_haircut, has_core_reason, is_strong_confidence
from nt.bankroll_regime import bankroll_regime_cfg, evaluate_bankroll_regime
from nt.research_prefilter import stage1_fast_screen
from nt.light_research import LightRecord, promotion_score, tiers_cfg


def _hv_cfg(**sel_extra) -> dict:
    """Minimal High-Volume v2 config (mirrors production knobs)."""
    return {
        "norsk_tipping": {"min_stake_nok": 10.0},
        "capital_v2": {
            "enabled": True,
            "unit_ladder": [
                {"max_liquid_exclusive": 1500.0, "unit": 12.0},
                {"max_liquid_exclusive": 2500.0, "unit": 15.0},
                {"max_liquid_exclusive": None, "unit": 20.0},
            ],
            "grade_stake_mult": {"C": 1.0, "B": 1.4, "A": 2.0, "A_high_conf": 2.2},
            "secure_bucket": {
                "enabled": True,
                "trigger_multiple_of_ref": 1.30,
                "transfer_fraction_of_profit_above_ref": 0.27,
                "min_working_frac_of_equity": 0.55,
                "min_working_units": 8.0,
            },
        },
        "bankroll_regime": {
            "enabled": True,
            "exploration": {
                "exit_settled": 40,
                "exit_equity": 650,
                "min_ev": 0.02,
                "open_risk_cap_nok": 100,
            },
            "survival": {"min_ev": 0.03, "open_risk_cap_nok": 100},
        },
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
            "standard_min_ev": 0.02,
            **sel_extra,
        },
        "recommend": {"max_run_stake_pct_of_equity": 0.20},
        "research": {
            "tiers": {
                "short_chalk_odds": 1.70,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "promo_mid_band_boost": 60,
                "promo_alt_boost": 14,
                "promo_short_chalk_penalty": -55,
            },
            "prefilter": {
                "enabled": True,
                "stage1": {
                    "enabled": True,
                    "drop_short_chalk_ml": True,
                    "strong_data_p_needed": 0.55,
                    "max_p_needed": 0.78,
                },
            },
        },
        "learning": {"enabled": False},
        "risk": {},
        "phases": {
            "1A": {
                "stake_min": 10,
                "stake_max": 12,
                "max_bets_per_round": 5,
            }
        },
    }


def test_haircut_3pp():
    # p=0.55, odds=2.0 → p_adj=0.52 → EV = 0.04
    assert abs(ev_after_haircut(0.55, 2.0, 0.03) - 0.04) < 1e-9
    # old 5pp would be 0.00
    assert abs(ev_after_haircut(0.55, 2.0, 0.05) - 0.0) < 1e-9


def test_unit_ladder_12_under_1500():
    v2 = capital_v2_cfg(_hv_cfg())
    assert unit_size(500.0, v2) == 12.0
    assert unit_size(1499.0, v2) == 12.0
    assert unit_size(1500.0, v2) == 15.0


def test_grade_mult_B_and_A():
    v2 = capital_v2_cfg(_hv_cfg())
    assert grade_stake_multiplier("B", v2=v2) == pytest.approx(1.4)
    assert grade_stake_multiplier("A", v2=v2) == pytest.approx(2.0)
    assert grade_stake_multiplier("A", high_confidence=True, v2=v2) == pytest.approx(2.2)
    assert grade_stake_multiplier("C", v2=v2) == pytest.approx(1.0)

    d = compute_unit_stake(
        size_mode="NORMAL",
        unit_size_nok=12.0,
        remaining_room_nok=100.0,
        min_stake=10.0,
        grade_mult=1.4,
    )
    # 12 * 1.4 = 16.8 → whole krone 16
    assert d.final_stake_nok == 16.0


def test_secure_27pct():
    # equity 700, ref 500 → profit_above 200 → 0.27*200 = 54
    res = compute_secure_transfer(
        ledger_equity=700.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        trigger_multiple=1.30,
        transfer_fraction=0.27,
        unit_size_nok=12.0,
    )
    assert res.triggered is True
    assert res.transferred == 54.0


def test_exploration_regime_min_ev_2pct():
    cfg = _hv_cfg()
    reg = evaluate_bankroll_regime(cfg, equity=500.0, settled_count=0)
    assert reg["id"] == "exploration"
    assert float(reg["min_ev"]) == pytest.approx(0.02)
    assert float(reg["open_risk_cap_nok"]) == pytest.approx(100.0)


def test_core_reason_and_strong_confidence():
    assert not has_core_reason({})
    assert not has_core_reason({"summary": "short"})
    assert has_core_reason(
        {"summary": "Clear mid-band total with injury-driven unders."}
    )
    pack = {
        "sources": [{"name": f"s{i}", "url": f"http://x/{i}"} for i in range(8)],
        "summary": "Solid multi-source case for the under.",
    }
    assert is_strong_confidence(pack, "B", min_sources=8)
    assert not is_strong_confidence({"sources": [{"name": "a"}]}, "B", min_sources=8)


def test_stage1_short_chalk_1_70_blocks_without_strong():
    cfg = _hv_cfg()
    # Short main ML at 1.65 — need_p for 2% EV + 3pp is high → block
    ok, reason = stage1_fast_screen(
        selection="Vinner: Home",
        odds=1.65,
        sport="football",
        cfg=cfg,
    )
    assert ok is False
    assert "short_chalk" in reason


def test_stage1_short_chalk_strong_data_exception():
    cfg = _hv_cfg()
    # Very high odds relative need is low when odds high... use odds where
    # need_p is low: for odds 1.65, need_p = (1.02)/1.65 + 0.03 ≈ 0.648 > 0.55
    # so still blocks. Exception needs need_p <= 0.55 → odds roughly:
    # (1+min_ev)/odds + haircut <= 0.55 → (1.02)/odds <= 0.52 → odds >= 1.96
    # For short_chalk path we need odds < 1.70. So true strong exception on
    # short prices requires higher min_ev in need calc... use absolute:
    # need_p = (1.02)/1.60 + 0.03 = 0.6675 — still high.
    # At odds 1.69, need_p ≈ 0.633. Exception only when strong_need is high
    # or haircut/min_ev low enough. Force exception by setting strong_data_p_needed high.
    cfg["research"]["prefilter"]["stage1"]["strong_data_p_needed"] = 0.70
    ok, reason = stage1_fast_screen(
        selection="Vinner: Home",
        odds=1.65,
        sport="football",
        cfg=cfg,
    )
    assert ok is True
    assert "strong_data" in reason


def test_mid_promotion_over_short():
    cfg = _hv_cfg()
    mid = LightRecord(
        match="A vs B",
        selection="Handikap -1.5: Away",
        sport="football",
        decimal_odds=2.10,
        odds_band="1.8-2.2",
        market_family="handicap",
        rough_p_needed=0.50,
    )
    short = LightRecord(
        match="C vs D",
        selection="Vinner: Home",
        sport="football",
        decimal_odds=1.55,
        odds_band="<1.5",
        market_family="ml",
        rough_p_needed=0.70,
    )
    sm = promotion_score(mid, cfg)
    ss = promotion_score(short, cfg)
    assert sm > ss


def test_run_budget_20pct_math():
    equity = 500.0
    remaining = 200.0
    run_pct = 0.20
    budget = min(remaining, equity * run_pct)
    assert budget == 100.0
    # Three grade-B stakes at 16 NOK = 48 ≤ 100
    assert 3 * 16 <= budget
    # Ten unit-A at 24 would exceed → pack must stop
    assert 10 * 24 > budget


def test_tiers_cfg_high_volume_defaults():
    cfg = _hv_cfg()
    cfg["research"]["tiers"]["deep_target_n"] = 8
    t = tiers_cfg(cfg)
    assert float(t["short_chalk_odds"]) == pytest.approx(1.70)
    assert float(t["deep_target_n"]) == pytest.approx(8)
    assert float(t["promo_mid_band_boost"]) == pytest.approx(60)
