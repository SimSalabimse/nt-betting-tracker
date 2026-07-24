"""PR5: reasoning schema v2, soft-UD feedback, promo research boosts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import grade_evidence
from nt.feh_feedback import (
    PATTERN_SOFT_UD_FAV_FORM,
    feh_proves_process_miss,
    process_settlement_feh_feedback,
    should_tag_soft_ud_loss,
)
from nt.light_research import LightRecord, promotion_score_components
from nt.portfolio import Recommendation
from nt.reasoning_chain import (
    SCHEMA_VERSION,
    build_chain_from_near_miss,
    build_chain_from_pick,
    build_recommend_chains,
)


def _promo_cfg(**tier_over) -> dict:
    tiers = {
        "short_chalk_odds": 1.70,
        "preferred_odds_lo": 1.85,
        "preferred_odds_hi": 2.60,
        "alt_preferred_odds_lo": 1.80,
        "soft_value_min_rel": 0.08,
        "promo_mid_band_boost": 60,
        "promo_alt_boost": 14,
        "promo_short_chalk_penalty": -55,
        "promo_fav_hc_boost": 12,
        "promo_natural_total_boost": 10,
    }
    tiers.update(tier_over)
    return {"research": {"tiers": tiers}, "selection": {"probability_haircut": 0.03}}


def test_schema_version_is_2():
    assert SCHEMA_VERSION == 2


def test_chain_v2_feh_fields_from_pick():
    pick = Recommendation(
        match="A vs B",
        selection="A -1.5",
        decimal_odds=1.95,
        stake_nok=10.0,
        ev=0.04,
        grade="B",
        odds_band="1.8-2.2",
        sport="darts",
        market_type="handicap",
        p_model=0.55,
        notes="p_model=0.55; FEH_TEST_CAP:10NOK (1/10)",
        stake_decision={"constraints_applied": ["feh_test_cap_10nok"]},
        feh={
            "hard_reject": False,
            "reject_codes": [],
            "checklist_complete": True,
            "checklist": {
                "strongest_positive": "ranking gap favours A clearly",
                "strongest_negative": "B checkout form mixed lately",
                "why_this_side_not_opposite": (
                    "A ranking and form both lean favourite side not dog HC"
                ),
                "primary_factors_used": ["ranking_seed", "h2h_matchup"],
                "complete": True,
            },
            "anti_soft_underdog": {
                "applies": False,
                "triggered": False,
                "hard_reject": False,
                "failures": [],
            },
            "h2h": {"polarity": "positive"},
            "final_grade_suggestion": "B",
            "saef": {"E": 0.7, "hard_rejects": []},
        },
    )
    cfg = {
        "selection": {
            "probability_haircut": 0.03,
            "test_stake_cap": {"enabled": True, "max_bets": 10, "max_stake_nok": 10.0},
        },
        "paths": {"state_dir": str(ROOT / "data" / "state")},
    }
    chain = build_chain_from_pick(pick, haircut=0.03, phase_id="1A", cfg=cfg)
    assert chain["schema_version"] == 2
    assert "ranking" in chain["strongest_positive"].lower()
    assert chain["strongest_negative"]
    assert len(chain["why_this_side_not_opposite"]) >= 20
    assert "ranking_seed" in chain["primary_factors"]
    assert chain["final_grade"] == "B"
    assert chain["h2h_polarity"] == "positive"
    assert chain["odds_band"]
    assert isinstance(chain["test_cap_10nok"], dict)
    assert chain["test_cap_10nok"].get("applied") is True
    assert chain["saef"]["E"] == 0.7


def test_chain_v2_near_miss_anti_soft_codes():
    row = {
        "match": "Smith vs Price",
        "selection": "Smith +2.5",
        "odds": 1.85,
        "grade": "F",
        "reason": "evidence grade F",
        "issues": ["feh:FEH_ANTI_SOFT_UNDERDOG", "saef_card=darts"],
        "feh": {
            "hard_reject": True,
            "reject_codes": ["FEH_ANTI_SOFT_UNDERDOG"],
            "checklist_complete": True,
            "anti_soft_underdog": {
                "applies": True,
                "triggered": True,
                "hard_reject": True,
                "failures": ["A"],
            },
            "h2h": {"polarity": "mixed"},
            "final_grade_suggestion": "F",
        },
        "near_miss": True,
    }
    chain = build_chain_from_near_miss(row, haircut=0.03)
    assert chain["schema_version"] == 2
    assert "FEH_ANTI_SOFT_UNDERDOG" in chain["feh_reject_codes"]
    assert chain["anti_soft_underdog"]["triggered"] is True
    assert chain["anti_soft_underdog"]["failures"] == ["A"]
    assert chain["h2h_polarity"] == "mixed"
    assert chain["final_grade"] == "F"


def test_soft_ud_feedback_pattern_only_without_feh_proof(tmp_path: Path):
    """Legacy soft-UD loss: tag pattern, do NOT lean process_miss without FEH proof."""
    cfg = {
        "paths": {"state_dir": str(tmp_path)},
        "selection": {"feh_feedback": {"enabled": True, "jsonl": "feh_feedback.jsonl"}},
    }
    bet = {
        "bet_id": "legacy1",
        "match": "Smith vs Price",
        "selection": "Smith +2.5",
        "decimal_odds": 1.85,
        "sport": "darts",
        "notes": "EXPLORE; ranking gap favours Price; mixed h2h",
        "result": "Loss",
    }
    packet = {
        "variance_class": "unknown",
        "predictability": "weakly_predictable",
        "learning_weight": 0.18,
    }
    meta = process_settlement_feh_feedback(
        cfg, bet, result="Loss", packet=packet, feh_audit=None
    )
    assert meta["tagged"] is True
    assert meta["pattern"] == PATTERN_SOFT_UD_FAV_FORM
    assert meta["lean_applied"] is False
    assert packet["variance_class"] == "unknown"  # no invent
    assert PATTERN_SOFT_UD_FAV_FORM in (bet.get("notes") or "")
    path = tmp_path / "feh_feedback.jsonl"
    assert path.is_file()
    line = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert line["legacy_no_feh_proof"] is True


def test_soft_ud_feedback_leans_process_miss_when_feh_proves(tmp_path: Path):
    cfg = {
        "paths": {"state_dir": str(tmp_path)},
        "selection": {"feh_feedback": {"enabled": True}},
    }
    bet = {
        "bet_id": "feh1",
        "match": "Smith vs Price",
        "selection": "Smith +2.5",
        "decimal_odds": 1.85,
        "sport": "darts",
        "notes": "placed soft dog",
        "result": "Loss",
    }
    feh = {
        "hard_reject": True,
        "reject_codes": ["FEH_ANTI_SOFT_UNDERDOG"],
        "checklist_complete": True,
        "anti_soft_underdog": {
            "applies": True,
            "triggered": True,
            "hard_reject": True,
            "failures": ["A"],
        },
        "checklist": {
            "higher_ranked_side": "favourite",
            "better_form_side": "favourite",
        },
    }
    packet = {"variance_class": "unknown", "predictability": "weakly_predictable"}
    meta = process_settlement_feh_feedback(
        cfg, bet, result="Loss", packet=packet, feh_audit=feh
    )
    assert meta["tagged"] is True
    assert meta["lean_applied"] is True
    assert meta["variance_lean"] == "research_process_miss"
    assert packet["variance_class"] == "research_process_miss"


def test_feh_proves_requires_audit_not_guess():
    ok, proofs = feh_proves_process_miss(None)
    assert ok is False
    assert proofs == []
    ok2, proofs2 = feh_proves_process_miss(
        {
            "hard_reject": True,
            "reject_codes": ["FEH_ANTI_SOFT_UNDERDOG"],
            "anti_soft_underdog": {"hard_reject": True, "triggered": True},
        }
    )
    assert ok2 is True
    assert proofs2


def test_should_tag_requires_soft_ud_and_fav_signal():
    bet_ok = {
        "selection": "Dog +2.5",
        "decimal_odds": 1.90,
        "notes": "higher rank favours home",
        "result": "Loss",
    }
    hit, meta = should_tag_soft_ud_loss(bet_ok, result="Loss")
    assert hit is True
    bet_no = {
        "selection": "Dog +2.5",
        "decimal_odds": 1.90,
        "notes": "plain notes",
        "result": "Loss",
    }
    hit2, _ = should_tag_soft_ud_loss(bet_no, result="Loss")
    assert hit2 is False


def test_promo_fav_hc_and_natural_total_boosts():
    cfg = _promo_cfg()
    fav = LightRecord(
        match="A vs B",
        selection="A -2.5",
        sport="darts",
        decimal_odds=1.90,
        odds_band="1.85-2.20",
        market_family="handicap",
        verdict="pass",
    )
    dog = LightRecord(
        match="A vs B",
        selection="B +2.5",
        sport="darts",
        decimal_odds=1.90,
        odds_band="1.85-2.20",
        market_family="handicap",
        verdict="pass",
    )
    total = LightRecord(
        match="A vs B",
        selection="Over 27.5",
        sport="darts",
        decimal_odds=1.90,
        odds_band="1.85-2.20",
        market_family="totals_over",
        verdict="pass",
    )
    fav_br = promotion_score_components(fav, cfg)
    dog_br = promotion_score_components(dog, cfg)
    tot_br = promotion_score_components(total, cfg)
    assert fav_br["components"].get("fav_hc", 0) == 12
    assert "fav_hc" not in dog_br["components"]
    assert tot_br["components"].get("natural_total", 0) == 10
    # Fav HC should outrank soft dog at same odds (research rank only)
    assert fav_br["total"] > dog_br["total"]


def test_promo_cannot_place_anti_soft_pack():
    """Invariant: max promo is research-rank only — FEH still grades soft UD F."""
    smith_path = (
        ROOT
        / "evidence"
        / "smith_ross_vs_price_gerwyn_runde_handikap_2_5_smith_ross_2_5.json"
    )
    if not smith_path.is_file():
        return  # skip if fixture absent
    ev = json.loads(smith_path.read_text(encoding="utf-8"))
    cfg = {
        "selection": {
            "probability_haircut": 0.03,
            "high_odds_threshold": 2.5,
            "high_odds_min_grade": "A",
            "grade_a_require_uncertainty": True,
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
            "evidence": {
                "enabled": True,
                "shadow_mode": False,
                "fail_closed": True,
                "auto_onboard_cards": True,
                "forced_hierarchy": {
                    "enabled": True,
                    "require_checklist": True,
                    "anti_soft_underdog": True,
                    "allow_soft_ud_grade_c": False,
                    "natural_market_elevation": False,
                    "side_first": True,
                    "soft_ud_odds_lo": 1.70,
                    "soft_ud_odds_hi_hard": 2.20,
                    "soft_ud_odds_hi_soft": 2.60,
                },
            },
        },
        "research": {
            "gates": {"enabled": True},
            "tiers": {
                "promo_mid_band_boost": 999,
                "promo_alt_boost": 999,
                "promo_fav_hc_boost": 999,
                "promo_natural_total_boost": 999,
            },
        },
        "paths": {"evidence": str(ROOT / "evidence")},
    }
    # Promo score can be huge — still must not place
    rec = LightRecord(
        match="Smith Ross vs Price Gerwyn",
        selection=str(ev.get("selection") or "Smith Ross +2.5"),
        sport="darts",
        decimal_odds=1.85,
        odds_band="1.85-2.20",
        market_family="handicap",
        verdict="pass",
        promote_to_deep=True,
    )
    br = promotion_score_components(rec, cfg)
    assert br["total"] > 100  # research rank inflated
    grade, issues = grade_evidence(
        ev,
        cfg,
        1.85,
        selection=str(ev.get("selection") or ""),
        sport="darts",
    )
    assert grade == "F"
    blob = " ".join(str(x) for x in issues)
    assert "FEH_ANTI_SOFT" in blob or "ANTI_SOFT" in blob or "feh:" in blob.lower()


def test_build_recommend_chains_passes_cfg_for_v2(tmp_path: Path):
    cfg = {
        "paths": {
            "state_dir": str(tmp_path),
            "outbox": str(tmp_path / "outbox"),
            "reasoning_chains_jsonl": str(tmp_path / "chains.jsonl"),
        },
        "selection": {
            "probability_haircut": 0.03,
            "test_stake_cap": {
                "enabled": True,
                "max_bets": 10,
                "max_stake_nok": 10.0,
                "state_path": str(tmp_path / "feh_test_cap.json"),
            },
        },
        "reasoning": {"enabled": True, "join_light": False, "max_near_miss": 4},
    }
    pick = Recommendation(
        match="X vs Y",
        selection="Over 2.5",
        decimal_odds=2.0,
        stake_nok=10.0,
        ev=0.05,
        grade="B",
        odds_band="1.8-2.2",
        sport="football",
        market_type="total",
        p_model=0.54,
        notes="ok",
        feh={
            "checklist_complete": True,
            "checklist": {
                "strongest_positive": "script supports goals both ways here",
                "strongest_negative": "weather may suppress total slightly",
                "why_this_side_not_opposite": (
                    "xg form and open game script support over not under"
                ),
                "primary_factors_used": ["script_consistency"],
                "complete": True,
            },
            "final_grade_suggestion": "B",
            "h2h": {"polarity": "unknown"},
        },
    )
    chains = build_recommend_chains(cfg, [pick], [], phase_id="1A")
    assert chains
    c0 = chains[0]
    assert c0["schema_version"] == 2
    assert c0.get("strongest_positive")
    assert "test_cap_10nok" in c0
