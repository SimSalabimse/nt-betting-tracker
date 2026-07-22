"""
Clearability ranking helpers (HV Research Regime v3 §1.0–1.1).

Pure functions for research-rank only. Never invents recommendable p_model.
Relative-prior ranking works when Stage2 prior_ev is all/mostly negative after
the 3pp haircut (production reality). Soft-book refs are optional.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

# Frozen default weights (PR1). Config may override but production freezes these.
DEFAULT_CLEARABILITY_WEIGHTS: dict[str, float] = {
    "w_mid": 25.0,
    "w_rel_prior": 80.0,
    "w_batch": 20.0,
    "w_coin": -35.0,
    "w_soft": 40.0,
    "w_alt": 14.0,
    "w_short": -55.0,
    "w_struct": 15.0,
    "w_disp": 25.0,
    "w_hist": 15.0,
    "w_cov": 30.0,
    "w_cl_force": 35.0,
    "w_fail": -40.0,
}

# Scaling / thresholds for normalized features
DEFAULT_CLEARABILITY_PARAMS: dict[str, float] = {
    "rel_prior_clip_lo": -0.12,
    "rel_prior_clip_hi": 0.08,
    "rel_prior_scale": 0.08,  # clip / scale → [-1.5, +1]
    "disp_scale": 0.06,  # |prior_p − implied| saturation
    "hist_min_sample": 12.0,
    "fail_raw_ev": -0.05,
    "coin_flip_eps": 0.02,
    "even_market_rel": 0.05,  # |odds_a − odds_b| / mid without prior
    "soft_value_min_rel": 0.08,
    "preferred_odds_lo": 1.85,
    "preferred_odds_hi": 2.60,
}


def implied_prob(odds: float) -> float:
    o = float(odds)
    if o <= 1.0:
        return 1.0
    return 1.0 / o


def fair_ev_after_haircut(odds: float, haircut: float = 0.03) -> float:
    """Pure-implied EV after subtractive haircut: −haircut × odds."""
    return -float(haircut) * float(odds)


def p_needed_for_min_ev(
    odds: float, min_ev: float = 0.02, haircut: float = 0.03
) -> float:
    """Minimum p_model to clear min_ev after haircut at given odds."""
    o = float(odds)
    if o <= 1.0:
        return 0.99
    return min(0.99, max(0.01, (1.0 + float(min_ev)) / o + float(haircut)))


def relative_prior_ev(
    prior_ev: float | None, odds: float, haircut: float = 0.03
) -> float | None:
    """
    prior_ev − fair_ev. ≈0 for market-mimic; >0 means prior beats pure-implied fair.
    None when prior_ev is missing (caller must treat as 0 contribution).
    """
    if prior_ev is None:
        return None
    return float(prior_ev) - fair_ev_after_haircut(odds, haircut)


def clearability_cfg(cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """
    Merge frozen defaults with research.tiers.clearability (and related tier keys).
    """
    cfg = cfg or {}
    research = dict(cfg.get("research") or {})
    tiers = dict(research.get("tiers") or {})
    raw = dict(tiers.get("clearability") or {})

    out: dict[str, Any] = {**DEFAULT_CLEARABILITY_WEIGHTS, **DEFAULT_CLEARABILITY_PARAMS}
    # Prefer tier preferred band / soft when not overridden under clearability:
    if "preferred_odds_lo" not in raw and tiers.get("preferred_odds_lo") is not None:
        out["preferred_odds_lo"] = float(tiers["preferred_odds_lo"])
    if "preferred_odds_hi" not in raw and tiers.get("preferred_odds_hi") is not None:
        out["preferred_odds_hi"] = float(tiers["preferred_odds_hi"])
    if "soft_value_min_rel" not in raw and tiers.get("soft_value_min_rel") is not None:
        out["soft_value_min_rel"] = float(tiers["soft_value_min_rel"])
    out.update(raw)
    return out


def batch_prior_percentile(
    prior_ev: float | None,
    batch_prior_evs: Sequence[float | None] | None,
) -> float | None:
    """
    Percentile rank of prior_ev among finite batch values in [0, 1].
    Returns None when prior missing or fewer than 3 finite priors (w_batch → 0).
    """
    if prior_ev is None or not batch_prior_evs:
        return None
    vals = [float(v) for v in batch_prior_evs if v is not None]
    if len(vals) < 3:
        return None
    target = float(prior_ev)
    # Fraction of batch strictly below + half of ties (standard midrank percentile)
    below = sum(1 for v in vals if v < target - 1e-15)
    ties = sum(1 for v in vals if abs(v - target) <= 1e-15)
    return (below + 0.5 * ties) / float(len(vals))


def is_coin_flip_line(
    *,
    odds: float,
    prior_p: float | None = None,
    peer_odds: float | None = None,
    peer_prior_p: float | None = None,
    both_sides_present: bool = False,
    coin_flip_eps: float = 0.02,
    even_market_rel: float = 0.05,
) -> bool:
    """
    Coin-flip demotion only when both sides of the market are on the board.

    With prior: |implied − prior_p| < coin_flip_eps (market-mimic).
    Without prior: even two-way market |odds_a − odds_b| / mid < even_market_rel.
    """
    if not both_sides_present or peer_odds is None:
        return False
    o_a = float(odds)
    o_b = float(peer_odds)
    if o_a <= 1.0 or o_b <= 1.0:
        return False
    implied_a = implied_prob(o_a)
    if prior_p is not None:
        if abs(implied_a - float(prior_p)) < float(coin_flip_eps):
            return True
        if peer_prior_p is not None and abs(implied_prob(o_b) - float(peer_prior_p)) < float(
            coin_flip_eps
        ):
            # Peer is market-mimic; still demote this side only if we also mimic
            # (caller applies per-line; require this line's prior near implied)
            return abs(implied_a - float(prior_p)) < float(coin_flip_eps)
        return False
    mid = 0.5 * (o_a + o_b)
    if mid <= 0:
        return False
    return abs(o_a - o_b) / mid < float(even_market_rel)


def is_alt_preferred_macro(family: str | None, selection: str | None) -> bool:
    """HC / alt totals (non-2.5) / period macros preferred for research expansion."""
    fam = (family or "").lower()
    sel = (selection or "").lower()
    if fam == "handicap" or "handikap" in sel:
        return True
    if fam == "period" or "1. omgang" in sel or "1. sett" in sel:
        return True
    if fam in ("totals_over", "totals_under", "ou_other") and "2.5" not in sel:
        return True
    if ("3.5" in sel or "4.5" in sel) and (
        "over" in sel or "under" in sel or "totalt" in sel
    ):
        return True
    return False


def _clip(x: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(x)))


def clearability_score(
    *,
    odds: float,
    prior_ev: float | None = None,
    prior_p: float | None = None,
    haircut: float = 0.03,
    batch_percentile: float | None = None,
    is_coin_flip: bool = False,
    soft_decimal_odds: float | None = None,
    is_alt: bool = False,
    is_short_main: bool = False,
    has_structural_note: bool = False,
    family_hist_n: int = 0,
    force_coverage_active: bool = False,
    force_clearability_active: bool = False,
    has_pack: bool = False,
    raw_ev: float | None = None,
    weights: Mapping[str, Any] | None = None,
    cfg: Mapping[str, Any] | None = None,
) -> float:
    """
    Non-vacuous clearability rank score (research only).

    Missing prior → w_rel_prior and w_disp contribute 0.
    Soft refs optional; coin-flip only when caller sets is_coin_flip True.
    """
    p = clearability_cfg(cfg)
    if weights:
        p = {**p, **dict(weights)}

    o = float(odds)
    score = 0.0

    pref_lo = float(p.get("preferred_odds_lo") or 1.85)
    pref_hi = float(p.get("preferred_odds_hi") or 2.60)
    if pref_lo <= o <= pref_hi:
        score += float(p["w_mid"])

    rel = relative_prior_ev(prior_ev, o, haircut)
    if rel is not None:
        clip_lo = float(p["rel_prior_clip_lo"])
        clip_hi = float(p["rel_prior_clip_hi"])
        scale = float(p["rel_prior_scale"]) or 0.08
        norm = _clip(rel, clip_lo, clip_hi) / scale  # [-1.5, +1]
        score += float(p["w_rel_prior"]) * norm

    if batch_percentile is not None:
        bp = _clip(float(batch_percentile), 0.0, 1.0)
        score += float(p["w_batch"]) * bp

    if is_coin_flip:
        score += float(p["w_coin"])  # typically negative

    soft_rel = float(p.get("soft_value_min_rel") or 0.08)
    if soft_decimal_odds is not None and o > 1.0:
        try:
            soft = float(soft_decimal_odds)
        except (TypeError, ValueError):
            soft = 0.0
        if soft >= o * (1.0 + soft_rel):
            score += float(p["w_soft"])

    if is_alt:
        score += float(p["w_alt"])

    if is_short_main:
        score += float(p["w_short"])  # typically negative

    if has_structural_note:
        score += float(p["w_struct"])

    if prior_p is not None and o > 1.0:
        disp = abs(float(prior_p) - implied_prob(o))
        disp_scale = float(p["disp_scale"]) or 0.06
        score += min(1.0, disp / disp_scale) * float(p["w_disp"])

    hist_min = int(float(p.get("hist_min_sample") or 12))
    if int(family_hist_n) >= hist_min:
        score += float(p["w_hist"])

    if force_coverage_active:
        score += float(p["w_cov"])

    if force_clearability_active:
        score += float(p["w_cl_force"])

    fail_thr = float(p.get("fail_raw_ev") if p.get("fail_raw_ev") is not None else -0.05)
    if has_pack and raw_ev is not None and float(raw_ev) < fail_thr:
        score += float(p["w_fail"])  # typically negative

    return round(float(score), 3)


def promotion_score_v3(
    clearability: float,
    board_score: float | None = None,
) -> float:
    """Cap legacy board contribution so shortlist scores cannot re-dominate."""
    board = 0.0
    if board_score is not None:
        board = min(15.0, 0.1 * float(board_score))
    return round(float(clearability) + board, 3)


def score_candidates(
    candidates: Iterable[Mapping[str, Any]],
    *,
    haircut: float = 0.03,
    cfg: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Score a batch of candidate dicts; attaches clearability_score + batch percentile.

    Expected keys (optional unless noted):
      odds (required), prior_ev, prior_p, is_coin_flip, soft_decimal_odds,
      is_alt, is_short_main, has_structural_note, family_hist_n,
      force_coverage_active, force_clearability_active, has_pack, raw_ev,
      board_score
    """
    rows = [dict(c) for c in candidates]
    batch_evs = [r.get("prior_ev") for r in rows]
    out: list[dict[str, Any]] = []
    for r in rows:
        odds = float(r["odds"])
        pev = r.get("prior_ev")
        if pev is not None:
            pev = float(pev)
        pp = r.get("prior_p")
        if pp is not None:
            pp = float(pp)
        bp = batch_prior_percentile(pev, batch_evs)
        cl = clearability_score(
            odds=odds,
            prior_ev=pev,
            prior_p=pp,
            haircut=haircut,
            batch_percentile=bp,
            is_coin_flip=bool(r.get("is_coin_flip")),
            soft_decimal_odds=r.get("soft_decimal_odds"),
            is_alt=bool(r.get("is_alt")),
            is_short_main=bool(r.get("is_short_main")),
            has_structural_note=bool(r.get("has_structural_note")),
            family_hist_n=int(r.get("family_hist_n") or 0),
            force_coverage_active=bool(r.get("force_coverage_active")),
            force_clearability_active=bool(r.get("force_clearability_active")),
            has_pack=bool(r.get("has_pack")),
            raw_ev=r.get("raw_ev"),
            cfg=cfg,
        )
        promo = promotion_score_v3(cl, r.get("board_score"))
        r["rel_prior"] = relative_prior_ev(pev, odds, haircut)
        r["batch_percentile"] = bp
        r["clearability_score"] = cl
        r["promotion_score_v3"] = promo
        out.append(r)
    out.sort(key=lambda x: float(x.get("clearability_score") or 0.0), reverse=True)
    return out
