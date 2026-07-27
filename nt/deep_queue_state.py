"""
Deep queue SSOT — data/state/deep_queue.json (D17).

Engine-written composition + queue lines for Lumina preferred/short-main bars.
Does not invent shares: composition comes from light_research build_deep_queue
stats when present, otherwise counted from preferred/short_main flags on the
actual queue lines (still engine-derived line flags when light_research provides
them).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config


SCHEMA_VERSION = 1

# Stage 3b expansion (ESR K17) — large board & < min picks → next light-pass tier
DEFAULT_MIN_BOARD_MATCHES = 15
DEFAULT_MIN_BOARD_LINES = 80
DEFAULT_EXPANSION_MIN_PICKS = 2
DEFAULT_NEXT_TIER_N = 8

_EMPTY_COMPOSITION: dict[str, Any] = {
    "n": 0,
    "preferred_n": 0,
    "short_main_n": 0,
    "preferred_share": 0.0,
    "short_main_share": 0.0,
    "meets_preferred_floor": True,
    "meets_short_main_cap": True,
}


def deep_queue_state_path(cfg: dict[str, Any]) -> Path:
    """Path to data/state/deep_queue.json (configurable via paths.deep_queue_json)."""
    paths = cfg.get("paths") or {}
    if paths.get("deep_queue_json"):
        return path_from_config(cfg, "deep_queue_json")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "deep_queue.json"


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


def _fallback_line_flags(
    selection: str,
    odds: float,
    family: str = "",
    *,
    preferred_odds_lo: float = 1.85,
    alt_preferred_odds_lo: float = 1.80,
) -> tuple[bool, bool]:
    """
    Local preferred/short_main when light_research helpers are unavailable.
    Mirrors light_research definitions (not invented shares).
    """
    o = float(odds or 0)
    short_main = False
    if o < float(preferred_odds_lo):
        if _is_ou25(selection) or _is_first_goal(selection) or _is_ml_family(family, selection):
            short_main = True
    if o + 1e-12 >= float(preferred_odds_lo):
        preferred = True
    elif (not short_main) and o + 1e-12 >= float(alt_preferred_odds_lo):
        preferred = True
    else:
        preferred = False
    return preferred, short_main


def _line_flags(line: dict[str, Any], tcfg: dict[str, Any] | None = None) -> tuple[bool, bool]:
    if "preferred" in line and "short_main" in line:
        return bool(line.get("preferred")), bool(line.get("short_main"))

    selection = str(line.get("selection") or "")
    odds = float(line.get("decimal_odds") or 0)
    family = str(line.get("market_family") or line.get("family") or "")
    pref_lo = float((tcfg or {}).get("preferred_odds_lo") or 1.85)
    alt_lo = float(
        (tcfg or {}).get("alt_preferred_odds_lo")
        or (tcfg or {}).get("short_chalk_odds")
        or 1.80
    )

    try:
        from nt.light_research import is_preferred_line, is_short_main_line

        preferred = is_preferred_line(
            selection,
            odds,
            family,
            preferred_odds_lo=pref_lo,
            alt_preferred_odds_lo=alt_lo,
        )
        short_main = is_short_main_line(
            selection, odds, family, preferred_odds_lo=pref_lo
        )
        return bool(preferred), bool(short_main)
    except Exception:
        return _fallback_line_flags(
            selection,
            odds,
            family,
            preferred_odds_lo=pref_lo,
            alt_preferred_odds_lo=alt_lo,
        )


def normalize_queue_line(
    line: dict[str, Any], tcfg: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Export line shape: match, selection, odds, preferred/short_main flags."""
    preferred, short_main = _line_flags(line, tcfg)
    out: dict[str, Any] = {
        "match": str(line.get("match") or ""),
        "selection": str(line.get("selection") or ""),
        "decimal_odds": float(line.get("decimal_odds") or 0),
        "preferred": preferred,
        "short_main": short_main,
    }
    sport = line.get("sport")
    if sport is not None and str(sport) != "":
        out["sport"] = str(sport)
    # Optional diagnostics when present (not required by D17)
    for key in ("reason", "prior_ev", "market_family"):
        if key in line and line[key] is not None:
            out[key] = line[key]
    return out


