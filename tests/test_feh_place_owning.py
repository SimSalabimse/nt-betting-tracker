"""Place-owning FEH — checklist, Smith F, explore cannot bypass (PR2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.evidence import grade_evidence
from nt.evidence_hierarchy.feh import run_forced_evidence_hierarchy
from nt.evidence_hierarchy.score import place_uses_saef

SMITH_PATH = (
    ROOT
    / "evidence"
    / "smith_ross_vs_price_gerwyn_runde_handikap_2_5_smith_ross_2_5.json"
)
PRICE_PATH = ROOT / "evidence" / "smith_ross_vs_price_gerwyn_vinner_price_gerwyn.json"


def _place_cfg(**fh_over):
    evidence = {
        "enabled": True,
        "shadow_mode": False,
        "fail_closed": True,
        "auto_onboard_cards": True,
        "strict_band_cd": True,
        "min_takeaway_chars": 24,
        "min_quality_sources_floor": 3,
        "min_quality_sources_b": 4,
        "min_E_grade_b": 0.55,
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
            "anti_soft_ml_dogs": {
                "individual_sports": True,
                "team_sports": False,
            },
        },
    }
    if fh_over:
        fh = dict(evidence["forced_hierarchy"])
        fh.update(fh_over)
        evidence["forced_hierarchy"] = fh
    return {
        "selection": {
            "probability_haircut": 0.03,
            "high_odds_threshold": 2.5,
            "high_odds_min_grade": "A",
            "grade_a_require_uncertainty": True,
            "min_research_sources": {
                "default": 6,
                "grade_A": 10,
                "high_odds": 12,
            },
            "evidence": evidence,
        },
        "research": {"gates": {"enabled": True}},
        "paths": {"evidence": str(ROOT / "evidence")},
    }


def _load_smith() -> dict:
    assert SMITH_PATH.is_file(), "Smith pack missing"
    return json.loads(SMITH_PATH.read_text(encoding="utf-8"))


def test_production_config_place_uses_saef():
    cfg = load_config()
    assert place_uses_saef(cfg) is True
    ev = (cfg.get("selection") or {}).get("evidence") or {}
    assert ev.get("shadow_mode") is False
    assert (ev.get("forced_hierarchy") or {}).get("enabled") is True


def test_s1_smith_grade_f_anti_soft():
    """S1: Smith +2.5 @ 1.85 → F with FEH_ANTI_SOFT_UNDERDOG."""
    pack = _load_smith()
    cfg = _place_cfg()
    assert place_uses_saef(cfg) is True
    grade, issues = grade_evidence(
        pack,
        cfg,
        1.85,
        selection=str(pack.get("selection") or ""),
        sport="darts",
    )
    assert grade == "F", (grade, issues)
    blob = " ".join(issues)
    assert "FEH_ANTI_SOFT_UNDERDOG" in blob

    feh = run_forced_evidence_hierarchy(
        pack,
        sport="darts",
        selection=str(pack.get("selection") or ""),
        odds=1.85,
        cfg=cfg,
    )
    assert feh.hard_reject is True
    assert "FEH_ANTI_SOFT_UNDERDOG" in feh.reject_codes
    assert feh.anti_soft.get("condition_a") is False
    assert feh.anti_soft.get("applies") is True


def test_s2_price_fav_anti_soft_n_a():
    """S2: fav HC / Price side — anti_soft.applies is False."""
    if PRICE_PATH.is_file():
        pack = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
    else:
        pack = {
            "sport": "darts",
            "selection": "Runde handikap 2.5: Price, Gerwyn -2.5",
            "summary": "Price favourite HC supported by ranking form and H2H edge.",
            "failure_modes": "Smith whitewash upset cover.",
            "p_model": 0.55,
            "p_model_sd": 0.06,
            "h2h": {
                "checked": True,
                "edge": "positive",
                "summary": "Price leads H2H.",
            },
            "signals": {
                "h2h_matchup": {
                    "filled": True,
                    "strength": "positive",
                    "note": "Price H2H edge clear over Smith.",
                },
                "ranking_seed": {
                    "filled": True,
                    "strength": "positive",
                    "note": "Price higher ranked seed.",
                },
                "recent_form": {
                    "filled": True,
                    "strength": "positive",
                    "note": "Price form strong into Matchplay.",
                },
            },
            "sources": [
                {
                    "name": f"s{i}",
                    "url": f"https://flashscore.com/p/{i}",
                    "takeaway": f"Quality takeaway number {i} with enough characters.",
                }
                for i in range(6)
            ],
            "availability_status": "stable_guess",
            "availability_notes": "Both active listed no WD on board confirmed.",
            "script_lean": "fav_control",
            "selection_vs_script": "agree",
            "base_rate_conflict": False,
            "context_risk": "low",
            "feh_checklist": {
                "schema_version": 1,
                "higher_ranked_side": "favourite",
                "ranking_confidence": 0.8,
                "better_form_side": "favourite",
                "form_confidence": 0.7,
                "h2h_verdict": "positive",
                "h2h_summary": "Price leads H2H series clearly over Smith.",
                "natural_markets": ["none"],
                "natural_market_hint": "none",
                "underdog_supported_by_evidence": False,
                "underdog_support_reason": "Not an underdog selection; Price is favourite HC.",
                "why_this_side_not_opposite": (
                    "Ranking, form and positive H2H all support Price favourite "
                    "over the Smith underdog cover line."
                ),
                "strongest_positive": "Price ranking and H2H edge vs Smith clear.",
                "strongest_negative": "Smith can still cover +2.5 in long format.",
                "primary_factors_used": ["h2h_matchup", "ranking_seed", "recent_form"],
            },
        }
    cfg = _place_cfg()
    # Canonical fav HC — live Price pack may be ML; S2 isolates fav HC N/A
    sel = "Runde handikap 2.5: Price, Gerwyn -2.5"
    pack = dict(pack)
    pack["selection"] = sel
    feh = run_forced_evidence_hierarchy(
        pack, sport="darts", selection=sel, odds=1.75, cfg=cfg
    )
    assert feh.anti_soft.get("applies") is False


def test_s5_explore_notes_cannot_bypass_feh_f():
    """S5: EXPLORE / virgin / temp_ev_relax markers on pack still F."""
    pack = _load_smith()
    pack = dict(pack)
    pack["notes"] = "EXPLORE virgin sport market temp_ev_relax coverage pressure"
    pack["explore"] = True
    pack["temp_ev_relax"] = True
    pack["coverage_pressure"] = True
    cfg = _place_cfg()
    grade, issues = grade_evidence(
        pack, cfg, 1.85, selection=pack["selection"], sport="darts"
    )
    assert grade == "F"
    assert any("FEH_ANTI_SOFT_UNDERDOG" in i for i in issues)


def test_checklist_incomplete_fail_closed():
    cfg = _place_cfg()
    pack = {
        "sport": "darts",
        "selection": "Legs handikap +1.5: Dog +1.5",
        "summary": "Some summary text for a soft dog mid band line look.",
        "failure_modes": "fav thrashing.",
        "p_model": 0.52,
        "h2h": {"checked": True, "edge": "mixed", "summary": "mixed"},
        "signals": {},
        "sources": [
            {
                "name": f"s{i}",
                "url": f"https://pdc.tv/x/{i}",
                "takeaway": f"Detailed takeaway {i} with enough characters here.",
            }
            for i in range(6)
        ],
        "availability_status": "stable_guess",
        "availability_notes": "Both players listed active no WD flags present.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "context_risk": "low",
    }
    feh = run_forced_evidence_hierarchy(
        pack, sport="darts", selection=pack["selection"], odds=1.90, cfg=cfg
    )
    assert feh.checklist_complete is False
    assert "FEH_CHECKLIST_INCOMPLETE" in feh.reject_codes
    assert feh.hard_reject is True
    grade, issues = grade_evidence(
        pack, cfg, 1.90, selection=pack["selection"], sport="darts"
    )
    assert grade == "F"
    assert any("FEH_CHECKLIST_INCOMPLETE" in i for i in issues)


def test_feh_error_fail_closed_not_legacy():
    """Place-owning must not fail-open to legacy B on FEH exception path."""
    cfg = _place_cfg()
    # Minimal broken-ish pack still graded via FEH; missing fields → F
    pack = {"sport": "darts", "selection": "x +2.5", "p_model": 0.5}
    grade, issues = grade_evidence(
        pack, cfg, 1.90, selection="Dog +2.5", sport="darts"
    )
    assert grade == "F"
