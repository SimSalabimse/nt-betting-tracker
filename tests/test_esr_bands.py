"""PR3 ESR: Band A soft demote, UD H2H soft when flag false, K16 high-odds boundary."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_confidence import (
    BAND_A,
    BAND_D,
    BAND_HIGH,
    classify_odds_confidence_band,
    evaluate_odds_band_gates,
    odds_confidence_cfg,
)


def _sources(n: int) -> list[dict]:
    return [{"name": f"src{i}", "url": f"https://ex.example/{i}"} for i in range(n)]


def _core_summary_no_rank_form() -> str:
    """Core reason without H2H/rank/form keywords so soft-demote path is exercised."""
    return (
        "Clear core: this side is the justified short price after lineup "
        "confirmation and market mispricing of the opponent."
    )


def test_short_fav_grade_b_soft_demote_placeable():
    """Favourite ML @1.55 Grade B, 4 sources, core reason, thin H2H → soft demote ok."""
    r = evaluate_odds_band_gates(
        odds=1.55,
        grade="B",
        evidence={
            "summary": _core_summary_no_rank_form(),
            "sources": _sources(4),
            "p_model": 0.68,
        },
        selection="Vinner: Seed Player",
    )
    assert r.band_id == BAND_A
    assert r.ok is True, (r.failures, r.passes)
    assert any("soft_missing_matchup" in p for p in r.passes), r.passes
    # stake_mult ≈ band A 0.95 * soft_missing 0.85
    assert abs(r.stake_mult - 0.95 * 0.85) < 1e-6


def test_short_fav_no_core_no_h2h_still_rejects():
    """Same short fav without core reason and without H2H/rank → hard fail."""
    r = evaluate_odds_band_gates(
        odds=1.55,
        grade="B",
        evidence={
            "summary": "thin",  # < 20 chars → no core reason
            "sources": _sources(4),
        },
        selection="Vinner: Seed Player",
    )
    assert r.band_id == BAND_A
    assert r.ok is False
    assert r.failures


def test_ud_h2h_hard_path_off_when_flag_false():
    """Soft UD HC @1.90 negative H2H, underdog_hc_negative_h2h_reject false → not rejected by path C."""
    # Explicit ESR cfg (defaults already false; pin for clarity)
    cfg = {
        "selection": {
            "odds_confidence": {
                "underdog_hc_negative_h2h_reject": False,
            }
        }
    }
    r = evaluate_odds_band_gates(
        odds=1.90,
        grade="B",
        evidence={
            "summary": (
                "Underdog HC with venue edge and form support; "
                "H2H is historically poor but style matchup favours dog."
            ),
            "h2h": "never beaten this opponent; 0-5 in H2H",
            "form": "recent form strong last 5",
            "sources": _sources(5),
        },
        selection="Handikap +2.5: Underdog Team +2.5",
        cfg=cfg,
    )
    # Band C — may pass or fail on other bars; must NOT fail on negative H2H alone
    assert r.ok is True or not any(
        "negative" in f.lower() or "never" in f.lower() or "h2h" in f.lower()
        for f in r.failures
        if "checked" not in f.lower()
    )
    # Soft note path when band applies UD check
    if r.ok:
        assert not any("reject" in f.lower() and "h2h" in f.lower() for f in r.failures)


def test_ud_h2h_hard_path_on_when_flag_true_legacy():
    """Legacy mode: flag true still hard-rejects negative H2H on UD HC (Band D path)."""
    cfg = {
        "selection": {
            "odds_confidence": {
                "underdog_hc_negative_h2h_reject": True,
                "bands": {
                    "D": {
                        "underdog_hc_require_matchup": True,
                    }
                },
            }
        }
    }
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
        cfg=cfg,
    )
    assert r.band_id == BAND_D
    assert r.ok is False
    assert any(
        "h2h" in f.lower() or "never" in f.lower() or "negative" in f.lower()
        for f in r.failures
    )


def test_odds_2_50_band_d_not_high():
    """K16: odds exactly 2.50 = Band D only (usable_hi inclusive)."""
    assert classify_odds_confidence_band(2.50) == BAND_D
    assert classify_odds_confidence_band(2.50, {}) == BAND_D


def test_odds_2_51_is_high_odds():
    """K16: odds 2.51+ = high-odds path (strict > usable_hi / thr)."""
    assert classify_odds_confidence_band(2.51) == BAND_HIGH
    assert classify_odds_confidence_band(2.51, {}) == BAND_HIGH

    r = evaluate_odds_band_gates(
        odds=2.51,
        grade="B",
        evidence={"summary": "Longer price look.", "sources": _sources(4)},
        selection="Long shot ML",
    )
    assert r.band_id == BAND_HIGH
    assert r.ok is True  # defer to portfolio high-odds rules


def test_portfolio_high_odds_strict_inequality():
    """
    Portfolio K16 boundary: high = odds > thr (not >=).
    2.50 is Band D only; 2.51 is high-odds.
    """
    thr = 2.5
    assert (2.50 > thr) is False
    assert (2.51 > thr) is True
    # Align with production high_odds_threshold default
    from nt.config import load_config

    cfg = load_config()
    thr_live = float((cfg.get("selection") or {}).get("high_odds_threshold") or 2.5)
    assert thr_live == 2.5
    oc = odds_confidence_cfg(cfg)
    assert float(oc["usable_hi"]) == thr_live
