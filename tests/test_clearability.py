"""
HV Research Regime v3 PR1 — clearability pure helpers + frozen weights.

T1: fair_ev / p_needed / rel_prior math at odds 2.0 with haircut=0.03, min_ev=0.02
T3: non-vacuous rank — production-like all-negative Stage2 priors; higher
    rel_prior / |prior_p−implied| alts outrank coin-flip mid ML (soft not required).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.clearability import (
    DEFAULT_CLEARABILITY_WEIGHTS,
    batch_prior_percentile,
    clearability_cfg,
    clearability_score,
    fair_ev_after_haircut,
    implied_prob,
    is_coin_flip_line,
    p_needed_for_min_ev,
    promotion_score_v3,
    relative_prior_ev,
    score_candidates,
)
from nt.defaults import research_cfg
from nt.research_prefilter import (
    fair_ev_after_haircut as prefilter_fair_ev,
    p_needed_for_min_ev as prefilter_p_needed,
    relative_prior_ev as prefilter_rel_prior,
)


# ---------------------------------------------------------------------------
# T1 — clearability math
# ---------------------------------------------------------------------------


def test_t1_fair_ev_p_needed_rel_prior_at_odds_2():
    haircut = 0.03
    min_ev = 0.02
    odds = 2.0

    fair = fair_ev_after_haircut(odds, haircut)
    assert fair == pytest.approx(-0.06)

    need = p_needed_for_min_ev(odds, min_ev=min_ev, haircut=haircut)
    # (1.02)/2 + 0.03 = 0.51 + 0.03 = 0.54
    assert need == pytest.approx(0.54)

    # Production-like mid ML after 3pp: prior_ev ≈ −0.078
    prior_ev = -0.078
    rel = relative_prior_ev(prior_ev, odds, haircut)
    assert rel == pytest.approx(prior_ev - fair)
    assert rel == pytest.approx(-0.018)

    # Pure-implied prior_ev equals fair → rel_prior 0
    assert relative_prior_ev(fair, odds, haircut) == pytest.approx(0.0)

    assert implied_prob(odds) == pytest.approx(0.5)


def test_t1_prefilter_reexports_same_math():
    """research_prefilter re-exports clearability SSOT helpers."""
    assert prefilter_fair_ev(2.0, 0.03) == fair_ev_after_haircut(2.0, 0.03)
    assert prefilter_p_needed(2.0, 0.02, 0.03) == p_needed_for_min_ev(2.0, 0.02, 0.03)
    assert prefilter_rel_prior(-0.08, 2.0, 0.03) == relative_prior_ev(-0.08, 2.0, 0.03)


def test_frozen_weights_match_design():
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_mid"] == 25.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_rel_prior"] == 80.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_batch"] == 20.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_coin"] == -35.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_soft"] == 40.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_alt"] == 14.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_short"] == -55.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_struct"] == 15.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_disp"] == 25.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_hist"] == 15.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_cov"] == 30.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_cl_force"] == 35.0
    assert DEFAULT_CLEARABILITY_WEIGHTS["w_fail"] == -40.0


def test_defaults_and_cfg_clearability_block():
    cfg = research_cfg({})
    cl = (cfg.get("tiers") or {}).get("clearability") or {}
    # research_cfg empty → defaults include clearability with frozen weights
    assert float(cl["w_rel_prior"]) == 80.0
    assert float(cl["w_mid"]) == 25.0

    merged = clearability_cfg(
        {"research": {"tiers": {"clearability": {"w_mid": 1.0}, "preferred_odds_lo": 1.90}}}
    )
    assert merged["w_mid"] == 1.0
    assert merged["w_rel_prior"] == 80.0  # frozen default kept on partial override
    assert merged["preferred_odds_lo"] == 1.90


# ---------------------------------------------------------------------------
# Missing prior / coin-flip / short-main unit behaviour
# ---------------------------------------------------------------------------


def test_missing_prior_rel_prior_contributes_zero():
    """No prior → w_rel_prior and w_disp contribute 0 (not invented)."""
    base = clearability_score(odds=2.0, prior_ev=None, prior_p=None)
    mid_only = clearability_score(
        odds=2.0,
        prior_ev=None,
        prior_p=None,
        weights={**DEFAULT_CLEARABILITY_WEIGHTS, "w_mid": 25.0},
    )
    # Only mid-band membership fires
    assert base == pytest.approx(25.0)
    assert mid_only == pytest.approx(25.0)
    assert relative_prior_ev(None, 2.0) is None


def test_coin_flip_skipped_when_only_one_side():
    assert (
        is_coin_flip_line(
            odds=2.0,
            prior_p=0.50,
            peer_odds=None,
            both_sides_present=False,
        )
        is False
    )
    # Both sides + market-mimic prior → coin flip
    assert (
        is_coin_flip_line(
            odds=2.0,
            prior_p=0.50,
            peer_odds=2.05,
            both_sides_present=True,
            coin_flip_eps=0.02,
        )
        is True
    )
    # Both sides but prior disagrees with implied → not coin flip
    assert (
        is_coin_flip_line(
            odds=2.0,
            prior_p=0.58,
            peer_odds=2.05,
            both_sides_present=True,
            coin_flip_eps=0.02,
        )
        is False
    )


def test_coin_flip_no_prior_even_market_restricted_to_totals():
    """Without prior, even-odds geometry applies only to totals/OU (not bare ML)."""
    # Even ML pair without prior → not auto coin-flip
    assert (
        is_coin_flip_line(
            odds=2.0,
            peer_odds=2.05,
            both_sides_present=True,
            market_family="ml",
        )
        is False
    )
    # Even totals pair without prior → coin-flip
    assert (
        is_coin_flip_line(
            odds=1.95,
            peer_odds=1.95,
            both_sides_present=True,
            market_family="totals_over",
            selection="Totalt over 2.5",
        )
        is True
    )


def test_family_clear_rate_scales_w_hist():
    """n≥12 + clear rate scales w_hist; n≥12 without rate → full binary gate."""
    base = clearability_score(odds=1.70, family_hist_n=0)
    full = clearability_score(odds=1.70, family_hist_n=12)
    half = clearability_score(odds=1.70, family_hist_n=12, family_clear_rate=0.5)
    assert full == pytest.approx(base + DEFAULT_CLEARABILITY_WEIGHTS["w_hist"])
    assert half == pytest.approx(base + 0.5 * DEFAULT_CLEARABILITY_WEIGHTS["w_hist"])
    assert clearability_score(odds=1.70, family_hist_n=5, family_clear_rate=1.0) == base


def test_short_main_penalty_applies():
    no_short = clearability_score(odds=1.75, is_short_main=False, prior_ev=None)
    with_short = clearability_score(odds=1.75, is_short_main=True, prior_ev=None)
    assert with_short == pytest.approx(no_short + DEFAULT_CLEARABILITY_WEIGHTS["w_short"])
    assert with_short < no_short


def test_batch_percentile_requires_n_ge_3():
    assert batch_prior_percentile(-0.08, [-0.09, -0.07]) is None
    p = batch_prior_percentile(-0.08, [-0.10, -0.08, -0.06])
    assert p is not None
    assert 0.0 <= p <= 1.0


def test_promotion_score_v3_caps_board():
    assert promotion_score_v3(10.0, 0.0) == pytest.approx(10.0)
    assert promotion_score_v3(10.0, 200.0) == pytest.approx(25.0)  # +min(15, 20)
    assert promotion_score_v3(10.0, 50.0) == pytest.approx(15.0)  # +5


# ---------------------------------------------------------------------------
# T3 — non-vacuous rank (PR1 acceptance gate)
# ---------------------------------------------------------------------------


def test_t3_non_vacuous_rank_negative_priors_alts_above_coin_ml():
    """
    Fixture board with production-like Stage2 priors (all/mostly negative after 3pp).

    Rank by clearability_score must put higher rel_prior / higher |prior_p−implied|
    alts above coin-flip mid ML with worse rel_prior. Soft refs NOT required.
    """
    haircut = 0.03

    # Coin-flip mid ML @2.00 — market-mimic; prior_ev≈−0.078, fair=−0.06 → rel≈−0.018
    coin_ml = {
        "id": "coin_mid_ml",
        "odds": 2.0,
        "prior_p": 0.491,
        "prior_ev": -0.078,
        "is_coin_flip": True,
        "is_alt": False,
        "is_short_main": False,
    }

    # Alt HC @2.20 — prior_p=0.48 → prior_ev≈−0.010, fair≈−0.066 → rel≈+0.056
    alt_hc = {
        "id": "alt_hc_plus",
        "odds": 2.20,
        "prior_p": 0.48,
        "prior_ev": (0.48 - haircut) * 2.20 - 1.0,
        "is_coin_flip": False,
        "is_alt": True,
        "is_short_main": False,
    }

    # Alt O3.5 @2.10 — prior_p=0.50 → prior_ev≈−0.013, better rel than coin + alt flag
    alt_ou = {
        "id": "alt_ou35",
        "odds": 2.10,
        "prior_p": 0.50,
        "prior_ev": (0.50 - haircut) * 2.10 - 1.0,
        "is_coin_flip": False,
        "is_alt": True,
        "is_short_main": False,
    }

    # Dog ML @2.50 — prior_p=0.42 → prior_ev≈−0.025 (still negative absolute EV)
    dog_ml = {
        "id": "dog_ml",
        "odds": 2.50,
        "prior_p": 0.42,
        "prior_ev": (0.42 - haircut) * 2.50 - 1.0,
        "is_coin_flip": False,
        "is_alt": False,
        "is_short_main": False,
    }

    # Second coin-ish mid ML @1.95 — market-mimic, worse rel than alts
    coin_ml_b = {
        "id": "coin_mid_ml_b",
        "odds": 1.95,
        "prior_p": 0.505,
        "prior_ev": (0.505 - haircut) * 1.95 - 1.0,
        "is_coin_flip": True,
        "is_alt": False,
        "is_short_main": False,
    }

    # Ensure all prior_ev negative (production-like after 3pp)
    board = [coin_ml, alt_hc, alt_ou, dog_ml, coin_ml_b]
    for row in board:
        assert row["prior_ev"] < 0.0, f"{row['id']} prior_ev should be negative"

    ranked = score_candidates(board, haircut=haircut)
    order = [r["id"] for r in ranked]

    # Coin-flip mid MLs must not sit above the better-rel alts
    assert order.index("alt_hc_plus") < order.index("coin_mid_ml")
    assert order.index("alt_ou35") < order.index("coin_mid_ml")
    # Higher |prior_p−implied| / rel_prior alt beats coin
    coin_score = next(r["clearability_score"] for r in ranked if r["id"] == "coin_mid_ml")
    alt_score = next(r["clearability_score"] for r in ranked if r["id"] == "alt_hc_plus")
    assert alt_score > coin_score

    # Soft not required: scores work without soft_decimal_odds
    for r in ranked:
        assert r.get("soft_decimal_odds") is None

    # Sanity: coin_mid_ml has worse rel_prior than alt_hc
    coin_rel = relative_prior_ev(coin_ml["prior_ev"], coin_ml["odds"], haircut)
    alt_rel = relative_prior_ev(alt_hc["prior_ev"], alt_hc["odds"], haircut)
    assert alt_rel is not None and coin_rel is not None
    assert alt_rel > coin_rel


def test_t3_score_breakdown_rel_prior_dominates_mid_alone():
    """w_mid=25 alone cannot outrank a worse mid line with much better rel_prior."""
    haircut = 0.03
    # Mid-band coin with bad rel
    mid_bad = clearability_score(
        odds=2.0,
        prior_ev=-0.10,
        prior_p=0.48,
        is_coin_flip=True,
        is_alt=False,
        haircut=haircut,
    )
    # Also mid-band but better rel + disp + alt (still negative prior_ev)
    mid_good_alt = clearability_score(
        odds=2.05,
        prior_ev=-0.02,
        prior_p=0.52,
        is_coin_flip=False,
        is_alt=True,
        haircut=haircut,
    )
    assert mid_good_alt > mid_bad
