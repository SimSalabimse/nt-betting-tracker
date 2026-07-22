from __future__ import annotations

"""
Tiered research — Stage 1 (Light) vs Stage 2 (Deep).

Light: broad, structured, fast filter over most of the shortlist.
Deep: full evidence/*.json + p_model (only deep lines may be recommended).

Coverage targets (config research.tiers):
  light_coverage_target: 0.70–1.0 of shortlist
  min_light_per_sport_when_n: if sport has ≥N shortlist lines, light at least K
"""

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import odds_band, utc_now
from nt.config import path_from_config
from nt.defaults import research_cfg
from nt.odds_parse import Candidate, attach_evidence, parse_odds_file
from nt.research_gates.infer import selection_family


def tiers_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    rcfg = research_cfg(cfg)
    raw = dict(rcfg.get("tiers") or {})
    defaults = {
        "light_coverage_target": 0.85,  # fraction of shortlist
        "light_coverage_min_n": 8,  # always light at least this many if shortlist ≥ this
        "min_light_per_sport_when_n": 5,  # if sport has ≥5 shortlist lines…
        "min_light_per_sport": 3,  # …light at least 3
        "deep_target_n": 8,  # High-Volume v2: focused deep queue
        "deep_max_n": 12,  # cap deep promotions
        "auto_light_on_board": True,
        "auto_promote_to_deep": False,  # assess never promotes (P1)
        "engine_deep_queue": True,  # P0: engine fills deep_queue via anti-chalk scorer
        "deep_min_preferred_share": 0.55,
        "deep_max_short_main_share": 0.25,
        "short_chalk_odds": 1.70,
        "preferred_odds_lo": 1.85,
        "preferred_odds_hi": 2.60,
        "alt_preferred_odds_lo": 1.80,  # non-main alts only preferred if ≥ this
        "promo_mid_band_boost": 60.0,
        "promo_alt_boost": 14.0,
        "promo_short_chalk_penalty": -55.0,
        "soft_value_min_rel": 0.08,
        "fail_odds_below": 1.35,  # light-fail ultra-short unless exceptional
        "fail_odds_above": 4.0,  # light-fail longshots without deep plan
        "pass_odds_lo": 1.45,
        "pass_odds_hi": 2.60,
        # HV v3 dual-track clearability promotion + EV-fail refresh
        "clearability_promotion": True,
        "dual_track_deep_queue": True,
        "second_pass_from_dump": True,
        "second_pass_max_inject": 12,
        "raw_ev_exhausted": -0.05,
        "second_pass_min_deep_packs": 8,
    }
    return {**defaults, **raw}


