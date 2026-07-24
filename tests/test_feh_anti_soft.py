"""Anti-soft underdog Condition A seal + pass conditions (PR2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence_hierarchy.anti_soft_underdog import (
    anti_soft_condition_a,
    anti_soft_condition_c,
    evaluate_anti_soft_underdog,
    matchup_eligible_factor_ids,
)
from nt.evidence_hierarchy.cards import load_sport_card
from nt.evidence_hierarchy.checklist import ChecklistAnswers, load_checklist_from_pack
from nt.evidence_hierarchy.feh import _is_underdog_hc, _is_favourite_hc
from nt.evidence_hierarchy.h2h_normalize import normalize_h2h
from nt.evidence_hierarchy.side_select import decide_side

SMITH_PATH = (
    ROOT
    / "evidence"
    / "smith_ross_vs_price_gerwyn_runde_handikap_2_5_smith_ross_2_5.json"
)


def _smith_pack() -> dict:
    if SMITH_PATH.is_file():
        return json.loads(SMITH_PATH.read_text(encoding="utf-8"))
    return {
        "sport": "darts",
        "selection": "Runde handikap 2.5: Smith, Ross +2.5",
        "h2h": {
            "checked": True,
            "edge": "mixed_competitive",
            "summary": "Competitive H2H Price slight lead.",
        },
        "signals": {
            "h2h_matchup": {"filled": True, "strength": "mixed", "note": "mixed h2h"},
            "recent_form": {
                "filled": True,
                "strength": "positive",
                "note": "Smith form decent recently overall.",
            },
            "checkout_scoring": {
                "filled": True,
                "strength": "positive",
                "note": "Long format keeps cover live always.",
            },
            "ranking_seed": {
                "filled": True,
                "strength": "negative",
                "note": "Price higher ranked.",
            },
            "format_stage": {
                "filled": True,
                "strength": "positive",
                "note": "Matchplay QF long legs format.",
            },
        },
    }


def test_anti_soft_a_fails_on_smith_pack():
    pack = _smith_pack()
    card = load_sport_card("darts")
    h2h = normalize_h2h(pack).to_dict()
    cl = load_checklist_from_pack(pack, h2h=h2h)
    a, sources = anti_soft_condition_a(pack, card, cl, h2h)
    assert a is False, sources
    assert h2h["positive"] is False


def test_anti_soft_a_excludes_checkout():
    """S1b: only positive checkout_scoring + mixed H2H → A false."""
    pack = {
        "sport": "darts",
        "selection": "Legs handikap +2.5: Dog +2.5",
        "h2h": {
            "checked": True,
            "edge": "mixed_competitive",
            "summary": "mixed only",
        },
        "signals": {
            "checkout_scoring": {
                "filled": True,
                "strength": "positive",
                "note": "High averages both sides long format cover.",
            },
            "h2h_matchup": {
                "filled": True,
                "strength": "mixed",
                "note": "Competitive series not one sided.",
            },
        },
    }
    card = load_sport_card("darts")
    h2h = normalize_h2h(pack).to_dict()
    cl = ChecklistAnswers(
        higher_ranked_side="favourite",
        ranking_confidence=0.7,
        better_form_side="even",
        form_confidence=0.5,
        h2h_verdict="mixed",
    )
    a, _ = anti_soft_condition_a(pack, card, cl, h2h)
    assert a is False


def test_anti_soft_a_excludes_recent_form():
    pack = {
        "h2h": {"checked": True, "edge": "mixed", "summary": "mixed"},
        "signals": {
            "recent_form": {
                "filled": True,
                "strength": "positive",
                "note": "Dog won last three ranking events easily.",
            },
        },
    }
    card = load_sport_card("darts")
    h2h = normalize_h2h(pack).to_dict()
    cl = ChecklistAnswers(
        higher_ranked_side="even",
        ranking_confidence=0.5,
        better_form_side="underdog",
        form_confidence=0.7,
        h2h_verdict="mixed",
    )
    a, _ = anti_soft_condition_a(pack, card, cl, h2h)
    assert a is False


def test_anti_soft_a_positive_h2h_passes():
    """S1c: positive structured H2H → A true."""
    pack = {
        "h2h": {
            "checked": True,
            "edge": "positive",
            "summary": "Dog leads H2H clearly 6-2.",
        },
        "signals": {
            "h2h_matchup": {
                "filled": True,
                "strength": "positive",
                "note": "Clear positive matchup edge for dog.",
            },
        },
    }
    card = load_sport_card("darts")
    h2h = normalize_h2h(pack).to_dict()
    cl = ChecklistAnswers(
        higher_ranked_side="even",
        ranking_confidence=0.4,
        better_form_side="underdog",
        form_confidence=0.6,
        h2h_verdict="positive",
        why_this_side_not_opposite=(
            "Positive H2H and form favour the underdog over the favourite chalk."
        ),
    )
    a, sources = anti_soft_condition_a(pack, card, cl, h2h)
    assert a is True, sources


def test_anti_soft_rank_fav_seal_blocks_misflagged_slot():
    """Even positive matchup slot fails A when rank fav + H2H not positive."""
    pack = {
        "h2h": {"checked": True, "edge": "mixed", "summary": "mixed"},
        "signals": {
            "h2h_matchup": {
                "filled": True,
                "strength": "positive",
                "note": "Would look positive but rank seal applies.",
            },
        },
    }
    card = load_sport_card("darts")
    h2h = normalize_h2h(pack).to_dict()
    assert h2h["positive"] is False
    cl = ChecklistAnswers(
        higher_ranked_side="favourite",
        ranking_confidence=0.7,
        better_form_side="even",
        form_confidence=0.5,
        h2h_verdict="mixed",
    )
    a, sources = anti_soft_condition_a(pack, card, cl, h2h)
    assert a is False, sources


def test_evaluate_anti_soft_smith_hard_reject():
    pack = _smith_pack()
    card = load_sport_card("darts")
    h2h = normalize_h2h(pack).to_dict()
    cl = load_checklist_from_pack(pack, h2h=h2h)
    res = evaluate_anti_soft_underdog(
        pack,
        cl,
        h2h,
        card=card,
        selection=str(pack.get("selection") or ""),
        odds=1.85,
        family="handicap",
    )
    assert res.applies is True
    assert res.condition_a is False
    assert res.hard_reject is True
    assert res.reject_code == "FEH_ANTI_SOFT_UNDERDOG"
    assert "A" in res.failures


def test_fav_hc_anti_soft_does_not_apply():
    pack = {
        "sport": "darts",
        "selection": "Runde handikap 2.5: Price, Gerwyn -2.5",
        "h2h": {"checked": True, "edge": "positive", "summary": "fav edge"},
    }
    card = load_sport_card("darts")
    cl = ChecklistAnswers(
        higher_ranked_side="favourite",
        ranking_confidence=0.8,
        better_form_side="favourite",
        form_confidence=0.7,
        h2h_verdict="positive",
    )
    res = evaluate_anti_soft_underdog(
        pack,
        cl,
        normalize_h2h(pack).to_dict(),
        card=card,
        selection=pack["selection"],
        odds=1.75,
        family="handicap",
    )
    assert res.applies is False


def test_minus_hc_not_underdog_even_at_long_odds():
    """Minus HC at odds>=1.85 is favourite HC, never soft underdog."""
    sel = "Runde handikap 5.5: Price, Gerwyn -5.5"
    assert _is_underdog_hc(sel, 1.95) is False
    assert _is_favourite_hc(sel) is True
    assert _is_underdog_hc("Smith, Ross +2.5", 1.85) is True

    cl = ChecklistAnswers(
        higher_ranked_side="favourite",
        ranking_confidence=0.8,
        better_form_side="favourite",
        form_confidence=0.7,
        h2h_verdict="positive",
    )
    h2h = {"checked": True, "positive": True, "negative": False, "mixed": False}
    side = decide_side(
        cl,
        h2h,
        selection=sel,
        odds=1.95,
        is_underdog_hc=_is_underdog_hc(sel, 1.95),
        is_favourite_hc=_is_favourite_hc(sel),
        family="handicap",
    )
    assert side.selection_side == "favourite"
    assert side.hard_reject is False
    assert side.reject_code != "FEH_SIDE_CONFLICT"


def test_default_matchup_allowlist_h2h_only():
    """Without card flags, only h2h_matchup is matchup-eligible."""
    ids = matchup_eligible_factor_ids(None)
    assert ids == {"h2h_matchup"}
    assert "surface_h2h" not in ids
    assert "underdog_matchup_edge" not in ids
    # Tennis card flags surface_h2h with individual_h2h
    tennis = load_sport_card("tennis")
    if tennis is not None:
        tids = matchup_eligible_factor_ids(tennis)
        assert "h2h_matchup" in tids or "surface_h2h" in tids
        # surface only if card declares individual_h2h
        for f in tennis.all_factors():
            if f.get("id") == "surface_h2h" and f.get("individual_h2h"):
                assert "surface_h2h" in tids


def test_condition_c_does_not_pass_on_odds_price_alone():
    """Bare 'price' / odds language must not satisfy opposite-side C."""
    cl = ChecklistAnswers(
        why_this_side_not_opposite=(
            "This is a good price at mid band with value on the number line."
        )
    )
    assert anti_soft_condition_c(cl) is False
    cl2 = ChecklistAnswers(
        why_this_side_not_opposite=(
            "Form and H2H favour the underdog rather than the favourite chalk."
        )
    )
    assert anti_soft_condition_c(cl2) is True
