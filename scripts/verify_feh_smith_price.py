#!/usr/bin/env python3
"""Closed Smith/Price FEH oracle — exit non-zero on any miss (PR2: S1,S1b,S1c,S2,S5,S6)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import grade_evidence
from nt.evidence_hierarchy.anti_soft_underdog import anti_soft_condition_a
from nt.evidence_hierarchy.cards import load_sport_card
from nt.evidence_hierarchy.checklist import ChecklistAnswers, load_checklist_from_pack
from nt.evidence_hierarchy.feh import run_forced_evidence_hierarchy
from nt.evidence_hierarchy.h2h_normalize import normalize_h2h
from nt.evidence_hierarchy.score import place_uses_saef

SMITH = (
    ROOT
    / "evidence"
    / "smith_ross_vs_price_gerwyn_runde_handikap_2_5_smith_ross_2_5.json"
)
PRICE_ML = ROOT / "evidence" / "smith_ross_vs_price_gerwyn_vinner_price_gerwyn.json"


def _cfg():
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
            "evidence": {
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
            },
        },
        "research": {"gates": {"enabled": True}},
        "paths": {"evidence": str(ROOT / "evidence")},
    }


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    cfg = _cfg()
    if not place_uses_saef(cfg):
        _fail("place_uses_saef must be True for oracle config")

    if not SMITH.is_file():
        _fail(f"missing Smith pack {SMITH}")
    smith = json.loads(SMITH.read_text(encoding="utf-8"))
    card = load_sport_card("darts", cfg)
    sel = str(smith.get("selection") or "Runde handikap 2.5: Smith, Ross +2.5")

    # --- S1 ---
    grade, issues = grade_evidence(
        smith, cfg, 1.85, selection=sel, sport="darts"
    )
    if grade != "F":
        _fail(f"S1 grade={grade} expected F; issues={issues}")
    blob = " ".join(issues)
    if "FEH_ANTI_SOFT_UNDERDOG" not in blob:
        _fail(f"S1 missing FEH_ANTI_SOFT_UNDERDOG in {issues}")
    feh = run_forced_evidence_hierarchy(
        smith, sport="darts", selection=sel, odds=1.85, cfg=cfg
    )
    if not feh.anti_soft.get("applies"):
        _fail("S1 anti_soft.applies expected True")
    if feh.anti_soft.get("condition_a") is not False:
        _fail("S1 condition A must fail despite positive checkout/form")
    if "FEH_ANTI_SOFT_UNDERDOG" not in feh.reject_codes:
        _fail(f"S1 reject_codes={feh.reject_codes}")
    print("PASS S1: Smith +2.5 → F FEH_ANTI_SOFT_UNDERDOG (A fails)")

    # --- S1b ---
    pack_b = {
        "sport": "darts",
        "selection": sel,
        "h2h": {
            "checked": True,
            "edge": "mixed_competitive",
            "summary": "mixed only",
        },
        "signals": {
            "checkout_scoring": {
                "filled": True,
                "strength": "positive",
                "note": "High checkout both sides long format cover path.",
            },
            "h2h_matchup": {
                "filled": True,
                "strength": "mixed",
                "note": "Competitive not one sided matchup record.",
            },
        },
    }
    h2h_b = normalize_h2h(pack_b).to_dict()
    cl_b = ChecklistAnswers(
        higher_ranked_side="favourite",
        ranking_confidence=0.7,
        better_form_side="even",
        form_confidence=0.5,
        h2h_verdict="mixed",
    )
    a_b, _ = anti_soft_condition_a(pack_b, card, cl_b, h2h_b)
    if a_b is not False:
        _fail("S1b checkout alone must not pass condition A")
    print("PASS S1b: checkout alone cannot pass A")

    # --- S1c ---
    pack_c = {
        "sport": "darts",
        "selection": sel,
        "h2h": {
            "checked": True,
            "edge": "positive",
            "summary": "Dog leads H2H 6-2 clear edge.",
        },
        "signals": {
            "h2h_matchup": {
                "filled": True,
                "strength": "positive",
                "note": "Clear positive matchup edge for underdog side.",
            },
        },
    }
    h2h_c = normalize_h2h(pack_c).to_dict()
    cl_c = ChecklistAnswers(
        higher_ranked_side="even",
        ranking_confidence=0.4,
        better_form_side="underdog",
        form_confidence=0.6,
        h2h_verdict="positive",
        why_this_side_not_opposite=(
            "Positive H2H and form favour underdog over the favourite chalk side."
        ),
    )
    a_c, src = anti_soft_condition_a(pack_c, card, cl_c, h2h_c)
    if a_c is not True:
        _fail(f"S1c positive H2H must pass A; sources={src}")
    print("PASS S1c: positive H2H can pass A")

    # --- S2 ---
    if PRICE_ML.is_file():
        price = json.loads(PRICE_ML.read_text(encoding="utf-8"))
    else:
        price = {
            "sport": "darts",
            "selection": "Runde handikap 2.5: Price, Gerwyn -2.5",
            "h2h": {"checked": True, "edge": "positive", "summary": "Price edge"},
        }
    price_sel = "Runde handikap 2.5: Price, Gerwyn -2.5"
    feh2 = run_forced_evidence_hierarchy(
        price, sport="darts", selection=price_sel, odds=1.75, cfg=cfg
    )
    if feh2.anti_soft.get("applies") is not False:
        _fail(f"S2 anti_soft.applies must be False; got {feh2.anti_soft}")
    print("PASS S2: Price fav HC anti_soft N/A")

    # --- S5 explore bypass ---
    smith_ex = dict(smith)
    smith_ex["notes"] = "EXPLORE virgin temp_ev_relax coverage"
    smith_ex["explore"] = True
    g5, i5 = grade_evidence(
        smith_ex, cfg, 1.85, selection=sel, sport="darts"
    )
    if g5 != "F" or "FEH_ANTI_SOFT_UNDERDOG" not in " ".join(i5):
        _fail(f"S5 explore must still F anti-soft; grade={g5} issues={i5}")
    print("PASS S5: explore/temp_ev_relax cannot bypass")

    # --- S6 promo max (grade path independent of promotion_score) ---
    smith_pr = dict(smith)
    smith_pr["promotion_score"] = 10_000
    smith_pr["promo_mid_band_boost"] = 999
    g6, i6 = grade_evidence(
        smith_pr, cfg, 1.85, selection=sel, sport="darts"
    )
    if g6 != "F" or "FEH_ANTI_SOFT_UNDERDOG" not in " ".join(i6):
        _fail(f"S6 promo max must still F; grade={g6} issues={i6}")
    print("PASS S6: max promotion_score cannot place")

    # Production config smoke (if loadable)
    try:
        from nt.config import load_config

        prod = load_config()
        if not place_uses_saef(prod):
            _fail("production config place_uses_saef is False")
        print("PASS production: place_uses_saef True")
    except Exception as exc:
        print(f"WARN production config check skipped: {exc}")

    print("ALL SMITH/PRICE ORACLE CHECKS PASSED (S1,S1b,S1c,S2,S5,S6)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
