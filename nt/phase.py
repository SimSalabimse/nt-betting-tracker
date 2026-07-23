from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from nt.bets_io import fnum, is_performance_settled, load_bets
from nt.config import path_from_config


def _rolling_roi(rows: list[dict[str, str]], n: int) -> float | None:
    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    if not settled:
        return None
    window = settled[-n:]
    stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in window)
    pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in window)
    if stake <= 0:
        return None
    return pl / stake


def _peak_equity(rows: list[dict[str, str]], baseline: float) -> float:
    """
    Max equity HWM for phase demote — **same settlement-day curve** as
    capital_v2 / risk size_mode (Europe/Oslo via updated_at).

    Fail-closed single source of truth: never use match-date-only peak.
    """
    from nt.capital_v2 import peak_equity_settlement

    return peak_equity_settlement(rows, float(baseline))


def _phase_order(cfg: dict[str, Any]) -> list[str]:
    return list(cfg["phases"].keys())


# ── Continuous unit / open-risk (phase_continuous) ─────────────────────────


def phase_continuous_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Defaults for hybrid continuous sizing inside each phase band."""
    raw = dict((cfg or {}).get("phase_continuous") or {})
    return {
        "enabled": bool(raw.get("enabled", False)),
        "scale_factor": float(raw.get("scale_factor", 100.0)),
    }


def resolve_hard_phase_id(cfg: dict[str, Any], phase_id: str) -> str:
    """
    Hard gates (max_doubles, max_bets) use parent when half-steps set
    ``hard_phase_id`` or ``inherits_hard_gates_from``. Display phase_id stays
    the half-step (e.g. 1A+).
    """
    phases = (cfg or {}).get("phases") or {}
    p = phases.get(phase_id) or {}
    hard = p.get("hard_phase_id") or p.get("inherits_hard_gates_from") or phase_id
    hard_s = str(hard)
    if hard_s in phases:
        return hard_s
    return str(phase_id)


def progress_inside_phase(cfg: dict[str, Any], phase_id: str, equity: float) -> float:
    """
    progress = clamp((equity - enter) / max(1, next_enter - enter), 0, 1)

    0 at phase enter equity; ~1 approaching next phase enter.
    Terminal phase (no next) → 1.0.
    """
    phases = (cfg or {}).get("phases") or {}
    p = phases.get(phase_id) or {}
    enter = float(p.get("enter_equity") or 0.0)
    nxt = p.get("next")
    if not nxt or nxt not in phases:
        return 1.0
    next_enter = float(phases[nxt].get("enter_equity") or enter)
    span = max(1.0, next_enter - enter)
    return max(0.0, min(1.0, (float(equity) - enter) / span))


def continuous_unit_size(cfg: dict[str, Any], phase_id: str, equity: float) -> float:
    """
    unit = base_unit + (equity - enter) / scale_factor
    base_unit = phase stake_min; clamped to [stake_min, stake_max], whole krone.

    Visible ~1 NOK unit step every scale_factor equity (default 100).
    """
    pc = phase_continuous_cfg(cfg)
    phases = (cfg or {}).get("phases") or {}
    p = phases.get(phase_id) or {}
    stake_min = float(p.get("stake_min") or 10.0)
    stake_max = float(p.get("stake_max") or stake_min)
    if stake_max < stake_min:
        stake_max = stake_min
    enter = float(p.get("enter_equity") or 0.0)
    scale = max(1.0, float(pc.get("scale_factor") or 100.0))
    raw = stake_min + (float(equity) - enter) / scale
    unit = max(stake_min, min(stake_max, raw))
    # whole krone (floor toward zero for positive)
    return float(int(unit)) if unit > 0 else 0.0


def continuous_open_risk_params(
    cfg: dict[str, Any], phase_id: str, equity: float
) -> dict[str, float]:
    """
    Lerp daily open-risk knobs from current phase toward next by progress 0–1.

    When continuous disabled or no next phase, return current phase values.
    """
    phases = (cfg or {}).get("phases") or {}
    p = phases.get(phase_id) or {}
    cur_floor = float(p.get("daily_risk_floor") or 0.0)
    cur_ceil = float(p.get("daily_risk_ceil") or cur_floor)
    cur_pct = float(p.get("daily_risk_pct") or 0.0)
    pc = phase_continuous_cfg(cfg)
    if not pc.get("enabled"):
        return {
            "daily_risk_floor": cur_floor,
            "daily_risk_ceil": cur_ceil,
            "daily_risk_pct": cur_pct,
        }
    prog = progress_inside_phase(cfg, phase_id, equity)
    nxt = p.get("next")
    if not nxt or nxt not in phases:
        return {
            "daily_risk_floor": cur_floor,
            "daily_risk_ceil": cur_ceil,
            "daily_risk_pct": cur_pct,
        }
    n = phases[nxt]
    nxt_floor = float(n.get("daily_risk_floor") or cur_floor)
    nxt_ceil = float(n.get("daily_risk_ceil") or cur_ceil)
    nxt_pct = float(n.get("daily_risk_pct") or cur_pct)
    return {
        "daily_risk_floor": round(cur_floor + prog * (nxt_floor - cur_floor), 4),
        "daily_risk_ceil": round(cur_ceil + prog * (nxt_ceil - cur_ceil), 4),
        "daily_risk_pct": round(cur_pct + prog * (nxt_pct - cur_pct), 6),
    }


def hard_gate_fields(cfg: dict[str, Any], phase_id: str) -> dict[str, Any]:
    """max_doubles / max_bets from hard parent phase when configured."""
    phases = (cfg or {}).get("phases") or {}
    hard_id = resolve_hard_phase_id(cfg, phase_id)
    hard_p = phases.get(hard_id) or phases.get(phase_id) or {}
    display_p = phases.get(phase_id) or hard_p
    return {
        "phase_hard_id": hard_id,
        "max_bets_per_round": int(
            hard_p.get("max_bets_per_round", display_p.get("max_bets_per_round", 3))
        ),
        "max_doubles_per_round": int(
            hard_p.get(
                "max_doubles_per_round", display_p.get("max_doubles_per_round", 0)
            )
        ),
    }


def evaluate_phase(
    cfg: dict[str, Any],
    equity: float,
    settled_count: int,
    rows: list[dict[str, str]] | None = None,
    current_phase: str | None = None,
) -> dict[str, Any]:
    """
    Phase selection (v4 safe hybrid + half-steps + continuous sizing):

    1. equity_phase  = highest phase whose enter_equity is met
    2. count_phase   = highest phase whose enter_settled is met
    3. count may advance at most one step above equity_phase **only if**
       rolling ROI >= min_rolling_roi (default 0% — no advance while red)
    4. demote one step if rolling ROI deeply negative
    5. demote one step if equity is in a large drawdown vs peak equity
    6. at most one step advance vs previous written phase
    7. hard gates (max_doubles, max_bets) from hard_phase_id parent when set
    8. continuous unit / open-risk progress inside band when phase_continuous
    """
    phases = cfg["phases"]
    order = _phase_order(cfg)
    stability = cfg.get("phase_stability", {})
    min_roll = int(stability.get("min_rolling_settled", 25))
    min_roi = float(stability.get("min_rolling_roi", 0.0))
    demote_roi = float(stability.get("demote_if_rolling_roi_below", -0.10))
    demote_n = int(stability.get("demote_min_settled", 25))
    dd_pct = float(stability.get("demote_drawdown_pct_of_peak", 0.12))

    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))

    baseline = float(cfg.get("bankroll", {}).get("baseline_nok", 500.0))
    peak = _peak_equity(rows, baseline)
    roll = _rolling_roi(rows, min_roll)
    stable_enough = roll is None or roll >= min_roi

    equity_phase = order[0]
    for pid in order:
        if equity >= float(phases[pid].get("enter_equity", 0)):
            equity_phase = pid

    count_phase = order[0]
    for pid in order:
        if settled_count >= int(phases[pid].get("enter_settled", 0)):
            count_phase = pid

    eq_i = order.index(equity_phase)
    count_i = order.index(count_phase)
    reasons = [
        f"equity_phase={equity_phase} (equity {equity:.2f})",
        f"count_phase={count_phase} (settled {settled_count})",
        f"peak_equity={peak:.2f}",
    ]

    if stable_enough:
        allowed_i = min(count_i, eq_i + 1)
        reasons.append(f"count unlock capped at equity+1 → {order[allowed_i]}")
    else:
        allowed_i = eq_i
        roi_s = f"{roll:.1%}" if roll is not None else "n/a"
        reasons.append(f"count unlock blocked: rolling ROI {roi_s} < stability {min_roi:.1%}")

    chosen_i = max(eq_i, allowed_i)
    chosen = order[chosen_i]
    demoted = False

    # Demote if deep red on rolling window
    if roll is not None and roll < demote_roi and settled_count >= demote_n:
        if chosen_i > 0:
            chosen_i -= 1
            chosen = order[chosen_i]
            demoted = True
            reasons.append(f"demote for rolling ROI {roll:.1%} < {demote_roi:.1%}")

    # Demote if large drawdown from peak (does not stack a second drop same evaluation)
    if not demoted and peak > 0 and settled_count >= demote_n:
        dd = (peak - equity) / peak
        if dd >= dd_pct and chosen_i > 0:
            chosen_i -= 1
            chosen = order[chosen_i]
            demoted = True
            reasons.append(f"demote for drawdown {dd:.1%} of peak (limit {dd_pct:.0%})")

    # One-step advance vs previously stored phase
    if current_phase and current_phase in phases:
        cur_i = order.index(current_phase)
        if chosen_i > cur_i + 1:
            chosen_i = cur_i + 1
            chosen = order[chosen_i]
            reasons.append(f"one-step advance cap from {current_phase} → {chosen}")

    p = phases[chosen]
    gates = hard_gate_fields(cfg, chosen)
    hard_id = gates["phase_hard_id"]
    prog = progress_inside_phase(cfg, chosen, equity)
    pc = phase_continuous_cfg(cfg)
    open_params = continuous_open_risk_params(cfg, chosen, equity)
    cont_unit = continuous_unit_size(cfg, chosen, equity) if pc.get("enabled") else None

    # ── v5 multi-factor PhaseState (alongside ladder) ─────────────────────
    from nt.phase_factors import compute_phase_factors, phase_health_cfg

    hcfg = phase_health_cfg(cfg)
    baseline = float(cfg.get("bankroll", {}).get("baseline_nok", 500.0))
    factors = compute_phase_factors(
        cfg, equity=equity, peak=peak, rows=rows, baseline=baseline
    )

    size_mode_floor: str | None = None
    research_only = False
    process_health_until: str | None = None
    process_health_action: str | None = None
    process_health_reason: str | None = None

    prev = load_phase_state(cfg)

    now = datetime.now(timezone.utc)
    if prev:
        sticky_until = _parse_phase_ts(str(prev.get("process_health_until") or ""))
        if sticky_until and sticky_until > now:
            process_health_until = sticky_until.strftime("%Y-%m-%dT%H:%M:%SZ")
            process_health_action = str(
                prev.get("process_health_action") or hcfg["process_error_action"]
            ).upper()
            process_health_reason = str(
                prev.get("process_health_reason") or "sticky process health hold"
            )
            if process_health_action == "RESEARCH_ONLY":
                research_only = True
                size_mode_floor = "REDUCED"
            else:
                size_mode_floor = "REDUCED"

    # Fresh breach → (re)start 7d hold
    if hcfg["enabled"] and factors.get("force_process_health"):
        hold_days = int(hcfg["process_error_hold_days"])
        until = now + timedelta(days=hold_days)
        process_health_until = until.strftime("%Y-%m-%dT%H:%M:%SZ")
        process_health_action = str(hcfg["process_error_action"]).upper()
        process_health_reason = (
            f"process_error_rate_14d={factors.get('process_error_rate_14d')} "
            f"n={factors.get('raw', {}).get('n_reviews_14d')}"
        )
        if process_health_action == "RESEARCH_ONLY":
            research_only = True
            size_mode_floor = "REDUCED"
        else:
            size_mode_floor = "REDUCED"
        reasons.append(
            f"phase_health: process_error_rate force {process_health_action} "
            f"until {process_health_until}"
        )
    elif process_health_until:
        reasons.append(
            f"phase_health: sticky {process_health_action} until {process_health_until}"
        )

    high_odds_stress = bool(factors.get("high_odds_stress_block"))
    if high_odds_stress:
        reasons.append("phase_health: high_odds_stress_block (concentration/calibration)")

    if pc.get("enabled"):
        reasons.append(
            f"phase_continuous: progress={prog:.3f} unit={cont_unit} "
            f"hard_id={hard_id} open_ceil={open_params['daily_risk_ceil']:.1f}"
        )

    out: dict[str, Any] = {
        "phase_id": chosen,
        "phase_hard_id": hard_id,
        "label": p.get("label", chosen),
        "stake_min": float(p["stake_min"]),
        "stake_max": float(p["stake_max"]),
        "max_bets_per_round": int(gates["max_bets_per_round"]),
        "max_doubles_per_round": int(gates["max_doubles_per_round"]),
        "daily_risk_pct": float(open_params["daily_risk_pct"]),
        "daily_risk_floor": float(open_params["daily_risk_floor"]),
        "daily_risk_ceil": float(open_params["daily_risk_ceil"]),
        "next": p.get("next"),
        "equity_phase": equity_phase,
        "count_phase": count_phase,
        "rolling_roi": roll,
        "peak_equity_nok": peak,
        "drawdown_from_peak_pct": round((peak - equity) / peak, 4) if peak > 0 else 0.0,
        "reasons": reasons,
        "equity_nok": equity,
        "settled_count": settled_count,
        "progress_inside_phase": round(prog, 6),
        "phase_continuous_enabled": bool(pc.get("enabled")),
        # v5 multi-factor
        "phase_model": "v5_multifactor",
        "phase_state": factors,
        "size_mode_floor": size_mode_floor,
        "research_only": research_only,
        "high_odds_stress_block": high_odds_stress,
        "process_health_until": process_health_until,
        "process_health_action": process_health_action,
        "process_health_reason": process_health_reason,
    }
    if cont_unit is not None:
        out["unit_size_nok"] = float(cont_unit)
        out["unit_size_source"] = "phase_continuous"
    return out


def _parse_phase_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        raw = s.replace("Z", "+00:00") if s.endswith("Z") else s
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def write_phase_state(cfg: dict[str, Any], phase: dict[str, Any]) -> None:
    state_dir = path_from_config(cfg, "state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "phase.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(phase, f, indent=2)
        f.write("\n")


def load_phase_state(cfg: dict[str, Any]) -> dict[str, Any] | None:
    path = path_from_config(cfg, "state_dir") / "phase.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
