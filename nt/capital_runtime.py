"""
Capital v2 runtime (Phase 2.4).

Secure-transfer persistence, day/week liquid snapshots (Europe/Oslo),
stake_decisions.jsonl audit. All gated by capital_v2.enabled (default false).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.capital_segments import is_frozen, load_segments, save_segments
from nt.capital_v2 import (
    RULE_BUNDLE_VERSION,
    capital_v2_cfg,
    compute_secure_transfer,
    oslo_iso_week_id,
    oslo_today,
    riskable_liquid,
    unit_size,
)
from nt.config import path_from_config
from nt.risk import day_pending_risk, day_realized_pl, week_realized_pl


def capital_v2_enabled(cfg: dict[str, Any]) -> bool:
    return bool(capital_v2_cfg(cfg).get("enabled"))


def unfreeze_capital(
    cfg: dict[str, Any],
    *,
    reason: str = "manual_unfreeze",
    actor: str = "operator",
) -> dict[str, Any]:
    """
    Clear capital_segments freeze flag + audit entry; refresh risk state.
    Safe when capital_v2 disabled (still clears file freeze if present).
    """
    from nt.capital_segments import load_segments, save_segments, set_freeze

    baseline = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)
    segs = load_segments(cfg, baseline_nok=baseline)
    was = bool((segs.get("freeze") or {}).get("active"))
    segs = set_freeze(segs, active=False, reason=None)
    audit = list(segs.get("freeze_audit") or [])
    audit.append(
        {
            "ts": utc_now(),
            "action": "unfreeze",
            "reason": reason,
            "actor": actor,
            "was_active": was,
            "rule_bundle_version": RULE_BUNDLE_VERSION,
        }
    )
    segs["freeze_audit"] = audit
    path = save_segments(cfg, segs)
    return {
        "ok": True,
        "was_frozen": was,
        "segments_path": str(path),
        "freeze_active": False,
        "audit_entries": len(audit),
    }


def stake_decisions_path(cfg: dict[str, Any]) -> Path:
    """Append-only audit path for StakeDecision records (under state_dir by default)."""
    paths = cfg.get("paths") or {}
    if paths.get("stake_decisions"):
        return path_from_config(cfg, "stake_decisions")
    state = path_from_config(cfg, "state_dir")
    return state / "stake_decisions.jsonl"


def append_stake_decision(cfg: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """
    Append one stake decision line. Fail-closed: never raises to caller path
    (errors re-raised only if explicitly needed — recommend wraps).
    """
    path = stake_decisions_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(record)
    rec.setdefault("ts", utc_now())
    rec.setdefault("schema_version", rec.get("schema_version") or 1)
    rec.setdefault("rule_bundle_version", RULE_BUNDLE_VERSION)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    return rec


def apply_secure_transfer_to_segments(
    segments: dict[str, Any],
    *,
    ledger_equity: float,
    v2: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Pure-ish: return (updated_segments, transfer_info).
    Skips when freeze active or secure_bucket disabled.
    Idempotent after ref reset (re-run below trigger → no-op).
    """
    v2 = v2 or capital_v2_cfg({})
    out = dict(segments)
    sb = v2.get("secure_bucket") or {}
    info: dict[str, Any] = {
        "triggered": False,
        "transferred": 0.0,
        "reason": "skipped",
    }
    if not bool(sb.get("enabled", True)):
        info["reason"] = "secure_bucket_disabled"
        return out, info
    if is_frozen(out):
        info["reason"] = "frozen"
        return out, info

    ref = float(out.get("unit_hwm_reset_equity_nok") or 0.0)
    secure = max(0.0, float(out.get("secure_nok") or 0.0))
    working_now = max(0.0, float(ledger_equity) - secure)
    u = unit_size(working_now, v2)
    result = compute_secure_transfer(
        ledger_equity=ledger_equity,
        secure_nok=secure,
        ref_hwm=ref if ref > 0 else float(ledger_equity),
        trigger_multiple=float(sb.get("trigger_multiple_of_ref") or 1.30),
        transfer_fraction=float(sb.get("transfer_fraction_of_profit_above_ref") or 0.40),
        unit_size_nok=u,
        min_working_frac=float(sb.get("min_working_frac_of_equity") or 0.55),
        min_working_units=float(sb.get("min_working_units") or 8.0),
    )
    info = {
        "triggered": result.triggered,
        "transferred": result.transferred,
        "secure_after": result.secure_after,
        "ref_hwm_after": result.ref_hwm_after,
        "working_equity_after": result.working_equity_after,
        "reason": result.reason,
        "min_working_required": result.min_working_required,
        "transfer_capped_by_buffer": result.transfer_capped_by_buffer,
    }
    if not result.triggered:
        return out, info

    out["secure_nok"] = result.secure_after
    out["unit_hwm_reset_equity_nok"] = result.ref_hwm_after
    transfers = list(out.get("secure_transfers") or [])
    transfers.append(
        {
            "ts": utc_now(),
            "ledger_equity_nok": round(float(ledger_equity), 2),
            "transferred_nok": result.transferred,
            "secure_after_nok": result.secure_after,
            "ref_hwm_before_nok": ref,
            "ref_hwm_after_nok": result.ref_hwm_after,
            "working_equity_after_nok": result.working_equity_after,
            "reason": result.reason,
            "rule_bundle_version": RULE_BUNDLE_VERSION,
        }
    )
    out["secure_transfers"] = transfers
    return out, info


