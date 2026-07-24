from __future__ import annotations

"""
Multi-sport research gates (FRA–ENG postmortem + 12h board balance).

Public API:
  evaluate_research_gates(ev, cfg, selection=..., sport=..., odds=...)
    -> (hard_issues, soft_notes)
  football_selection_family(selection)  # back-compat alias
"""

from typing import Any

from nt.research_gates.infer import (
    availability_notes,
    availability_status,
    base_rate_conflict,
    infer_context_risk,
    normalize_sport,
    script_lean,
    selection_family,
    selection_vs_script,
    tier_for_context,
)
from nt.research_gates.profiles import get_profile
from nt.research_gates.profiles import basketball as bb_prof
from nt.research_gates.profiles import darts as da_prof
from nt.research_gates.profiles import default as def_prof
from nt.research_gates.profiles import football as fb_prof
from nt.research_gates.profiles import snooker as sn_prof
from nt.research_gates.profiles import tennis as tn_prof
from nt.research_gates.types import GateContext, GateResult


def football_selection_family(selection: str) -> str:
    """Back-compat for tests and callers."""
    return selection_family(selection, "football")


def _gates_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    """Merge research.gates with legacy flat research keys."""
    from nt.defaults import research_cfg

    rcfg = research_cfg(cfg)
    nested = dict(rcfg.get("gates") or {})
    # Legacy aliases → nested
    legacy_map = {
        "reject_script_conflict": "reject_script_conflict",
        "reject_base_rate_conflict": "reject_base_rate_conflict",
        "require_lineup_status_football": "require_availability_status",
        "predicted_lineup_ok_for_totals_btts": "predicted_availability_ok",
        "require_injury_research_if_predicted": "require_availability_research_if_predicted",
        "require_confirmed_lineup_for_totals_btts": "strict_confirmed_only",
        "high_rotation_stricter_lineup": "high_context_stricter_notes",
        "high_rotation_require_confirmed": "high_context_require_confirmed",
        "high_odds_prefer_confirmed_lineup": "high_odds_prefer_confirmed",
        "lineup_gate_all_football": "lineup_gate_all_football",
    }
    out = {
        "enabled": True,
        "reject_script_conflict": True,
        "reject_base_rate_conflict": True,
        "require_availability_status": True,
        "predicted_availability_ok": True,
        "require_availability_research_if_predicted": True,
        "high_context_stricter_notes": True,
        "high_context_min_notes_chars": 40,
        "high_context_require_confirmed": False,
        "strict_confirmed_only": False,
        "high_odds_prefer_confirmed": True,
        "lineup_gate_all_football": False,
        "gate_all_markets": False,
        "high_odds_threshold": float((cfg.get("selection") or {}).get("high_odds_threshold", 2.5)),
        "sports": {
            "football": {"enabled": True},
            "tennis": {"enabled": True},
            "basketball": {"enabled": True},
            "darts": {"enabled": True},
            "snooker": {"enabled": True},
            "default": {"enabled": True},
        },
    }
    # Apply legacy flat keys first
    for old, new in legacy_map.items():
        if old in rcfg and rcfg[old] is not None:
            out[new] = rcfg[old]
    # Nested gates override
    for k, v in nested.items():
        if k == "sports" and isinstance(v, dict):
            merged = dict(out.get("sports") or {})
            for sk, sv in v.items():
                if isinstance(sv, dict):
                    merged[sk] = {**(merged.get(sk) or {}), **sv}
                else:
                    merged[sk] = sv
            out["sports"] = merged
        else:
            out[k] = v
    return out


def _sport_enabled(sport: str, gcfg: dict[str, Any]) -> bool:
    sports = gcfg.get("sports") or {}
    entry = sports.get(sport) or sports.get("default") or {"enabled": True}
    if isinstance(entry, dict):
        return bool(entry.get("enabled", True))
    return True


