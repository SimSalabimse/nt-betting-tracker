from __future__ import annotations

"""
Tiered research — Stage 1 (Light) vs Stage 2 (Deep).

Light: broad, structured, fast filter over most of the shortlist.
Deep: full evidence/*.json + p_model (only deep lines may be recommended).

Coverage targets (config research.tiers):
  light_coverage_target: 0.70–1.0 of shortlist
  min_light_per_sport_when_n: if sport has ≥N shortlist lines, light at least K

Coverage floor (config research.coverage_floor) — Mechanism A only:
  dynamic deep_target_n, top-promo scaffolds, sport-rotation floor.
  Never invents p_model; never softens min_ev.
"""

import json
import math
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
        "deep_max_n": 15,  # hard cap (≥ deep_target_max when dynamic)
        "deep_target_dynamic": True,  # scale target with board size
        "deep_target_min": 8,
        "deep_target_max": 15,
        "deep_target_divisor": 8,  # target = clamp(min, max, board_lines // divisor)
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
    }
    return {**defaults, **raw}


def coverage_floor_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    """Quality-preserving coverage floor knobs (Mechanism A)."""
    rcfg = research_cfg(cfg)
    raw = dict(rcfg.get("coverage_floor") or {})
    defaults = {
        "enabled": True,
        "top_promo_scaffold_pct": 0.20,
        "sport_rotation_min_lines": 5,
        # Policy: scaffolds never invent p_model. Enforced at end of build_deep_queue
        # when True (filter any has_p_model — defense in depth; selection already excludes them).
        "require_real_pack": True,
        "coverage_pressure_boost": 40.0,
    }
    return {**defaults, **raw}


def _cfg_num(d: dict[str, Any], key: str, default: float | int) -> float | int:
    """None-aware numeric read — preserves legitimate 0 / 0.0 (unlike `or default`)."""
    raw = d.get(key, default)
    if raw is None:
        return default
    try:
        if isinstance(default, bool):
            return bool(raw)
        if isinstance(default, int) and not isinstance(default, bool):
            return int(raw)
        return float(raw)
    except (TypeError, ValueError):
        return default


def _sport_key(sport_or_rec: Any) -> str:
    """Normalize sport for caps + rotation (blank → unknown; one bucket)."""
    if hasattr(sport_or_rec, "sport"):
        s = getattr(sport_or_rec, "sport", None)
    else:
        s = sport_or_rec
    sp = (str(s) if s is not None else "").strip().lower()
    return sp or "unknown"