def dual_track_sizes(
    target: int,
    *,
    coverage_overlay_active: bool = False,
    clearability_overlay_active: bool = False,
) -> tuple[int, int]:
    """
    Frozen dual-track split (design §1.3).

    clearable_n = min(8, max(5, round(0.70 * target))) clamped to target;
    coverage_n = remainder. Force flags raise the corresponding floor.

    Single-flag behaviour (unchanged):
      force_coverage → coverage_n = max(base, min(4, target//2)); clearable rest
      force_clearability → clearable_n = max(base, min(8, round(0.80*target))); cov rest

    Both flags: raise each floor from base, then **joint proportional scale** if
    sum > target so neither floor fully undoes the other (e.g. target=8 both →
    raised (6,4) scales to (5,3) not clearability-only (6,2)).
    """
    target = max(0, int(target))
    if target <= 0:
        return 0, 0
    base_cl = min(8, max(5, int(round(0.70 * target))))
    base_cl = min(base_cl, target)
    base_cov = target - base_cl

    cov_force = bool(coverage_overlay_active)
    cl_force = bool(clearability_overlay_active)

    if cov_force and not cl_force:
        coverage_n = max(base_cov, min(4, target // 2))
        clearable_n = target - coverage_n
        return int(clearable_n), int(coverage_n)

    if cl_force and not cov_force:
        clearable_n = max(base_cl, min(8, int(round(0.80 * target))))
        clearable_n = min(clearable_n, target)
        coverage_n = target - clearable_n
        return int(clearable_n), int(coverage_n)

    if cov_force and cl_force:
        cov_floor = min(4, target // 2)
        cl_floor = min(8, int(round(0.80 * target)))
        clearable_n = max(base_cl, cl_floor)
        coverage_n = max(base_cov, cov_floor)
        total = clearable_n + coverage_n
        if total > target:
            # Proportional joint scale of raised pair
            clearable_n = int(round(clearable_n * target / float(total)))
            clearable_n = max(0, min(target, clearable_n))
            coverage_n = target - clearable_n
            if target >= 2:
                if coverage_n < 1:
                    coverage_n = 1
                    clearable_n = target - 1
                elif clearable_n < 1:
                    clearable_n = 1
                    coverage_n = target - 1
        else:
            leftover = target - total
            clearable_n += leftover  # clearability-primary remainder
        return int(clearable_n), int(coverage_n)

    return int(base_cl), int(base_cov)


def ev_fail_refresh_triggered(
    *,
    n_packs_with_p: int,
    n_raw_ev_pass: int,
    mid_unresearched: int,
    min_deep_packs: int = 8,
) -> bool:
    """
    Auto EV-fail refresh trigger (design §1b).

    n_packs_with_p >= min_deep_packs AND n_raw_ev_pass == 0 AND mid_unresearched == 0.
    Operator second-pass bypasses this via force=True on research_second_pass.
    """
    return (
        int(n_packs_with_p) >= int(min_deep_packs)
        and int(n_raw_ev_pass) == 0
        and int(mid_unresearched) == 0
    )


def _haircut_from_cfg(cfg: dict[str, Any]) -> float:
    sel = cfg.get("selection") or {}
    return float(sel.get("probability_haircut", 0.03))


def _active_clearability_overlay(cfg: dict[str, Any]) -> dict[str, Any]:
    """Best-effort force_clearability_priority active flag (PR6 owns full signal path)."""
    try:
        from nt.control_signals import load_all_signals

        now_active = False
        for rec in load_all_signals(cfg):
            if str(rec.get("kind") or "") != "force_clearability_priority":
                continue
            if rec.get("revoked"):
                continue
            now_active = True
            break
        return {"active": now_active}
    except Exception:
        return {"active": False}


def _is_structural_note(rec: "LightRecord") -> bool:
    notes = f"{rec.strength_notes or ''} {rec.rough_ev_note or ''} {rec.reason or ''}"
    low = notes.lower()
    if "structural" in low or "injury" in low or "rotation" in low:
        return True
    need = rec.rough_p_needed
    if need is not None and float(need) <= 0.55 and not _is_first_goal(rec.selection):
        return True
    return False


def _peer_odds_map(
    records: list["LightRecord"],
) -> dict[tuple[str, str], list[tuple[float, "LightRecord"]]]:
    """Group by (match, family) for coin-flip pairing."""
    groups: dict[tuple[str, str], list[tuple[float, LightRecord]]] = defaultdict(list)
    for r in records:
        fam = (r.market_family or selection_family(r.selection, (r.sport or "").lower()) or "").lower()
        groups[(r.match or "", fam)].append((float(r.decimal_odds), r))
    return groups


def _coin_flip_for_record(
    rec: "LightRecord",
    groups: dict[tuple[str, str], list[tuple[float, "LightRecord"]]],
    cfg: dict[str, Any] | None = None,
) -> bool:
    from nt.clearability import clearability_cfg, is_coin_flip_line

    p = clearability_cfg(cfg)
    fam = (rec.market_family or selection_family(rec.selection, (rec.sport or "").lower()) or "").lower()
    peers = groups.get((rec.match or "", fam)) or []
    if len(peers) < 2:
        return False
    # Peer = other side with different selection token
    peer_odds = None
    for o, other in peers:
        if other.key() == rec.key():
            continue
        # Prefer opposite OU / other ML side
        peer_odds = o
        break
    if peer_odds is None:
        return False
    return is_coin_flip_line(
        odds=float(rec.decimal_odds),
        prior_p=rec.prior_p,
        peer_odds=float(peer_odds),
        both_sides_present=True,
        coin_flip_eps=float(p.get("coin_flip_eps") or 0.02),
        even_market_rel=float(p.get("even_market_rel") or 0.05),
        market_family=fam,
        selection=rec.selection,
    )


def parse_odds_band(band: str | None) -> tuple[float, float | None]:
    """
    Parse force_coverage / target odds band strings.
    Supports: "1.85-2.60", "1.90+", "1.85+", bare "1.90".
    Returns (lo, hi) with hi=None meaning open-ended.
    """
    raw = str(band or "").strip()
    if not raw:
        return 1.85, 2.60
    m = re.match(
        r"^\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*$",
        raw,
    )
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*\+\s*$", raw)
    if m:
        return float(m.group(1)), None
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*$", raw)
    if m:
        return float(m.group(1)), None
    return 1.85, 2.60


def _is_ou25(selection: str) -> bool:
    s = (selection or "").lower()
    return "2.5" in s and ("over" in s or "under" in s or "over/under" in s)


def _is_first_goal(selection: str) -> bool:
    s = (selection or "").lower()
    return bool(
        re.search(r"1\.\s*mål|first goal|første mål", s, re.I)
    )


def _is_ml_family(family: str, selection: str) -> bool:
    fam = (family or "").lower()
    if fam == "ml" or fam.startswith("ml_"):
        return True
    s = (selection or "").lower()
    return "vinner" in s or "to win" in s or re.search(r"\bhub\b", s) is not None


def is_short_main_line(
    selection: str,
    odds: float,
    family: str,
    *,
    preferred_odds_lo: float = 1.85,
) -> bool:
    """Short favourite ML / O2.5 / first-goal under preferred odds floor."""
    if float(odds) >= float(preferred_odds_lo):
        return False
    if _is_ou25(selection) or _is_first_goal(selection):
        return True
    return _is_ml_family(family, selection)


def is_preferred_line(
    selection: str,
    odds: float,
    family: str,
    *,
    preferred_odds_lo: float = 1.85,
    alt_preferred_odds_lo: float = 1.80,
) -> bool:
    """
    Survivable preferred for deep-queue composition.

    - Odds ≥ preferred_odds_lo (default 1.85), OR
    - Non short-main (HC / alt totals / period / dogs markets) with odds ≥ alt_preferred_odds_lo (1.80).

    Short alts below alt_preferred_odds_lo do NOT pad the preferred floor
    (they fail Calibration min-EV after 5pp haircut too often).
    """
    o = float(odds)
    if o >= float(preferred_odds_lo):
        return True
    if o < float(alt_preferred_odds_lo):
        return False
    return not is_short_main_line(
        selection, odds, family, preferred_odds_lo=preferred_odds_lo
    )


def _parse_soft_odds(item: dict[str, Any] | None, rec: "LightRecord | None" = None) -> float | None:
    """Optional soft-book ref; never invent. Fail-closed if absent/invalid."""
    if item:
        raw = item.get("soft_decimal_odds")
        if raw is not None:
            try:
                v = float(raw)
                if v > 1.01:
                    return v
            except (TypeError, ValueError):
                pass
        notes = str(item.get("notes") or "")
        m = re.search(r"soft_odds\s*=\s*([0-9]+(?:\.[0-9]+)?)", notes, re.I)
        if m:
            try:
                v = float(m.group(1))
                if v > 1.01:
                    return v
            except ValueError:
                pass
    if rec and rec.strength_notes:
        m = re.search(r"soft_odds\s*=\s*([0-9]+(?:\.[0-9]+)?)", rec.strength_notes, re.I)
        if m:
            try:
                v = float(m.group(1))
                if v > 1.01:
                    return v
            except ValueError:
                pass
    return None


def promotion_score(
    rec: "LightRecord",
    cfg: dict[str, Any],
    *,
    soft_odds: float | None = None,
    board_score: float = 0.0,
    coverage_overlay: dict[str, Any] | None = None,
) -> float:
    """
    Anti-chalk promotion score for deep worklist.
    Higher = more worth deep research. Does not invent p_model.
    Heavily favors survivable band 1.85–2.60; demotes short chalk.
    """
    tcfg = tiers_cfg(cfg)
    odds = float(rec.decimal_odds)
    family = rec.market_family or selection_family(rec.selection, (rec.sport or "").lower())
    short_chalk = float(tcfg["short_chalk_odds"])
    pref_lo = float(tcfg["preferred_odds_lo"])
    pref_hi = float(tcfg["preferred_odds_hi"])
    alt_lo = float(tcfg.get("alt_preferred_odds_lo") or short_chalk)
    soft_rel = float(tcfg["soft_value_min_rel"])

    mid_boost = float(tcfg.get("promo_mid_band_boost") or 60.0)
    alt_boost = float(tcfg.get("promo_alt_boost") or 14.0)
    short_pen = float(tcfg.get("promo_short_chalk_penalty") or -55.0)

    score = 50.0
    # Odds band — primary research band is preferred_lo–preferred_hi (High-Volume v2)
    if pref_lo <= odds <= pref_hi:
        score += mid_boost
    elif alt_lo <= odds < pref_lo:
        score += 20.0
    elif pref_hi < odds <= 3.20:
        score += 12.0
    elif odds < short_chalk:
        # Hard demote short chalk unless structural edge note (strong data)
        structural = False
        need = rec.rough_p_needed
        if need is not None and float(need) <= 0.55 and not _is_first_goal(rec.selection):
            structural = True
        score += -15.0 if structural else short_pen

    preferred = is_preferred_line(
        rec.selection,
        odds,
        family,
        preferred_odds_lo=pref_lo,
        alt_preferred_odds_lo=alt_lo,
    )
    short_main = is_short_main_line(rec.selection, odds, family, preferred_odds_lo=pref_lo)
    if preferred and not short_main:
        score += 25.0
    if short_main:
        score -= 30.0
    # Alt totals / HC / period explicit (boosted High-Volume v2)
    fam = (family or "").lower()
    sel = (rec.selection or "").lower()
    if fam == "handicap" or "handikap" in sel:
        score += alt_boost
    if "3.5" in sel or "4.5" in sel or fam in ("totals_over", "totals_under") and "2.5" not in sel:
        score += alt_boost
    if fam == "period" or "1. omgang" in sel or "1. sett" in sel:
        score += 6.0

    if soft_odds is not None and odds > 1.0:
        if soft_odds >= odds * (1.0 + soft_rel):
            score += 30.0

    ov = coverage_overlay or {}
    if ov.get("active"):
        # Boost target band / prefer tags under force_coverage_priority
        band_lo, band_hi = parse_odds_band(str(ov.get("target_odds_band") or "1.85-2.60"))
        in_band = odds >= band_lo and (band_hi is None or odds <= band_hi)
        if in_band:
            score += float(ov.get("weight_boost") or 30.0)
        prefer = [str(x).lower() for x in (ov.get("prefer") or [])]
        if "handicaps" in prefer and (fam == "handicap" or "handikap" in sel):
            score += 10.0
        if "alt_totals" in prefer and ("3.5" in sel or "4.5" in sel or "totalt" in sel):
            score += 10.0
        if "period" in prefer and (fam == "period" or "1. omgang" in sel or "1. sett" in sel):
            score += 10.0
        if "dogs" in prefer and odds >= pref_lo and _is_ml_family(family, rec.selection):
            score += 10.0

    if board_score:
        score += min(15.0, 0.1 * float(board_score))

    # Stage-2 classical prior EV (research-rank only; never invent when missing)
    if rec.prior_available and rec.prior_ev is not None:
        pev = float(rec.prior_ev)
        if pev > 0:
            score += min(25.0, 80.0 * pev)
        elif pev < -0.02:
            score += max(-25.0, 60.0 * pev)

    return round(score, 3)


def build_deep_queue(
    records: list["LightRecord"],
    cfg: dict[str, Any],
    *,
    soft_by_key: dict[tuple[str, str], float | None] | None = None,
    board_score_by_key: dict[tuple[str, str], float] | None = None,
    coverage_overlay: dict[str, Any] | None = None,
    clearability_overlay: dict[str, Any] | None = None,
    mode: str = "normal",
    inject_records: list["LightRecord"] | None = None,
    pack_meta_by_key: dict[tuple[str, str], dict[str, Any]] | None = None,
    force_requeue_exhausted: bool = False,
) -> list["LightRecord"]:
    """
    Engine deep worklist with hard composition quotas (fail-closed shrink).

    HV v3 (clearability_promotion / dual_track_deep_queue):
      - Rank light-pass by clearability_score (relative prior; not prior_ev > 0)
      - Dual-track fill: clearable first, then coverage mid preferred
      - Never pad chalk
      - mode=refresh: demote exhausted has_p_model via w_fail; prefer injects;
        do not re-queue exhausted without force_requeue_exhausted
    """
    tcfg = tiers_cfg(cfg)
    if not bool(tcfg.get("engine_deep_queue", True)):
        # Legacy agent/merge-only path
        auto_promote = bool(tcfg.get("auto_promote_to_deep", False))
        promotable = [
            r
            for r in records
            if r.verdict == "pass"
            and r.promote_to_deep
            and not r.has_p_model
            and (auto_promote or r.source in ("agent", "merge"))
        ]
        return promotable[: int(tcfg["deep_max_n"])]

    use_v3 = bool(tcfg.get("clearability_promotion", True)) and bool(
        tcfg.get("dual_track_deep_queue", True)
    )
    if use_v3:
        return _build_deep_queue_v3(
            records,
            cfg,
            soft_by_key=soft_by_key,
            board_score_by_key=board_score_by_key,
            coverage_overlay=coverage_overlay,
            clearability_overlay=clearability_overlay,
            mode=mode,
            inject_records=inject_records,
            pack_meta_by_key=pack_meta_by_key,
            force_requeue_exhausted=force_requeue_exhausted,
        )

    return _build_deep_queue_legacy(
        records,
        cfg,
        soft_by_key=soft_by_key,
        board_score_by_key=board_score_by_key,
        coverage_overlay=coverage_overlay,
    )


def _build_deep_queue_legacy(
    records: list["LightRecord"],
    cfg: dict[str, Any],
    *,
    soft_by_key: dict[tuple[str, str], float | None] | None = None,
    board_score_by_key: dict[tuple[str, str], float] | None = None,
    coverage_overlay: dict[str, Any] | None = None,
) -> list["LightRecord"]:
    """Pre-v3 anti-chalk scorer + preferred/short composition (unchanged behaviour)."""
    tcfg = tiers_cfg(cfg)
    ov = coverage_overlay or {}
    pref_lo = float(tcfg["preferred_odds_lo"])
    alt_lo = float(tcfg.get("alt_preferred_odds_lo") or tcfg["short_chalk_odds"])
    min_pref = float(tcfg["deep_min_preferred_share"])
    max_short = float(tcfg["deep_max_short_main_share"])
    if ov.get("active"):
        min_pref = max(min_pref, float(ov.get("coverage_preferred_share") or 0.55))
    target = int(tcfg["deep_target_n"])
    if ov.get("active"):
        target = max(target, int(ov.get("min_deep_packs") or target))
    deep_max = int(tcfg["deep_max_n"])
    target = min(target, deep_max)

    soft_by_key = soft_by_key or {}
    board_score_by_key = board_score_by_key or {}

    def _pref(r: LightRecord) -> bool:
        return is_preferred_line(
            r.selection,
            r.decimal_odds,
            r.market_family,
            preferred_odds_lo=pref_lo,
            alt_preferred_odds_lo=alt_lo,
        )

    def _sm(r: LightRecord) -> bool:
        return is_short_main_line(
            r.selection, r.decimal_odds, r.market_family, preferred_odds_lo=pref_lo
        )

    candidates: list[tuple[float, LightRecord]] = []
    for r in records:
        if r.verdict != "pass" or r.has_p_model:
            continue
        if r.script_conflict or r.base_rate_conflict:
            continue
        k = r.key()
        sc = promotion_score(
            r,
            cfg,
            soft_odds=soft_by_key.get(k),
            board_score=float(board_score_by_key.get(k) or 0.0),
            coverage_overlay=ov,
        )
        r.rough_ev_note = (r.rough_ev_note or "") + f" | promo_score={sc:.1f}"
        candidates.append((sc, r))

    candidates.sort(key=lambda x: (-x[0], x[1].decimal_odds))

    preferred_pool = [(sc, r) for sc, r in candidates if _pref(r)]
    short_pool = [(sc, r) for sc, r in candidates if _sm(r)]
    other_pool = [
        (sc, r) for sc, r in candidates if not _pref(r) and not _sm(r)
    ]

    n_pref_avail = len(preferred_pool)
    if n_pref_avail == 0:
        return []

    max_n_from_pref = int(n_pref_avail / min_pref) if min_pref > 0 else deep_max
    n_target = min(target, deep_max, max_n_from_pref)
    if n_target < 1:
        n_target = min(n_pref_avail, 1)

    deep_queue: list[LightRecord] = []
    sp_count: dict[str, int] = defaultdict(int)
    short_count = 0
    pref_count = 0
    selected: set[tuple[str, str]] = set()

    def _try_add(r: LightRecord, *, as_short: bool, as_pref: bool) -> bool:
        nonlocal short_count, pref_count
        if len(deep_queue) >= n_target:
            return False
        k = r.key()
        if k in selected:
            return False
        sp = (r.sport or "").lower()
        if sp_count[sp] >= 3:
            return False
        if as_short:
            trial_n = len(deep_queue) + 1
            if (short_count + 1) / max(trial_n, 1) > max_short + 1e-9:
                return False
            if (short_count + 1) / max(n_target, 1) > max_short + 1e-9:
                return False
        deep_queue.append(r)
        selected.add(k)
        sp_count[sp] += 1
        if as_short:
            short_count += 1
        if as_pref:
            pref_count += 1
        return True

    for _sc, r in preferred_pool:
        if len(deep_queue) >= n_target:
            break
        _try_add(r, as_short=False, as_pref=True)

    def _pref_share() -> float:
        if not deep_queue:
            return 0.0
        return pref_count / len(deep_queue)

    for _sc, r in other_pool + short_pool:
        if len(deep_queue) >= n_target:
            break
        is_p = _pref(r)
        is_s = _sm(r)
        trial_n = len(deep_queue) + 1
        trial_pref = pref_count + (1 if is_p else 0)
        if not is_p and trial_pref / max(trial_n, 1) + 1e-9 < min_pref:
            continue
        _try_add(r, as_short=is_s, as_pref=is_p)

    while deep_queue and _pref_share() + 1e-9 < min_pref:
        removed = False
        for i in range(len(deep_queue) - 1, -1, -1):
            r = deep_queue[i]
            if _sm(r):
                deep_queue.pop(i)
                short_count = max(0, short_count - 1)
                if _pref(r):
                    pref_count = max(0, pref_count - 1)
                removed = True
                break
        if not removed:
            for i in range(len(deep_queue) - 1, -1, -1):
                r = deep_queue[i]
                if not _pref(r):
                    deep_queue.pop(i)
                    removed = True
                    break
        if not removed:
            break

    return deep_queue


def _build_deep_queue_v3(
    records: list["LightRecord"],
    cfg: dict[str, Any],
    *,
    soft_by_key: dict[tuple[str, str], float | None] | None = None,
    board_score_by_key: dict[tuple[str, str], float] | None = None,
    coverage_overlay: dict[str, Any] | None = None,
    clearability_overlay: dict[str, Any] | None = None,
    mode: str = "normal",
    inject_records: list["LightRecord"] | None = None,
    pack_meta_by_key: dict[tuple[str, str], dict[str, Any]] | None = None,
    force_requeue_exhausted: bool = False,
) -> list["LightRecord"]:
    """
    Dual-track clearability promotion (design §1.3) + refresh mode (§1b).
    """
    from nt.clearability import (
        batch_prior_percentile,
        clearability_score,
        is_alt_preferred_macro,
        promotion_score_v3,
    )

    tcfg = tiers_cfg(cfg)
    ov = coverage_overlay or {}
    cl_ov = clearability_overlay if clearability_overlay is not None else _active_clearability_overlay(cfg)
    pref_lo = float(tcfg["preferred_odds_lo"])
    pref_hi = float(tcfg["preferred_odds_hi"])
    alt_lo = float(tcfg.get("alt_preferred_odds_lo") or tcfg["short_chalk_odds"])
    min_pref = float(tcfg["deep_min_preferred_share"])
    max_short = float(tcfg["deep_max_short_main_share"])
    if ov.get("active"):
        min_pref = max(min_pref, float(ov.get("coverage_preferred_share") or 0.55))
    target = int(tcfg["deep_target_n"])
    if ov.get("active"):
        target = max(target, int(ov.get("min_deep_packs") or target))
    deep_max = int(tcfg["deep_max_n"])
    target = min(target, deep_max)

    clearable_n, coverage_n = dual_track_sizes(
        target,
        coverage_overlay_active=bool(ov.get("active")),
        clearability_overlay_active=bool(cl_ov.get("active")),
    )

    soft_by_key = soft_by_key or {}
    board_score_by_key = board_score_by_key or {}
    pack_meta_by_key = pack_meta_by_key or {}
    exhausted_thr = float(
        tcfg.get("raw_ev_exhausted")
        if tcfg.get("raw_ev_exhausted") is not None
        else -0.05
    )
    haircut = _haircut_from_cfg(cfg)
    queue_mode = "refresh" if str(mode or "normal").lower() == "refresh" else "normal"
    force_cov = bool(ov.get("active"))
    force_cl = bool(cl_ov.get("active"))

    def _pref(r: LightRecord) -> bool:
        return is_preferred_line(
            r.selection,
            r.decimal_odds,
            r.market_family,
            preferred_odds_lo=pref_lo,
            alt_preferred_odds_lo=alt_lo,
        )

    def _sm(r: LightRecord) -> bool:
        return is_short_main_line(
            r.selection, r.decimal_odds, r.market_family, preferred_odds_lo=pref_lo
        )

    def _mid_band(r: LightRecord) -> bool:
        o = float(r.decimal_odds)
        return pref_lo <= o <= pref_hi

    # Merge light records + injects (injects win if same key — prefer new alts)
    by_key: dict[tuple[str, str], LightRecord] = {}
    for r in list(records) + list(inject_records or []):
        by_key[r.key()] = r
    pool = list(by_key.values())
    groups = _peer_odds_map(pool)

    # Annotate pack meta / exhausted
    for r in pool:
        meta = pack_meta_by_key.get(r.key()) or {}
        raw_ev = meta.get("raw_ev")
        if raw_ev is None and getattr(r, "raw_ev", None) is not None:
            raw_ev = r.raw_ev
        has_pack = bool(meta.get("has_pack") or r.has_p_model or r.has_deep_pack)
        if raw_ev is not None:
            try:
                r.raw_ev = float(raw_ev)
            except (TypeError, ValueError):
                r.raw_ev = None
        else:
            r.raw_ev = getattr(r, "raw_ev", None)
        exhausted = bool(meta.get("deep_exhausted"))
        if r.raw_ev is not None and float(r.raw_ev) < exhausted_thr:
            exhausted = True
        r.deep_exhausted = exhausted
        if has_pack and not r.has_p_model:
            r.has_p_model = True
            r.has_deep_pack = True

    # Batch priors for percentile among eligible-ish lines
    batch_priors = [
        float(r.prior_ev) if r.prior_ev is not None else None for r in pool
    ]

    scored: list[tuple[float, LightRecord]] = []
    for r in pool:
        # Conflicts always out
        if r.script_conflict or r.base_rate_conflict:
            continue
        # Light-pass required unless inject from second-pass (source inject)
        is_inject = (r.source or "") == "inject" or bool(
            getattr(r, "is_inject", False)
        )
        if r.verdict not in ("pass", "") and not is_inject:
            if r.verdict == "fail" and not is_inject:
                continue
        if r.verdict == "fail" and not is_inject:
            continue

        has_pack = bool(r.has_p_model or r.has_deep_pack)
        exhausted = bool(getattr(r, "deep_exhausted", False))

        # Normal mode: skip already researched
        if queue_mode == "normal" and has_pack:
            continue

        # Refresh mode: skip non-exhausted packs (already researched OK);
        # skip exhausted unless force and no better injects later (handled below)
        if queue_mode == "refresh":
            if has_pack and not exhausted:
                continue
            if has_pack and exhausted and not force_requeue_exhausted:
                # Prefer injects — do not re-queue exhausted for research
                continue

        if r.verdict != "pass" and not is_inject:
            # Require pass for non-inject
            if r.verdict not in ("pass",):
                continue

        k = r.key()
        soft = soft_by_key.get(k)
        board_sc = float(board_score_by_key.get(k) or 0.0)
        fam = r.market_family or selection_family(r.selection, (r.sport or "").lower())
        is_alt = is_alt_preferred_macro(fam, r.selection)
        is_coin = _coin_flip_for_record(r, groups, cfg)
        pev = float(r.prior_ev) if r.prior_ev is not None else None
        bp = batch_prior_percentile(pev, batch_priors)

        # family_hist_n / family_clear_rate: intentionally unwired in PR2.
        # Learning state is sport-level only (no family clear-rate SSOT yet);
        # w_hist stays 0 until a family-level ledger metric lands (post-PR2).
        cl = clearability_score(
            odds=float(r.decimal_odds),
            prior_ev=pev,
            prior_p=float(r.prior_p) if r.prior_p is not None else None,
            haircut=haircut,
            batch_percentile=bp,
            is_coin_flip=is_coin,
            soft_decimal_odds=soft,
            is_alt=is_alt,
            is_short_main=_sm(r),
            has_structural_note=_is_structural_note(r),
            family_hist_n=0,
            family_clear_rate=None,
            force_coverage_active=force_cov and _mid_band(r),
            force_clearability_active=force_cl,
            has_pack=has_pack,
            raw_ev=r.raw_ev,
            cfg=cfg,
        )
        # Refresh demotion: w_fail already applied inside clearability when raw_ev bad
        promo = promotion_score_v3(cl, board_sc)
        # Inject boost slightly so dump alts outrank exhausted when force requeue
        if is_inject:
            promo = round(promo + 5.0, 3)

        r.clearability_score = cl
        r.promotion_score_v3 = promo
        r.queue_mode = queue_mode
        r.rough_ev_note = (r.rough_ev_note or "") + f" | clear={cl:.1f} promo_v3={promo:.1f}"
        if is_inject:
            r.rough_ev_note += " | inject"
        scored.append((promo, r))

    # Prefer injects over any residual exhausted if both present
    scored.sort(
        key=lambda x: (
            -1 if ((x[1].source or "") == "inject" or getattr(x[1], "is_inject", False)) else 0,
            -x[0],
            x[1].decimal_odds,
        )
    )

    preferred_pool = [(sc, r) for sc, r in scored if _pref(r)]
    n_pref_avail = len(preferred_pool)
    if n_pref_avail == 0:
        return []

    max_n_from_pref = int(n_pref_avail / min_pref) if min_pref > 0 else deep_max
    n_target = min(target, deep_max, max_n_from_pref)
    if n_target < 1:
        n_target = min(n_pref_avail, 1)

    # Rescale dual-track to n_target (thin pool shrinks both)
    if n_target < target and target > 0:
        scale = n_target / float(target)
        clearable_n = max(1, int(round(clearable_n * scale))) if clearable_n else 0
        clearable_n = min(clearable_n, n_target)
        coverage_n = n_target - clearable_n
    else:
        clearable_n = min(clearable_n, n_target)
        coverage_n = n_target - clearable_n

    deep_queue: list[LightRecord] = []
    sp_count: dict[str, int] = defaultdict(int)
    short_count = 0
    pref_count = 0
    selected: set[tuple[str, str]] = set()
    clearable_count = 0
    coverage_count = 0

    def _try_add(
        r: LightRecord,
        *,
        as_short: bool,
        as_pref: bool,
        track: str,
        track_cap: int | None = None,
        track_count: int = 0,
    ) -> bool:
        nonlocal short_count, pref_count, clearable_count, coverage_count
        if len(deep_queue) >= n_target:
            return False
        if track_cap is not None and track_count >= track_cap:
            return False
        k = r.key()
        if k in selected:
            return False
        sp = (r.sport or "").lower()
        if sp_count[sp] >= 3:
            return False
        if as_short:
            trial_n = len(deep_queue) + 1
            if (short_count + 1) / max(trial_n, 1) > max_short + 1e-9:
                return False
            if (short_count + 1) / max(n_target, 1) > max_short + 1e-9:
                return False
        # Never pad pure chalk into clearable/coverage tracks
        if as_short and track in ("clearable", "coverage"):
            # short-main only allowed under global short cap, never as coverage pad
            if track == "coverage":
                return False
        r.queue_track = track
        r.queue_mode = queue_mode
        deep_queue.append(r)
        selected.add(k)
        sp_count[sp] += 1
        if as_short:
            short_count += 1
        if as_pref:
            pref_count += 1
        if track == "clearable":
            clearable_count += 1
        elif track == "coverage":
            coverage_count += 1
        return True

    # Track 1: clearable — top clearability rank overall (prefer preferred)
    for sc, r in scored:
        if clearable_count >= clearable_n:
            break
        if len(deep_queue) >= n_target:
            break
        is_p = _pref(r)
        is_s = _sm(r)
        # Prefer preferred for clearable; allow non-pref only if preferred floor still ok
        if not is_p:
            trial_n = len(deep_queue) + 1
            trial_pref = pref_count
            if trial_pref / max(trial_n, 1) + 1e-9 < min_pref:
                continue
        _try_add(
            r,
            as_short=is_s,
            as_pref=is_p,
            track="clearable",
            track_cap=clearable_n,
            track_count=clearable_count,
        )

    # Track 2: coverage — remaining preferred mid-band, even mid clearability
    coverage_pool = [
        (sc, r)
        for sc, r in scored
        if r.key() not in selected and _pref(r) and (_mid_band(r) or float(r.decimal_odds) >= alt_lo)
    ]
    # Prefer mid-unresearched (no pack) for coverage track
    coverage_pool.sort(
        key=lambda x: (
            0 if not (x[1].has_p_model or x[1].has_deep_pack) else 1,
            -x[0],
            x[1].decimal_odds,
        )
    )
    for sc, r in coverage_pool:
        if coverage_count >= coverage_n:
            break
        if len(deep_queue) >= n_target:
            break
        _try_add(
            r,
            as_short=False,
            as_pref=True,
            track="coverage",
            track_cap=coverage_n,
            track_count=coverage_count,
        )

    # If clearable slots unfilled and preferred remain, backfill clearable (still no chalk pad)
    if clearable_count < clearable_n and len(deep_queue) < n_target:
        for sc, r in scored:
            if clearable_count >= clearable_n or len(deep_queue) >= n_target:
                break
            if r.key() in selected:
                continue
            if not _pref(r):
                continue
            _try_add(
                r,
                as_short=False,
                as_pref=True,
                track="clearable",
                track_cap=clearable_n,
                track_count=clearable_count,
            )

    def _pref_share() -> float:
        if not deep_queue:
            return 0.0
        return pref_count / len(deep_queue)

    # Fail-closed: drop short-main / non-preferred from tail if preferred floor slips
    while deep_queue and _pref_share() + 1e-9 < min_pref:
        removed = False
        for i in range(len(deep_queue) - 1, -1, -1):
            r = deep_queue[i]
            if _sm(r):
                deep_queue.pop(i)
                short_count = max(0, short_count - 1)
                if _pref(r):
                    pref_count = max(0, pref_count - 1)
                if getattr(r, "queue_track", "") == "clearable":
                    clearable_count = max(0, clearable_count - 1)
                elif getattr(r, "queue_track", "") == "coverage":
                    coverage_count = max(0, coverage_count - 1)
                removed = True
                break
        if not removed:
            for i in range(len(deep_queue) - 1, -1, -1):
                r = deep_queue[i]
                if not _pref(r):
                    deep_queue.pop(i)
                    if getattr(r, "queue_track", "") == "clearable":
                        clearable_count = max(0, clearable_count - 1)
                    elif getattr(r, "queue_track", "") == "coverage":
                        coverage_count = max(0, coverage_count - 1)
                    removed = True
                    break
        if not removed:
            break

    return deep_queue


@dataclass
class LightRecord:
    match: str
    selection: str
    sport: str
    decimal_odds: float
    odds_band: str
    market_family: str
    tier: str = "light"  # light | deep | skipped
    verdict: str = "pass"  # pass | fail | skip
    promote_to_deep: bool = False
    script_lean: str = "unknown"
    script_conflict: bool = False
    base_rate_conflict: bool = False
    rough_p_needed: float | None = None
    rough_ev_note: str = ""
    strength_notes: str = ""
    weakness_notes: str = ""
    reason: str = ""
    has_deep_pack: bool = False
    has_p_model: bool = False
    researched_at: str = ""
    source: str = "auto"  # auto | agent | merge | inject
    # Quant prefilter (research-rank only — not recommend p_model)
    prior_p: float | None = None
    prior_ev: float | None = None
    prior_available: bool = False
    prefilter_stage1: str = ""
    prefilter_stage2: str = ""
    prefilter_rank: float | None = None
    # HV v3 dual-track / refresh diagnostics
    clearability_score: float | None = None
    promotion_score_v3: float | None = None
    queue_track: str = ""  # clearable | coverage
    queue_mode: str = "normal"  # normal | refresh
    deep_exhausted: bool = False
    raw_ev: float | None = None
    is_inject: bool = False

    def key(self) -> tuple[str, str]:
        return (self.match or "", self.selection or "")


def _p_needed_for_min_ev(odds: float, min_ev: float = 0.03, haircut: float = 0.05) -> float:
    """p_model needed so (p - haircut)*odds - 1 >= min_ev."""
    if odds <= 1.0:
        return 0.99
    return min(0.99, max(0.01, (1.0 + min_ev) / odds + haircut))


def auto_light_assess(
    *,
    match: str,
    selection: str,
    sport: str,
    odds: float,
    cfg: dict[str, Any],
    has_deep: bool = False,
    has_p: bool = False,
    p_model: float | None = None,
    score: float = 0.0,
) -> LightRecord:
    """Heuristic light research (no web). Agent may overwrite with richer notes."""
    tcfg = tiers_cfg(cfg)
    sel_cfg = cfg.get("selection") or {}
    haircut = float(sel_cfg.get("probability_haircut", 0.05))
    min_ev = float(sel_cfg.get("standard_min_ev", 0.03))
    thr_high = float(sel_cfg.get("high_odds_threshold", 2.5))

    family = selection_family(selection, (sport or "").lower())
    band = odds_band(odds)
    need_p = _p_needed_for_min_ev(odds, min_ev, haircut)

    rec = LightRecord(
        match=match,
        selection=selection,
        sport=sport or "unknown",
        decimal_odds=float(odds),
        odds_band=band,
        market_family=family,
        rough_p_needed=round(need_p, 3),
        has_deep_pack=has_deep,
        has_p_model=has_p,
        researched_at=utc_now(),
        source="auto",
    )

    # Already deep
    if has_deep and has_p and p_model is not None:
        rec.tier = "deep"
        rec.verdict = "pass"
        rec.promote_to_deep = False
        rec.reason = "already has deep pack + p_model"
        rec.strength_notes = f"p_model={p_model}"
        rec.rough_ev_note = f"need p≥{need_p:.2f} for min EV; have {p_model}"
        return rec

    lo_fail = float(tcfg["fail_odds_below"])
    hi_fail = float(tcfg["fail_odds_above"])
    lo_pass = float(tcfg["pass_odds_lo"])
    hi_pass = float(tcfg["pass_odds_hi"])

    strengths: list[str] = []
    weaknesses: list[str] = []

    if lo_pass <= odds <= hi_pass:
        strengths.append(f"mid odds band {band} tradeable for Phase 1A")
    if score >= 90:
        strengths.append("high board research score")
    if family in ("totals_under", "totals_over", "btts_no", "btts_yes", "ml", "handicap"):
        strengths.append(f"core family {family}")

    if odds < lo_fail:
        weaknesses.append(f"odds {odds:.2f} too short — need p≥{need_p:.0%} after haircut")
        rec.verdict = "fail"
        rec.promote_to_deep = False
        rec.reason = "light-fail: odds too short for realistic EV"
    elif odds > hi_fail:
        weaknesses.append(f"odds {odds:.2f} longshot — needs grade A deep pack")
        rec.verdict = "fail"
        rec.promote_to_deep = False
        rec.reason = "light-fail: longshot without deep plan (auto)"
    elif need_p >= 0.78:
        weaknesses.append(f"EV bar needs p≥{need_p:.2f} — hard for honest model")
        rec.verdict = "fail"
        rec.promote_to_deep = False
        rec.reason = "light-fail: EV bar too high vs price"
    else:
        rec.verdict = "pass"
        # P1: auto light never auto-promotes to deep (agent/manual only)
        rec.promote_to_deep = False
        rec.reason = "light-pass: mid-band / tradeable — deep only via agent promote"
        if odds > thr_high:
            weaknesses.append("high odds — deep needs grade A + elevated EV")
        if family in ("totals_under", "btts_no"):
            rec.script_lean = "unknown"
            weaknesses.append("unders/BTTS No need script + availability in deep")
        if family in ("totals_over", "btts_yes"):
            weaknesses.append("overs/BTTS Yes need script lean not cagey")

    # Multi-stage quant prefilter (Stage1 screens + Stage2 classical prior)
    rec.script_conflict = False
    rec.base_rate_conflict = False
    try:
        from nt.research_prefilter import run_prefilter

        pf = run_prefilter(
            selection=selection,
            odds=float(odds),
            sport=sport or "",
            family=family,
            cfg=cfg,
        )
        rec.prefilter_stage1 = pf.stage1_reason
        rec.prefilter_stage2 = pf.stage2_reason
        rec.prior_p = pf.prior_p
        rec.prior_ev = pf.prior_ev
        rec.prior_available = bool(pf.prior_available)
        rec.prefilter_rank = pf.rank_score
        if pf.base_rate_conflict:
            rec.base_rate_conflict = True
            weaknesses.append("stage2 base_rate_conflict vs short chalk")
        if pf.discarded and rec.verdict == "pass":
            rec.verdict = "fail"
            rec.promote_to_deep = False
            stage = pf.discard_stage or "prefilter"
            rec.reason = f"light-fail:{stage}:{pf.stage1_reason if stage == 'stage1' else pf.stage2_reason}"
            weaknesses.append(rec.reason)
        elif pf.prior_ev is not None and pf.prior_available:
            strengths.append(f"prior_ev={pf.prior_ev:+.3f} (research-rank only)")
    except Exception as ex:  # noqa: BLE001
        # Fail-open on prefilter crash — do not invent prior; leave light band result
        weaknesses.append(f"prefilter_error:{ex}")

    rec.strength_notes = "; ".join(strengths) or "none flagged"
    rec.weakness_notes = "; ".join(weaknesses) or "none flagged"
    rec.rough_ev_note = f"min EV bar needs honest p_model ≥ {need_p:.2f} at odds {odds:.2f}"
    if rec.prior_ev is not None:
        rec.rough_ev_note += f"; prior_ev={rec.prior_ev:+.3f}"
    return rec


def _queue_line_export(r: "LightRecord", tcfg: dict[str, Any]) -> dict[str, Any]:
    """Serialize a deep-queue LightRecord for light report / deep_queue.json."""
    pref_lo = float(tcfg.get("preferred_odds_lo") or 1.85)
    alt_lo = float(tcfg.get("alt_preferred_odds_lo") or tcfg.get("short_chalk_odds") or 1.80)
    out: dict[str, Any] = {
        "match": r.match,
        "selection": r.selection,
        "sport": r.sport,
        "decimal_odds": r.decimal_odds,
        "reason": r.reason,
        "prior_ev": r.prior_ev,
        "preferred": is_preferred_line(
            r.selection,
            r.decimal_odds,
            r.market_family,
            preferred_odds_lo=pref_lo,
            alt_preferred_odds_lo=alt_lo,
        ),
        "short_main": is_short_main_line(
            r.selection,
            r.decimal_odds,
            r.market_family,
            preferred_odds_lo=pref_lo,
        ),
        "market_family": r.market_family,
        "mode": getattr(r, "queue_mode", None) or "normal",
    }
    if getattr(r, "clearability_score", None) is not None:
        out["clearability_score"] = r.clearability_score
    if getattr(r, "promotion_score_v3", None) is not None:
        out["promotion_score_v3"] = r.promotion_score_v3
    track = getattr(r, "queue_track", None) or ""
    if track:
        out["track"] = track
    if getattr(r, "deep_exhausted", False):
        out["deep_exhausted"] = True
    if getattr(r, "raw_ev", None) is not None:
        out["raw_ev"] = r.raw_ev
    if getattr(r, "is_inject", False) or (r.source or "") == "inject":
        out["inject"] = True
    return out


def _queue_composition_stats(
    deep_queue: list["LightRecord"], tcfg: dict[str, Any]
) -> dict[str, Any]:
    pref_lo = float(tcfg.get("preferred_odds_lo") or 1.85)
    alt_lo = float(tcfg.get("alt_preferred_odds_lo") or tcfg.get("short_chalk_odds") or 1.80)
    n = len(deep_queue)
    if n == 0:
        return {
            "n": 0,
            "preferred_n": 0,
            "short_main_n": 0,
            "preferred_share": 0.0,
            "short_main_share": 0.0,
            "meets_preferred_floor": True,
            "meets_short_main_cap": True,
        }
    pref_n = sum(
        1
        for r in deep_queue
        if is_preferred_line(
            r.selection,
            r.decimal_odds,
            r.market_family,
            preferred_odds_lo=pref_lo,
            alt_preferred_odds_lo=alt_lo,
        )
    )
    sm_n = sum(
        1
        for r in deep_queue
        if is_short_main_line(
            r.selection, r.decimal_odds, r.market_family, preferred_odds_lo=pref_lo
        )
    )
    pref_share = pref_n / n
    sm_share = sm_n / n
    return {
        "n": n,
        "preferred_n": pref_n,
        "short_main_n": sm_n,
        "preferred_share": round(pref_share, 3),
        "short_main_share": round(sm_share, 3),
        "meets_preferred_floor": pref_share + 1e-9
        >= float(tcfg.get("deep_min_preferred_share") or 0.55),
        "meets_short_main_cap": sm_share
        <= float(tcfg.get("deep_max_short_main_share") or 0.25) + 1e-9,
    }


def light_path(cfg: dict[str, Any], day: str | None = None) -> Path:
    outbox = path_from_config(cfg, "outbox")
    d = day or date.today().isoformat()
    return outbox / "light_research" / f"{d}.json"


def load_light_batch(cfg: dict[str, Any], day: str | None = None) -> dict[str, Any]:
    path = light_path(cfg, day)
    if not path.exists():
        return {"records": [], "path": str(path), "day": day or date.today().isoformat()}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"records": data, "path": str(path), "day": day or date.today().isoformat()}
    return data


def save_light_batch(cfg: dict[str, Any], payload: dict[str, Any], day: str | None = None) -> Path:
    path = light_path(cfg, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # latest pointer
    latest = path.parent / "LATEST.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def coverage_stats(records: list[dict[str, Any]], shortlist_n: int) -> dict[str, Any]:
    n = len(records)
    by_verdict = Counter(r.get("verdict") for r in records)
    by_tier = Counter(r.get("tier") for r in records)
    by_sport = Counter((r.get("sport") or "unknown").lower() for r in records)
    light_n = sum(1 for r in records if r.get("tier") in ("light", "deep") or r.get("verdict") in ("pass", "fail"))
    # Any structured light assessment counts as "received light research"
    assessed = sum(1 for r in records if r.get("source") in ("auto", "agent", "merge") and r.get("verdict"))
    deep_n = sum(1 for r in records if r.get("tier") == "deep" or r.get("has_p_model"))
    promote = [r for r in records if r.get("promote_to_deep") and r.get("verdict") == "pass"]
    pct = (assessed / shortlist_n) if shortlist_n else 0.0
    return {
        "shortlist_n": shortlist_n,
        "assessed_n": assessed,
        "light_coverage_pct": round(100.0 * pct, 1),
        "deep_n": deep_n,
        "promote_to_deep_n": len(promote),
        "by_verdict": dict(by_verdict),
        "by_tier": dict(by_tier),
        "by_sport": dict(by_sport),
    }


def sport_min_coverage_ok(
    records: list[dict[str, Any]],
    shortlist_by_sport: dict[str, int],
    tcfg: dict[str, Any],
) -> list[str]:
    """Return human warnings if sport minimums not met."""
    warnings: list[str] = []
    thr_n = int(tcfg["min_light_per_sport_when_n"])
    min_k = int(tcfg["min_light_per_sport"])
    assessed_by_sp: dict[str, int] = defaultdict(int)
    for r in records:
        if r.get("verdict") in ("pass", "fail", "skip"):
            assessed_by_sp[(r.get("sport") or "unknown").lower()] += 1
    for sp, n in shortlist_by_sport.items():
        if n >= thr_n and assessed_by_sp.get(sp, 0) < min_k:
            warnings.append(
                f"sport {sp}: shortlist n={n} but light assessed only {assessed_by_sp.get(sp, 0)} "
                f"(need ≥{min_k})"
            )
    return warnings


def run_light_research(
    cfg: dict[str, Any],
    odds_path: Path,
    shortlist: list[Any],
    *,
    write: bool = True,
    day: str | None = None,
) -> dict[str, Any]:
    """
    Stage 1: light-assess shortlist items (auto heuristics).
    Enforces coverage targets by assessing enough lines.
    """
    tcfg = tiers_cfg(cfg)
    target = float(tcfg["light_coverage_target"])
    min_n = int(tcfg["light_coverage_min_n"])

    # Normalize shortlist to dicts
    items: list[dict[str, Any]] = []
    for it in shortlist:
        if hasattr(it, "match"):
            items.append(
                {
                    "match": it.match,
                    "selection": it.selection,
                    "sport": it.sport,
                    "decimal_odds": it.decimal_odds,
                    "score": getattr(it, "score", 0),
                    "has_evidence": getattr(it, "has_evidence", False),
                    "has_p_model": getattr(it, "has_p_model", False),
                    "p_model": getattr(it, "p_model", None),
                }
            )
        else:
            items.append(dict(it))

    shortlist_n = len(items)
    need = max(min_n, int(round(target * shortlist_n))) if shortlist_n else 0
    need = min(need, shortlist_n)

    # Sort: already deep first, then by score
    items_sorted = sorted(
        items,
        key=lambda x: (
            0 if x.get("has_p_model") else 1,
            -float(x.get("score") or 0),
            float(x.get("decimal_odds") or 99),
        ),
    )

    # Ensure sport minimums get assessed
    by_sport: dict[str, list[dict]] = defaultdict(list)
    for it in items_sorted:
        by_sport[(it.get("sport") or "unknown").lower()].append(it)

    must: list[dict] = []
    thr_n = int(tcfg["min_light_per_sport_when_n"])
    min_k = int(tcfg["min_light_per_sport"])
    seen: set[tuple[str, str]] = set()

    def _add(it: dict) -> None:
        k = (it.get("match") or "", it.get("selection") or "")
        if k in seen:
            return
        seen.add(k)
        must.append(it)

    for sp, lst in by_sport.items():
        if len(lst) >= thr_n:
            for it in lst[:min_k]:
                _add(it)

    for it in items_sorted:
        if len(must) >= need:
            break
        _add(it)

    # Fill to 100% of shortlist if target ≥ 0.99
    if target >= 0.99:
        for it in items_sorted:
            _add(it)

    records: list[LightRecord] = []
    soft_by_key: dict[tuple[str, str], float | None] = {}
    board_score_by_key: dict[tuple[str, str], float] = {}
    for it in must:
        rec = auto_light_assess(
            match=str(it.get("match") or ""),
            selection=str(it.get("selection") or ""),
            sport=str(it.get("sport") or ""),
            odds=float(it.get("decimal_odds") or 1.5),
            cfg=cfg,
            has_deep=bool(it.get("has_evidence")),
            has_p=bool(it.get("has_p_model")),
            p_model=it.get("p_model"),
            score=float(it.get("score") or 0),
        )
        records.append(rec)
        k = rec.key()
        soft_by_key[k] = _parse_soft_odds(it, rec)
        board_score_by_key[k] = float(it.get("score") or 0)

    # Fail/conflict demotion: never keep promote on fail
    for r in records:
        if r.verdict == "fail":
            r.promote_to_deep = False

    # P0: engine deep worklist (anti-chalk score + composition). Assess stays promote=False.
    coverage_overlay: dict[str, Any] = {}
    try:
        from nt.control_signals import active_coverage_priority_overlay

        coverage_overlay = active_coverage_priority_overlay(cfg)
    except Exception:
        coverage_overlay = {"active": False}

    deep_queue = build_deep_queue(
        records,
        cfg,
        soft_by_key=soft_by_key,
        board_score_by_key=board_score_by_key,
        coverage_overlay=coverage_overlay,
    )
    promote_keys = {r.key() for r in deep_queue}
    for r in records:
        if r.key() in promote_keys:
            r.promote_to_deep = True
            r.tier = "light"
            if "deep queue" not in (r.reason or ""):
                r.reason = (r.reason or "") + " | engine deep queue"
        else:
            if r.promote_to_deep and not r.has_p_model:
                r.promote_to_deep = False
                if "not selected for deep" not in (r.reason or ""):
                    r.reason = (r.reason or "") + " | not selected for deep this round"

    rec_dicts = [asdict(r) for r in records]
    shortlist_by_sport = {sp: len(lst) for sp, lst in by_sport.items()}
    stats = coverage_stats(rec_dicts, shortlist_n)
    warnings = sport_min_coverage_ok(rec_dicts, shortlist_by_sport, tcfg)
    target_pct = 100.0 * target
    if stats["light_coverage_pct"] + 0.1 < target_pct * (shortlist_n and 1 or 0) and shortlist_n:
        # compare to target fraction
        if stats["assessed_n"] < need:
            warnings.append(
                f"light coverage {stats['light_coverage_pct']}% < target {target_pct:.0f}% "
                f"({stats['assessed_n']}/{shortlist_n})"
            )

    # Prefilter funnel stats (Stage1+Stage2 discard share)
    prefilter_stats: dict[str, Any] = {}
    try:
        from nt.research_prefilter import PrefilterResult, prefilter_batch_stats

        pf_results: list[PrefilterResult] = []
        for r in records:
            discarded = r.verdict == "fail" and (
                (r.prefilter_stage1 or "").startswith("stage1:")
                and "pass" not in (r.prefilter_stage1 or "")
                or (r.prefilter_stage2 or "").startswith("stage2:")
                and "pass" not in (r.prefilter_stage2 or "")
            )
            # Prefer explicit stage markers from prefilter reasons
            d_stage = ""
            if r.verdict == "fail":
                if "stage1:" in (r.reason or "") or (
                    r.prefilter_stage1 and "pass" not in r.prefilter_stage1
                ):
                    if r.prefilter_stage1 and "pass" not in r.prefilter_stage1:
                        d_stage = "stage1"
                if not d_stage and r.prefilter_stage2 and "pass" not in r.prefilter_stage2:
                    d_stage = "stage2"
            pf_results.append(
                PrefilterResult(
                    stage1_pass=bool(
                        r.prefilter_stage1 and "pass" in r.prefilter_stage1
                    )
                    or (not r.prefilter_stage1 and r.verdict != "fail"),
                    stage1_reason=r.prefilter_stage1 or "",
                    stage2_pass=bool(
                        r.prefilter_stage2 and "pass" in r.prefilter_stage2
                    )
                    or (not r.prefilter_stage2 and r.verdict == "pass"),
                    stage2_reason=r.prefilter_stage2 or "",
                    prior_p=r.prior_p,
                    prior_ev=r.prior_ev,
                    prior_available=r.prior_available,
                    base_rate_conflict=r.base_rate_conflict,
                    rank_score=float(r.prefilter_rank or 0),
                    discarded=bool(d_stage),
                    discard_stage=d_stage,
                )
            )
        prefilter_stats = prefilter_batch_stats(pf_results)
    except Exception as ex:  # noqa: BLE001
        prefilter_stats = {"error": str(ex)}

    payload = {
        "day": day or date.today().isoformat(),
        "odds_path": str(odds_path),
        "generated_at": utc_now(),
        "tiers_config": tcfg,
        "stats": stats,
        "prefilter_stats": prefilter_stats,
        "warnings": warnings,
        "coverage_ok": stats["assessed_n"] >= need and not any("sport " in w for w in warnings),
        "deep_queue": [_queue_line_export(r, tcfg) for r in deep_queue],
        "deep_queue_composition": _queue_composition_stats(deep_queue, tcfg),
        "deep_queue_mode": "normal",
        "dual_track_sizes": dict(
            zip(
                ("clearable_n", "coverage_n"),
                dual_track_sizes(
                    min(int(tcfg["deep_target_n"]), int(tcfg["deep_max_n"])),
                    coverage_overlay_active=bool(coverage_overlay.get("active")),
                    clearability_overlay_active=bool(
                        _active_clearability_overlay(cfg).get("active")
                    ),
                ),
            )
        ),
        "coverage_overlay_active": bool(coverage_overlay.get("active")),
        "records": rec_dicts,
        "shortlist_n": shortlist_n,
        "assessed_n": len(records),
    }

    path = None
    if write:
        path = save_light_batch(cfg, payload, day=day)
        md_path = path.with_suffix(".md")
        md_path.write_text(render_light_markdown(payload), encoding="utf-8")
        (path.parent / "LATEST.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
        payload["path"] = str(path)
        payload["md_path"] = str(md_path)
        # D17: engine SSOT for Lumina composition bars (preferred/short-main)
        try:
            from nt.deep_queue_state import write_deep_queue_from_light_payload

            dq_state_path = write_deep_queue_from_light_payload(
                cfg, payload, source="light_research"
            )
            payload["deep_queue_state_path"] = str(dq_state_path)
        except Exception as ex:  # noqa: BLE001
            payload["deep_queue_state_error"] = str(ex)

    return payload


def render_light_markdown(payload: dict[str, Any]) -> str:
    stats = payload.get("stats") or {}
    lines = [
        f"# Light Research Report — {payload.get('day')}",
        "",
        f"**Odds:** `{payload.get('odds_path')}`  ",
        f"**Generated:** {payload.get('generated_at')}  ",
        f"**Coverage OK:** {payload.get('coverage_ok')}",
        "",
        "## Coverage",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Shortlist | {stats.get('shortlist_n', 0)} |",
        f"| Light assessed | {stats.get('assessed_n', 0)} |",
        f"| Light coverage | **{stats.get('light_coverage_pct', 0)}%** |",
        f"| Already deep / p_model | {stats.get('deep_n', 0)} |",
        f"| Promote to deep | {stats.get('promote_to_deep_n', 0)} |",
        "",
        f"By verdict: `{stats.get('by_verdict')}`  ",
        f"By sport: `{stats.get('by_sport')}`",
        "",
    ]
    pf = payload.get("prefilter_stats") or {}
    if pf and not pf.get("error"):
        lines.extend(
            [
                "## Quant prefilter (Stage1 + Stage2)",
                "",
                f"| Metric | Value |",
                f"|--------|------:|",
                f"| Assessed | {pf.get('n', 0)} |",
                f"| Stage1 pass | {pf.get('stage1_pass_n', 0)} |",
                f"| Stage2 pass | {pf.get('stage2_pass_n', 0)} |",
                f"| Discarded | {pf.get('discard_n', 0)} ({100 * float(pf.get('discard_share') or 0):.0f}%) |",
                f"| Stage1 discards | {pf.get('stage1_discard_n', 0)} |",
                f"| Stage2 discards | {pf.get('stage2_discard_n', 0)} |",
                "",
            ]
        )
    comp = payload.get("deep_queue_composition") or {}
    if comp:
        lines.extend(
            [
                "## Deep queue composition",
                "",
                f"- Preferred share: **{comp.get('preferred_share')}** "
                f"(floor met: {comp.get('meets_preferred_floor')})",
                f"- Short-main share: **{comp.get('short_main_share')}** "
                f"(cap met: {comp.get('meets_short_main_cap')})",
                f"- n={comp.get('n')} preferred_n={comp.get('preferred_n')} "
                f"short_main_n={comp.get('short_main_n')}",
                "",
            ]
        )
    warns = payload.get("warnings") or []
    if warns:
        lines.append("## Warnings")
        lines.append("")
        for w in warns:
            lines.append(f"- ⚠ {w}")
        lines.append("")

    dq = payload.get("deep_queue") or []
    lines.append("## Deep research queue (Stage 2)")
    lines.append("")
    if not dq:
        lines.append("_Empty — no light-pass promotions._")
    else:
        lines.append("| # | Sport | Match | Selection | Odds |")
        lines.append("|---|-------|-------|-----------|-----:|")
        for i, r in enumerate(dq, 1):
            lines.append(
                f"| {i} | {r.get('sport')} | {r.get('match','')[:32]} | "
                f"{(r.get('selection') or '')[:40]} | {r.get('decimal_odds')} |"
            )
    lines.append("")
    lines.append("## All light assessments")
    lines.append("")
    lines.append("| Sport | Match | Selection | Odds | Verdict | Deep? | Reason |")
    lines.append("|-------|-------|-----------|-----:|---------|:-----:|--------|")
    for r in payload.get("records") or []:
        lines.append(
            f"| {r.get('sport','')} | {(r.get('match') or '')[:28]} | "
            f"{(r.get('selection') or '')[:36]} | {r.get('decimal_odds')} | "
            f"**{r.get('verdict')}** | {'Y' if r.get('promote_to_deep') else ''} | "
            f"{(r.get('reason') or '')[:50]} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("_Stage 1 Light Research. Only **deep** packs (evidence + p_model) can be recommended._")
    lines.append("")
    return "\n".join(lines)


def merge_deep_status(cfg: dict[str, Any], day: str | None = None) -> dict[str, Any]:
    """Refresh light batch flags from current evidence dir."""
    from nt.board import shortlist_board
    from nt.odds_parse import parse_odds_file, attach_evidence

    payload = load_light_batch(cfg, day)
    records = payload.get("records") or []
    if not records:
        return payload

    # Build deep index from evidence files
    ev_dir = path_from_config(cfg, "evidence")
    deep_keys: set[tuple[str, str]] = set()
    p_by_key: dict[tuple[str, str], float] = {}
    if ev_dir.exists():
        for p in ev_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            m = str(data.get("match") or "").strip()
            s = str(data.get("selection") or "").strip()
            if m and s and data.get("p_model") is not None:
                deep_keys.add((m, s))
                try:
                    p_by_key[(m, s)] = float(data["p_model"])
                except (TypeError, ValueError):
                    pass

    for r in records:
        k = (r.get("match") or "", r.get("selection") or "")
        if k in deep_keys:
            r["tier"] = "deep"
            r["has_deep_pack"] = True
            r["has_p_model"] = True
            r["promote_to_deep"] = False
            if k in p_by_key:
                r["strength_notes"] = (r.get("strength_notes") or "") + f" | deep p={p_by_key[k]}"
            r["reason"] = (r.get("reason") or "") + " | deep pack present"

    payload["records"] = records
    payload["stats"] = coverage_stats(records, int(payload.get("shortlist_n") or len(records)))
    payload["merged_at"] = utc_now()
    save_light_batch(cfg, payload, day=day)
    return payload


def _scan_pack_meta(
    cfg: dict[str, Any],
    *,
    haircut: float | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """
    Index evidence packs → raw_ev / deep_exhausted (research rank only).
    raw_ev uses board-attached odds_at_research / decimal_odds_ref / odds if present.
    """
    from nt.evidence import ev_after_haircut

    hc = float(haircut if haircut is not None else _haircut_from_cfg(cfg))
    tcfg = tiers_cfg(cfg)
    exhausted_thr = float(
        tcfg.get("raw_ev_exhausted")
        if tcfg.get("raw_ev_exhausted") is not None
        else -0.05
    )
    out: dict[tuple[str, str], dict[str, Any]] = {}
    ev_dir = path_from_config(cfg, "evidence")
    if not ev_dir.exists():
        return out
    for p in ev_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        m = str(data.get("match") or "").strip()
        s = str(data.get("selection") or "").strip()
        if not m or not s:
            continue
        pm = data.get("p_model")
        if pm is None:
            continue
        try:
            p_model = float(pm)
        except (TypeError, ValueError):
            continue
        odds = None
        for k in ("odds_at_research", "decimal_odds_ref", "odds", "decimal_odds"):
            if data.get(k) is not None:
                try:
                    odds = float(data[k])
                    break
                except (TypeError, ValueError):
                    pass
        raw_ev = None
        if odds is not None and odds > 1.0:
            raw_ev = float(ev_after_haircut(p_model, odds, hc))
        meta = {
            "has_pack": True,
            "p_model": p_model,
            "odds": odds,
            "raw_ev": raw_ev,
            "deep_exhausted": bool(
                raw_ev is not None and float(raw_ev) < exhausted_thr
            ),
            "path": str(p),
        }
        out[(m, s)] = meta
    return out


def _score_inject_clearability(
    rec: "LightRecord",
    cfg: dict[str, Any],
    *,
    batch_priors: list[float | None] | None = None,
    groups: dict[tuple[str, str], list[tuple[float, "LightRecord"]]] | None = None,
) -> float:
    """Clearability rank for inject hard-cap (research only; no p_model invent)."""
    from nt.clearability import (
        batch_prior_percentile,
        clearability_score,
        is_alt_preferred_macro,
    )

    haircut = _haircut_from_cfg(cfg)
    tcfg = tiers_cfg(cfg)
    pref_lo = float(tcfg.get("preferred_odds_lo") or 1.85)
    fam = rec.market_family or selection_family(rec.selection, (rec.sport or "").lower())
    pev = float(rec.prior_ev) if rec.prior_ev is not None else None
    bp = batch_prior_percentile(pev, batch_priors or [pev])
    is_coin = False
    if groups is not None:
        is_coin = _coin_flip_for_record(rec, groups, cfg)
    return clearability_score(
        odds=float(rec.decimal_odds),
        prior_ev=pev,
        prior_p=float(rec.prior_p) if rec.prior_p is not None else None,
        haircut=haircut,
        batch_percentile=bp,
        is_coin_flip=is_coin,
        is_alt=is_alt_preferred_macro(fam, rec.selection),
        is_short_main=is_short_main_line(
            rec.selection, rec.decimal_odds, fam, preferred_odds_lo=pref_lo
        ),
        has_structural_note=_is_structural_note(rec),
        family_hist_n=0,
        family_clear_rate=None,
        cfg=cfg,
    )


def rank_inject_records(
    inject_recs: list["LightRecord"],
    cfg: dict[str, Any],
    *,
    max_inject: int,
) -> list["LightRecord"]:
    """
    Rank inject candidates by clearability_score and hard-cap to max_inject.

    Must run **before** build_deep_queue so large dumps do not drop high-clear
    alts solely because they appear late in file order.
    """
    if not inject_recs or max_inject <= 0:
        return []
    batch_priors = [
        float(r.prior_ev) if r.prior_ev is not None else None for r in inject_recs
    ]
    groups = _peer_odds_map(inject_recs)
    scored: list[tuple[float, LightRecord]] = []
    for r in inject_recs:
        sc = _score_inject_clearability(
            r, cfg, batch_priors=batch_priors, groups=groups
        )
        r.clearability_score = sc
        scored.append((sc, r))
    scored.sort(key=lambda x: (-x[0], x[1].decimal_odds))
    return [r for _sc, r in scored[: int(max_inject)]]


def _mid_unresearched_from_coverage(cfg: dict[str, Any]) -> int | None:
    """Best-effort mid_unresearched_n from coverage_health.json; None if unknown."""
    try:
        from nt.config import path_from_config

        paths = cfg.get("paths") or {}
        if paths.get("state_dir"):
            state = path_from_config(cfg, "state_dir")
        else:
            state = Path("data/state")
        path = state / "coverage_health.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("mid_unresearched_n") is None:
            return None
        return int(data["mid_unresearched_n"])
    except Exception:
        return None


def _raw_ev_pass_threshold(cfg: dict[str, Any]) -> float:
    """
    Min raw_ev after haircut treated as "pass" for EV-fail trigger counts.

    Uses selection.standard_min_ev (default 0.02), not bare ≥0 — matches desk
    min-EV bar better than the zero proxy (PR6 may refine with full funnel).
    """
    sel = cfg.get("selection") or {}
    return float(sel.get("standard_min_ev", 0.02))


def _records_from_dicts(
    items: list[dict[str, Any]],
    cfg: dict[str, Any],
    *,
    source: str = "inject",
) -> list[LightRecord]:
    """Build LightRecords for dump/scan injects (research-rank; may run prefilter)."""
    out: list[LightRecord] = []
    for it in items:
        match = str(it.get("match") or "")
        selection = str(it.get("selection") or "")
        if not match or not selection:
            continue
        sport = str(it.get("sport") or "unknown")
        odds = float(it.get("decimal_odds") or it.get("odds") or 1.5)
        rec = auto_light_assess(
            match=match,
            selection=selection,
            sport=sport,
            odds=odds,
            cfg=cfg,
            has_deep=bool(it.get("has_evidence") or it.get("has_deep_pack")),
            has_p=bool(it.get("has_p_model")),
            p_model=it.get("p_model"),
            score=float(it.get("score") or 0),
        )
        # Injects that pass stage screens stay eligible even if auto would fail longshot
        if it.get("force_pass") or source == "inject":
            # Keep prefilter discard; only override pure light-band fails when prior ok
            if rec.verdict == "fail" and "prefilter" not in (rec.reason or "") and "stage" not in (
                rec.reason or ""
            ):
                o = odds
                if 1.70 <= o <= 3.20:
                    rec.verdict = "pass"
                    rec.reason = (rec.reason or "") + " | inject band override"
            if rec.verdict == "fail" and (
                "stage1" in (rec.reason or "") or "stage2" in (rec.reason or "")
            ):
                # Stage discard stands — do not inject noise
                continue
        rec.source = source
        rec.is_inject = source == "inject"
        if it.get("prior_ev") is not None:
            try:
                rec.prior_ev = float(it["prior_ev"])
                rec.prior_available = True
            except (TypeError, ValueError):
                pass
        if it.get("prior_p") is not None:
            try:
                rec.prior_p = float(it["prior_p"])
                rec.prior_available = True
            except (TypeError, ValueError):
                pass
        out.append(rec)
    return out


def research_second_pass(
    cfg: dict[str, Any],
    odds_path: Path | None = None,
    *,
    records: list[LightRecord] | list[dict[str, Any]] | None = None,
    inject_candidates: list[dict[str, Any]] | None = None,
    pack_meta_by_key: dict[tuple[str, str], dict[str, Any]] | None = None,
    coverage_overlay: dict[str, Any] | None = None,
    clearability_overlay: dict[str, Any] | None = None,
    force: bool = True,
    write: bool = True,
    day: str | None = None,
    n_raw_ev_pass: int | None = None,
    mid_unresearched: int | None = None,
    force_requeue_exhausted: bool = False,
) -> dict[str, Any]:
    """
    EV-fail refresh / second-pass (design §1b).

    Marks raw_ev < raw_ev_exhausted packs as deep_exhausted, injects dump/scan
    alts (unpacked), rebuilds dual-track queue in refresh mode. Does not invent
    p_model. Exhausted packs are not re-queued unless force_requeue_exhausted
    and no injects remain.
    """
    tcfg = tiers_cfg(cfg)
    haircut = _haircut_from_cfg(cfg)
    exhausted_thr = float(
        tcfg.get("raw_ev_exhausted")
        if tcfg.get("raw_ev_exhausted") is not None
        else -0.05
    )
    max_inject = int(tcfg.get("second_pass_max_inject") or 12)
    min_deep = int(tcfg.get("second_pass_min_deep_packs") or 8)

    # Normalize records
    light_recs: list[LightRecord] = []
    if records is None:
        batch = load_light_batch(cfg, day)
        raw_list = batch.get("records") or []
        for d in raw_list:
            if not isinstance(d, dict):
                continue
            light_recs.append(
                LightRecord(
                    match=str(d.get("match") or ""),
                    selection=str(d.get("selection") or ""),
                    sport=str(d.get("sport") or ""),
                    decimal_odds=float(d.get("decimal_odds") or 1.5),
                    odds_band=str(d.get("odds_band") or ""),
                    market_family=str(d.get("market_family") or ""),
                    tier=str(d.get("tier") or "light"),
                    verdict=str(d.get("verdict") or "pass"),
                    promote_to_deep=bool(d.get("promote_to_deep")),
                    script_conflict=bool(d.get("script_conflict")),
                    base_rate_conflict=bool(d.get("base_rate_conflict")),
                    rough_p_needed=d.get("rough_p_needed"),
                    rough_ev_note=str(d.get("rough_ev_note") or ""),
                    strength_notes=str(d.get("strength_notes") or ""),
                    weakness_notes=str(d.get("weakness_notes") or ""),
                    reason=str(d.get("reason") or ""),
                    has_deep_pack=bool(d.get("has_deep_pack")),
                    has_p_model=bool(d.get("has_p_model")),
                    source=str(d.get("source") or "auto"),
                    prior_p=d.get("prior_p"),
                    prior_ev=d.get("prior_ev"),
                    prior_available=bool(d.get("prior_available")),
                    prefilter_stage1=str(d.get("prefilter_stage1") or ""),
                    prefilter_stage2=str(d.get("prefilter_stage2") or ""),
                    prefilter_rank=d.get("prefilter_rank"),
                    deep_exhausted=bool(d.get("deep_exhausted")),
                    raw_ev=d.get("raw_ev"),
                )
            )
    else:
        for r in records:
            if isinstance(r, LightRecord):
                light_recs.append(r)
            elif isinstance(r, dict):
                light_recs.extend(_records_from_dicts([r], cfg, source=str(r.get("source") or "auto")))

    pack_meta = pack_meta_by_key if pack_meta_by_key is not None else _scan_pack_meta(cfg, haircut=haircut)
    raw_pass_thr = _raw_ev_pass_threshold(cfg)

    # Pack count SSOT: evidence index size, then light flags not already in meta
    seen_pack_keys: set[tuple[str, str]] = set(pack_meta.keys())
    n_packs = len(pack_meta)
    n_pass = 0
    exhausted_keys: list[tuple[str, str]] = []

    # Count passes from pack_meta first (full evidence dir)
    for k, meta in pack_meta.items():
        rev = meta.get("raw_ev")
        if rev is not None and float(rev) >= raw_pass_thr:
            n_pass += 1

    # Mark exhausted on light records
    for r in light_recs:
        meta = pack_meta.get(r.key())
        if meta:
            r.has_p_model = True
            r.has_deep_pack = True
            if meta.get("raw_ev") is not None:
                r.raw_ev = float(meta["raw_ev"])
            if meta.get("deep_exhausted") or (
                r.raw_ev is not None and float(r.raw_ev) < exhausted_thr
            ):
                r.deep_exhausted = True
                exhausted_keys.append(r.key())
                r.reason = (r.reason or "") + " | deep_exhausted"
        elif r.has_p_model:
            if r.key() not in seen_pack_keys:
                n_packs += 1
                seen_pack_keys.add(r.key())
                if r.raw_ev is not None and float(r.raw_ev) >= raw_pass_thr:
                    n_pass += 1
            if r.raw_ev is not None and float(r.raw_ev) < exhausted_thr:
                r.deep_exhausted = True
                exhausted_keys.append(r.key())

    if n_raw_ev_pass is not None:
        n_pass = int(n_raw_ev_pass)

    # mid_unresearched: explicit arg > coverage_health > unknown
    mid_unknown = False
    if mid_unresearched is not None:
        mid_u = int(mid_unresearched)
    else:
        cov_mid = _mid_unresearched_from_coverage(cfg)
        if cov_mid is None:
            mid_unknown = True
            mid_u = -1  # sentinel for auto path
        else:
            mid_u = int(cov_mid)

    if not force and mid_unknown:
        # Fail-closed auto path: unknown mid coverage must not false-trigger EV-fail
        return {
            "ok": False,
            "reason": "mid_unresearched_unknown",
            "n_packs_with_p": n_packs,
            "n_raw_ev_pass": n_pass,
            "mid_unresearched": None,
            "raw_ev_pass_threshold": raw_pass_thr,
            "deep_queue": [],
            "mode": "normal",
            "note": (
                "Pass mid_unresearched=0 explicitly or ensure coverage_health.json; "
                "CLI/operator second-pass uses force=True"
            ),
        }

    mid_for_trigger = mid_u if mid_u >= 0 else 0
    triggered = force or ev_fail_refresh_triggered(
        n_packs_with_p=n_packs,
        n_raw_ev_pass=n_pass,
        mid_unresearched=mid_for_trigger,
        min_deep_packs=min_deep,
    )
    if not triggered:
        return {
            "ok": False,
            "reason": "ev_fail_refresh_not_triggered",
            "n_packs_with_p": n_packs,
            "n_raw_ev_pass": n_pass,
            "mid_unresearched": mid_u if mid_u >= 0 else None,
            "raw_ev_pass_threshold": raw_pass_thr,
            "deep_queue": [],
            "mode": "normal",
        }

    # Inject candidates (unpacked only)
    inject_items = list(inject_candidates or [])
    if not inject_items and bool(tcfg.get("second_pass_from_dump", True)) and odds_path:
        try:
            cands = parse_odds_file(Path(odds_path), cfg)
            packed = set(pack_meta.keys()) | {r.key() for r in light_recs if r.has_p_model}
            for c in cands:
                k = (str(getattr(c, "match", "") or ""), str(getattr(c, "selection", "") or ""))
                if k in packed or not k[0] or not k[1]:
                    continue
                odds = float(getattr(c, "decimal_odds", 0) or 0)
                if odds < 1.70 or odds > 3.20:
                    continue
                inject_items.append(
                    {
                        "match": k[0],
                        "selection": k[1],
                        "sport": str(getattr(c, "sport", "") or ""),
                        "decimal_odds": odds,
                        "score": float(getattr(c, "score", 0) or 0),
                    }
                )
        except Exception:
            pass

    # Assess all inject candidates (soft pre-cap only for pathological dumps)
    soft_cap = max(max_inject * 5, max_inject)
    if len(inject_items) > soft_cap:
        # Still score all if modest; only truncate extreme dumps before assess
        # Keep soft_cap*2 max for assess cost control
        inject_items = inject_items[: max(soft_cap * 2, 60)]
    inject_recs = _records_from_dicts(inject_items, cfg, source="inject")
    # Drop injects that already have packs
    inject_recs = [
        r
        for r in inject_recs
        if r.key() not in pack_meta and not r.has_p_model
    ]
    # Rank by clearability THEN hard-cap (not dump order)
    inject_recs = rank_inject_records(inject_recs, cfg, max_inject=max_inject)

    # If no injects and not force_requeue, queue may be empty (correct)
    requeue = bool(force_requeue_exhausted) and len(inject_recs) == 0

    if coverage_overlay is None:
        try:
            from nt.control_signals import active_coverage_priority_overlay

            coverage_overlay = active_coverage_priority_overlay(cfg)
        except Exception:
            coverage_overlay = {"active": False}

    soft_by_key: dict[tuple[str, str], float | None] = {}
    board_score_by_key: dict[tuple[str, str], float] = {}
    deep_queue = build_deep_queue(
        light_recs,
        cfg,
        soft_by_key=soft_by_key,
        board_score_by_key=board_score_by_key,
        coverage_overlay=coverage_overlay or {"active": False},
        clearability_overlay=clearability_overlay,
        mode="refresh",
        inject_records=inject_recs,
        pack_meta_by_key=pack_meta,
        force_requeue_exhausted=requeue,
    )

    promote_keys = {r.key() for r in deep_queue}
    for r in light_recs:
        if r.key() in promote_keys:
            r.promote_to_deep = True
            if "second-pass" not in (r.reason or ""):
                r.reason = (r.reason or "") + " | engine second-pass queue"
        elif r.deep_exhausted:
            r.promote_to_deep = False

    target = min(int(tcfg["deep_target_n"]), int(tcfg["deep_max_n"]))
    cl_n, cov_n = dual_track_sizes(
        target,
        coverage_overlay_active=bool((coverage_overlay or {}).get("active")),
        clearability_overlay_active=bool(
            (clearability_overlay or _active_clearability_overlay(cfg)).get("active")
        ),
    )

    payload: dict[str, Any] = {
        "ok": True,
        "day": day or date.today().isoformat(),
        "odds_path": str(odds_path) if odds_path else None,
        "generated_at": utc_now(),
        "mode": "refresh",
        "second_pass_ran": True,
        "inject_n": len(inject_recs),
        "exhausted_n": len(exhausted_keys),
        "exhausted_keys": [{"match": m, "selection": s} for m, s in exhausted_keys],
        "n_packs_with_p": n_packs,
        "n_raw_ev_pass": n_pass,
        "mid_unresearched": mid_u if mid_u >= 0 else None,
        "raw_ev_pass_threshold": raw_pass_thr,
        "tiers_config": tcfg,
        "deep_queue": [_queue_line_export(r, tcfg) for r in deep_queue],
        "deep_queue_composition": _queue_composition_stats(deep_queue, tcfg),
        "deep_queue_mode": "refresh",
        "dual_track_sizes": {"clearable_n": cl_n, "coverage_n": cov_n},
        "records": [asdict(r) for r in light_recs],
        "force_requeue_exhausted": requeue,
    }

    if write:
        # Merge into light batch path
        try:
            path = save_light_batch(cfg, {**load_light_batch(cfg, day), **payload}, day=day)
            payload["path"] = str(path)
        except Exception as ex:  # noqa: BLE001
            payload["light_write_error"] = str(ex)
        try:
            from nt.deep_queue_state import write_deep_queue_from_light_payload

            dq_path = write_deep_queue_from_light_payload(
                cfg, payload, source="second_pass"
            )
            payload["deep_queue_state_path"] = str(dq_path)
        except Exception as ex:  # noqa: BLE001
            payload["deep_queue_state_error"] = str(ex)

    return payload