def _is_sensitive(sport: str, family: str, gcfg: dict[str, Any]) -> bool:
    if sport == "football":
        return fb_prof.is_avail_sensitive(family, gcfg)
    if sport == "tennis":
        return tn_prof.is_avail_sensitive(family, gcfg)
    if sport == "basketball":
        return bb_prof.is_avail_sensitive(family, gcfg)
    if sport == "darts":
        return da_prof.is_avail_sensitive(family, gcfg)
    if sport == "snooker":
        return sn_prof.is_avail_sensitive(family, gcfg)
    return def_prof.is_avail_sensitive(family, gcfg)


def evaluate_research_gates(
    ev: dict[str, Any],
    cfg: dict[str, Any],
    *,
    selection: str = "",
    sport: str = "",
    odds: float = 1.0,
) -> tuple[list[str], list[str]]:
    """
    Multi-sport research gates.

    Returns (hard_issues, soft_notes).
    hard_issues → grade F (cannot place).
    """
    gcfg = _gates_cfg(cfg)
    if not bool(gcfg.get("enabled", True)):
        return [], []

    sport_n = normalize_sport(sport, ev)
    if not _sport_enabled(sport_n, gcfg):
        return [], []

    sel_text = selection or str(ev.get("selection") or "")
    family = selection_family(sel_text, sport_n)
    ctx_risk = infer_context_risk(ev, sport_n)
    # Explicit rotation_risk=high still elevates
    tier = tier_for_context(ctx_risk, gcfg)
    # Lazy import avoids circular import with nt.evidence
    from nt.evidence import normalize_sources

    sources = normalize_sources(ev.get("sources"))
    sensitive = _is_sensitive(sport_n, family, gcfg)

    # P0: ControlSignals runtime overlay (temp_gate_raise → force confirmed + notes)
    overlay_force = False
    overlay_raise = 0.0
    try:
        from nt.control_signals import active_temp_gate_overlay

        ov = active_temp_gate_overlay(cfg, sport=sport_n, market=family)
        overlay_force = bool(ov.get("force_confirmed_lineup"))
        overlay_raise = float(ov.get("min_ev_raise") or 0)
        if overlay_force:
            gcfg = dict(gcfg)
            gcfg["high_context_require_confirmed"] = True
            gcfg["strict_confirmed_only"] = True
            gcfg["predicted_availability_ok"] = False
    except Exception:
        pass

    ctx = GateContext(
        sport=sport_n,
        selection=sel_text,
        family=family,
        odds=float(odds or 1.0),
        context_risk=ctx_risk,
        tier=tier,
        availability_status=availability_status(ev),
        availability_notes=availability_notes(ev),
        script_lean=script_lean(ev),
        selection_vs_script=selection_vs_script(ev),
        base_rate_conflict=base_rate_conflict(ev),
        sources=sources,
        ev=ev,
        cfg_gates=gcfg,
        avail_sensitive=sensitive,
    )
    result = GateResult(
        tier=tier,
        context_risk=ctx_risk,
        family=family,
        sport=sport_n,
        avail_sensitive=sensitive,
    )
    profile = get_profile(sport_n)
    profile(ctx, result)

    if overlay_force or overlay_raise > 0:
        result.soft.append(
            f"control_signal:temp_gate_raise "
            f"min_ev+{overlay_raise:.3f} force_confirmed={overlay_force}"
        )
        # Fail-closed: avail-sensitive + force confirmed + predicted/missing
        if overlay_force and sensitive:
            from nt.research_gates.universal import CONFIRMED

            st = (ctx.availability_status or "").strip().lower()
            if st not in CONFIRMED:
                result.hard.append(
                    "control_signal temp_gate_raise: confirmed availability required "
                    f"(got {st or 'missing'}) after process_error / poor retro"
                )

    return result.as_tuple()


__all__ = [
    "evaluate_research_gates",
    "football_selection_family",
    "selection_family",
    "normalize_sport",
]