def dynamic_deep_target_n(cfg: dict[str, Any], board_lines: int) -> int:
    """
    Deep queue target size from board width.

    If deep_target_dynamic is false → static deep_target_n.
    Else → clamp(board_lines // divisor, min, max).
    Fail-closed: bad/non-numeric board_lines → static; empty board → 0.
    None-aware min/max/divisor (0 is a valid configured value).
    """
    tcfg = tiers_cfg(cfg)
    static = int(_cfg_num(tcfg, "deep_target_n", 8))
    if not bool(tcfg.get("deep_target_dynamic", False)):
        return static
    try:
        n = int(board_lines)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return static
    if n <= 0:
        return 0
    lo = int(_cfg_num(tcfg, "deep_target_min", static))
    hi = int(_cfg_num(tcfg, "deep_target_max", int(_cfg_num(tcfg, "deep_max_n", 15))))
    if hi < lo:
        hi = lo
    div = max(1, int(_cfg_num(tcfg, "deep_target_divisor", 8)))
    return max(lo, min(hi, n // div))


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


def promotion_score_components(
    rec: "LightRecord",
    cfg: dict[str, Any],
    *,
    soft_odds: float | None = None,
    board_score: float = 0.0,
    coverage_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Auditable breakdown of anti-chalk promotion_score (research rank only).

    Returns ``{total, components, scorer}``. Total matches ``promotion_score``.
    Does not invent p_model.
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

    components: dict[str, float] = {"base": 50.0}
    # Odds band — primary research band is preferred_lo–preferred_hi (High-Volume v2)
    if pref_lo <= odds <= pref_hi:
        components["mid_band"] = mid_boost
    elif alt_lo <= odds < pref_lo:
        components["near_pref_band"] = 20.0
    elif pref_hi < odds <= 3.20:
        components["longish_band"] = 12.0
    elif odds < short_chalk:
        structural = False
        need = rec.rough_p_needed
        if need is not None and float(need) <= 0.55 and not _is_first_goal(rec.selection):
            structural = True
        components["short_chalk"] = -15.0 if structural else short_pen

    preferred = is_preferred_line(
        rec.selection,
        odds,
        family,
        preferred_odds_lo=pref_lo,
        alt_preferred_odds_lo=alt_lo,
    )
    short_main = is_short_main_line(rec.selection, odds, family, preferred_odds_lo=pref_lo)
    if preferred and not short_main:
        components["preferred"] = 25.0
    if short_main:
        components["short_main"] = -30.0
    fam = (family or "").lower()
    sel = (rec.selection or "").lower()
    if fam == "handicap" or "handikap" in sel:
        components["handicap"] = alt_boost
    if "3.5" in sel or "4.5" in sel or fam in ("totals_over", "totals_under") and "2.5" not in sel:
        components["alt_total"] = alt_boost
    if fam == "period" or "1. omgang" in sel or "1. sett" in sel:
        components["period"] = 6.0

    if soft_odds is not None and odds > 1.0:
        if soft_odds >= odds * (1.0 + soft_rel):
            components["soft_value"] = 30.0

    ov = coverage_overlay or {}
    if ov.get("active"):
        band_lo, band_hi = parse_odds_band(str(ov.get("target_odds_band") or "1.85-2.60"))
        in_band = odds >= band_lo and (band_hi is None or odds <= band_hi)
        if in_band:
            wb = ov.get("weight_boost")
            components["coverage_band"] = 30.0 if wb is None else float(wb)
            cfc = coverage_floor_cfg(cfg)
            if cfc.get("enabled", True):
                pressure = float(_cfg_num(cfc, "coverage_pressure_boost", 0.0))
                if pressure:
                    components["coverage_pressure"] = pressure
        prefer = [str(x).lower() for x in (ov.get("prefer") or [])]
        if "handicaps" in prefer and (fam == "handicap" or "handikap" in sel):
            components["cov_prefer_hc"] = 10.0
        if "alt_totals" in prefer and ("3.5" in sel or "4.5" in sel or "totalt" in sel):
            components["cov_prefer_alt"] = 10.0
        if "period" in prefer and (fam == "period" or "1. omgang" in sel or "1. sett" in sel):
            components["cov_prefer_period"] = 10.0
        if "dogs" in prefer and odds >= pref_lo and _is_ml_family(family, rec.selection):
            components["cov_prefer_dogs"] = 10.0

    if board_score:
        components["board_score"] = min(15.0, 0.1 * float(board_score))

    if rec.prior_available and rec.prior_ev is not None:
        pev = float(rec.prior_ev)
        if pev > 0:
            components["prior_ev"] = min(25.0, 80.0 * pev)
        elif pev < -0.02:
            components["prior_ev"] = max(-25.0, 60.0 * pev)

    total = round(sum(float(v) for v in components.values()), 3)
    return {
        "total": total,
        "components": {k: round(float(v), 3) for k, v in components.items()},
        "scorer": "promotion_score",
        "preferred": preferred,
        "short_main": short_main,
    }


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
    return float(
        promotion_score_components(
            rec,
            cfg,
            soft_odds=soft_odds,
            board_score=board_score,
            coverage_overlay=coverage_overlay,
        )["total"]
    )


def build_deep_queue(
    records: list["LightRecord"],
    cfg: dict[str, Any],
    *,
    soft_by_key: dict[tuple[str, str], float | None] | None = None,
    board_score_by_key: dict[tuple[str, str], float] | None = None,
    coverage_overlay: dict[str, Any] | None = None,
    board_lines: int | None = None,
) -> list["LightRecord"]:
    """
    Engine deep worklist with hard composition quotas (fail-closed shrink).

    Coverage floor (Mechanism A): dynamic target, top-promo scaffold, sport rotation.
    Never invents p_model; never softens min_ev / haircut.
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

    ov = coverage_overlay or {}
    cfc = coverage_floor_cfg(cfg)
    floor_on = bool(cfc.get("enabled", True))
    pref_lo = float(tcfg["preferred_odds_lo"])
    alt_lo_raw = tcfg.get("alt_preferred_odds_lo")
    alt_lo = (
        float(tcfg["short_chalk_odds"])
        if alt_lo_raw is None
        else float(alt_lo_raw)
    )
    min_pref = float(tcfg["deep_min_preferred_share"])
    max_short = float(tcfg["deep_max_short_main_share"])
    if ov.get("active"):
        cov_share = ov.get("coverage_preferred_share")
        min_pref = max(min_pref, 0.55 if cov_share is None else float(cov_share))

    try:
        n_board = int(board_lines) if board_lines is not None else len(records)
    except (TypeError, ValueError):
        n_board = len(records)
    target = dynamic_deep_target_n(cfg, n_board)
    if ov.get("active"):
        mdp = ov.get("min_deep_packs")
        if mdp is not None:
            target = max(target, int(mdp))
    # Hard cap: deep_max_n (aligned with deep_target_max when dynamic — see config)
    deep_max = int(_cfg_num(tcfg, "deep_max_n", 15))
    if bool(tcfg.get("deep_target_dynamic", False)):
        deep_max = max(deep_max, int(_cfg_num(tcfg, "deep_target_max", deep_max)))
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

    def _is_pure_short_main(r: LightRecord) -> bool:
        """Short-main chalk (not preferred) — never force-promote via floor paths."""
        return _sm(r) and not _pref(r)

    def _annotate(r: LightRecord, tag: str) -> None:
        if tag not in (r.rough_ev_note or ""):
            r.rough_ev_note = (r.rough_ev_note or "") + f" | {tag}"
        if tag not in (r.reason or ""):
            r.reason = (r.reason or "") + f" | {tag}"

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
        # stash for reason tags
        r.rough_ev_note = (r.rough_ev_note or "") + f" | promo_score={sc:.1f}"
        candidates.append((sc, r))

    candidates.sort(key=lambda x: (-x[0], x[1].decimal_odds))

    # Top-promo scaffold keys (top pct by promotion_score among candidates)
    # None-aware: top_promo_scaffold_pct=0 disables scaffolds (not treated as missing).
    scaffold_keys: set[tuple[str, str]] = set()
    if floor_on and candidates:
        pct = float(_cfg_num(cfc, "top_promo_scaffold_pct", 0.20))
        if pct <= 0:
            n_scaffold = 0
        else:
            n_scaffold = min(len(candidates), max(1, math.ceil(pct * len(candidates))))
        for _sc, r in candidates[:n_scaffold]:
            scaffold_keys.add(r.key())
            _annotate(r, "coverage_floor:top_promo_scaffold")

    preferred_pool = [(sc, r) for sc, r in candidates if _pref(r)]
    short_pool = [(sc, r) for sc, r in candidates if _sm(r)]
    other_pool = [
        (sc, r)
        for sc, r in candidates
        if not _pref(r) and not _sm(r)
    ]

    # Fail-closed shrink: never pad with chalk to hit target
    n_pref_avail = len(preferred_pool)
    if n_pref_avail == 0:
        # Only non-preferred exist — prefer empty worklist over chalk flood
        return []

    # Max queue size such that preferred can still be ≥ min_pref of final size
    # n_pref / n >= min_pref  =>  n <= n_pref / min_pref
    max_n_from_pref = int(n_pref_avail / min_pref) if min_pref > 0 else deep_max
    n_target = min(target, deep_max, max_n_from_pref)
    if n_target < 1:
        n_target = min(n_pref_avail, 1)

    deep_queue: list[LightRecord] = []
    sp_count: dict[str, int] = defaultdict(int)
    short_count = 0
    pref_count = 0
    selected: set[tuple[str, str]] = set()

    def _try_add(
        r: LightRecord,
        *,
        as_short: bool,
        as_pref: bool,
        force: bool = False,
    ) -> bool:
        nonlocal short_count, pref_count
        # Force paths may expand to deep_max (aligned with deep_target_max when dynamic).
        # Non-force fills stop at n_target (composition shrink target).
        hard_cap = deep_max if force else n_target
        if len(deep_queue) >= hard_cap:
            return False
        k = r.key()
        if k in selected:
            return False
        sp = _sport_key(r)
        if sp_count[sp] >= 3:
            return False
        if as_short:
            # Short-main share vs *final* trial size (works under force expansion too)
            trial_n = len(deep_queue) + 1
            if (short_count + 1) / max(trial_n, 1) > max_short + 1e-9:
                return False
        # Prefer floor on force: apply even when queue is empty (non-pref cannot open queue)
        if force and not as_pref:
            trial_n = len(deep_queue) + 1
            trial_pref = pref_count  # non-pref add leaves pref_count unchanged
            if trial_pref / max(trial_n, 1) + 1e-9 < min_pref:
                return False
        deep_queue.append(r)
        selected.add(k)
        sp_count[sp] += 1
        if as_short:
            short_count += 1
        if as_pref:
            pref_count += 1
        return True

    # Phase A0: force top-promo scaffolds first (expand candidate selection, not chalk flood)
    if floor_on and scaffold_keys:
        for _sc, r in candidates:
            if r.key() not in scaffold_keys:
                continue
            if len(deep_queue) >= deep_max:
                break
            is_p = _pref(r)
            is_s = _sm(r)
            if _is_pure_short_main(r):
                # Scaffolds expand preferred/mid set; do not force short-main chalk
                continue
            ok = _try_add(r, as_short=is_s, as_pref=is_p, force=True)
            if not ok and r.key() not in selected:
                # Composition blocked — still record forced intent
                _annotate(r, "coverage_floor:top_promo_scaffold:blocked")

    # Phase A: preferred first (score order)
    for _sc, r in preferred_pool:
        if len(deep_queue) >= n_target:
            break
        _try_add(r, as_short=False, as_pref=True)

    # Ensure preferred share on current queue
    def _pref_share() -> float:
        if not deep_queue:
            return 0.0
        return pref_count / len(deep_queue)

    # Phase B: fill remainder with other then short under cap (never pad chalk past floor)
    for _sc, r in other_pool + short_pool:
        if len(deep_queue) >= n_target:
            break
        is_p = _pref(r)
        is_s = _sm(r)
        # Do not add non-preferred if it would break preferred floor at target size
        trial_n = len(deep_queue) + 1
        trial_pref = pref_count + (1 if is_p else 0)
        if not is_p and trial_pref / max(trial_n, 1) + 1e-9 < min_pref:
            continue
        _try_add(r, as_short=is_s, as_pref=is_p)

    # If preferred share slipped below floor, drop short_main then non-preferred from tail
    while deep_queue and _pref_share() + 1e-9 < min_pref:
        removed = False
        for i in range(len(deep_queue) - 1, -1, -1):
            r = deep_queue[i]
            if _sm(r):
                deep_queue.pop(i)
                short_count = max(0, short_count - 1)
                if _pref(r):
                    pref_count = max(0, pref_count - 1)
                sp = _sport_key(r)
                sp_count[sp] = max(0, sp_count[sp] - 1)
                selected.discard(r.key())
                removed = True
                break
        if not removed:
            for i in range(len(deep_queue) - 1, -1, -1):
                r = deep_queue[i]
                if not _pref(r):
                    deep_queue.pop(i)
                    sp = _sport_key(r)
                    sp_count[sp] = max(0, sp_count[sp] - 1)
                    selected.discard(r.key())
                    removed = True
                    break
        if not removed:
            break

    # Phase C: sport-rotation floor — sports with ≥min *eligible* light-pass and zero deep picks
    # Eligible = same as candidates (pass, no p_model, no script/base_rate conflict).
    if floor_on:
        min_sp_lines = int(_cfg_num(cfc, "sport_rotation_min_lines", 5))
        if min_sp_lines > 0:
            eligible_by_sport: dict[str, int] = Counter()
            for _sc, r in candidates:
                eligible_by_sport[_sport_key(r)] += 1
            sports_in_queue = {_sport_key(r) for r in deep_queue}
            for sport, n_elig in eligible_by_sport.items():
                if n_elig < min_sp_lines:
                    continue
                if sport in sports_in_queue:
                    continue
                sport_cands = [
                    (sc, r)
                    for sc, r in candidates
                    if _sport_key(r) == sport and r.key() not in selected
                ]
                # Mirror scaffold policy: never force pure short-main chalk.
                # Prefer preferred; fall back to non-short-main only.
                rot_pool = [
                    (sc, r) for sc, r in sport_cands if not _is_pure_short_main(r)
                ]
                pref_rot = [(sc, r) for sc, r in rot_pool if _pref(r)]
                use_pool = pref_rot if pref_rot else rot_pool
                if not use_pool:
                    # Only pure chalk / nothing left — annotate, do not force
                    if sport_cands:
                        _annotate(sport_cands[0][1], "coverage_floor:sport_rotation:no_eligible")
                    else:
                        for r in records:
                            if _sport_key(r) == sport and r.verdict == "pass" and not r.has_p_model:
                                _annotate(r, "coverage_floor:sport_rotation:no_eligible")
                                break
                    continue
                use_pool.sort(key=lambda x: (-x[0], x[1].decimal_odds))
                _sc, best = use_pool[0]
                is_p = _pref(best)
                is_s = _sm(best)
                _annotate(best, "coverage_floor:sport_rotation")
                ok = _try_add(best, as_short=is_s, as_pref=is_p, force=True)
                if ok:
                    sports_in_queue.add(sport)
                else:
                    _annotate(best, "coverage_floor:sport_rotation:blocked")

    # require_real_pack: never return invented / pre-existing p_model rows as deep worklist
    if bool(cfc.get("require_real_pack", True)):
        deep_queue = [r for r in deep_queue if not r.has_p_model]

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
    source: str = "auto"  # auto | agent | merge
    # Quant prefilter (research-rank only — not recommend p_model)
    prior_p: float | None = None
    prior_ev: float | None = None
    prior_available: bool = False
    prefilter_stage1: str = ""
    prefilter_stage2: str = ""
    prefilter_rank: float | None = None

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
        board_lines=shortlist_n,
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
        "deep_queue": [
            {
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
                    preferred_odds_lo=float(tcfg["preferred_odds_lo"]),
                    alt_preferred_odds_lo=float(
                        tcfg.get("alt_preferred_odds_lo") or tcfg["short_chalk_odds"]
                    ),
                ),
                "short_main": is_short_main_line(
                    r.selection,
                    r.decimal_odds,
                    r.market_family,
                    preferred_odds_lo=float(tcfg["preferred_odds_lo"]),
                ),
            }
            for r in deep_queue
        ],
        "deep_queue_composition": _queue_composition_stats(deep_queue, tcfg),
        "coverage_overlay_active": bool(coverage_overlay.get("active")),
        "records": rec_dicts,
        "shortlist_n": shortlist_n,
        "assessed_n": len(records),
    }

    # Mechanism B: temp_ev_relax safety net when large board + coverage warn + empty deep queue
    try:
        from nt.control_signals import maybe_emit_temp_ev_relax_from_light

        unique_matches = len({(r.match or "").strip() for r in records if (r.match or "").strip()})
        # Prefer unique shortlist matches when available
        shortlist_matches = len(
            {
                str(it.get("match") or "").strip()
                for it in items
                if str(it.get("match") or "").strip()
            }
        )
        ter_out = maybe_emit_temp_ev_relax_from_light(
            cfg,
            records=records,
            deep_queue=deep_queue,
            board_matches=max(unique_matches, shortlist_matches),
            coverage_level=None,  # load coverage_health.json when present
            shortlist_n=shortlist_n,
        )
        payload["temp_ev_relax"] = ter_out
    except Exception as ex:  # noqa: BLE001
        payload["temp_ev_relax"] = {"ok": False, "error": str(ex)}

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
