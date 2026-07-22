"""
Multi-stage quantitative pre-filter (research funnel).

Stage 1 — Fast screens: hard-discard noise / impossible EV / ultra-short chalk.
Stage 2 — Lightweight classical prior: family anchor + implied blend; prior EV
          after the same 5pp haircut as recommend (does not change haircut).

Research-ranking only — never invents recommendable p_model.
Clean-restart neutral: no learning.json / sport mults.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from nt.defaults import research_cfg
from nt.research_gates.infer import selection_family


def prefilter_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    rcfg = research_cfg(cfg)
    raw = dict(rcfg.get("prefilter") or {})
    stage1 = dict(raw.get("stage1") or {})
    stage2 = dict(raw.get("stage2") or {})
    defaults = {
        "enabled": True,
        "target_discard_share": 0.70,
        "stage1": {
            "enabled": True,
            "max_p_needed": 0.78,
            "drop_short_chalk_ml": True,
            "drop_noise_specials": True,
            "drop_ultra_short_alts": True,
            "ultra_short_alt_odds": 1.55,
        },
        "stage2": {
            "enabled": True,
            # Absolute floor (after 5pp haircut). Fair mid-band sits near -haircut*odds
            # (~-0.09 @1.90); only discard if worse than that by slack AND under floor.
            "min_prior_ev": -0.12,
            "short_odds_prior_ev_floor": -0.08,
            "prior_ev_slack_vs_fair": 0.04,
            "blend_weight_implied": 0.55,
            "require_prior": False,
            "base_rate_conflict_delta": 0.18,
        },
    }
    s1 = {**defaults["stage1"], **stage1}
    s2 = {**defaults["stage2"], **stage2}
    out = {**defaults, **raw, "stage1": s1, "stage2": s2}
    return out


def _tiers_odds_bounds(cfg: dict[str, Any]) -> tuple[float, float, float]:
    rcfg = research_cfg(cfg)
    t = dict(rcfg.get("tiers") or {})
    return (
        float(t.get("fail_odds_below") or 1.35),
        float(t.get("fail_odds_above") or 4.0),
        float(t.get("short_chalk_odds") or 1.70),
    )


def _preferred_odds_lo(cfg: dict[str, Any]) -> float:
    rcfg = research_cfg(cfg)
    t = dict(rcfg.get("tiers") or {})
    return float(t.get("preferred_odds_lo") or 1.85)


def _haircut_min_ev(cfg: dict[str, Any]) -> tuple[float, float]:
    sel = cfg.get("selection") or {}
    return (
        float(sel.get("probability_haircut", 0.03)),
        float(sel.get("standard_min_ev", 0.02)),
    )


def p_needed_for_min_ev(odds: float, min_ev: float = 0.02, haircut: float = 0.03) -> float:
    if odds <= 1.0:
        return 0.99
    return min(0.99, max(0.01, (1.0 + min_ev) / odds + haircut))


def prior_ev(prior_p: float, odds: float, haircut: float = 0.03) -> float:
    """Research-only EV using the same subtractive haircut as recommend."""
    return float(prior_p - haircut) * float(odds) - 1.0


def is_noise_special(selection: str, odds: float) -> bool:
    """Shareable noise heuristic (aligned with market_coverage)."""
    sel = (selection or "").lower()
    if odds >= 50:
        return True
    if re.search(r"100 sekund|minst 3 mål|scorer før det er spilt 15", sel):
        return True
    if odds >= 25 and ("&" in selection or " og " in sel):
        return True
    if re.search(r"korrekt resultat|score \d+-\d+|6-0|0-6", sel):
        return True
    if odds >= 12 and re.search(r"eksakt|exact score|korrekt resultat", sel):
        return True
    return False


def _is_ou25(selection: str) -> bool:
    s = (selection or "").lower()
    return "2.5" in s and ("over" in s or "under" in s or "over/under" in s)


def _is_first_goal(selection: str) -> bool:
    s = (selection or "").lower()
    return bool(re.search(r"1\.\s*mål|first goal|første mål", s, re.I))


def _is_ml_family(family: str, selection: str) -> bool:
    fam = (family or "").lower()
    if fam == "ml" or fam.startswith("ml_"):
        return True
    s = (selection or "").lower()
    return "vinner" in s or "to win" in s or re.search(r"\bhub\b", s) is not None


def _is_short_main(
    selection: str, odds: float, family: str, *, short_chalk: float, pref_lo: float = 1.85
) -> bool:
    if float(odds) >= float(pref_lo):
        return False
    if _is_ou25(selection) or _is_first_goal(selection):
        return True
    return _is_ml_family(family, selection)


@dataclass
class PrefilterResult:
    stage1_pass: bool
    stage1_reason: str
    stage2_pass: bool
    stage2_reason: str
    prior_p: float | None = None
    prior_ev: float | None = None
    prior_available: bool = False
    base_rate_conflict: bool = False
    rank_score: float = 0.0
    discarded: bool = False
    discard_stage: str = ""  # "" | "stage1" | "stage2"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stage1_fast_screen(
    *,
    selection: str,
    odds: float,
    sport: str = "",
    family: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """
    Stage 1 hard screens. Returns (pass, reason).
    Does not invent p_model; never reads learning.
    """
    cfg = cfg or {}
    pcfg = prefilter_cfg(cfg)
    s1 = pcfg.get("stage1") or {}
    if not pcfg.get("enabled", True) or not s1.get("enabled", True):
        return True, "stage1_disabled"

    odds = float(odds)
    fam = family or selection_family(selection, (sport or "").lower())
    lo_fail, hi_fail, short_chalk = _tiers_odds_bounds(cfg)
    haircut, min_ev = _haircut_min_ev(cfg)
    need_p = p_needed_for_min_ev(odds, min_ev, haircut)
    max_need = float(s1.get("max_p_needed") or 0.78)

    if odds < lo_fail:
        return False, f"stage1:odds_below_{lo_fail}"
    if odds > hi_fail:
        return False, f"stage1:odds_above_{hi_fail}"
    if bool(s1.get("drop_noise_specials", True)) and is_noise_special(selection, odds):
        return False, "stage1:noise_special"
    if need_p >= max_need:
        return False, f"stage1:ev_impossible_need_p>={max_need}"
    if bool(s1.get("drop_short_chalk_ml", True)) and odds < short_chalk:
        if _is_short_main(selection, odds, fam, short_chalk=short_chalk):
            # High-Volume v2: allow short-main < short_chalk only with strong data
            # (rough p_needed ≤ strong_data_p_needed — unusually strong edge)
            strong_need = float(s1.get("strong_data_p_needed") or 0.55)
            if need_p <= strong_need + 1e-12:
                return True, f"stage1:short_chalk_strong_data_need_p<={strong_need}"
            return False, f"stage1:short_chalk_ml_ou_lt_{short_chalk}"

    # Ultra-short non-main alts (1.45–1.55 HC etc.) rarely clear Calibration EV bars
    if bool(s1.get("drop_ultra_short_alts", True)):
        ultra = float(s1.get("ultra_short_alt_odds") or 1.55)
        if odds < ultra and not _is_short_main(selection, odds, fam, short_chalk=short_chalk):
            return False, f"stage1:ultra_short_alt_lt_{ultra}"

    return True, "stage1:pass"


def family_prior_anchor(
    *,
    selection: str,
    family: str,
    sport: str,
    odds: float,
) -> tuple[float | None, str]:
    """
    Clean-restart-safe family anchors (constants only).
    Returns (anchor_p or None if unknown, note).
    """
    fam = (family or "").lower()
    sel = (selection or "").lower()
    sp = (sport or "").lower()
    implied = 1.0 / odds if odds > 1.0 else 0.5

    # Handicap / spread — fair-line prior near 0.50
    if fam == "handicap" or "handikap" in sel:
        return 0.50, "hc_fair"

    # Totals
    if "totalt" in sel or fam in ("totals_over", "totals_under", "ou_25", "ou_other"):
        is_over = "over" in sel and "under" not in sel.split("over")[0][-8:]
        # crude: "Under" / "Over" token
        if re.search(r"\bunder\b", sel):
            is_over = False
        elif re.search(r"\bover\b", sel):
            is_over = True
        else:
            is_over = "over" in sel
        if sp in ("football", "soccer") and "2.5" in sel:
            base = 0.52 if is_over else 0.48
            return base, "fb_ou25"
        if sp == "tennis":
            return 0.50, "tennis_games_ou"
        if sp in ("esports", "counter-strike", "cs2"):
            return 0.42 if is_over and "2.5" in sel else 0.50, "esports_maps"
        return 0.50, "totals_neutral"

    # BTTS
    if "btts" in fam or "begge lag" in sel or "both teams" in sel:
        yes = "ja" in sel or "yes" in sel
        return (0.52 if yes else 0.48), "btts"

    # ML / HUB
    if _is_ml_family(fam, selection):
        # 3-way draw token
        if re.search(r"\buavgjort\b|\bdraw\b|\bx\b", sel) and odds > 2.5:
            return 0.28, "hub_draw"
        # Mild fav anchor vs dog — still blended with implied later
        if odds < 1.90:
            return 0.55, "ml_fav_band"
        if odds >= 2.50:
            return 0.38, "ml_dog_band"
        return 0.48, "ml_mid"

    # First goal / props — fail-closed (no strong anchor)
    if _is_first_goal(selection) or fam in ("props", "player", "goalscorer"):
        return None, "no_anchor_props"

    # Period / set winners — mild
    if "sett" in sel or "period" in fam or "1. sett" in sel or "1. omgang" in sel:
        return 0.50, "period_neutral"

    return None, "no_anchor"


def stage2_classical_prior(
    *,
    selection: str,
    odds: float,
    sport: str = "",
    family: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> tuple[bool, str, float | None, float | None, bool, bool]:
    """
    Stage 2 classical prior.

    Returns:
      (pass, reason, prior_p, prior_ev, prior_available, base_rate_conflict)
    """
    cfg = cfg or {}
    pcfg = prefilter_cfg(cfg)
    s2 = pcfg.get("stage2") or {}
    if not pcfg.get("enabled", True) or not s2.get("enabled", True):
        return True, "stage2_disabled", None, None, False, False

    odds = float(odds)
    fam = family or selection_family(selection, (sport or "").lower())
    haircut, _min_ev = _haircut_min_ev(cfg)
    blend_w = float(s2.get("blend_weight_implied") or 0.55)
    blend_w = min(0.95, max(0.05, blend_w))
    min_prior_ev = float(s2.get("min_prior_ev") if s2.get("min_prior_ev") is not None else -0.12)
    short_floor = float(
        s2.get("short_odds_prior_ev_floor")
        if s2.get("short_odds_prior_ev_floor") is not None
        else -0.08
    )
    slack = float(
        s2.get("prior_ev_slack_vs_fair") if s2.get("prior_ev_slack_vs_fair") is not None else 0.04
    )
    require_prior = bool(s2.get("require_prior", False))
    br_delta = float(s2.get("base_rate_conflict_delta") or 0.18)
    pref_lo = _preferred_odds_lo(cfg)

    implied = 1.0 / odds if odds > 1.0 else 0.5
    anchor, note = family_prior_anchor(
        selection=selection, family=fam, sport=sport, odds=odds
    )

    if anchor is None:
        if require_prior:
            return False, "stage2:prior_unavailable", None, None, False, False
        # Fail-closed: no invent boost; still pass funnel
        return True, f"stage2:pass_no_prior({note})", None, None, False, False

    prior_p = blend_w * implied + (1.0 - blend_w) * float(anchor)
    prior_p = min(0.95, max(0.05, prior_p))
    pev = prior_ev(prior_p, odds, haircut)
    # Fair line after same haircut: always ≈ -haircut * odds (no edge claim)
    fair_ev = -haircut * odds

    # Base-rate conflict: short chalk fighting prior hard
    br_conflict = False
    _, _, short_chalk = _tiers_odds_bounds(cfg)
    if odds < short_chalk and (prior_p + br_delta) < implied:
        # prior much lower than market-implied short fav → conflict for promote
        br_conflict = True

    # Short prices (below preferred band) need a tighter prior-EV floor
    floor = short_floor if odds < pref_lo else min_prior_ev
    # Discard only if both: worse than floor AND worse than fair-by-slack
    hopeless = pev < floor and pev < (fair_ev - slack)
    if hopeless:
        return (
            False,
            f"stage2:prior_ev_hopeless (ev={pev:.3f}<{floor:.3f},{note})",
            round(prior_p, 4),
            round(pev, 4),
            True,
            br_conflict,
        )

    if br_conflict and _is_short_main(
        selection, odds, fam, short_chalk=short_chalk
    ):
        return (
            False,
            f"stage2:base_rate_conflict({note})",
            round(prior_p, 4),
            round(pev, 4),
            True,
            True,
        )

    return (
        True,
        f"stage2:pass({note})",
        round(prior_p, 4),
        round(pev, 4),
        True,
        False,
    )


def rank_score_from_prior(
    *,
    odds: float,
    prior_ev_val: float | None,
    family: str,
    selection: str,
) -> float:
    """Higher = better candidate for deep research (not p_model)."""
    score = 50.0
    if prior_ev_val is not None:
        score += max(-30.0, min(30.0, 100.0 * float(prior_ev_val)))
    # mild mid-band preference (aligned with survivable band)
    if 1.85 <= odds <= 2.60:
        score += 15.0
    elif 1.80 <= odds < 1.85:
        score += 8.0
    elif 1.70 <= odds < 1.80:
        score += 2.0
    fam = (family or "").lower()
    sel = (selection or "").lower()
    if fam == "handicap" or "handikap" in sel:
        score += 5.0
    if "3.5" in sel or "4.5" in sel:
        score += 5.0
    return round(score, 3)


def run_prefilter(
    *,
    selection: str,
    odds: float,
    sport: str = "",
    family: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> PrefilterResult:
    """Full Stage1 → Stage2 pipeline for one line."""
    cfg = cfg or {}
    pcfg = prefilter_cfg(cfg)
    if not pcfg.get("enabled", True):
        return PrefilterResult(
            stage1_pass=True,
            stage1_reason="prefilter_disabled",
            stage2_pass=True,
            stage2_reason="prefilter_disabled",
            rank_score=50.0,
            discarded=False,
        )

    fam = family or selection_family(selection, (sport or "").lower())
    s1_ok, s1_reason = stage1_fast_screen(
        selection=selection, odds=odds, sport=sport, family=fam, cfg=cfg
    )
    if not s1_ok:
        return PrefilterResult(
            stage1_pass=False,
            stage1_reason=s1_reason,
            stage2_pass=False,
            stage2_reason="skipped_after_stage1",
            discarded=True,
            discard_stage="stage1",
            rank_score=0.0,
        )

    s2_ok, s2_reason, pp, pev, pavail, brc = stage2_classical_prior(
        selection=selection, odds=odds, sport=sport, family=fam, cfg=cfg
    )
    rs = rank_score_from_prior(
        odds=float(odds), prior_ev_val=pev, family=fam, selection=selection
    )
    if not s2_ok:
        return PrefilterResult(
            stage1_pass=True,
            stage1_reason=s1_reason,
            stage2_pass=False,
            stage2_reason=s2_reason,
            prior_p=pp,
            prior_ev=pev,
            prior_available=pavail,
            base_rate_conflict=brc,
            rank_score=rs,
            discarded=True,
            discard_stage="stage2",
        )

    return PrefilterResult(
        stage1_pass=True,
        stage1_reason=s1_reason,
        stage2_pass=True,
        stage2_reason=s2_reason,
        prior_p=pp,
        prior_ev=pev,
        prior_available=pavail,
        base_rate_conflict=brc,
        rank_score=rs,
        discarded=False,
        discard_stage="",
    )


def prefilter_batch_stats(results: list[PrefilterResult]) -> dict[str, Any]:
    n = len(results)
    if n == 0:
        return {
            "n": 0,
            "stage1_pass_n": 0,
            "stage2_pass_n": 0,
            "discard_n": 0,
            "discard_share": 0.0,
            "stage1_discard_n": 0,
            "stage2_discard_n": 0,
        }
    s1 = sum(1 for r in results if r.stage1_pass)
    s2 = sum(1 for r in results if r.stage2_pass and r.stage1_pass)
    disc = sum(1 for r in results if r.discarded)
    return {
        "n": n,
        "stage1_pass_n": s1,
        "stage2_pass_n": s2,
        "discard_n": disc,
        "discard_share": round(disc / n, 3),
        "stage1_discard_n": sum(1 for r in results if r.discard_stage == "stage1"),
        "stage2_discard_n": sum(1 for r in results if r.discard_stage == "stage2"),
    }
