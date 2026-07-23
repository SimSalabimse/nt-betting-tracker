"""
Quality-preserving coverage floor (Mechanism A).

Dynamic deep_target_n, top-promo scaffolds, sport-rotation floor,
coverage_pressure_boost. Never invents p_model / never softens EV.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.light_research import (
    LightRecord,
    _sport_key,
    build_deep_queue,
    coverage_floor_cfg,
    dynamic_deep_target_n,
    promotion_score,
    tiers_cfg,
)


def _cfg(
    *,
    floor_enabled: bool = True,
    dynamic: bool = True,
    deep_target_n: int = 8,
    deep_target_min: int = 8,
    deep_target_max: int = 15,
    deep_target_divisor: int = 8,
    deep_max_n: int = 15,
    top_promo_scaffold_pct: float = 0.20,
    sport_rotation_min_lines: int = 5,
    coverage_pressure_boost: float = 40.0,
) -> dict:
    return {
        "research": {
            "tiers": {
                "engine_deep_queue": True,
                "auto_promote_to_deep": False,
                "deep_target_n": deep_target_n,
                "deep_max_n": deep_max_n,
                "deep_target_dynamic": dynamic,
                "deep_target_min": deep_target_min,
                "deep_target_max": deep_target_max,
                "deep_target_divisor": deep_target_divisor,
                "deep_min_preferred_share": 0.55,
                "deep_max_short_main_share": 0.25,
                "short_chalk_odds": 1.70,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "promo_mid_band_boost": 60,
                "promo_alt_boost": 14,
                "promo_short_chalk_penalty": -55,
            },
            "coverage_floor": {
                "enabled": floor_enabled,
                "top_promo_scaffold_pct": top_promo_scaffold_pct,
                "sport_rotation_min_lines": sport_rotation_min_lines,
                "require_real_pack": True,
                "coverage_pressure_boost": coverage_pressure_boost,
            },
        },
        "selection": {
            "probability_haircut": 0.03,
            "standard_min_ev": 0.03,
        },
    }


def _rec(
    match: str,
    selection: str,
    sport: str,
    odds: float,
    *,
    family: str = "handicap",
    verdict: str = "pass",
    has_p_model: bool = False,
    script_conflict: bool = False,
    base_rate_conflict: bool = False,
) -> LightRecord:
    return LightRecord(
        match=match,
        selection=selection,
        sport=sport,
        decimal_odds=odds,
        odds_band="1.8-2.2",
        market_family=family,
        verdict=verdict,
        has_p_model=has_p_model,
        script_conflict=script_conflict,
        base_rate_conflict=base_rate_conflict,
        promote_to_deep=False,
        source="auto",
    )


def _multi_sport_board() -> list[LightRecord]:
    recs: list[LightRecord] = []
    for i in range(10):
        recs.append(
            _rec(
                f"FBL {i} vs Opp",
                "Handikap -1.5: Away" if i % 2 == 0 else "Over 3.5",
                "football",
                2.05 + (i % 4) * 0.05,
                family="handicap" if i % 2 == 0 else "totals_over",
            )
        )
    for i in range(6):
        recs.append(
            _rec(
                f"Tennis A{i} vs B{i}",
                f"Vinner: A{i}",
                "tennis",
                1.95 + (i % 3) * 0.08,
                family="ml",
            )
        )
    for i in range(6):
        recs.append(
            _rec(
                f"NBA H{i} vs A{i}",
                "Handikap -4.5: Away" if i < 4 else f"Vinner: H{i}",
                "basketball",
                2.10 + i * 0.03 if i < 4 else 1.55,
                family="handicap" if i < 4 else "ml",
            )
        )
    for i in range(2):
        recs.append(
            _rec(
                f"HB {i}",
                "Over 55.5",
                "handball",
                1.92,
                family="totals_over",
            )
        )
    for i in range(3):
        recs.append(
            _rec(
                f"Chalk {i}",
                "Vinner: Fav",
                "football",
                1.45,
                family="ml",
            )
        )
    return recs


# ---------------------------------------------------------------------------
# dynamic_deep_target_n
# ---------------------------------------------------------------------------


def test_dynamic_deep_target_clamp_board_40():
    cfg = _cfg()
    assert dynamic_deep_target_n(cfg, 40) == 8  # 40//8=5 → min 8


def test_dynamic_deep_target_board_80():
    cfg = _cfg()
    assert dynamic_deep_target_n(cfg, 80) == 10


def test_dynamic_deep_target_board_200_caps_at_max():
    cfg = _cfg()
    assert dynamic_deep_target_n(cfg, 200) == 15


def test_dynamic_deep_target_disabled_uses_static():
    cfg = _cfg(dynamic=False, deep_target_n=8)
    assert dynamic_deep_target_n(cfg, 200) == 8
    assert dynamic_deep_target_n(cfg, 10) == 8


def test_dynamic_deep_target_empty_and_bad_board_lines():
    cfg = _cfg()
    assert dynamic_deep_target_n(cfg, 0) == 0
    assert dynamic_deep_target_n(cfg, -5) == 0
    # non-numeric → static fallback
    assert dynamic_deep_target_n(cfg, "nope") == 8  # type: ignore[arg-type]


def test_dynamic_deep_target_hi_lt_lo_snaps():
    cfg = _cfg(deep_target_min=12, deep_target_max=10)
    # hi snapped to lo → always 12
    assert dynamic_deep_target_n(cfg, 200) == 12


def test_dynamic_deep_target_zero_min_is_valid():
    """None-aware: deep_target_min=0 must not fall through to static 8."""
    cfg = _cfg(deep_target_min=0, deep_target_max=15, deep_target_divisor=8)
    # 40//8=5 → clamp(0, 15, 5)=5
    assert dynamic_deep_target_n(cfg, 40) == 5


def test_tiers_cfg_reads_dynamic_keys():
    cfg = _cfg()
    t = tiers_cfg(cfg)
    assert t["deep_target_dynamic"] is True
    assert int(t["deep_target_min"]) == 8
    assert int(t["deep_target_max"]) == 15
    assert int(t["deep_target_divisor"]) == 8
    assert int(t["deep_max_n"]) == 15
    cfc = coverage_floor_cfg(cfg)
    assert cfc["enabled"] is True
    assert float(cfc["top_promo_scaffold_pct"]) == pytest.approx(0.20)
    assert float(cfc["coverage_pressure_boost"]) == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# top promo scaffold
# ---------------------------------------------------------------------------


def test_top_promo_scaffold_tags_top_20pct():
    cfg = _cfg(floor_enabled=True, sport_rotation_min_lines=0)  # isolate scaffold
    recs = _multi_sport_board()
    scored = []
    for r in recs:
        if r.verdict != "pass" or r.has_p_model:
            continue
        if r.script_conflict or r.base_rate_conflict:
            continue
        sc = promotion_score(r, cfg)
        scored.append((sc, r))
    scored.sort(key=lambda x: (-x[0], x[1].decimal_odds))
    n_cand = len(scored)
    n_scaffold = max(1, math.ceil(0.20 * n_cand))
    top_keys = {r.key() for _sc, r in scored[:n_scaffold]}

    q = build_deep_queue(recs, cfg, board_lines=len(recs))
    for r in recs:
        if r.key() in top_keys:
            assert "coverage_floor:top_promo_scaffold" in (r.rough_ev_note or "")

    q_keys = {r.key() for r in q}
    preferred_scaffolds = [
        r for _sc, r in scored[:n_scaffold] if r.decimal_odds >= 1.85
    ]
    assert any(r.key() in q_keys for r in preferred_scaffolds)
    assert all(not r.has_p_model for r in q)


def test_scaffold_pct_zero_disables_scaffolds():
    """Falsy-or regression: top_promo_scaffold_pct=0 must yield zero scaffold tags."""
    cfg = _cfg(
        floor_enabled=True,
        top_promo_scaffold_pct=0.0,
        sport_rotation_min_lines=0,
    )
    recs = _multi_sport_board()
    build_deep_queue(recs, cfg, board_lines=len(recs))
    for r in recs:
        note = r.rough_ev_note or ""
        assert "coverage_floor:top_promo_scaffold" not in note


def test_scaffold_skips_pure_short_main():
    cfg = _cfg(
        floor_enabled=True,
        top_promo_scaffold_pct=1.0,  # all candidates scaffolded
        sport_rotation_min_lines=0,
        deep_target_n=10,
        deep_max_n=15,
    )
    recs = [
        _rec(f"Pref {i}", "Handikap -1.5: Away", "football", 2.10, family="handicap")
        for i in range(6)
    ]
    chalk = _rec("Chalk ML", "Vinner: Fav", "football", 1.45, family="ml")
    recs.append(chalk)
    q = build_deep_queue(recs, cfg, board_lines=len(recs))
    q_keys = {r.key() for r in q}
    # Chalk may be tagged as scaffold candidate but must not be force-added via scaffold
    assert chalk.key() not in q_keys or chalk.decimal_odds >= 1.85
    # Stronger: chalk is pure short-main and should not enter via force
    assert chalk.key() not in q_keys


def test_scaffold_disabled_no_tags():
    cfg = _cfg(floor_enabled=False, dynamic=False)
    recs = _multi_sport_board()
    q = build_deep_queue(recs, cfg, board_lines=len(recs))
    for r in recs:
        note = r.rough_ev_note or ""
        assert "coverage_floor:top_promo_scaffold" not in note
        assert "coverage_floor:sport_rotation" not in note
    assert len(q) <= 8


# ---------------------------------------------------------------------------
# sport rotation
# ---------------------------------------------------------------------------


def test_sport_rotation_promotes_preferred_underrepresented():
    """
    Football fills small target; basketball has ≥5 preferred eligible lines.
    Rotation must put basketball into the queue (membership, not just annotation).
    """
    cfg = _cfg(
        floor_enabled=True,
        deep_target_n=3,
        deep_target_min=3,
        deep_target_max=8,
        deep_max_n=10,
        dynamic=False,
        sport_rotation_min_lines=5,
        top_promo_scaffold_pct=0.0,  # must actually disable (Issue 2 regression)
    )
    recs: list[LightRecord] = []
    for i in range(6):
        recs.append(
            _rec(
                f"TopFBL {i}",
                "Handikap -1.5: Away",
                "football",
                2.40,
                family="handicap",
            )
        )
    for i in range(5):
        recs.append(
            _rec(
                f"BB mid {i}",
                "Handikap -3.5: Home",
                "basketball",
                2.00 + i * 0.01,
                family="handicap",
            )
        )

    q = build_deep_queue(recs, cfg, board_lines=len(recs))
    sports = {_sport_key(r) for r in q}
    assert "football" in sports
    assert "basketball" in sports, "sport rotation must force-promote preferred basketball"
    bball = [r for r in q if _sport_key(r) == "basketball"]
    assert len(bball) >= 1
    assert all(r.decimal_odds >= 1.85 for r in bball)
    # scaffold must be off
    for r in recs:
        assert "coverage_floor:top_promo_scaffold" not in (r.rough_ev_note or "")


def test_sport_rotation_rejects_pure_short_main_only_sport():
    """
    Tennis has ≥5 light-pass lines but all pure short-main chalk.
    Rotation must NOT enqueue any of them; annotate no_eligible instead.
    """
    cfg = _cfg(
        floor_enabled=True,
        deep_target_n=3,
        deep_max_n=10,
        dynamic=False,
        sport_rotation_min_lines=5,
        top_promo_scaffold_pct=0.0,
    )
    recs: list[LightRecord] = []
    for i in range(6):
        recs.append(
            _rec(
                f"FBL fill {i}",
                "Handikap -1.5: Away",
                "football",
                2.20,
                family="handicap",
            )
        )
    for i in range(5):
        recs.append(
            _rec(
                f"Tennis chalk {i}",
                f"Vinner: Fav{i}",
                "tennis",
                1.40,
                family="ml",
            )
        )

    q = build_deep_queue(recs, cfg, board_lines=len(recs))
    tennis_in_q = [r for r in q if _sport_key(r) == "tennis"]
    assert tennis_in_q == [], "rotation must not force pure short-main chalk"
    tennis_notes = [
        r.rough_ev_note or ""
        for r in recs
        if _sport_key(r) == "tennis"
    ]
    assert any("coverage_floor:sport_rotation:no_eligible" in n for n in tennis_notes)


def test_sport_rotation_counts_only_eligible_candidates():
    """Lines with has_p_model / script_conflict do not count toward rotation threshold."""
    cfg = _cfg(
        floor_enabled=True,
        deep_target_n=3,
        dynamic=False,
        sport_rotation_min_lines=5,
        top_promo_scaffold_pct=0.0,
    )
    recs: list[LightRecord] = []
    for i in range(6):
        recs.append(
            _rec(f"FBL {i}", "Handikap -1.5: Away", "football", 2.20, family="handicap")
        )
    # Only 2 eligible basketball + 4 already-deep / conflicted → below min 5
    for i in range(2):
        recs.append(
            _rec(f"BB ok {i}", "Handikap -2.5: Away", "basketball", 2.05, family="handicap")
        )
    for i in range(4):
        recs.append(
            _rec(
                f"BB deep {i}",
                "Handikap -2.5: Home",
                "basketball",
                2.05,
                family="handicap",
                has_p_model=True,
            )
        )
    q = build_deep_queue(recs, cfg, board_lines=len(recs))
    # Rotation should not fire for basketball (only 2 eligible)
    for r in recs:
        if _sport_key(r) == "basketball":
            assert "coverage_floor:sport_rotation" not in (r.rough_ev_note or "")


def test_sport_key_blank_and_unknown_same_bucket():
    assert _sport_key("") == "unknown"
    assert _sport_key(None) == "unknown"
    assert _sport_key("  ") == "unknown"
    assert _sport_key("Tennis") == "tennis"
    r = _rec("M", "Vinner: A", "", 2.0, family="ml")
    assert _sport_key(r) == "unknown"


# ---------------------------------------------------------------------------
# coverage pressure boost
# ---------------------------------------------------------------------------


def test_coverage_pressure_boost_when_overlay_active():
    cfg = _cfg(coverage_pressure_boost=40.0, floor_enabled=True)
    rec = _rec("A vs B", "Handikap -1.5: Away", "football", 2.10, family="handicap")
    base = promotion_score(rec, cfg, coverage_overlay=None)
    boosted = promotion_score(
        rec,
        cfg,
        coverage_overlay={
            "active": True,
            "target_odds_band": "1.85-2.60",
            "weight_boost": 30.0,
            "prefer": ["handicaps"],
        },
    )
    assert boosted >= base + 30.0 + 40.0


def test_coverage_pressure_boost_off_when_floor_disabled():
    cfg = _cfg(coverage_pressure_boost=40.0, floor_enabled=False)
    rec = _rec("A vs B", "Handikap -1.5: Away", "football", 2.10, family="handicap")
    base = promotion_score(rec, cfg, coverage_overlay=None)
    with_ov = promotion_score(
        rec,
        cfg,
        coverage_overlay={
            "active": True,
            "target_odds_band": "1.85-2.60",
            "weight_boost": 30.0,
            "prefer": [],
        },
    )
    assert with_ov == pytest.approx(base + 30.0)


def test_coverage_pressure_boost_zero_is_valid():
    """0.0 pressure must not fall through to a non-zero default."""
    cfg = _cfg(coverage_pressure_boost=0.0, floor_enabled=True)
    rec = _rec("A vs B", "Handikap -1.5: Away", "football", 2.10, family="handicap")
    base = promotion_score(rec, cfg, coverage_overlay=None)
    with_ov = promotion_score(
        rec,
        cfg,
        coverage_overlay={
            "active": True,
            "target_odds_band": "1.85-2.60",
            "weight_boost": 30.0,
            "prefer": [],
        },
    )
    assert with_ov == pytest.approx(base + 30.0)


# ---------------------------------------------------------------------------
# board_lines + caps + no p_model
# ---------------------------------------------------------------------------


def test_board_lines_scales_target_and_queue():
    cfg = _cfg(dynamic=True, deep_max_n=15, top_promo_scaffold_pct=0.0, sport_rotation_min_lines=0)
    # Enough preferred mid lines for both targets
    recs = [
        _rec(f"P {i}", "Handikap -1.5: Away", "football" if i < 10 else "tennis", 2.10 + (i % 5) * 0.02, family="handicap")
        for i in range(30)
    ]
    assert dynamic_deep_target_n(cfg, 40) == 8
    assert dynamic_deep_target_n(cfg, 80) == 10
    assert dynamic_deep_target_n(cfg, 200) == 15

    q_small = build_deep_queue(recs, cfg, board_lines=40)
    q_large = build_deep_queue(recs, cfg, board_lines=80)
    assert len(q_small) <= 8
    assert len(q_large) <= 10
    # Larger board allows a larger (or equal) queue under composition
    assert len(q_large) >= len(q_small)


def test_dynamic_cap_board_200_queue_at_most_15():
    cfg = _cfg(dynamic=True, deep_max_n=15, deep_target_max=15)
    recs = [
        _rec(
            f"P {i}",
            "Handikap -1.5: Away",
            ["football", "tennis", "basketball", "handball"][i % 4],
            2.05 + (i % 6) * 0.03,
            family="handicap",
        )
        for i in range(60)
    ]
    q = build_deep_queue(recs, cfg, board_lines=200)
    assert dynamic_deep_target_n(cfg, 200) == 15
    assert len(q) <= 15


def test_static_path_queue_at_most_deep_target_n():
    cfg = _cfg(dynamic=False, deep_target_n=8, deep_max_n=15, floor_enabled=False)
    recs = [
        _rec(f"P {i}", "Handikap -1.5: Away", "football", 2.10, family="handicap")
        for i in range(20)
    ]
    q = build_deep_queue(recs, cfg, board_lines=200)
    assert len(q) <= 8


def test_never_invents_p_model():
    cfg = _cfg()
    recs = _multi_sport_board()
    # Inject one already-researched line — must stay out of deep queue worklist
    recs.append(
        _rec("Done", "Handikap -1.5: Home", "football", 2.10, family="handicap", has_p_model=True)
    )
    q = build_deep_queue(recs, cfg, board_lines=80)
    assert all(not r.has_p_model for r in q)
    assert all(r.key() != ("Done", "Handikap -1.5: Home") for r in q)


def test_force_non_pref_cannot_open_empty_queue():
    """Issue 3: preferred-share guard applies when queue empty — non-pref force blocked."""
    cfg = _cfg(
        floor_enabled=True,
        top_promo_scaffold_pct=1.0,
        sport_rotation_min_lines=0,
        deep_target_n=5,
        deep_max_n=10,
    )
    # Only non-preferred short alts (odds < alt_preferred 1.80, not short-main)
    # Actually short alt under 1.80 that's not ML/O2.5/FG is "other"
    # Preferred pool empty → fail-closed empty queue before force.
    recs = [
        _rec(f"Alt {i}", "Oddsmatcher special", "football", 1.60, family="other")
        for i in range(8)
    ]
    q = build_deep_queue(recs, cfg, board_lines=len(recs))
    assert q == []
