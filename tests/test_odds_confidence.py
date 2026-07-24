"""Sliding odds-band confidence gates (1.40ÔÇô2.60)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_confidence import (
    BAND_A,
    BAND_B,
    BAND_BELOW,
    BAND_C,
    BAND_D,
    BAND_HIGH,
    classify_odds_confidence_band,
    detect_h2h_signal,
    evaluate_odds_band_gates,
)
from nt.reasoning_chain import build_chain_from_near_miss, build_chain_from_pick
from nt.portfolio import Recommendation


def _sources(n: int) -> list[dict]:
    return [{"name": f"src{i}", "url": f"https://ex.example/{i}"} for i in range(n)]


def _ev_strong(**kwargs) -> dict:
    """Strong multi-source pack with H2H + form edge (Band A candidate)."""
    base = {
        "summary": (
            "Clear short-price edge: ranking gap and positive H2H favour this side; "
            "market mispriced the favourite after confirmed lineup."
        ),
        "h2h": {"edge": 0.12, "note": "leads H2H 4-1"},
        "form": "Won last 5; ranking seed advantage",
        "sources": _sources(10),
        "p_model": 0.72,
    }
    base.update(kwargs)
    return base


def _ev_soft_mid() -> dict:
    """Previous soft Grade-B mid-odds underdog: thin process / explore-style."""
    return {
        "summary": "Mid-odds underdog explore look.",
        "sources": _sources(6),
        "p_model": 0.55,
    }


def test_classify_bands():
    assert classify_odds_confidence_band(1.35) == BAND_BELOW
    assert classify_odds_confidence_band(1.40) == BAND_A
    assert classify_odds_confidence_band(1.59) == BAND_A
    assert classify_odds_confidence_band(1.60) == BAND_B
    assert classify_odds_confidence_band(1.84) == BAND_B
    assert classify_odds_confidence_band(1.85) == BAND_C
    assert classify_odds_confidence_band(2.29) == BAND_C
    assert classify_odds_confidence_band(2.30) == BAND_D
    assert classify_odds_confidence_band(2.60) == BAND_D
    assert classify_odds_confidence_band(2.61) == BAND_HIGH


def test_band_a_short_favourite_requires_strong_evidence():
    """Short favourite @1.50: Grade B alone fails; strong A + H2H/form passes."""
    thin = evaluate_odds_band_gates(
        odds=1.50,
        grade="B",
        evidence={
            "summary": "Solid favourite.",
            "sources": _sources(8),
        },
        selection="Vinner: Seed Player",
    )
    assert thin.band_id == BAND_A
    assert thin.ok is False
    assert any("grade" in f.lower() for f in thin.failures)

    weak_a = evaluate_odds_band_gates(
        odds=1.50,
        grade="A",
        evidence={
            "summary": "Favourite looks good.",
            "sources": _sources(8),
        },
        selection="Vinner: Seed Player",
    )
    assert weak_a.ok is False
    assert any("h2h" in f.lower() or "rank" in f.lower() for f in weak_a.failures)

    strong = evaluate_odds_band_gates(
        odds=1.50,
        grade="A",
        evidence=_ev_strong(),
        selection="Vinner: Seed Player",
    )
    assert strong.ok is True
    assert strong.stake_mult < 1.0
    assert strong.min_ev is not None and strong.min_ev >= 0.03
    assert strong.explore_allowed is False


def test_band_c_soft_underdog_rejected_without_support():
    """Previous soft 1.90 underdog / explore-style Grade B should fail Band C bar."""
    soft = evaluate_odds_band_gates(
        odds=1.90,
        grade="B",
        evidence=_ev_soft_mid(),
        selection="Underdog +1.5",
    )
    assert soft.band_id == BAND_C
    assert soft.ok is False
    # Missing H2H check and/or thin support
    assert soft.failures
    assert any(
        "h2h" in f.lower()
        or "support" in f.lower()
        or "matchup" in f.lower()
        or "core" in f.lower()
        for f in soft.failures
    )


def test_band_c_solid_b_with_h2h_and_support_passes():
    solid = evaluate_odds_band_gates(
        odds=1.95,
        grade="B",
        evidence={
            "summary": (
                "Clear core: home control + under script; H2H 3-1 last meetings "
                "favour low totals; recent form both sides cagey."
            ),
            "h2h": "3-1 H2H under 2.5 in last 4",
            "form": "Both last 5 avg 1.8 goals",
            "sources": _sources(7),
        },
        selection="Under 2.5",
    )
    assert solid.band_id == BAND_C
    assert solid.ok is True
    assert solid.explore_allowed is True


def test_band_b_explore_disabled():
    r = evaluate_odds_band_gates(
        odds=1.72,
        grade="B",
        evidence={
            "summary": "Solid core reason with form and ranking gap vs opponent.",
            "form": "Won last 4",
            "ranking": "seed vs qualifier",
            "sources": _sources(7),
        },
        selection="Vinner: Fav",
    )
    assert r.band_id == BAND_B
    assert r.explore_allowed is False


def test_below_floor_rejects_non_exceptional():
    r = evaluate_odds_band_gates(
        odds=1.30,
        grade="B",
        evidence=_ev_strong(),
        selection="Vinner: Big Fav",
    )
    assert r.band_id == BAND_BELOW
    assert r.ok is False


def test_high_odds_defers():
    r = evaluate_odds_band_gates(
        odds=2.80,
        grade="B",
        evidence=_ev_soft_mid(),
        selection="Long shot",
    )
    assert r.band_id == BAND_HIGH
    assert r.ok is True  # caller applies high-odds grade/EV rules


def test_underdog_hc_negative_h2h_rejects():
    r = evaluate_odds_band_gates(
        odds=2.40,
        grade="B",
        evidence={
            "summary": "Underdog HC with venue edge and form support.",
            "h2h": "never beaten this opponent; 0-5 in H2H",
            "form": "recent form mixed",
            "sources": _sources(7),
        },
        selection="Handikap +2.5: Underdog Team +2.5",
    )
    assert r.band_id == BAND_D
    assert r.ok is False
    assert any("h2h" in f.lower() or "never" in f.lower() or "negative" in f.lower() for f in r.failures)


def test_reasoning_chain_embeds_odds_confidence():
    rec = Recommendation(
        match="A vs B",
        selection="Vinner: A",
        decimal_odds=1.55,
        stake_nok=10.0,
        ev=0.04,
        grade="A",
        odds_band="1.5-1.8",
        sport="tennis",
        market_type="ML",
        p_model=0.72,
        notes="test",
        odds_confidence_band=BAND_A,
        odds_confidence={
            "ok": True,
            "band_id": BAND_A,
            "band_label": "A Short high-confidence (1.40ÔÇô1.60)",
            "passes": ["grade_ok:A", "h2h_or_rank_form:h2h_pos"],
            "failures": [],
            "min_ev": 0.035,
            "stake_mult": 0.8,
        },
    )
    chain = build_chain_from_pick(rec, haircut=0.03)
    assert chain["odds_confidence_band"] == BAND_A
    assert chain["odds_confidence"]["ok"] is True

    miss = build_chain_from_near_miss(
        {
            "match": "C vs D",
            "selection": "Underdog ML",
            "decimal_odds": 1.90,
            "reason": "odds_band:Band C requires supporting evidence",
            "grade": "B",
            "ev": 0.03,
            "near_miss": True,
            "odds_confidence_band": BAND_C,
            "odds_confidence": {
                "ok": False,
                "band_id": BAND_C,
                "failures": ["Band C requires supporting evidence beyond bare mid-odds/explore"],
            },
        }
    )
    assert miss["odds_confidence_band"] == BAND_C
    assert miss["odds_confidence"]["ok"] is False


def test_detect_h2h_prefers_feh_polarity():
    """FEH h2h polarity overrides regex blob (mixed string is not positive)."""
    pack = {
        "summary": "leads H2H positive edge dominat favour",  # would look positive to regex
        "h2h": {"checked": True, "edge": "mixed_competitive", "summary": "mixed"},
    }
    # Without FEH: normalize_h2h path → mixed not positive
    h = detect_h2h_signal(pack)
    assert h["positive"] is False
    assert h.get("source") in ("normalize_h2h", "feh")

    feh = {
        "feh_version": 1,
        "h2h": {
            "checked": True,
            "positive": False,
            "negative": False,
            "mixed": True,
            "polarity": "mixed",
        },
    }
    h2 = detect_h2h_signal(pack, feh=feh)
    assert h2["source"] == "feh"
    assert h2["positive"] is False
    assert h2["checked"] is True

    feh_pos = {
        "feh_version": 1,
        "h2h": {
            "checked": True,
            "positive": True,
            "negative": False,
            "polarity": "positive",
        },
    }
    h3 = detect_h2h_signal({"summary": "no h2h words"}, feh=feh_pos)
    assert h3["source"] == "feh"
    assert h3["positive"] is True


def test_band_cannot_bypass_feh_hard_reject():
    """Bands cannot place FEH hard-reject / grade F candidates."""
    strong = _ev_strong()
    r = evaluate_odds_band_gates(
        odds=1.95,
        grade="B",
        evidence=strong,
        selection="Under 2.5",
        feh={
            "feh_version": 1,
            "hard_reject": True,
            "final_grade_suggestion": "F",
            "reject_codes": ["FEH_ANTI_SOFT_UNDERDOG"],
            "h2h": {"checked": True, "positive": False, "negative": False},
        },
    )
    assert r.ok is False
    assert r.band_id == "feh_blocked"
    assert any("FEH" in f for f in r.failures)
