"""PR3 ESR: composition quotas off — coverage cannot re-arm; n_pref empty still queues."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.light_research import LightRecord, build_deep_queue, tiers_cfg


def _cfg(
    *,
    min_pref: float = 0.0,
    max_short: float = 1.0,
    preferred_lo: float = 1.85,
    alt_lo: float = 1.80,
    short_chalk: float = 1.70,
    deep_max_n: int = 15,
    deep_target_n: int = 8,
    floor_enabled: bool = False,
) -> dict:
    return {
        "research": {
            "tiers": {
                "engine_deep_queue": True,
                "auto_promote_to_deep": False,
                "deep_target_n": deep_target_n,
                "deep_max_n": deep_max_n,
                "deep_target_dynamic": False,
                "deep_min_preferred_share": min_pref,
                "deep_max_short_main_share": max_short,
                "short_chalk_odds": short_chalk,
                "preferred_odds_lo": preferred_lo,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": alt_lo,
                "promo_mid_band_boost": 8,
                "promo_alt_boost": 12,
                "promo_short_chalk_penalty": -12,
                "promo_preferred_boost": 0,
                "promo_short_main_penalty": 0,
                "promo_require_signal_for_family_boost": True,
            },
            "coverage_floor": {
                "enabled": floor_enabled,
                "top_promo_scaffold_pct": 0.0,
                "sport_rotation_min_lines": 99,
                "require_real_pack": True,
                "coverage_pressure_boost": 0.0,
            },
        },
        "selection": {"probability_haircut": 0.03},
    }


def _rec(
    match: str,
    selection: str,
    sport: str,
    odds: float,
    *,
    family: str = "ml",
    prior_ev: float | None = None,
) -> LightRecord:
    return LightRecord(
        match=match,
        selection=selection,
        sport=sport,
        decimal_odds=odds,
        odds_band="1.4-1.8",
        market_family=family,
        verdict="pass",
        has_p_model=False,
        promote_to_deep=False,
        source="auto",
        prior_ev=prior_ev,
        prior_available=prior_ev is not None,
        reason="form edge" if prior_ev else "",
    )


def _short_chalk_only_board(n: int = 6) -> list[LightRecord]:
    """All short-main ML chalk under preferred_lo=1.85 → n_pref_avail == 0."""
    return [
        _rec(f"Match {i}", f"Vinner: Fav{i}", "tennis", 1.45 + (i % 3) * 0.03, family="ml")
        for i in range(n)
    ]


def test_coverage_active_min_pref_zero_does_not_rearm():
    """
    Coverage overlay with stale coverage_preferred_share=0.55 must NOT re-arm
    when deep_min_preferred_share is 0 — queue still fills (composition off).
    """
    cfg = _cfg(min_pref=0.0, preferred_lo=1.85)
    # Confirm tiers stay at 0
    assert float(tiers_cfg(cfg)["deep_min_preferred_share"]) == 0.0

    records = _short_chalk_only_board(8)
    # Stale overlay that would re-arm to 0.55 under FEH-era code
    ov = {
        "active": True,
        "coverage_preferred_share": 0.55,
        "target_odds_band": "1.40-2.80",
        "prefer": ["alt_totals", "handicaps", "period", "natural_totals"],
        "min_deep_packs": 6,
        "weight_boost": 30.0,
    }
    q = build_deep_queue(
        records,
        cfg,
        coverage_overlay=ov,
        board_lines=len(records),
    )
    assert q, "ESR: coverage must not empty queue when min_pref=0"
    assert len(q) >= 1
    # All candidates are non-preferred short chalk — queue still non-empty
    assert all(r.decimal_odds < 1.85 for r in q)


def test_n_pref_avail_zero_composition_off_nonempty():
    """When min_pref<=0 and preferred pool empty → pure promo order, not []."""
    cfg = _cfg(min_pref=0.0, preferred_lo=1.85)
    # Multi-sport so sport cap (3/sp) does not empty the board alone
    records = [
        _rec(f"T{i}", f"Vinner: Fav{i}", "tennis", 1.45, family="ml")
        for i in range(3)
    ] + [
        _rec(f"F{i}", f"Vinner: Fav{i}", "football", 1.48, family="ml")
        for i in range(3)
    ]
    q = build_deep_queue(records, cfg, board_lines=len(records))
    assert q, "composition off must not return empty when only non-preferred exist"
    assert len(q) >= 3


def test_n_pref_avail_zero_composition_on_returns_empty():
    """Legacy FEH-era: min_pref>0 + empty preferred pool → fail-closed []."""
    cfg = _cfg(min_pref=0.55, preferred_lo=1.85, max_short=0.25)
    records = _short_chalk_only_board(5)
    q = build_deep_queue(records, cfg, board_lines=len(records))
    assert q == []


def test_coverage_cannot_rearm_when_min_pref_zero_even_with_mixed_board():
    """Mixed board + coverage active + min_pref=0 → queue non-empty, no shrink to preferred-only."""
    cfg = _cfg(min_pref=0.0, preferred_lo=1.40, floor_enabled=False)
    records = [
        _rec("S1", "Vinner: A", "tennis", 1.55, family="ml", prior_ev=0.04),
        _rec("S2", "Vinner: B", "tennis", 1.62, family="ml"),
        _rec("F1", "Handikap +1.5: Away", "football", 1.95, family="handicap"),
        _rec("F2", "Over 2.5", "football", 1.88, family="totals_over"),
        _rec("B1", "Vinner: H", "basketball", 1.70, family="ml"),
    ]
    ov = {
        "active": True,
        "coverage_preferred_share": 0.55,
        "target_odds_band": "1.40-2.80",
        "prefer": ["natural_totals"],
    }
    q = build_deep_queue(records, cfg, coverage_overlay=ov, board_lines=20)
    assert len(q) >= 3