def ensure_day_week_snapshots(
    segments: dict[str, Any],
    *,
    liquid_now: float,
    unit_now: float,
    today: str | None = None,
    week_id: str | None = None,
    realized_day: float = 0.0,
    realized_week: float = 0.0,
) -> dict[str, Any]:
    """
    Freeze start-of-day / start-of-week riskable liquid when the period rolls.
    Same day/week: keep liquid_start; refresh realized_pl diagnostics only.
    """
    out = dict(segments)
    day = today or oslo_today()
    wid = week_id or oslo_iso_week_id(day)
    liquid_now = max(0.0, round(float(liquid_now), 2))
    unit_now = max(0.0, float(unit_now))

    day_snap = dict(out.get("day_snapshot") or {})
    if day_snap.get("oslo_date") != day or day_snap.get("liquid_start_nok") is None:
        day_snap = {
            "oslo_date": day,
            "liquid_start_nok": liquid_now,
            "unit_size_nok": unit_now,
            "realized_pl_nok": float(realized_day),
        }
    else:
        day_snap["realized_pl_nok"] = float(realized_day)
        # unit_size_nok stays as start-of-day unit for loss-limit consistency
        day_snap.setdefault("unit_size_nok", unit_now)
    out["day_snapshot"] = day_snap

    week_snap = dict(out.get("week_snapshot") or {})
    if week_snap.get("week_id") != wid or week_snap.get("liquid_start_nok") is None:
        week_snap = {
            "week_id": wid,
            "liquid_start_nok": liquid_now,
            "unit_size_nok": unit_now,
            "realized_pl_nok": float(realized_week),
        }
    else:
        week_snap["realized_pl_nok"] = float(realized_week)
        week_snap.setdefault("unit_size_nok", unit_now)
    out["week_snapshot"] = week_snap
    return out


def sync_capital_v2_state(
    cfg: dict[str, Any],
    ledger_equity: float,
    rows: list[dict[str, str]],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """
    When capital_v2.enabled: load segments → secure transfer → snapshots → save.
    When disabled: no-op empty load (does not write).

    Returns segments dict used for subsequent risk evaluation.
    """
    v2 = capital_v2_cfg(cfg)
    baseline = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)
    if not bool(v2.get("enabled")):
        return load_segments(cfg, baseline_nok=baseline)

    segs = load_segments(cfg, baseline_nok=baseline)
    segs, transfer_info = apply_secure_transfer_to_segments(
        segs, ledger_equity=ledger_equity, v2=v2
    )

    today = oslo_today()
    week_id = oslo_iso_week_id(today)
    open_risk = day_pending_risk(rows, today)
    secure = max(0.0, float(segs.get("secure_nok") or 0.0))
    liquid = riskable_liquid(ledger_equity, secure, open_risk)
    unit = unit_size(liquid, v2)
    realized_day = day_realized_pl(rows, today)
    realized_week = week_realized_pl(rows, week_id)

    segs = ensure_day_week_snapshots(
        segs,
        liquid_now=liquid,
        unit_now=unit,
        today=today,
        week_id=week_id,
        realized_day=realized_day,
        realized_week=realized_week,
    )
    segs["rule_bundle_version"] = v2.get("rule_bundle_version") or RULE_BUNDLE_VERSION
    segs["_last_sync"] = {
        "ts": utc_now(),
        "ledger_equity_nok": round(float(ledger_equity), 2),
        "secure_transfer": transfer_info,
        "riskable_liquid_nok": liquid,
        "oslo_date": today,
        "week_id": week_id,
    }

    if persist:
        # Strip internal diagnostic before write? Keep _last_sync for ops visibility.
        try:
            save_segments(cfg, segs)
        except OSError:
            # Fail-closed: still return in-memory segs for this process; no crash
            segs["_last_sync"]["persist_error"] = True
    return segs


def persist_stake_decisions_for_picks(
    cfg: dict[str, Any],
    picks: list[Any],
    *,
    bet_ids: list[str] | None = None,
    phase_id: str | None = None,
    risk: dict[str, Any] | None = None,
) -> int:
    """
    Append stake decisions for recommendations that carry stake_decision.
    Returns number of lines written. No-op when capital_v2 disabled.
    """
    if not capital_v2_enabled(cfg):
        return 0
    n = 0
    ids = bet_ids or []
    for i, rec in enumerate(picks):
        sd = getattr(rec, "stake_decision", None)
        if not sd:
            # Minimal audit even if decision missing under flag
            sd = {
                "final_stake_nok": getattr(rec, "stake_nok", None),
                "size_mode": (risk or {}).get("size_mode"),
                "reject_reason": "missing_stake_decision_payload",
            }
        payload = dict(sd)
        payload["ts"] = utc_now()
        if i < len(ids) and ids[i]:
            payload["bet_id"] = ids[i]
        payload.setdefault("match", getattr(rec, "match", ""))
        payload.setdefault("selection", getattr(rec, "selection", ""))
        inputs = dict(payload.get("inputs") or {})
        inputs.setdefault("phase_id", phase_id or (risk or {}).get("phase_id"))
        inputs.setdefault("odds", getattr(rec, "decimal_odds", None))
        inputs.setdefault("ev", getattr(rec, "ev", None))
        inputs.setdefault("p_model", getattr(rec, "p_model", None))
        if risk:
            inputs.setdefault("remaining_room", risk.get("remaining_risk_nok"))
            inputs.setdefault("size_mode", risk.get("size_mode"))
            inputs.setdefault("unit_size", risk.get("unit_size_nok"))
            inputs.setdefault("equity", risk.get("equity_nok"))
            inputs.setdefault("secure", risk.get("secure_nok"))
            inputs.setdefault("dd_from_peak", risk.get("drawdown_from_peak"))
        # Always stamp phase when provided (even if inputs already existed)
        if phase_id:
            inputs["phase_id"] = phase_id
        payload["inputs"] = inputs
        append_stake_decision(cfg, payload)
        n += 1
    return n
