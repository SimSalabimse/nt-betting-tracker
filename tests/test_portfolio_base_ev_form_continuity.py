"""PR2: base_ev + explore gate + form_continuity soft-reject via portfolio."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import ev_after_haircut
from nt.form_continuity import form_continuity_penalty
from nt.learning import learning_adjustments
from nt.portfolio import Candidate, Recommendation, build_portfolio, compose_soft_sort_ev

# Verbatim fixture strings (design / live ledger SSOT)
MATCH = "Milwaukee Brewers vs Colorado Rockies"
PRIOR_SEL = (
    "Handikap 2-veis -1.5 (inkludert ekstra innings): Milwaukee Brewers -1.5"
)
CAND_SEL = "Handikap 2-veis -2.5: Colorado Rockies +2.5"
PRIOR_ODDS = 1.79
CAND_ODDS = 1.75


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


def _cfg(*, fc_enabled: bool = True, weak_flip_action: str = "soft_reject"):
    return {
        "norsk_tipping": {"min_stake_nok": 10},
        "selection": {
            "probability_haircut": 0.05,
            "standard_min_ev": 0.02,
            "strong_min_ev": 0.015,
            "absolute_min_ev": 0.01,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.08,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {
                "min_sample": 15,
                "bad_roi_below": -0.10,
                "extra_ev_required": 0.05,
            },
            "band_prior_boost": {},
            "min_research_sources": {"default": 4, "grade_A": 8, "high_odds": 10},
            "grade_c_placeable": True,
            "grade_c_require_core_reason": True,
            "grade_c_min_sources": 4,
        },
        "learning": {
            "enabled": True,
            "diversification": {
                "max_per_sport": 3,
                "max_per_market": 3,
                "max_per_band": 4,
                "max_per_match": 1,
                "max_football_per_round": 2,
                "min_non_football_per_round": 0,
                "prefer_explore_first": False,
                "explore_min_n": 0,
                "explore_max_n": 14,
                "explore_ev_boost": 0.018,
                "explore_virgin_ev_boost": 0.022,
                "explore_stake_floor": 0.92,
                "explore_min_roi": -0.15,
                "explore_min_ev": 0.012,
                "explore_base_ev_min": 0.005,
                "sort": {
                    "similar_penalty_weight": 1.0,
                    "macro_underrep_bonus": 0.0,
                    "explore_tiebreak": False,
                    "continuity_penalty_weight": 1.0,
                },
                "form_continuity": {
                    "enabled": fc_enabled,
                    "live_ledger_only": True,
                    "anchor_scan_limit": 30,
                    "max_hours": 48,
                    "max_games": 2,
                    "heavy_fav_max_odds": 2.10,
                    "include_pending_anchors": True,
                    "base_penalty": 0.035,
                    "pending_penalty": 0.015,
                    "weak_extra_penalty": 0.025,
                    "convincing_win_mult": 1.25,
                    "strong_flip_min_ev": 0.06,
                    "weak_flip_action": weak_flip_action,
                    "heavy_line_by_sport": {
                        "baseball": 1.5,
                        "default": 1.5,
                    },
                },
                "ranking_gap_hc": {"enabled": False},
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
        "combos": {"enabled": False},
    }


def _pack(p: float = 0.68, summary: str = "public on fav; +2.5 is easier") -> dict:
    # Full v5-ish pack so FEH/odds-band gates grade ≥ B (continuity wiring under test).
    sources = [
        {
            "url": f"https://example.com/{i}",
            "takeaway": "stats edge note for unit test pack",
            "kind": "stats",
        }
        for i in range(8)
    ]
    summary_s = summary if len(summary) >= 20 else (summary + " supporting research text")
    return {
        "match": MATCH,
        "selection": CAND_SEL,
        "p_model": p,
        "summary": summary_s,
        "failure_modes": "test",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "expected full strength for unit test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
    }


def _brewers_win_row(*, hours_ago: float = 12.0, **extra):
    now = datetime.now(timezone.utc)
    ts = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d")
    row = {
        "bet_id": "brewers-win-1",
        "match": MATCH,
        "selection": PRIOR_SEL,
        "sport": "baseball",
        "market_type": "Handikap 2-veis",
        "market_family": "baseball_handicap",
        "result": "Win",
        "decimal_odds": str(PRIOR_ODDS),
        "odds": str(PRIOR_ODDS),
        "updated_at": ts,
        "created_at": ts,
        "date": day,
        "notes": "",
        "source": "live",
    }
    row.update(extra)
    return row


def _rockies_cand(*, p_model: float = 0.68, notes: str = "public on fav; +2.5 is easier"):
    return Candidate(
        date="2026-07-26",
        match=MATCH,
        selection=CAND_SEL,
        decimal_odds=CAND_ODDS,
        sport="baseball",
        market_type="Handikap 2-veis",
        p_model=p_model,
        evidence=_pack(p_model, notes),
        notes=notes,
    )


def _empty_learning():
    """Learning blob with no sport/market sample → virgin explore boosts."""
    return {
        "enabled": True,
        "sports": {},
        "markets": {},
        "bands": {},
        "updated_at": "2026-07-26T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# learning_adjustments split
# ---------------------------------------------------------------------------
def test_learning_adjustments_splits_explore_and_other():
    cfg = _cfg()
    learn = _empty_learning()
    adj = learning_adjustments(
        learn,
        sport="baseball",
        market="Handikap 2-veis",
        selection=CAND_SEL,
        band="1.6-1.9",
        enabled=True,
        learn_cfg=cfg["learning"],
    )
    assert "ev_boost_other" in adj
    assert "ev_boost_explore" in adj
    assert abs(adj["ev_boost"] - (adj["ev_boost_other"] + adj["ev_boost_explore"])) < 1e-9
    assert adj["explored"] is True
    assert adj["ev_boost_explore"] > 0
    # No settled sample → no sport/market other boost
    assert adj["ev_boost_other"] == 0.0


# ---------------------------------------------------------------------------
# Brewers → Rockies soft-reject through build_portfolio
# ---------------------------------------------------------------------------
def test_brewers_rockies_soft_reject_not_in_scored_or_picked():
    cfg = _cfg(fc_enabled=True)
    hist = [_brewers_win_row(hours_ago=10.0)]
    # p_model high enough to clear standard_min_ev without explore
    # haircut 0.05, odds 1.75 → need (p-0.05)*1.75 - 1 >= 0.02 → p >= ~0.63
    cand = _rockies_cand(p_model=0.68, notes="public on fav; +2.5 is easier")
    picked, rejects = build_portfolio(
        cfg, [cand], _phase(), _risk(), hist, learning=_empty_learning()
    )
    assert not any(r.selection == CAND_SEL for r in picked)
    fc_rejects = [
        r
        for r in rejects
        if str(r.get("reason") or "").startswith("form_continuity:")
        or r.get("form_continuity")
    ]
    assert fc_rejects, f"expected form_continuity reject; got {rejects}"
    assert str(fc_rejects[0]["reason"]).startswith("form_continuity:")
    assert fc_rejects[0].get("form_continuity") is True
    # true EV present and not rewritten to sort-only
    assert "ev" in fc_rejects[0]


def test_rec_ev_invariant_through_annotate():
    """When demote_only, candidate stays scored; rec.ev equals pre-annotate place EV."""
    cfg = _cfg(fc_enabled=True, weak_flip_action="demote_only")
    hist = [_brewers_win_row(hours_ago=8.0)]
    cand = _rockies_cand(p_model=0.70, notes="easier line; public chalk")
    # Capture base path: score with learning that has no explore so place EV stable
    learn = {
        "enabled": True,
        "sports": {
            "baseball": {
                "n": 20,
                "ev_boost": 0.0,
                "stake_mult": 1.0,
                "roi_blended": 0.05,
                "blocked": False,
            }
        },
        "markets": {
            "handicap": {
                "n": 20,
                "ev_boost": 0.0,
                "stake_mult": 1.0,
                "roi_blended": 0.05,
                "blocked": False,
                "status": "ok",
            }
        },
        "bands": {},
    }
    picked, rejects = build_portfolio(
        cfg, [cand], _phase(), _risk(), hist, learning=learn
    )
    # demote_only → should not soft-reject
    assert not any(
        str(r.get("reason") or "").startswith("form_continuity:") for r in rejects
    )
    assert len(picked) == 1
    rec = picked[0]
    # place EV must equal score-time place EV (sort_ev may be lower)
    haircut_ev = ev_after_haircut(0.70, CAND_ODDS, 0.05)
    assert rec.base_ev is not None
    assert abs(float(rec.base_ev) - float(haircut_ev)) < 1e-4
    assert rec.ev == round(float(rec.base_ev) + float(rec.explore_boost_applied), 4)
    assert rec.sort_ev is not None
    assert float(rec.sort_ev) < float(rec.ev)  # continuity pen applied to sort only
    assert (rec.form_continuity_reason or "").startswith("form_continuity:")
    assert rec.reject_reason == ""


def test_explore_withheld_when_base_ev_below_min():
    """base_ev ≤ explore_base_ev_min → boost withheld; explore_min_ev floor not used."""
    cfg = _cfg(fc_enabled=False)
    # Force low base EV: p such that haircut_ev just under / around 0
    # (p-0.05)*1.90 - 1. If p=0.55 → 0.5*1.90-1 = -0.05
    odds = 1.90
    p = 0.55
    haircut = 0.05
    base = ev_after_haircut(p, odds, haircut)
    assert base < 0.005

    cand = Candidate(
        date="2026-07-26",
        match="Virgin Sport A vs Virgin Sport B",
        selection="Virgin Sport A to Win",
        decimal_odds=odds,
        sport="darts",  # thin / virgin
        market_type="Match result",
        p_model=p,
        evidence=_pack(p, "thin virgin sport edge for unit test pack"),
        notes="explore candidate",
    )
    learn = _empty_learning()
    # Confirm learning would give explore boost
    adj = learning_adjustments(
        learn,
        sport="darts",
        market="Match result",
        selection=cand.selection,
        band="1.8-2.2",
        enabled=True,
        learn_cfg=cfg["learning"],
    )
    assert adj["ev_boost_explore"] > 0
    assert adj["explored"] is True

    picked, rejects = build_portfolio(
        cfg, [cand], _phase(), _risk(), [], learning=learn
    )
    # Without explore rescue, EV stays at base (< min 0.02) → reject
    assert not picked
    ev_rejects = [r for r in rejects if "EV" in str(r.get("reason") or "")]
    assert ev_rejects, f"expected EV reject; got {rejects}"
    # Must not have been rescued by explore floor (0.012)
    reason = str(ev_rejects[0]["reason"])
    assert "0.012" not in reason  # explore_min_ev not applied
    # learning boost reported as zero / withheld on reject path
    assert float(ev_rejects[0].get("learning_ev_boost") or 0) == 0.0
    # Explicit: rejected place EV is base (no explore rescue)
    assert "ev" in ev_rejects[0]
    assert "base_ev" in ev_rejects[0]
    assert float(ev_rejects[0]["ev"]) < 0.005 + 1e-6
    assert float(ev_rejects[0]["base_ev"]) < 0.005 + 1e-6
    assert abs(float(ev_rejects[0]["ev"]) - float(ev_rejects[0]["base_ev"])) < 1e-6


def test_explore_inflated_still_soft_rejects_weak_flip():
    """
    KD15: strong_flip S3 must use base_ev, never post-explore place EV.

    Distinguishing fixture (review Issue 1):
      - base_ev < 0.06 ≤ place_ev (after explore boost)
      - grade B
      - exactly one other strong signal (S4 structural), so:
          correct wiring (base_ev) → 1 signal → still soft_reject
          wrong wiring (place EV)  → S3+S4 → strong_flip escape (would place)
    """
    cfg = _cfg(fc_enabled=True)
    hist = [_brewers_win_row(hours_ago=6.0)]
    # p=0.64 → haircut_ev ≈ 0.0325; virgin explore ~0.04 → place ≥ 0.06
    # S4 only (no S1/S2; no weak-phrase requirement for this distinguishing case)
    notes_s4 = "starting pitcher rest advantage for series game two"
    cand = _rockies_cand(p_model=0.64, notes=notes_s4)
    learn = _empty_learning()  # virgin explore inflates place EV
    adj = learning_adjustments(
        learn,
        sport="baseball",
        market="Handikap 2-veis",
        selection=CAND_SEL,
        band="1.6-1.9",
        enabled=True,
        learn_cfg=cfg["learning"],
    )
    explore = float(adj["ev_boost_explore"])
    assert explore > 0
    haircut_ev = ev_after_haircut(0.64, CAND_ODDS, 0.05)
    place_if_explore = haircut_ev + explore
    assert haircut_ev + 1e-12 < 0.06, f"base must be < strong_flip_min_ev; got {haircut_ev}"
    assert place_if_explore + 1e-12 >= 0.06, (
        f"place EV must clear strong_flip_min_ev when explore applied; "
        f"got place={place_if_explore} explore={explore}"
    )

    # Library-level: wrong S3 input (place EV) would escape with S4; base_ev does not
    pen_wrong, _why_wrong, meta_wrong = form_continuity_penalty(
        {
            "match": MATCH,
            "selection": CAND_SEL,
            "sport": "baseball",
            "market_type": "Handikap 2-veis",
            "notes": notes_s4,
            "grade": "B",
            "base_ev": place_if_explore,  # incorrect: post-explore
        },
        hist,
        cfg["learning"]["diversification"]["form_continuity"],
        base_ev=place_if_explore,
        grade="B",
        notes=notes_s4,
    )
    assert meta_wrong.get("strong_flip_evidence") is True, (
        "fixture invalid: place EV + S4 must count as strong_flip (≥2 signals)"
    )
    assert meta_wrong.get("soft_reject") is False

    pen_ok, _why_ok, meta_ok = form_continuity_penalty(
        {
            "match": MATCH,
            "selection": CAND_SEL,
            "sport": "baseball",
            "market_type": "Handikap 2-veis",
            "notes": notes_s4,
            "grade": "B",
            "base_ev": haircut_ev,
        },
        hist,
        cfg["learning"]["diversification"]["form_continuity"],
        base_ev=haircut_ev,
        grade="B",
        notes=notes_s4,
    )
    assert meta_ok.get("strong_flip_evidence") is False
    assert meta_ok.get("soft_reject") is True
    assert pen_ok > 0

    picked, rejects = build_portfolio(
        cfg, [cand], _phase(), _risk(), hist, learning=learn
    )
    assert not any(r.selection == CAND_SEL for r in picked), (
        "portfolio must soft_reject when wiring uses base_ev (not place EV)"
    )
    fc_rejects = [
        r for r in rejects if str(r.get("reason") or "").startswith("form_continuity:")
    ]
    assert fc_rejects
    assert fc_rejects[0].get("base_ev") is not None
    assert float(fc_rejects[0]["base_ev"]) < 0.06
    # place EV may be explore-inflated on reject payload; base_ev must stay low
    if fc_rejects[0].get("ev") is not None:
        assert float(fc_rejects[0]["ev"]) >= float(fc_rejects[0]["base_ev"]) - 1e-9


def test_sort_ev_composes_similar_lessons_and_continuity_pens():
    """Regression: named pens sum; none is overwritten (merge-safe composite)."""
    true_ev = 0.100
    se = compose_soft_sort_ev(
        true_ev,
        pen_similar=0.020,
        pen_lessons=0.008,
        pen_form_continuity=0.035,
        similar_weight=1.0,
        continuity_weight=1.0,
        macro_bonus=0.0,
    )
    assert abs(se - (0.100 - 0.020 - 0.008 - 0.035)) < 1e-9

    # Weights apply independently
    se_w = compose_soft_sort_ev(
        true_ev,
        pen_similar=0.020,
        pen_lessons=0.0,
        pen_form_continuity=0.035,
        similar_weight=0.5,
        continuity_weight=2.0,
        macro_bonus=0.004,
    )
    expected = 0.100 - (0.020 * 0.5) - (0.035 * 2.0) + 0.004
    assert abs(se_w - expected) < 1e-9

    # Continuity alone still works (this branch may lack similar_recent module)
    se_fc = compose_soft_sort_ev(
        true_ev,
        pen_form_continuity=0.035,
        continuity_weight=1.0,
    )
    assert abs(se_fc - 0.065) < 1e-9

    # demote_only portfolio path: form_continuity pen lands on sort_ev without wiping peers
    cfg = _cfg(fc_enabled=True, weak_flip_action="demote_only")
    hist = [_brewers_win_row(hours_ago=8.0)]
    cand = _rockies_cand(p_model=0.70, notes="easier line; public chalk")
    learn = {
        "enabled": True,
        "sports": {
            "baseball": {
                "n": 20,
                "ev_boost": 0.0,
                "stake_mult": 1.0,
                "roi_blended": 0.05,
                "blocked": False,
            }
        },
        "markets": {},
        "bands": {},
    }
    picked, _rejects = build_portfolio(
        cfg, [cand], _phase(), _risk(), hist, learning=learn
    )
    assert len(picked) == 1
    rec = picked[0]
    # Continuity pen present
    assert rec.sort_ev is not None
    assert float(rec.sort_ev) < float(rec.ev)
    # Compose helper matches annotate when only continuity pen fires
    expected_sort = compose_soft_sort_ev(
        float(rec.ev),
        pen_form_continuity=float(rec.ev) - float(rec.sort_ev),
        continuity_weight=1.0,
    )
    # pen already includes weight in delta; recompute from form_continuity default 0.035+0.025
    # (weak demote_only adds weak_extra): just check delta > 0 and ev unchanged
    assert rec.ev == round(float(rec.base_ev or 0) + float(rec.explore_boost_applied), 4)
    assert (rec.form_continuity_reason or "").startswith("form_continuity:")
    assert expected_sort  # sanity non-zero path


def test_base_ev_fields_on_recommendation_when_not_rejected():
    cfg = _cfg(fc_enabled=False)
    cand = Candidate(
        date="2026-07-26",
        match="Alpha FC vs Beta FC",
        selection="Alpha FC to Win",
        decimal_odds=1.80,
        sport="football",
        market_type="HUB",
        p_model=0.72,
        evidence=_pack(0.72, "clear core reason with form and venue support"),
        notes="solid short fav",
    )
    learn = {
        "enabled": True,
        "sports": {
            "football": {
                "n": 30,
                "ev_boost": 0.01,
                "stake_mult": 1.0,
                "roi_blended": 0.08,
                "blocked": False,
            }
        },
        "markets": {},
        "bands": {},
    }
    picked, _rejects = build_portfolio(
        cfg, [cand], _phase(), _risk(), [], learning=learn
    )
    assert len(picked) == 1
    rec = picked[0]
    assert isinstance(rec, Recommendation)
    assert rec.base_ev is not None
    assert rec.evidence_snapshot is not None
    assert rec.sort_ev is not None
    assert abs(float(rec.ev) - (float(rec.base_ev) + float(rec.explore_boost_applied))) < 1e-4
    # sport has sample (n=30) but market may still be virgin → explore only if base_ev clears gate
    if rec.explore_boost_applied > 0:
        assert rec.explore is True
        assert float(rec.base_ev) + 1e-12 >= 0.005
