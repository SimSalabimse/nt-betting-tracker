"""
Early-bankroll regimes: Exploration → Survival → Normal.

Orthogonal to phase ladder and capital_v2 size_mode.
Effects (tighten only unless Exploration weekly quota):
  - min-EV after 3pp haircut (portfolio; High-Volume v2)
  - open-risk daily cap on Pending+ConfirmedPlaced only (risk remaining)
  - soft prefer mid-odds under early regimes
  - Exploration: ≤2 unit regime-explore bets/week at thin EV on mid/alt

Settlement frees open risk immediately (engine already counts only open
statuses). This module does not invent p_model or change haircut.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from nt.bets_io import fnum, is_performance_settled

OSLO = ZoneInfo("Europe/Oslo")
EXPLORE_REGIME_TAG = "EXPLORE_REGIME"


def bankroll_regime_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("bankroll_regime") or {})
    # Prefer exploration; legacy calibration key merges as fallback defaults
    exp_raw = dict(raw.get("exploration") or {})
    cal_legacy = dict(raw.get("calibration") or {})
    sur = dict(raw.get("survival") or {})
    defaults = {
        "enabled": True,
        "exploration": {
            "exit_settled": 40,
            "exit_equity": 650.0,
            "min_ev": 0.02,  # High-Volume v2 (was 0.04)
            "open_risk_cap_nok": 100.0,  # was 50 — room for ~3 unit-scale bets
            "prefer_mid_odds": True,
            "mid_odds_lo": 1.85,
            "mid_odds_hi": 2.60,
            "weekly_explore_max": 2,
            "explore_min_ev": 0.01,
            "explore_max_ev": 0.02,
            "explore_odds_lo": 1.85,
            "explore_odds_hi": 2.60,
            "explore_require_alt_or_mid": True,
        },
        "survival": {
            "exit_settled": 100,
            "exit_equity": 800.0,
            "min_ev": 0.03,  # High-Volume v2 (was 0.075)
            "open_risk_cap_nok": 100.0,
            "prefer_mid_odds": True,
            "mid_odds_lo": 1.85,
            "mid_odds_hi": 2.60,
        },
    }
    # Map legacy calibration fields if exploration incomplete
    legacy_map = {
        "exit_settled": "exit_settled",
        "min_ev": "min_ev",
        "open_risk_cap_nok": "open_risk_cap_nok",
        "prefer_mid_odds": "prefer_mid_odds",
        "mid_odds_lo": "mid_odds_lo",
        "mid_odds_hi": "mid_odds_hi",
    }
    merged_exp = {**defaults["exploration"]}
    for k, src in legacy_map.items():
        if src in cal_legacy and k not in exp_raw:
            merged_exp[k] = cal_legacy[src]
    merged_exp.update(exp_raw)

    return {
        "enabled": bool(raw.get("enabled", defaults["enabled"])),
        "exploration": merged_exp,
        "survival": {**defaults["survival"], **sur},
        # back-compat alias for any reader still expecting calibration key
        "calibration": merged_exp,
    }


def evaluate_bankroll_regime(
    cfg: dict[str, Any],
    *,
    equity: float,
    settled_count: int,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Pure regime selection from equity + settled_count.

    Returns dict with id in {exploration, survival, normal}.
    (Legacy id 'calibration' is never emitted.)
    """
    rcfg = bankroll_regime_cfg(cfg)
    base: dict[str, Any] = {
        "enabled": bool(rcfg.get("enabled")),
        "id": "normal",
        "label": "Normal",
        "min_ev": None,
        "open_risk_cap_nok": None,
        "prefer_mid_odds": False,
        "mid_odds_lo": 1.85,
        "mid_odds_hi": 2.50,
        "settled_count": int(settled_count),
        "equity_nok": float(equity),
        "reasons": [],
        "schema_version": 2,
        "weekly_explore_max": 0,
        "explore_min_ev": None,
        "explore_max_ev": None,
    }
    if not rcfg.get("enabled"):
        base["reasons"] = ["bankroll_regime disabled"]
        return base

    exp = rcfg["exploration"]
    sur = rcfg["survival"]
    n = int(settled_count)
    eq = float(equity)
    reasons: list[str] = []

    exp_exit_n = int(exp.get("exit_settled") or 40)
    exp_exit_eq = float(exp.get("exit_equity") or 650.0)
    sur_exit_n = int(sur.get("exit_settled") or 100)
    sur_exit_eq = float(sur.get("exit_equity") or 800.0)

    # Survival → Normal
    if n >= sur_exit_n or eq + 1e-9 >= sur_exit_eq:
        if n >= sur_exit_n:
            reasons.append(f"normal: settled {n} >= survival exit {sur_exit_n}")
        else:
            reasons.append(
                f"normal: equity {eq:.0f} >= survival exit equity {sur_exit_eq:.0f}"
            )
        return {
            **base,
            "id": "normal",
            "label": "Normal",
            "reasons": reasons,
            "progress": {
                "settled": n,
                "exploration_exit": exp_exit_n,
                "survival_exit": sur_exit_n,
                "exploration_exit_equity": exp_exit_eq,
                "survival_exit_equity": sur_exit_eq,
            },
        }

    # Exploration → Survival
    if n >= exp_exit_n or eq + 1e-9 >= exp_exit_eq:
        if n >= exp_exit_n:
            reasons.append(
                f"survival: settled {n} >= exploration exit {exp_exit_n}"
            )
        else:
            reasons.append(
                f"survival: equity {eq:.0f} >= exploration exit equity {exp_exit_eq:.0f}"
            )
        return {
            **base,
            "id": "survival",
            "label": "Survival",
            "min_ev": float(sur.get("min_ev") or 0.075),
            "open_risk_cap_nok": float(sur.get("open_risk_cap_nok") or 50.0),
            "prefer_mid_odds": bool(sur.get("prefer_mid_odds", True)),
            "mid_odds_lo": float(sur.get("mid_odds_lo") or 1.85),
            "mid_odds_hi": float(sur.get("mid_odds_hi") or 2.50),
            "reasons": reasons,
            "progress": {
                "settled": n,
                "exploration_exit": exp_exit_n,
                "survival_exit": sur_exit_n,
                "exploration_exit_equity": exp_exit_eq,
                "survival_exit_equity": sur_exit_eq,
            },
        }

    # Exploration
    reasons.append(
        f"exploration: settled {n} < {exp_exit_n} and equity {eq:.0f} < {exp_exit_eq:.0f}"
    )
    return {
        **base,
        "id": "exploration",
        "label": "Exploration",
        "min_ev": float(exp.get("min_ev") or 0.04),
        "open_risk_cap_nok": float(exp.get("open_risk_cap_nok") or 50.0),
        "prefer_mid_odds": bool(exp.get("prefer_mid_odds", True)),
        "mid_odds_lo": float(exp.get("mid_odds_lo") or 1.85),
        "mid_odds_hi": float(exp.get("mid_odds_hi") or 2.50),
        "weekly_explore_max": int(exp.get("weekly_explore_max") or 2),
        "explore_min_ev": float(exp.get("explore_min_ev") or 0.02),
        "explore_max_ev": float(exp.get("explore_max_ev") or 0.04),
        "explore_odds_lo": float(exp.get("explore_odds_lo") or 1.85),
        "explore_odds_hi": float(exp.get("explore_odds_hi") or 2.50),
        "explore_require_alt_or_mid": bool(
            exp.get("explore_require_alt_or_mid", True)
        ),
        "reasons": reasons,
        "progress": {
            "settled": n,
            "exploration_exit": exp_exit_n,
            "survival_exit": sur_exit_n,
            "exploration_exit_equity": exp_exit_eq,
            "survival_exit_equity": sur_exit_eq,
        },
    }


