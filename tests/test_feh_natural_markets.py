"""PR3: Natural market elevation — S3b/S4b isolation + S3/S4 smoke + place-path E2E."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import grade_evidence
from nt.evidence_hierarchy.cards import load_sport_card
from nt.evidence_hierarchy.checklist import ChecklistAnswers
from nt.evidence_hierarchy.feh import run_forced_evidence_hierarchy
from nt.evidence_hierarchy.natural_markets import (
    detect_triggers,
    discover_sibling_packs,
    evaluate_natural_markets,
)
from nt.portfolio import Candidate, build_portfolio

SMITH_HC = (
    ROOT
    / "evidence"
    / "smith_ross_vs_price_gerwyn_runde_handikap_2_5_smith_ross_2_5.json"
)
SMITH_O27 = (
    ROOT
    / "evidence"
    / "smith_ross_vs_price_gerwyn_totalt_antall_runder_27_5_over_27_5.json"
)


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
            "natural_market_elevation": True,
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
        "research": {"gates": {"enabled": False}},
        "paths": {"evidence": str(ROOT / "evidence")},
    }


def _anti_soft_pass_pack() -> dict:
    """Soft UD HC that passes anti-soft A–D (positive H2H, form not fav, why-side, rank OK)."""
    return {
        "match": "Smith, Ross vs Price, Gerwyn",
        "selection": "Runde handikap 2.5: Smith, Ross +2.5",
        "sport": "darts",
        "p_model": 0.58,
        "p_model_sd": 0.06,
        "summary": (
            "Soft underdog HC with clear positive H2H and form for the dog; "
            "dual high scoring long format makes legs totals natural alternative."
        ),
        "failure_modes": "Favourite wins in straight sets blowout.",
        "confidence": "medium",
        "availability_status": "predicted",
        "script_lean": "close_cover",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "profile_flags": ["dual_high_scoring", "long_format"],
        "h2h": {
            "checked": True,
            "edge": "positive",
            "summary": "Dog leads H2H clearly 6-2 in recent meetings.",
            "sample_n": 8,
        },
        "signals": {
            "h2h_matchup": {
                "filled": True,
                "strength": "positive",
                "note": "Clear positive matchup edge for underdog cover.",
            },
            "recent_form": {
                "filled": True,
                "strength": "positive",
                "note": "Dog form strong last five ranking events.",
            },
            "checkout_scoring": {
                "filled": True,
                "strength": "positive",
                "note": "Both high averages dual scoring long format Matchplay.",
            },
            "ranking_seed": {
                "filled": True,
                "strength": "mixed",
                "note": "Rank gap modest not heavy favourite.",
            },
            "format_stage": {
                "filled": True,
                "strength": "positive",
                "note": "Matchplay QF long legs format.",
            },
        },
        "checklist": {
            "schema_version": 1,
            "higher_ranked_side": "even",
            "ranking_confidence": 0.4,
            "better_form_side": "underdog",
            "form_confidence": 0.7,
            "h2h_verdict": "positive",
            "h2h_summary": "Dog leads H2H 6-2.",
            "natural_markets": ["over_27_5_legs"],
            "natural_market_hint": "dual high scoring favours legs over",
            "underdog_supported_by_evidence": True,
            "underdog_support_reason": "Positive H2H and form for dog cover.",
            "why_this_side_not_opposite": (
                "Positive H2H and form favour the underdog over the favourite chalk "
                "minus line; rank gap is modest so cover is the better side."
            ),
            "strongest_positive": "h2h positive for dog",
            "strongest_negative": "favourite still shorter on ML",
            "primary_factors_used": ["h2h_matchup", "recent_form", "checkout_scoring"],
        },
        "sources": [
            {
                "url": f"https://example.com/nat/{i}",
                "takeaway": "Support note long enough for quality source takeaway.",
                "kind": "preview",
                "name": f"Src{i}",
            }
            for i in range(6)
        ],
        # Explicitly empty natural eval — S3b isolation
        "natural_market_eval": {
            "evaluated": [],
            "comparison_vs_hc": "",
        },
    }


def _sibling_over() -> dict:
    if SMITH_O27.is_file():
        return json.loads(SMITH_O27.read_text(encoding="utf-8"))
    return {
        "match": "Smith, Ross vs Price, Gerwyn",
        "selection": "Totalt antall runder 27.5: Over 27.5",
        "sport": "darts",
        "summary": (
            "Legs Over 27.5 supported by dual high scoring and competitive H2H; "
            "Matchplay QF long format often goes deep into legs."
        ),
        "p_model": 0.59,
    }


def test_s4b_evaluate_natural_markets_unevaluated():
    """S4b: module unit — triggers + sibling present + empty eval → hard reject."""
    pack = _anti_soft_pass_pack()
    card = load_sport_card("darts")
    cl = ChecklistAnswers(
        higher_ranked_side="even",
        ranking_confidence=0.4,
        better_form_side="underdog",
        form_confidence=0.7,
        h2h_verdict="positive",
        natural_markets=["over_27_5_legs"],
        natural_market_hint="dual high scoring",
        why_this_side_not_opposite=(
            "Positive H2H and form favour the underdog over the favourite chalk."
        ),
    )
    triggers = detect_triggers(pack, card, cl)
    assert triggers, "expected dual-high / checklist triggers"

    res = evaluate_natural_markets(
        triggers=triggers,
        pack=pack,
        selection=pack["selection"],
        family="handicap",
        card=card,
        checklist=cl,
        odds_rows=None,
        sibling_packs=[_sibling_over()],
        enabled=True,
        soft_ud_hc=True,
    )
    assert res.hard_reject is True
    assert res.reject_code == "FEH_NATURAL_MARKET_UNEVALUATED"
    assert res.candidates
    assert "over_legs_high" in res.candidates or res.candidates


def test_s4b_missing_on_board_is_na_not_fail():
    """Candidate not on board and no sibling → N/A, not hard reject."""
    pack = _anti_soft_pass_pack()
    card = load_sport_card("darts")
    res = evaluate_natural_markets(
        triggers=["dual_high_scoring", "long_format"],
        pack=pack,
        selection=pack["selection"],
        family="handicap",
        card=card,
        odds_rows=[],  # board known empty
        sibling_packs=[],
        enabled=True,
        soft_ud_hc=True,
    )
    assert res.hard_reject is False
    assert res.reject_code is None
    assert res.status in ("n_a", "no_trigger", "required_ok")


def test_s3b_feh_natural_unevaluated_with_anti_soft_pass():
    """
    S3b: Soft UD HC passes anti-soft A–D, dual-high trigger, sibling Over 27.5,
    empty natural_market_eval → F with FEH_NATURAL_MARKET_UNEVALUATED.
    """
    pack = _anti_soft_pass_pack()
    cfg = _place_cfg()
    sibling = _sibling_over()

    feh = run_forced_evidence_hierarchy(
        pack,
        sport="darts",
        selection=pack["selection"],
        odds=1.85,
        cfg=cfg,
        sibling_packs=[sibling],
        run_saef=True,
    )
    assert feh.anti_soft.get("hard_reject") is False, feh.anti_soft
    assert feh.anti_soft.get("condition_a") is True, feh.anti_soft
    assert feh.hard_reject is True
    assert "FEH_NATURAL_MARKET_UNEVALUATED" in feh.reject_codes, feh.reject_codes
    assert feh.final_grade_suggestion == "F"

    # Place boundary: grade_evidence with explicit siblings must also F + code
    grade, issues = grade_evidence(
        pack,
        cfg,
        1.85,
        selection=pack["selection"],
        sport="darts",
        sibling_packs=[sibling],
        auto_discover_siblings=False,
    )
    assert grade == "F", (grade, issues)
    blob = " ".join(issues)
    assert "FEH_NATURAL_MARKET_UNEVALUATED" in blob or "feh:FEH_NATURAL_MARKET_UNEVALUATED" in blob


def test_s3b_grade_with_sibling_via_feh_audit():
    """Full FEH with sibling → grade path reject codes include natural when wired."""
    pack = _anti_soft_pass_pack()
    cfg = _place_cfg()
    feh = run_forced_evidence_hierarchy(
        pack,
        sport="darts",
        selection=pack["selection"],
        odds=1.85,
        cfg=cfg,
        sibling_packs=[_sibling_over()],
    )
    assert feh.final_grade_suggestion == "F"
    assert "FEH_NATURAL_MARKET_UNEVALUATED" in feh.reject_codes
    # Anti-soft must not be the only reject — natural must appear
    assert feh.anti_soft.get("hard_reject") is False


def test_s3b_grade_evidence_auto_discover_from_evidence_dir(tmp_path: Path):
    """
    OPEN ISSUE 1 fix: grade_evidence discovers same-match sibling from evidence dir
    without callers passing sibling_packs kwargs.
    """
    pack = _anti_soft_pass_pack()
    sibling = _sibling_over()
    # Unique match so we don't collide with real evidence/ packs
    pack["match"] = "Natural Unit A vs Natural Unit B"
    sibling["match"] = "Natural Unit A vs Natural Unit B"
    sibling["selection"] = "Totalt antall runder 27.5: Over 27.5"

    evid = tmp_path / "evidence"
    evid.mkdir()
    (evid / "natural_unit_a_vs_natural_unit_b_over_27_5.json").write_text(
        json.dumps(sibling, ensure_ascii=False),
        encoding="utf-8",
    )
    cfg = _place_cfg()
    cfg["paths"] = {"evidence": str(evid)}

    # No sibling_packs kwarg — discovery only
    grade, issues = grade_evidence(
        pack,
        cfg,
        1.85,
        selection=pack["selection"],
        sport="darts",
        auto_discover_siblings=True,
    )
    assert grade == "F", (grade, issues)
    blob = " ".join(issues)
    assert "FEH_NATURAL_MARKET_UNEVALUATED" in blob
    # Confirm discovery helper sees sibling
    found = discover_sibling_packs(pack, evidence_dir=evid)
    assert found, "expected sibling pack on disk"
    assert any("over" in str(s.get("selection") or "").lower() for s in found)


def test_s3b_portfolio_place_boundary_rejects_unevaluated_natural(tmp_path: Path):
    """
    OPEN ISSUE 2: end-to-end place boundary — soft UD that passes anti-soft
    + sibling natural present among candidates → not placed; reject cites FEH natural.
    """
    pack = _anti_soft_pass_pack()
    sibling = _sibling_over()
    pack["match"] = "Port Natural A vs Port Natural B"
    sibling["match"] = "Port Natural A vs Port Natural B"
    sibling["selection"] = "Totalt antall runder 27.5: Over 27.5"
    sibling["p_model"] = 0.55
    sibling.setdefault("failure_modes", "Short match")
    sibling.setdefault(
        "sources",
        [
            {
                "url": f"https://example.com/sib/{i}",
                "takeaway": "Sibling takeaway long enough for quality.",
                "name": f"Sib{i}",
            }
            for i in range(6)
        ],
    )

    cfg = _place_cfg()
    cfg["selection"]["odds_confidence"] = {"enabled": False}
    cfg["selection"]["standard_min_ev"] = 0.01
    cfg["selection"]["probability_haircut"] = 0.0
    cfg["learning"] = {"enabled": False}
    cfg["norsk_tipping"] = {"min_stake_nok": 10}
    cfg["paths"] = {"evidence": str(tmp_path / "evidence")}
    (tmp_path / "evidence").mkdir(exist_ok=True)

    phase = {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 4,
    }
    risk = {
        "can_bet": True,
        "remaining_risk_nok": 100.0,
        "daily_risk_cap_nok": 100.0,
        "unit_size_nok": 12.0,
    }

    # Soft UD HC candidate (anti-soft pass) + sibling totals on same match
    hc = Candidate(
        date="2026-07-24",
        match=pack["match"],
        selection=pack["selection"],
        decimal_odds=1.85,
        sport="darts",
        market_type="HC",
        p_model=float(pack["p_model"]),
        evidence=pack,
    )
    tot = Candidate(
        date="2026-07-24",
        match=sibling["match"],
        selection=sibling["selection"],
        decimal_odds=1.72,
        sport="darts",
        market_type="Totals",
        p_model=float(sibling["p_model"]),
        evidence=sibling,
    )
    picked, rejects = build_portfolio(cfg, [hc, tot], phase, risk, [], learning={})
    # Soft UD HC must not be placed
    hc_picks = [p for p in picked if "+2.5" in (p.selection or "")]
    assert hc_picks == [], f"soft UD HC must be unplaceable; got {picked}"
    # Reject for HC must mention natural unevaluated or grade F / feh_blocked
    hc_rejects = [
        r
        for r in rejects
        if "+2.5" in str(r.get("selection") or "")
        or "handikap" in str(r.get("selection") or "").lower()
    ]
    assert hc_rejects, f"expected HC reject; rejects={rejects}"
    blob = " ".join(
        str(r.get("reason") or "") + " " + " ".join(str(x) for x in (r.get("issues") or []))
        for r in hc_rejects
    )
    assert (
        "FEH_NATURAL_MARKET_UNEVALUATED" in blob
        or "feh_blocked" in blob
        or "grade F" in blob.lower()
        or "odds_band" in blob
    ), blob


def test_s3_smoke_smith_not_placeable():
    """S3 smoke: Smith soft UD + natural elevation on → not placeable (anti-soft and/or natural)."""
    # Prefer live pack when present; else synthetic Smith-shaped fixture (CI-safe)
    if SMITH_HC.is_file():
        pack = json.loads(SMITH_HC.read_text(encoding="utf-8"))
    else:
        pack = {
            "match": "Smith, Ross vs Price, Gerwyn",
            "selection": "Runde handikap 2.5: Smith, Ross +2.5",
            "sport": "darts",
            "p_model": 0.59,
            "summary": (
                "BAND 1.85-2.30 Grade B. Smith +2.5 legs @ 1.85. "
                "POS: H2H competitive; long format. NEG: Price fav."
            ),
            "failure_modes": "Price 16-8 blowout.",
            "availability_status": "predicted",
            "h2h": {
                "checked": True,
                "edge": "mixed_competitive",
                "summary": "Competitive H2H Price slight lead.",
            },
            "signals": {
                "h2h_matchup": {
                    "filled": True,
                    "strength": "mixed",
                    "note": "Competitive H2H not one sided.",
                },
                "checkout_scoring": {
                    "filled": True,
                    "strength": "positive",
                    "note": "Long format cover live always both high.",
                },
                "ranking_seed": {
                    "filled": True,
                    "strength": "negative",
                    "note": "Price higher ranked.",
                },
            },
            "sources": [
                {
                    "url": f"https://example.com/smith/{i}",
                    "takeaway": "Takeaway long enough for quality source floor.",
                    "name": f"S{i}",
                }
                for i in range(6)
            ],
        }
    cfg = _place_cfg()
    siblings = [_sibling_over()]
    feh = run_forced_evidence_hierarchy(
        pack,
        sport="darts",
        selection=str(pack.get("selection") or ""),
        odds=1.85,
        cfg=cfg,
        sibling_packs=siblings,
    )
    assert feh.hard_reject is True
    assert feh.final_grade_suggestion == "F"
    grade, issues = grade_evidence(
        pack,
        cfg,
        1.85,
        selection=str(pack.get("selection") or ""),
        sport="darts",
        sibling_packs=siblings,
        auto_discover_siblings=False,
    )
    assert grade == "F"
    blob = " ".join(issues)
    assert "feh:" in blob or "FEH_" in blob or "anti_soft" in blob.lower()


def test_s4_smoke_natural_evaluated_still_anti_soft_on_mixed():
    """S4 smoke: complete natural eval + mixed H2H → F via anti-soft; natural may pass."""
    pack = {
        "match": "Dog vs Fav",
        "selection": "Runde handikap 2.5: Dog +2.5",
        "sport": "darts",
        "p_model": 0.56,
        "summary": "Soft dog HC with mixed H2H; natural totals evaluated as better path.",
        "failure_modes": "Fav covers easily.",
        "availability_status": "predicted",
        "profile_flags": ["dual_high_scoring"],
        "h2h": {
            "checked": True,
            "edge": "mixed_competitive",
            "summary": "Competitive mixed H2H not one sided.",
        },
        "signals": {
            "h2h_matchup": {
                "filled": True,
                "strength": "mixed",
                "note": "Mixed competitive series.",
            },
            "checkout_scoring": {
                "filled": True,
                "strength": "positive",
                "note": "Both high averages dual scoring.",
            },
        },
        "checklist": {
            "higher_ranked_side": "favourite",
            "ranking_confidence": 0.8,
            "better_form_side": "favourite",
            "form_confidence": 0.7,
            "h2h_verdict": "mixed",
            "natural_markets": ["over_27_5"],
            "natural_market_hint": "totals better",
            "why_this_side_not_opposite": (
                "Long format cover over the favourite chalk is the only play "
                "despite rank gap; H2H mixed."
            ),
            "underdog_supported_by_evidence": True,
            "underdog_support_reason": "format cover only",
            "strongest_positive": "format",
            "strongest_negative": "rank fav",
            "primary_factors_used": ["checkout_scoring"],
        },
        "natural_market_eval": {
            "evaluated": ["over_legs_high"],
            "comparison_vs_hc": (
                "Over 27.5 legs is the cleaner natural market versus soft underdog "
                "HC; dual high scoring supports totals over the plus handicap."
            ),
        },
        "sources": [
            {
                "url": f"https://example.com/s4/{i}",
                "takeaway": "Takeaway long enough for quality gate.",
                "name": f"S{i}",
            }
            for i in range(6)
        ],
    }
    cfg = _place_cfg()
    feh = run_forced_evidence_hierarchy(
        pack,
        sport="darts",
        selection=pack["selection"],
        odds=1.90,
        cfg=cfg,
        sibling_packs=[_sibling_over()],
    )
    # Natural should not hard-reject when evaluated
    assert feh.natural_markets.get("hard_reject") is False, feh.natural_markets
    # Anti-soft should still F (mixed H2H / rank fav)
    assert feh.hard_reject is True
    assert "FEH_ANTI_SOFT_UNDERDOG" in feh.reject_codes
    assert "FEH_NATURAL_MARKET_UNEVALUATED" not in feh.reject_codes


def test_natural_eval_complete_passes_gate():
    """With comparison text, natural gate does not hard reject soft UD."""
    pack = _anti_soft_pass_pack()
    pack["natural_market_eval"] = {
        "evaluated": ["over_legs_high"],
        "comparison_vs_hc": (
            "Over 27.5 legs is preferred to soft underdog HC given dual high scoring; "
            "HC still playable only with positive H2H which is present."
        ),
    }
    card = load_sport_card("darts")
    res = evaluate_natural_markets(
        triggers=["dual_high_scoring", "long_format"],
        pack=pack,
        selection=pack["selection"],
        family="handicap",
        card=card,
        sibling_packs=[_sibling_over()],
        enabled=True,
        soft_ud_hc=True,
    )
    assert res.hard_reject is False
    assert res.reject_code is None
    assert "over_legs_high" in res.evaluated
