"""
PR2 — dual-track clearability promotion (T3-like + T13).

Rank light-pass by clearability_score (relative prior, not prior_ev > 0).
Dual-track composition; never pad chalk.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.clearability import relative_prior_ev
from nt.light_research import (
    LightRecord,
    build_deep_queue,
    dual_track_sizes,
    tiers_cfg,
)


def _cfg(**tier_extra) -> dict:
    return {
        "selection": {"probability_haircut": 0.03, "standard_min_ev": 0.02},
        "research": {
            "tiers": {
                "engine_deep_queue": True,
                "clearability_promotion": True,
                "dual_track_deep_queue": True,
                "deep_target_n": 8,
                "deep_max_n": 12,
                "deep_min_preferred_share": 0.55,
                "deep_max_short_main_share": 0.25,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "short_chalk_odds": 1.70,
                **tier_extra,
            }
        },
    }


def _rec(
    match: str,
    selection: str,
    odds: float,
    *,
    sport: str = "football",
    family: str = "ml",
    prior_p: float | None = None,
    prior_ev: float | None = None,
    verdict: str = "pass",
    has_p: bool = False,
) -> LightRecord:
    haircut = 0.03
    if prior_ev is None and prior_p is not None:
        prior_ev = (float(prior_p) - haircut) * float(odds) - 1.0
    return LightRecord(
        match=match,
        selection=selection,
        sport=sport,
        decimal_odds=float(odds),
        odds_band="mid",
        market_family=family,
        verdict=verdict,
        has_p_model=has_p,
        has_deep_pack=has_p,
        prior_p=prior_p,
        prior_ev=prior_ev,
        prior_available=prior_ev is not None,
    )


def test_dual_track_sizes_frozen():
    # target=8 → clearable 6, coverage 2
    c, v = dual_track_sizes(8)
    assert c == 6
    assert v == 2
    c10, v10 = dual_track_sizes(10)
    assert c10 == 7
    assert v10 == 3
    # force_coverage raises coverage floor
    c_f, v_f = dual_track_sizes(8, coverage_overlay_active=True)
    assert v_f >= 2
    assert c_f + v_f == 8
    assert v_f == max(2, min(4, 8 // 2))
    # force_clearability raises clearable floor
    c_cl, v_cl = dual_track_sizes(8, clearability_overlay_active=True)
    assert c_cl >= 6
    assert c_cl + v_cl == 8


def test_t13_dual_track_preferred_composition():
    """T13: dual-track composition ≥55% preferred when pool allows."""
    cfg = _cfg()
    haircut = 0.03
    records: list[LightRecord] = []
    # 10 preferred mid/alt lines across sports (all-negative priors)
    alts = [
        ("M1", "Handikap 3.5: A +3.5", 2.10, "tennis", "handicap", 0.48),
        ("M2", "Totalt 3.5: Over 3.5", 2.05, "football", "totals_over", 0.50),
        ("M3", "Game handikap: B +2.5", 1.95, "tennis", "handicap", 0.49),
        ("M4", "Totalt 4.5: Under 4.5", 2.20, "football", "totals_under", 0.47),
        ("M5", "Vinner: Dog", 2.40, "basketball", "ml", 0.42),
        ("M6", "1. omgang: Over 0.5", 1.90, "football", "period", 0.51),
        ("M7", "Handikap -1.5: Away", 2.00, "football", "handicap", 0.48),
        ("M8", "Totalt 3.5: Under 3.5", 2.15, "football", "totals_under", 0.46),
        ("M9", "Vinner: Underdog", 2.55, "tennis", "ml", 0.40),
        ("M10", "Handikap +4.5: Home", 1.92, "basketball", "handicap", 0.50),
    ]
    for m, sel, o, sp, fam, pp in alts:
        records.append(
            _rec(m, sel, o, sport=sp, family=fam, prior_p=pp)
        )
    # A few short chalk that must not dominate
    records.append(
        _rec("SC1", "Vinner: Fav", 1.55, sport="football", family="ml", prior_p=0.62)
    )
    records.append(
        _rec("SC2", "Totalt over 2.5", 1.60, sport="football", family="ou_25", prior_p=0.60)
    )

    for r in records:
        if r.prior_ev is not None:
            assert r.prior_ev < 0.0 or r.decimal_odds < 1.70

    queue = build_deep_queue(records, cfg)
    assert len(queue) >= 5
    pref_n = sum(
        1
        for r in queue
        if r.decimal_odds >= 1.85
        or (
            r.decimal_odds >= 1.80
            and r.market_family
            not in ("ml", "ou_25")
        )
    )
    # Engine preferred flags
    from nt.light_research import is_preferred_line, is_short_main_line

    pref_n = sum(
        1
        for r in queue
        if is_preferred_line(
            r.selection, r.decimal_odds, r.market_family
        )
    )
    sm_n = sum(
        1
        for r in queue
        if is_short_main_line(r.selection, r.decimal_odds, r.market_family)
    )
    n = len(queue)
    assert pref_n / n + 1e-9 >= 0.55
    assert sm_n / n <= 0.25 + 1e-9
    # Tracks assigned
    tracks = {getattr(r, "queue_track", "") for r in queue}
    assert "clearable" in tracks or "coverage" in tracks
    # Never pad pure short chalk as majority
    chalk = [
        r
        for r in queue
        if is_short_main_line(r.selection, r.decimal_odds, r.market_family)
    ]
    assert len(chalk) <= max(1, int(0.25 * n + 1e-9))


def test_t3_like_rank_changes_on_all_negative_priors():
    """
    All-negative Stage2 priors: higher rel_prior / alt clearability outranks
    coin-flip mid ML. Soft refs not required.
    """
    cfg = _cfg(deep_target_n=6, deep_max_n=8)
    haircut = 0.03

    coin = _rec(
        "C vs D",
        "Vinner: Home",
        2.00,
        family="ml",
        prior_p=0.491,
        prior_ev=-0.078,
    )
    # Pair for coin-flip geometry (same match + family)
    coin_peer = _rec(
        "C vs D",
        "Vinner: Away",
        2.05,
        family="ml",
        prior_p=0.49,
        prior_ev=-0.085,
    )
    alt_hc = _rec(
        "A vs B",
        "Handikap 3.5: A +3.5",
        2.20,
        sport="tennis",
        family="handicap",
        prior_p=0.48,
    )
    alt_ou = _rec(
        "E vs F",
        "Totalt 3.5: Over 3.5",
        2.10,
        family="totals_over",
        prior_p=0.50,
    )
    dog = _rec(
        "G vs H",
        "Vinner: Dog",
        2.50,
        sport="basketball",
        family="ml",
        prior_p=0.42,
    )
    # Extra preferred fillers so queue non-empty under composition
    fillers = [
        _rec(f"F{i}", f"Handikap +{i}.5: Away", 1.95 + i * 0.02, family="handicap", prior_p=0.47)
        for i in range(4)
    ]

    board = [coin, coin_peer, alt_hc, alt_ou, dog] + fillers
    for r in board:
        assert r.prior_ev is None or r.prior_ev < 0.05

    queue = build_deep_queue(board, cfg)
    assert queue, "expected non-empty dual-track queue"

    # Scores attached
    for r in queue:
        assert r.clearability_score is not None
        assert r.promotion_score_v3 is not None

    # Alt HC should outrank coin mid ML if both present
    keys = [(r.match, r.selection) for r in queue]
    alt_key = (alt_hc.match, alt_hc.selection)
    coin_key = (coin.match, coin.selection)
    if alt_key in keys and coin_key in keys:
        assert keys.index(alt_key) < keys.index(coin_key)

    # Or clearability on alt > coin when scored
    scored = { (r.match, r.selection): float(r.clearability_score or 0) for r in queue }
    if alt_key in scored and coin_key in scored:
        assert scored[alt_key] > scored[coin_key]

    # Relative prior: alt better than coin
    coin_rel = relative_prior_ev(coin.prior_ev, coin.decimal_odds, haircut)
    alt_rel = relative_prior_ev(alt_hc.prior_ev, alt_hc.decimal_odds, haircut)
    assert alt_rel is not None and coin_rel is not None
    assert alt_rel > coin_rel


def test_skips_has_p_model_in_normal_mode():
    cfg = _cfg()
    packed = _rec(
        "P vs Q",
        "Handikap +2.5: A",
        2.00,
        family="handicap",
        prior_p=0.50,
        has_p=True,
    )
    open_line = _rec(
        "R vs S",
        "Totalt 3.5: Over 3.5",
        2.10,
        family="totals_over",
        prior_p=0.49,
    )
    extras = [
        _rec(f"X{i}", f"Handikap +{i}.5: B", 2.0 + i * 0.05, family="handicap", prior_p=0.48)
        for i in range(6)
    ]
    queue = build_deep_queue([packed, open_line] + extras, cfg)
    keys = {r.key() for r in queue}
    assert packed.key() not in keys
    assert open_line.key() in keys or any(r.decimal_odds >= 1.85 for r in queue)


def test_never_pads_chalk_when_preferred_thin():
    cfg = _cfg(deep_target_n=8)
    # Only 2 preferred + many short chalk
    pref = [
        _rec("A1", "Handikap +3.5: A", 2.00, family="handicap", prior_p=0.48),
        _rec("A2", "Totalt 3.5: Under 3.5", 2.10, family="totals_under", prior_p=0.47),
    ]
    chalk = [
        _rec(f"C{i}", f"Vinner: Fav{i}", 1.50 + i * 0.02, family="ml", prior_p=0.62)
        for i in range(10)
    ]
    queue = build_deep_queue(pref + chalk, cfg)
    # Thin preferred pool shrinks n — never flood with chalk
    from nt.light_research import is_preferred_line, is_short_main_line

    if queue:
        pref_share = sum(
            1
            for r in queue
            if is_preferred_line(r.selection, r.decimal_odds, r.market_family)
        ) / len(queue)
        assert pref_share + 1e-9 >= 0.55
        sm_share = sum(
            1
            for r in queue
            if is_short_main_line(r.selection, r.decimal_odds, r.market_family)
        ) / len(queue)
        assert sm_share <= 0.25 + 1e-9
    # Absolute: queue not filled to 8 with chalk
    assert len(queue) <= 4  # 2 pref / 0.55 ≈ 3.6


def test_tiers_cfg_dual_track_defaults():
    t = tiers_cfg({})
    assert t["clearability_promotion"] is True
    assert t["dual_track_deep_queue"] is True
    assert int(t["second_pass_max_inject"]) == 12
    assert float(t["raw_ev_exhausted"]) == pytest.approx(-0.05)
