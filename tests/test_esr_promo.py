"""PR3 ESR: edge-seeking promotion ranking + cov_prefer_natural token."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.light_research import (
    LightRecord,
    promotion_score,
    promotion_score_components,
    tiers_cfg,
)


def _esr_cfg(**tier_over) -> dict:
    tiers = {
        "engine_deep_queue": True,
        "short_chalk_odds": 1.50,
        "preferred_odds_lo": 1.40,
        "preferred_odds_hi": 2.80,
        "alt_preferred_odds_lo": 1.40,
        "promo_mid_band_boost": 8.0,
        "promo_mid_band_lo": 1.85,
        "promo_mid_band_hi": 2.40,
        "promo_alt_boost": 12.0,
        "promo_short_chalk_penalty": -12.0,
        "promo_preferred_boost": 0.0,
        "promo_short_main_penalty": 0.0,
        "promo_near_pref_boost": 8.0,
        "promo_require_signal_for_family_boost": True,
        "promo_fav_hc_boost": 8.0,
        "promo_natural_total_boost": 12.0,
        "soft_value_min_rel": 0.08,
    }
    tiers.update(tier_over)
    return {
        "research": {"tiers": tiers, "coverage_floor": {"enabled": False}},
        "selection": {"probability_haircut": 0.03},
    }


def _rec(
    match: str,
    selection: str,
    odds: float,
    *,
    family: str,
    sport: str = "football",
    prior_ev: float | None = None,
    reason: str = "",
) -> LightRecord:
    return LightRecord(
        match=match,
        selection=selection,
        sport=sport,
        decimal_odds=odds,
        odds_band="1.4-2.2",
        market_family=family,
        verdict="pass",
        has_p_model=False,
        promote_to_deep=False,
        source="auto",
        prior_ev=prior_ev,
        prior_available=prior_ev is not None,
        reason=reason,
        rough_ev_note="",
    )


def test_short_fav_with_prior_ev_ranks_above_bare_hc_dog():
    """
    Acceptance: clear short favourite @1.55 with prior_ev > 0 ranks above
    bare soft +HC dog @1.95 with no notes / no prior_ev / no soft_value.
    """
    cfg = _esr_cfg()
    short_fav = _rec(
        "Fav vs Dog",
        "Vinner: Fav",
        1.55,
        family="ml",
        sport="tennis",
        prior_ev=0.06,
        reason="form and ranking edge",
    )
    bare_dog = _rec(
        "Fav vs Dog",
        "Handikap +1.5: Dog +1.5",
        1.95,
        family="handicap",
        sport="tennis",
        prior_ev=None,
        reason="",
    )
    sf = promotion_score_components(short_fav, cfg)
    bd = promotion_score_components(bare_dog, cfg)
    assert sf["total"] > bd["total"], (sf, bd)
    assert "prior_ev" in sf["components"]
    # Bare HC without signal must not get family handicap boost
    assert "handicap" not in bd["components"]
    assert promotion_score(short_fav, cfg) > promotion_score(bare_dog, cfg)


def test_bare_hc_gets_boost_when_prior_signal_present():
    """Signal-gated family boost: HC with prior_ev > 0 receives handicap component."""
    cfg = _esr_cfg()
    with_signal = _rec(
        "A vs B",
        "Handikap +1.5: B +1.5",
        1.95,
        family="handicap",
        prior_ev=0.04,
        reason="form edge",
    )
    bare = _rec(
        "A vs B",
        "Handikap +1.5: B +1.5",
        1.95,
        family="handicap",
    )
    w = promotion_score_components(with_signal, cfg)
    b = promotion_score_components(bare, cfg)
    assert w["components"].get("handicap", 0) == 12.0
    assert "handicap" not in b["components"]
    assert w["total"] > b["total"]


def test_cov_prefer_natural_fires_when_prefer_includes_natural_totals():
    """prefer token natural_totals is not a no-op — sets cov_prefer_natural."""
    cfg = _esr_cfg()
    total = _rec(
        "Home vs Away",
        "Over 2.5",
        1.88,
        family="totals_over",
    )
    ov = {
        "active": True,
        "target_odds_band": "1.40-2.80",
        "prefer": ["alt_totals", "handicaps", "period", "natural_totals"],
        "weight_boost": 10.0,
    }
    br = promotion_score_components(total, cfg, coverage_overlay=ov)
    assert br["components"].get("cov_prefer_natural") == 10.0

    # Without natural_totals in prefer → no component
    ov2 = {
        "active": True,
        "target_odds_band": "1.40-2.80",
        "prefer": ["handicaps", "period"],
    }
    br2 = promotion_score_components(total, cfg, coverage_overlay=ov2)
    assert "cov_prefer_natural" not in br2["components"]


def test_cov_prefer_natural_not_on_handicap():
    """natural_totals prefer must not fire on HC selections."""
    cfg = _esr_cfg()
    hc = _rec("H vs A", "Handikap -1.5: H -1.5", 1.90, family="handicap")
    ov = {
        "active": True,
        "target_odds_band": "1.40-2.80",
        "prefer": ["natural_totals"],
    }
    br = promotion_score_components(hc, cfg, coverage_overlay=ov)
    assert "cov_prefer_natural" not in br["components"]


def test_promo_preferred_boost_default_zero():
    """preferred identity no longer injects +25 hardcode."""
    t = tiers_cfg({})
    assert float(t["promo_preferred_boost"]) == 0.0
    cfg = _esr_cfg()
    rec = _rec("A vs B", "Vinner: A", 2.00, family="ml")
    br = promotion_score_components(rec, cfg)
    assert "preferred" not in br["components"]