def composition_from_queue(
    queue: list[dict[str, Any]],
    *,
    min_preferred_share: float = 0.0,
    max_short_main_share: float = 1.0,
) -> dict[str, Any]:
    """
    Count preferred/short_main shares from normalized queue lines.
    Same field shape as light_research._queue_composition_stats.
    """
    n = len(queue)
    if n == 0:
        return dict(_EMPTY_COMPOSITION)
    pref_n = sum(1 for r in queue if r.get("preferred"))
    sm_n = sum(1 for r in queue if r.get("short_main"))
    pref_share = pref_n / n
    sm_share = sm_n / n
    min_pref = float(min_preferred_share)
    max_sm = float(max_short_main_share)
    return {
        "n": n,
        "preferred_n": pref_n,
        "short_main_n": sm_n,
        "preferred_share": round(pref_share, 3),
        "short_main_share": round(sm_share, 3),
        # Composition off (min_pref <= 0): always meets floor
        "meets_preferred_floor": (
            True if min_pref <= 0 else pref_share + 1e-9 >= min_pref
        ),
        "meets_short_main_cap": sm_share <= max_sm + 1e-9,
    }


def _cfg_share(tcfg: dict[str, Any], key: str, default: float) -> float:
    """None-aware share read — preserves legitimate 0.0 (unlike `or default`)."""
    raw = tcfg.get(key, default)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _normalize_composition(
    comp: dict[str, Any] | None,
    queue: list[dict[str, Any]],
    tcfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Prefer engine composition object when it matches queue length;
    otherwise recount from queue flags (never invent free-form shares).
    """
    tcfg = tcfg or {}
    # ESR defaults: preferred floor 0 / short-main cap 1.0 — never `or 0.55`
    min_pref = _cfg_share(tcfg, "deep_min_preferred_share", 0.0)
    max_sm = _cfg_share(tcfg, "deep_max_short_main_share", 1.0)

    if isinstance(comp, dict) and comp:
        n = int(comp.get("n") if comp.get("n") is not None else -1)
        if n == len(queue) or (n == 0 and len(queue) == 0):
            # Trust engine stats; fill any missing keys via recount of missing fields only
            base = composition_from_queue(
                queue, min_preferred_share=min_pref, max_short_main_share=max_sm
            )
            out = dict(base)
            for k in (
                "n",
                "preferred_n",
                "short_main_n",
                "preferred_share",
                "short_main_share",
                "meets_preferred_floor",
                "meets_short_main_cap",
            ):
                if k in comp and comp[k] is not None:
                    out[k] = comp[k]
            # Coerce numeric shares
            out["n"] = int(out["n"])
            out["preferred_n"] = int(out["preferred_n"])
            out["short_main_n"] = int(out["short_main_n"])
            out["preferred_share"] = float(out["preferred_share"])
            out["short_main_share"] = float(out["short_main_share"])
            out["meets_preferred_floor"] = bool(out["meets_preferred_floor"])
            out["meets_short_main_cap"] = bool(out["meets_short_main_cap"])
            return out

    return composition_from_queue(
        queue, min_preferred_share=min_pref, max_short_main_share=max_sm
    )


def _line_key(match: Any, selection: Any) -> str:
    return f"{str(match or '').strip().lower()}||{str(selection or '').strip().lower()}"


def _as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _promo_of(rec: dict[str, Any]) -> float:
    """Best-effort promo score for next-tier ranking (never invents research)."""
    for key in ("promotion_score", "promo_score"):
        v = _as_float(rec.get(key))
        if v is not None:
            return v
    bd = rec.get("promotion_score_breakdown")
    if isinstance(bd, dict):
        v = _as_float(bd.get("total"))
        if v is not None:
            return v
    note = str(rec.get("rough_ev_note") or rec.get("notes") or rec.get("reason") or "")
    if "promo_score=" in note:
        try:
            return float(note.split("promo_score=")[-1].split()[0].split("|")[0].rstrip(";,"))
        except (TypeError, ValueError, IndexError):
            pass
    # Soft ranking fallbacks from structured priors only
    prior = _as_float(rec.get("prior_ev"))
    if prior is not None:
        return 50.0 + 100.0 * prior
    prefilter = _as_float(rec.get("prefilter_rank"))
    if prefilter is not None:
        return float(prefilter)
    return 0.0


def expansion_thresholds(cfg: dict[str, Any] | None = None) -> dict[str, int]:
    """
    Board-size / pick thresholds for Stage 3b expansion signal.

    Prefer control_signals.temp_ev_relax.min_board_matches (same large-board law).
    """
    min_matches = DEFAULT_MIN_BOARD_MATCHES
    min_lines = DEFAULT_MIN_BOARD_LINES
    min_picks = DEFAULT_EXPANSION_MIN_PICKS
    next_n = DEFAULT_NEXT_TIER_N
    if cfg:
        try:
            learning = dict((cfg.get("learning") or {}).get("control_signals") or {})
            ter = dict(learning.get("temp_ev_relax") or {})
            if ter.get("min_board_matches") is not None:
                min_matches = int(ter["min_board_matches"])
        except (TypeError, ValueError):
            pass
        try:
            research = dict(cfg.get("research") or {})
            exp = dict(research.get("expansion") or {})
            if exp.get("min_board_matches") is not None:
                min_matches = int(exp["min_board_matches"])
            if exp.get("min_board_lines") is not None:
                min_lines = int(exp["min_board_lines"])
            if exp.get("min_picks") is not None:
                min_picks = int(exp["min_picks"])
            if exp.get("next_tier_n") is not None:
                next_n = int(exp["next_tier_n"])
        except (TypeError, ValueError):
            pass
    return {
        "min_board_matches": max(1, int(min_matches)),
        "min_board_lines": max(1, int(min_lines)),
        "min_picks": max(1, int(min_picks)),
        "next_tier_n": max(1, min(15, int(next_n))),
    }


def compute_expansion_signal(
    *,
    n_picks: int,
    board_matches: int | None = None,
    board_lines: int | None = None,
    light_payload: dict[str, Any] | None = None,
    deep_queue: list[Any] | None = None,
    cfg: dict[str, Any] | None = None,
    min_board_matches: int | None = None,
    min_board_lines: int | None = None,
    min_picks: int | None = None,
    next_tier_n: int | None = None,
) -> dict[str, Any]:
    """
    ESR Stage 3b: large board + low pick count + unresearched light-pass → expand.

    Pure signal — never invents p_model. Agent must deep ``next_tier_keys``
    before treating empty slip as success.
    """
    thr = expansion_thresholds(cfg)
    if min_board_matches is not None:
        thr["min_board_matches"] = int(min_board_matches)
    if min_board_lines is not None:
        thr["min_board_lines"] = int(min_board_lines)
    if min_picks is not None:
        thr["min_picks"] = int(min_picks)
    if next_tier_n is not None:
        thr["next_tier_n"] = int(next_tier_n)

    n_matches = int(board_matches) if board_matches is not None else 0
    n_lines = int(board_lines) if board_lines is not None else 0
    payload = light_payload if isinstance(light_payload, dict) else {}
    if n_matches <= 0 and payload:
        # Prefer unique matches from light records when board coverage absent
        matches = {
            str(r.get("match") or "").strip()
            for r in (payload.get("records") or [])
            if isinstance(r, dict) and str(r.get("match") or "").strip()
        }
        if matches:
            n_matches = len(matches)
        elif payload.get("shortlist_n") is not None:
            try:
                n_lines = max(n_lines, int(payload.get("shortlist_n") or 0))
            except (TypeError, ValueError):
                pass
    if n_lines <= 0 and payload:
        recs = payload.get("records") or []
        if isinstance(recs, list) and recs:
            n_lines = len(recs)
        elif payload.get("shortlist_n") is not None:
            try:
                n_lines = int(payload.get("shortlist_n") or 0)
            except (TypeError, ValueError):
                n_lines = 0

    large_board = n_matches >= thr["min_board_matches"] or n_lines >= thr["min_board_lines"]
    picks = int(n_picks) if n_picks is not None else 0
    base: dict[str, Any] = {
        "expansion_needed": False,
        "expansion_tier": 0,
        "next_tier_keys": [],
        "next_tier_n": 0,
        "reason": "",
        "large_board": large_board,
        "n_picks": picks,
        "board_matches": n_matches,
        "board_lines": n_lines,
        "min_picks": thr["min_picks"],
        "min_board_matches": thr["min_board_matches"],
        "min_board_lines": thr["min_board_lines"],
    }

    if not large_board:
        base["reason"] = "board_not_large"
        return base
    if picks >= thr["min_picks"]:
        base["reason"] = "enough_picks"
        return base

    # Current primary deep_queue keys
    dq = deep_queue
    if dq is None and payload:
        dq = payload.get("deep_queue") or []
    dq = list(dq or [])
    dq_keys: set[str] = set()
    for item in dq:
        if isinstance(item, dict):
            dq_keys.add(_line_key(item.get("match"), item.get("selection")))
        else:
            dq_keys.add(
                _line_key(getattr(item, "match", None), getattr(item, "selection", None))
            )

    # Light-pass survivors without p_model outside (or still on) queue
    survivors: list[dict[str, Any]] = []
    for rec in payload.get("records") or []:
        if not isinstance(rec, dict):
            continue
        verdict = str(rec.get("verdict") or "").lower()
        if verdict and verdict != "pass":
            continue
        if bool(rec.get("has_p_model")):
            continue
        # Drop prefilter discards
        stage1 = str(rec.get("prefilter_stage1") or "")
        if rec.get("discarded") or "fail" in stage1.lower():
            continue
        match = str(rec.get("match") or "").strip()
        sel = str(rec.get("selection") or "").strip()
        if not match or not sel:
            continue
        key = _line_key(match, sel)
        # Prefer survivors not already researched with pack; include queue gaps
        # (no p_model) as next-tier when still unfilled after primary deep.
        survivors.append(
            {
                "match": match,
                "selection": sel,
                "decimal_odds": rec.get("decimal_odds") or rec.get("odds"),
                "promotion_score": _promo_of(rec),
                "in_deep_queue": key in dq_keys,
                "has_deep_pack": bool(rec.get("has_deep_pack")),
                "key": key,
            }
        )

    # Next tier: light-pass without pack, prefer those NOT already in primary queue
    # (agent already deep-researched queue). If queue empty, any light-pass is next.
    outside = [s for s in survivors if not s["in_deep_queue"] and not s["has_deep_pack"]]
    if not outside:
        # Still expand when queue members lack packs (process miss)
        outside = [s for s in survivors if not s["has_deep_pack"]]
    if not outside:
        base["reason"] = "no_light_pass_survivors"
        return base

    outside.sort(
        key=lambda s: (
            0 if not s["in_deep_queue"] else 1,
            -float(s.get("promotion_score") or 0.0),
        )
    )
    n_take = thr["next_tier_n"]
    # Design: deep next 5–8
    n_take = max(5, min(n_take, 8)) if n_take >= 5 else n_take
    chosen = outside[:n_take]
    keys = [[c["match"], c["selection"]] for c in chosen]
    base.update(
        {
            "expansion_needed": True,
            "expansion_tier": 2,
            "next_tier_keys": keys,
            "next_tier_n": len(keys),
            "reason": "large_board_low_picks",
        }
    )
    return base


def merge_expansion_into_state(
    state: dict[str, Any],
    expansion: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach expansion fields onto a deep_queue state dict (in place + return)."""
    out = state if isinstance(state, dict) else {}
    if not expansion:
        out["expansion_needed"] = False
        out["expansion_tier"] = 0
        out["next_tier_keys"] = []
        out["expansion_reason"] = ""
        return out
    out["expansion_needed"] = bool(expansion.get("expansion_needed"))
    out["expansion_tier"] = int(expansion.get("expansion_tier") or 0)
    out["next_tier_keys"] = list(expansion.get("next_tier_keys") or [])
    out["next_tier_n"] = int(expansion.get("next_tier_n") or len(out["next_tier_keys"]))
    out["expansion_reason"] = str(expansion.get("reason") or "")
    out["expansion"] = {
        "needed": out["expansion_needed"],
        "tier": out["expansion_tier"],
        "next_tier_keys": out["next_tier_keys"],
        "next_tier_n": out["next_tier_n"],
        "reason": out["expansion_reason"],
        "large_board": bool(expansion.get("large_board")),
        "n_picks": expansion.get("n_picks"),
        "board_matches": expansion.get("board_matches"),
        "board_lines": expansion.get("board_lines"),
    }
    return out


def write_expansion_signal(
    cfg: dict[str, Any],
    expansion: dict[str, Any],
    *,
    existing_state: dict[str, Any] | None = None,
    source: str = "recommend",
) -> Path:
    """
    Merge expansion signal into data/state/deep_queue.json.

    Preserves queue composition when state already exists; otherwise writes a
    minimal expansion-only shell (queue empty) so the signal is still SSOT.
    """
    state = dict(existing_state) if isinstance(existing_state, dict) else load_deep_queue_state(cfg)
    if not state:
        state = build_deep_queue_state(queue=[], composition=None, source=source)
    else:
        state = dict(state)
        state["updated_at"] = utc_now()
        # Keep source of queue build; annotate who wrote expansion
        state["expansion_source"] = source
    merge_expansion_into_state(state, expansion)
    return write_deep_queue_state(cfg, state)


def build_deep_queue_state(
    *,
    queue: list[dict[str, Any]] | None = None,
    composition: dict[str, Any] | None = None,
    updated_at: str | None = None,
    source: str = "light_research",
    odds_path: str | None = None,
    day: str | None = None,
    tiers_config: dict[str, Any] | None = None,
    schema_version: int = SCHEMA_VERSION,
    expansion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Pure builder for deep_queue.json body.

    `queue` items should include match/selection/odds; preferred/short_main are
    normalized. `composition` should match light_research deep_queue_composition
    when provided by the engine. Optional `expansion` attaches Stage 3b fields.
    """
    tcfg = tiers_config or {}
    raw_queue = list(queue or [])
    lines = [normalize_queue_line(r, tcfg) for r in raw_queue]
    comp = _normalize_composition(composition, lines, tcfg)

    state: dict[str, Any] = {
        "schema_version": int(schema_version),
        "updated_at": updated_at or utc_now(),
        "source": source,
        "deep_queue_composition": comp,
        # Convenience mirrors for bars (same numbers as composition — not invented)
        "preferred_share": float(comp.get("preferred_share") or 0.0),
        "short_main_share": float(comp.get("short_main_share") or 0.0),
        "deep_queue": lines,
        "expansion_needed": False,
        "expansion_tier": 0,
        "next_tier_keys": [],
        "expansion_reason": "",
    }
    if odds_path is not None:
        state["odds_path"] = str(odds_path)
    if day is not None:
        state["day"] = str(day)
    if expansion is not None:
        merge_expansion_into_state(state, expansion)
    return state


def build_deep_queue_state_from_payload(
    payload: dict[str, Any],
    *,
    source: str = "light_research",
) -> dict[str, Any]:
    """Build state from run_light_research / board light payload (engine truth)."""
    queue = payload.get("deep_queue") or []
    if not isinstance(queue, list):
        queue = []
    comp = payload.get("deep_queue_composition")
    if not isinstance(comp, dict):
        comp = None
    tcfg = payload.get("tiers_config")
    if not isinstance(tcfg, dict):
        tcfg = None
    return build_deep_queue_state(
        queue=queue,
        composition=comp,
        updated_at=str(payload.get("generated_at") or "") or None,
        source=source,
        odds_path=payload.get("odds_path"),
        day=payload.get("day"),
        tiers_config=tcfg,
    )


def write_deep_queue_state(cfg: dict[str, Any], state: dict[str, Any]) -> Path:
    """Persist deep_queue.json under state_dir."""
    path = deep_queue_state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def write_deep_queue_from_light_payload(
    cfg: dict[str, Any],
    payload: dict[str, Any],
    *,
    source: str = "light_research",
) -> Path:
    """Build + write deep_queue.json from a light research payload."""
    state = build_deep_queue_state_from_payload(payload, source=source)
    return write_deep_queue_state(cfg, state)


def load_deep_queue_state(cfg: dict[str, Any]) -> dict[str, Any] | None:
    path = deep_queue_state_path(cfg)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None
