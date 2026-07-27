"""
MIC schema + coverage grade matrix tests.

Grade A/B/C/D/F fixtures with score±0.02 and exact grade.
Form partial credit; B requires n_miss==0.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.match_intel.coverage import (
    coverage_score,
    critical_missing_count,
    form_credit,
    grade_card,
    key_credit,
)
from nt.match_intel.schema import (
    empty_mic_skeleton,
    finalize_coverage,
    mic_match_key,
    side_dict,
    validate_mic_shape,
)


def _form(n: int, letters: str | None = None) -> dict:
    if letters is None:
        letters = ("WDLWD" * 3)[:n]
    results = list(letters[:n])
    return {"n": n, "results": results, "scores": [], "summary": "".join(results)}


def _base_football(**kwargs) -> dict:
    card = empty_mic_skeleton("Alpha FC vs Beta United", sport="football", errors=[])
    card["extraction"]["primary_method"] = "test"
    card["extraction"]["errors"] = []
    card["extraction"]["needs_review"] = False
    card["extraction"]["match_confidence"] = "exact"
    card.update(kwargs)
    return card


def test_mic_match_key_slug():
    assert mic_match_key("Barcelona SC vs LDU Quito") == "barcelona_sc_vs_ldu_quito"
    assert mic_match_key("Bodø/Glimt – Brann")  # nordic / dash
    key = mic_match_key("Bodø/Glimt – Brann")
    assert " " not in key
    assert key == key.lower()
    assert len(key) <= 120
    assert mic_match_key("") == "unknown_match"
    assert mic_match_key("!!!") == "unknown_match"


def test_form_credit_partial():
    assert form_credit(5) == 1.0
    assert form_credit(6) == 1.0
    assert form_credit(4) == 0.85
    assert form_credit(3) == 0.70
    assert form_credit(2) == 0.0
    assert form_credit(0) == 0.0


def test_form_key_credit_partial():
    card = _base_football()
    card["sides"]["home"] = side_dict("Alpha", recent_form=_form(3, "WDL"))
    card["sides"]["away"] = side_dict("Beta", recent_form=_form(4, "WWDL"))
    assert key_credit(card, "form_home") == pytest.approx(0.70)
    assert key_credit(card, "form_away") == pytest.approx(0.85)
    card["sides"]["home"]["recent_form"] = _form(5, "WWDLW")
    assert key_credit(card, "form_home") == pytest.approx(1.0)
    # n=2 → absent
    card["sides"]["away"]["recent_form"] = _form(2, "WW")
    assert key_credit(card, "form_away") == 0.0


def _card_grade_a() -> dict:
    """All critical full + ≥2 optional → score ≥ 0.80, n_miss=0 → A."""
    card = _base_football()
    card["competition"] = {"name": "Liga Pro", "country": "Ecuador"}
    card["sides"]["home"] = side_dict(
        "Alpha",
        recent_form=_form(5, "WWDLW"),
        standings={"rank": 2, "points": 40},
        home_away_split={"home_wdl": "6-2-1", "away_wdl": None, "notes": None},
        injuries_suspensions=[{"player": "X", "status": "out", "reason": "injury", "source": "t"}],
        rest_days=4,
    )
    card["sides"]["away"] = side_dict(
        "Beta",
        recent_form=_form(5, "LWDWL"),
        standings={"rank": 5, "points": 32},
        rest_days=3,
    )
    card["h2h"] = {"n": 5, "summary": "home edge", "recent": [], "polarity": "home_edge"}
    card["referee"] = {"name": "Ref", "cards_tendency": None, "notes": None}
    card["motivation_situational"] = {
        "tags": ["mid_table"],
        "notes": "ok",
        "final": False,
        "relegation_battle": False,
        "title_race": False,
    }
    return card


def _card_grade_b() -> dict:
    """All critical full, zero optional → score 0.70, n_miss=0 → B."""
    card = _base_football()
    card["competition"] = {"name": "Test League"}
    card["sides"]["home"] = side_dict(
        "Alpha",
        recent_form=_form(5, "WWWWW"),
        standings={"rank": 1},
    )
    card["sides"]["away"] = side_dict(
        "Beta",
        recent_form=_form(5, "LLLLL"),
        standings={"rank": 18},
    )
    # no h2h / injuries / referee / motivation / rest / split
    card["sides"]["home"]["injuries_suspensions"] = None
    card["sides"]["away"]["injuries_suspensions"] = None
    return card


def _card_grade_c_one_miss() -> dict:
    """n_miss==1 → C even if raw score would look high."""
    card = _base_football()
    card["competition"] = {"name": "Test League"}
    card["sides"]["home"] = side_dict(
        "Alpha",
        recent_form=_form(5, "WWWWW"),
        standings={"rank": 1},
        rest_days=3,
        injuries_suspensions=[],
        home_away_split={"home_wdl": "5-0-0", "away_wdl": None, "notes": None},
    )
    # form_away missing (n=0)
    card["sides"]["away"] = side_dict(
        "Beta",
        recent_form=_form(0, ""),
        standings={"rank": 10},
        rest_days=3,
    )
    card["h2h"] = {"n": 3, "summary": "even", "recent": [], "polarity": "even"}
    card["referee"] = {"name": "Ref", "cards_tendency": None, "notes": None}
    card["motivation_situational"] = {
        "tags": ["mid_table"],
        "notes": None,
        "final": False,
        "relegation_battle": False,
        "title_race": False,
    }
    return card


def _card_grade_d() -> dict:
    """n_miss>=2 or score<0.40 → D."""
    card = _base_football()
    card["competition"] = {"name": "Test League"}
    # both forms missing; standings missing → n_miss >= 2
    card["sides"]["home"] = side_dict("Alpha", recent_form=_form(0, ""))
    card["sides"]["away"] = side_dict("Beta", recent_form=_form(0, ""))
    return card


def _card_grade_f() -> dict:
    return empty_mic_skeleton("Ghost vs Void", sport="football", errors=["no_source"])


def test_grade_a_score_and_grade():
    card = _card_grade_a()
    score = coverage_score(card)
    assert score == pytest.approx(1.0, abs=0.02)
    assert critical_missing_count(card) == 0
    g = grade_card(card)
    assert g["grade"] == "A"
    assert g["score"] == pytest.approx(score, abs=0.02)


def test_grade_b_requires_n_miss_zero():
    card = _card_grade_b()
    score = coverage_score(card)
    assert score == pytest.approx(0.70, abs=0.02)
    assert critical_missing_count(card) == 0
    g = grade_card(card)
    assert g["grade"] == "B"
    assert g["score"] == pytest.approx(0.70, abs=0.02)
    # B requires n_miss==0 — inject one critical miss → not B
    card2 = _card_grade_b()
    card2["sides"]["away"]["recent_form"] = _form(0, "")
    assert critical_missing_count(card2) == 1
    g2 = grade_card(card2)
    assert g2["grade"] == "C"
    assert g2["grade"] != "B"


def test_grade_c_one_critical_missing():
    card = _card_grade_c_one_miss()
    assert critical_missing_count(card) == 1
    score = coverage_score(card)
    # may be high but grade forced to C
    assert score > 0.50
    g = grade_card(card)
    assert g["grade"] == "C"
    assert "form_away" in g["critical_missing"]


def test_grade_d_two_missing():
    card = _card_grade_d()
    assert critical_missing_count(card) >= 2
    score = coverage_score(card)
    g = grade_card(card)
    assert g["grade"] == "D"
    assert g["score"] == pytest.approx(score, abs=0.02)
    assert score == pytest.approx(0.175, abs=0.02)  # competition only


def test_grade_f_skeleton():
    card = _card_grade_f()
    g = grade_card(card)
    assert g["grade"] == "F"
    assert g["score"] == pytest.approx(0.0, abs=0.02)


def test_finalize_coverage_caps_fuzzy_at_c():
    card = _card_grade_a()
    card["extraction"]["match_confidence"] = "fuzzy"
    card["extraction"]["needs_review"] = True
    finalize_coverage(card)
    assert card["coverage"]["grade"] == "C"
    # exact keeps A
    card2 = _card_grade_a()
    card2["extraction"]["match_confidence"] = "exact"
    card2["extraction"]["needs_review"] = False
    finalize_coverage(card2)
    assert card2["coverage"]["grade"] == "A"


def test_validate_mic_shape():
    card = empty_mic_skeleton("A vs B")
    assert validate_mic_shape(card) == []
    assert "missing:match" in validate_mic_shape({"schema_version": 1})


def test_tennis_critical_keys_form_or_rank():
    card = empty_mic_skeleton("Player A vs Player B", sport="tennis", errors=[])
    card["extraction"]["primary_method"] = "test"
    card["extraction"]["errors"] = []
    card["competition"] = {"name": "ATP 250"}
    card["sides"]["home"] = side_dict("Player A", standings={"rank": 12})
    card["sides"]["away"] = side_dict("Player B", standings={"rank": 40})
    assert key_credit(card, "form_or_rank_home") == 1.0
    assert key_credit(card, "form_or_rank_away") == 1.0
    assert critical_missing_count(card) == 0
    score = coverage_score(card)
    # critical only: 0.70
    assert score == pytest.approx(0.70, abs=0.02)
    assert grade_card(card)["grade"] == "B"


def test_esports_default_sets():
    card = empty_mic_skeleton("Team X vs Team Y", sport="esports", errors=[])
    card["extraction"] = {
        "primary_method": "stub",
        "errors": ["parser_not_implemented"],
        "needs_review": True,
        "match_confidence": "none",
        "fallbacks_used": [],
        "exa_used": False,
        "duration_ms": 0,
    }
    g = grade_card(card)
    assert g["grade"] in ("F", "D")  # skeleton unusable → F preferred