def apply_regime_open_cap(
    remaining: float,
    open_pending: float,
    regime: dict[str, Any],
) -> tuple[float, list[str]]:
    """
    Bind remaining to max(0, regime_open_cap − open_pending).
    Open pending is Pending+ConfirmedPlaced only (caller provides).
    """
    reasons: list[str] = []
    cap = regime.get("open_risk_cap_nok")
    if cap is None or not regime.get("enabled", True):
        return max(0.0, remaining), reasons
    if regime.get("id") == "normal":
        return max(0.0, remaining), reasons

    cap_f = float(cap)
    open_f = max(0.0, float(open_pending))
    room = max(0.0, round(cap_f - open_f, 2))
    new_rem = min(float(remaining), room)
    if room + 1e-9 < float(remaining):
        reasons.append(
            f"REGIME {regime.get('id')}: open-risk cap {cap_f:.0f} − pending {open_f:.0f} "
            f"= room {room:.0f} binds remaining"
        )
    return max(0.0, round(new_rem, 2)), reasons


def regime_min_ev_floor(regime: dict[str, Any]) -> float | None:
    """Return min_ev floor for portfolio, or None if Normal/disabled."""
    if not regime.get("enabled", True):
        return None
    if regime.get("id") == "normal":
        return None
    me = regime.get("min_ev")
    if me is None:
        return None
    return float(me)


def is_mid_odds_preferred(odds: float, regime: dict[str, Any]) -> bool:
    if not regime.get("prefer_mid_odds"):
        return True
    lo = float(regime.get("mid_odds_lo") or 1.85)
    hi = float(regime.get("mid_odds_hi") or 2.50)
    return lo - 1e-9 <= float(odds) <= hi + 1e-9


def oslo_week_id(when: datetime | None = None) -> str:
    """ISO week id in Europe/Oslo, e.g. 2026-W30."""
    dt = when or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(OSLO)
    iso = local.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def is_regime_explore_bet(row: dict[str, Any]) -> bool:
    """True if ledger row was placed under Exploration weekly EV quota."""
    notes = str(row.get("notes") or "")
    if EXPLORE_REGIME_TAG in notes:
        return True
    # structured optional
    if str(row.get("explore_regime") or "").lower() in ("1", "true", "yes"):
        return True
    return False


def _row_week_id(row: dict[str, Any]) -> str | None:
    for key in ("created_at", "updated_at", "date"):
        raw = str(row.get(key) or "").strip()
        if not raw:
            continue
        try:
            if "T" in raw or raw.endswith("Z"):
                s = raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return oslo_week_id(dt)
            # date-only YYYY-MM-DD → Oslo midnight
            dt = datetime.fromisoformat(raw[:10]).replace(tzinfo=OSLO)
            return oslo_week_id(dt)
        except ValueError:
            continue
    return None


def count_weekly_regime_explore(
    rows: list[dict[str, Any]] | None,
    *,
    week_id: str | None = None,
) -> int:
    """
    Count Pending / ConfirmedPlaced / performance-settled EXPLORE_REGIME bets
    in the given Oslo ISO week.
    """
    if not rows:
        return 0
    wid = week_id or oslo_week_id()
    n = 0
    for r in rows:
        if not is_regime_explore_bet(r):
            continue
        result = str(r.get("result") or "")
        # count open + settled performance; skip Abandoned/void-only if not performance
        if result in ("Abandoned", "Void", "Cancelled"):
            continue
        rw = _row_week_id(r)
        if rw == wid:
            n += 1
    return n


def is_alt_or_mid_explore_line(
    selection: str,
    odds: float,
    sport: str = "",
    family: str = "",
    *,
    odds_lo: float = 1.85,
    odds_hi: float = 2.50,
) -> bool:
    """
    Mid-odds band OR non short-main alt (HC / totals / period / dog markets).
    Reuses light_research classifiers when available.
    """
    o = float(odds)
    if odds_lo - 1e-9 <= o <= odds_hi + 1e-9:
        return True
    try:
        from nt.light_research import is_preferred_line, is_short_main_line
        from nt.research_gates.infer import selection_family

        fam = family or selection_family(selection, (sport or "").lower())
        # preferred (survivable) alts count even slightly outside band if alt
        if is_preferred_line(selection, o, fam):
            return True
        if not is_short_main_line(selection, o, fam) and o >= odds_lo - 0.05:
            return True
    except Exception:
        sel = (selection or "").lower()
        if any(x in sel for x in ("handikap", "handicap", "totalt", "over", "under", "omgang")):
            return o >= 1.70
    return False


def regime_explore_slot_available(
    regime: dict[str, Any],
    *,
    weekly_used: int,
) -> bool:
    if regime.get("id") != "exploration":
        return False
    max_n = int(regime.get("weekly_explore_max") or 0)
    return weekly_used < max_n


def can_use_regime_explore_quota(
    *,
    regime: dict[str, Any],
    ev: float,
    odds: float,
    selection: str,
    sport: str = "",
    family: str = "",
    weekly_used: int = 0,
    has_deep_pack: bool = True,
) -> bool:
    """
    True if this candidate may use Exploration weekly EV quota (EV in [explore_min, floor)).
    Does not invent packs — caller must pass has_deep_pack from evidence attach.
    """
    if not has_deep_pack:
        return False
    if not regime_explore_slot_available(regime, weekly_used=weekly_used):
        return False
    floor = regime_min_ev_floor(regime)
    if floor is None:
        return False
    lo = float(regime.get("explore_min_ev") or 0.02)
    hi = float(regime.get("explore_max_ev") or floor)
    # EV must be in [lo, floor) — full floor bets do not consume quota
    if float(ev) + 1e-12 < lo:
        return False
    if float(ev) + 1e-12 >= float(floor):
        return False
    # also respect configured explore_max_ev if set below floor
    if float(ev) + 1e-12 >= hi and hi <= float(floor) + 1e-12:
        # if hi == floor, band is [lo, floor)
        pass
    odds_lo = float(regime.get("explore_odds_lo") or 1.85)
    odds_hi = float(regime.get("explore_odds_hi") or 2.50)
    if bool(regime.get("explore_require_alt_or_mid", True)):
        if not is_alt_or_mid_explore_line(
            selection, odds, sport, family, odds_lo=odds_lo, odds_hi=odds_hi
        ):
            return False
    return True
