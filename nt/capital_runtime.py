"""
Capital v2 runtime (Phase 2.4).

Secure-transfer persistence, day/week liquid snapshots (Europe/Oslo),
stake_decisions.jsonl audit. All gated by capital_v2.enabled (default false).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import is_performance_settled, utc_now
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


def _secure_bucket_transfer_kwargs(sb: dict[str, Any]) -> dict[str, Any]:
    """
    Build compute_secure_transfer kwargs from secure_bucket config.

    Variant A (default): soft/hard tiers when soft_* and hard_* are present.
    Variant B / legacy: single trigger_multiple + transfer_fraction when
    variant is B/C or soft/hard not fully set.
    """
    variant = str(sb.get("variant") or "A").upper()
    soft_m = sb.get("soft_trigger_multiple_of_ref")
    soft_f = sb.get("soft_transfer_fraction")
    hard_m = sb.get("hard_trigger_multiple_of_ref")
    hard_f = sb.get("hard_transfer_fraction")
    use_a = (
        variant == "A"
        and soft_m is not None
        and soft_f is not None
        and hard_m is not None
        and hard_f is not None
    )
    kw: dict[str, Any] = {
        "min_working_frac": float(sb.get("min_working_frac_of_equity") or 0.55),
        "min_working_units": float(sb.get("min_working_units") or 8.0),
    }
    if use_a:
        kw["soft_trigger_multiple"] = float(soft_m)
        kw["soft_transfer_fraction"] = float(soft_f)
        kw["hard_trigger_multiple"] = float(hard_m)
        kw["hard_transfer_fraction"] = float(hard_f)
    else:
        # Variant B (1.30/0.27), C, or explicit single-tier
        kw["trigger_multiple"] = float(sb.get("trigger_multiple_of_ref") or 1.30)
        kw["transfer_fraction"] = float(
            sb.get("transfer_fraction_of_profit_above_ref") or 0.27
        )
    return kw


def apply_secure_transfer_to_segments(
    segments: dict[str, Any],
    *,
    ledger_equity: float,
    v2: dict[str, Any] | None = None,
    phase_daily_risk_ceil: float | None = None,
    open_risk: float = 0.0,
    settled_count: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Pure-ish: return (updated_segments, transfer_info).
    Skips when freeze active or secure_bucket disabled.
    Idempotent after ref reset (re-run below trigger → no-op).

    Variant A soft/hard skim by default. Never skim below phase daily_risk_ceil
    liquid floor when phase_daily_risk_ceil is provided.
    """
    v2 = v2 or capital_v2_cfg({})
    out = dict(segments)
    sb = v2.get("secure_bucket") or {}
    info: dict[str, Any] = {
        "triggered": False,
        "transferred": 0.0,
        "reason": "skipped",
        "tier": None,
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
    xfer_kw = _secure_bucket_transfer_kwargs(sb)
    result = compute_secure_transfer(
        ledger_equity=ledger_equity,
        secure_nok=secure,
        ref_hwm=ref if ref > 0 else float(ledger_equity),
        unit_size_nok=u,
        phase_daily_risk_ceil=phase_daily_risk_ceil,
        open_risk=float(open_risk or 0.0),
        **xfer_kw,
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
        "tier": result.tier,
        "transfer_capped_by_liquid_floor": result.transfer_capped_by_liquid_floor,
        "liquid_floor_required": result.liquid_floor_required,
    }
    if not result.triggered:
        return out, info

    out["secure_nok"] = result.secure_after
    out["unit_hwm_reset_equity_nok"] = result.ref_hwm_after
    # Lock epoch for auto-unlock: settled count at skim time
    if settled_count is not None:
        out["secure_lock_settled_count"] = int(settled_count)
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
            "tier": result.tier,
            "rule_bundle_version": RULE_BUNDLE_VERSION,
            "settled_count_at_lock": out.get("secure_lock_settled_count"),
        }
    )
    out["secure_transfers"] = transfers
    return out, info


def _parse_utc_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def release_secure_to_working(
    segments: dict[str, Any],
    *,
    reason: str,
    actor: str = "system",
    settled_count: int | None = None,
    kind: str = "auto",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Release entire secure bucket to working capital (secure → 0).
    Does not change unit_hwm_reset_equity_nok. Logs audit on secure_unlocks.

    Sets ``defer_secure_skim`` so the next sync/tick does not immediately
    re-skim after unlock (unlock sticks for one capital pass).
    """
    out = dict(segments)
    released = max(0.0, float(out.get("secure_nok") or 0.0))
    info: dict[str, Any] = {
        "unlocked": False,
        "released_nok": 0.0,
        "reason": reason,
        "kind": kind,
    }
    if released < 1e-9:
        info["reason"] = "secure_already_zero"
        return out, info
    out["secure_nok"] = 0.0
    out.pop("secure_lock_epoch_untrusted", None)
    if settled_count is not None:
        out["secure_lock_settled_count"] = int(settled_count)
    # Skip skim on the same capital pass / next refresh after unlock
    out["defer_secure_skim"] = True
    entry = {
        "ts": utc_now(),
        "action": "unlock_secure",
        "kind": kind,
        "released_nok": round(released, 2),
        "reason": reason,
        "actor": actor,
        "settled_count": settled_count,
        "rule_bundle_version": RULE_BUNDLE_VERSION,
    }
    unlocks = list(out.get("secure_unlocks") or [])
    unlocks.append(entry)
    out["secure_unlocks"] = unlocks
    if kind == "manual":
        out["last_manual_unlock_at"] = entry["ts"]
    info["unlocked"] = True
    info["released_nok"] = round(released, 2)
    return out, info


def maybe_auto_unlock_secure(
    segments: dict[str, Any],
    *,
    settled_count: int,
    v2: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Auto-unlock after unlock_after_settled (default 25) performance-settled
    bets since last skim/lock epoch. Releases entire secure → working.

    Fail-closed migration: if ``secure_lock_epoch_untrusted`` (pre-PR file with
    secure but no lock key), seed lock epoch to current settled_count and
    **do not** unlock — requires 25 *additional* settles after seed.
    """
    v2 = v2 or capital_v2_cfg({})
    sb = v2.get("secure_bucket") or {}
    info: dict[str, Any] = {
        "unlocked": False,
        "released_nok": 0.0,
        "reason": "no_auto_unlock",
        "kind": "auto",
    }
    if not bool(sb.get("enabled", True)):
        info["reason"] = "secure_bucket_disabled"
        return dict(segments), info
    secure = max(0.0, float(segments.get("secure_nok") or 0.0))
    if secure < 1e-9:
        info["reason"] = "secure_already_zero"
        out = dict(segments)
        out.pop("secure_lock_epoch_untrusted", None)
        return out, info

    n = int(settled_count)
    # Pre-PR / missing epoch: seed to current settled, never unlock this pass
    if segments.get("secure_lock_epoch_untrusted"):
        out = dict(segments)
        out["secure_lock_settled_count"] = n
        out.pop("secure_lock_epoch_untrusted", None)
        info["reason"] = "seeded_lock_epoch_migration"
        info["settled_since_lock"] = 0
        info["unlock_after_settled"] = int(sb.get("unlock_after_settled") or 25)
        info["seeded_lock_settled_count"] = n
        return out, info

    need = int(sb.get("unlock_after_settled") or 25)
    lock_n = int(segments.get("secure_lock_settled_count") or 0)
    if n - lock_n < need:
        info["reason"] = "below_settled_threshold"
        info["settled_since_lock"] = n - lock_n
        info["unlock_after_settled"] = need
        return dict(segments), info
    return release_secure_to_working(
        segments,
        reason=f"auto_unlock_after_{need}_settled",
        actor="system",
        settled_count=n,
        kind="auto",
    )


def manual_unlock_secure(
    cfg: dict[str, Any],
    *,
    reason: str = "manual_unlock",
    actor: str = "operator",
    settled_count: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Manual unlock: release entire secure → working, subject to
    manual_unlock_cooldown_days (default 7) between manual unlocks.
    Pass force=True to bypass cooldown (ops only).
    """
    v2 = capital_v2_cfg(cfg)
    sb = v2.get("secure_bucket") or {}
    baseline = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)
    segs = load_segments(cfg, baseline_nok=baseline)
    secure = max(0.0, float(segs.get("secure_nok") or 0.0))
    if secure < 1e-9:
        return {
            "ok": False,
            "unlocked": False,
            "released_nok": 0.0,
            "reason": "secure_already_zero",
        }
    cooldown_days = float(sb.get("manual_unlock_cooldown_days") or 7)
    last = _parse_utc_ts(segs.get("last_manual_unlock_at"))
    if last is not None and not force and cooldown_days > 0:
        now = datetime.now(timezone.utc)
        elapsed_days = (now - last).total_seconds() / 86400.0
        if elapsed_days + 1e-9 < cooldown_days:
            remaining = round(cooldown_days - elapsed_days, 2)
            return {
                "ok": False,
                "unlocked": False,
                "released_nok": 0.0,
                "reason": "manual_unlock_cooldown",
                "cooldown_days": cooldown_days,
                "days_remaining": remaining,
                "last_manual_unlock_at": segs.get("last_manual_unlock_at"),
            }
    n = settled_count
    if n is None:
        try:
            from nt.bets_io import load_bets
            from nt.config import path_from_config as _pfc

            rows = load_bets(_pfc(cfg, "bets"))
            n = sum(1 for r in rows if is_performance_settled(r.get("result")))
        except Exception:
            n = int(segs.get("secure_lock_settled_count") or 0)
    segs, info = release_secure_to_working(
        segs,
        reason=reason,
        actor=actor,
        settled_count=n,
        kind="manual",
    )
    path = save_segments(cfg, segs)
    return {
        "ok": bool(info.get("unlocked")),
        "unlocked": bool(info.get("unlocked")),
        "released_nok": info.get("released_nok", 0.0),
        "reason": info.get("reason"),
        "segments_path": str(path),
        "secure_nok_after": segs.get("secure_nok"),
    }


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
    phase_daily_risk_ceil: float | None = None,
    unit_size_override: float | None = None,
) -> dict[str, Any]:
    """
    When capital_v2.enabled: load segments → auto-unlock → secure transfer →
    snapshots → save. When disabled: no-op empty load (does not write).

    ``unit_size_override``: when phase_continuous is enabled, pass continuous
    unit so day/week snapshots freeze the hybrid unit (not pure liquid ladder).

    Returns segments dict used for subsequent risk evaluation.
    """
    v2 = capital_v2_cfg(cfg)
    baseline = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)
    if not bool(v2.get("enabled")):
        return load_segments(cfg, baseline_nok=baseline)

    segs = load_segments(cfg, baseline_nok=baseline)
    today = oslo_today()
    week_id = oslo_iso_week_id(today)
    open_risk = day_pending_risk(rows, today)
    settled_n = sum(1 for r in rows if is_performance_settled(r.get("result")))

    # Auto-unlock (or seed untrusted lock epoch) before skim
    segs, unlock_info = maybe_auto_unlock_secure(
        segs, settled_count=settled_n, v2=v2
    )

    # Skip skim same tick after unlock (or one-shot defer from manual unlock)
    defer_skim = bool(segs.get("defer_secure_skim")) or bool(unlock_info.get("unlocked"))
    if defer_skim:
        segs = dict(segs)
        segs.pop("defer_secure_skim", None)
        transfer_info = {
            "triggered": False,
            "transferred": 0.0,
            "reason": "skipped_same_tick_after_unlock",
            "tier": None,
            "secure_after": max(0.0, float(segs.get("secure_nok") or 0.0)),
            "ref_hwm_after": segs.get("unit_hwm_reset_equity_nok"),
        }
    else:
        segs, transfer_info = apply_secure_transfer_to_segments(
            segs,
            ledger_equity=ledger_equity,
            v2=v2,
            phase_daily_risk_ceil=phase_daily_risk_ceil,
            open_risk=open_risk,
            settled_count=settled_n,
        )

    secure = max(0.0, float(segs.get("secure_nok") or 0.0))
    liquid = riskable_liquid(ledger_equity, secure, open_risk)
    # Prefer phase continuous unit when provided; else liquid ladder
    if unit_size_override is not None and float(unit_size_override) > 0:
        unit = float(unit_size_override)
    else:
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
        "secure_unlock": unlock_info,
        "riskable_liquid_nok": liquid,
        "oslo_date": today,
        "week_id": week_id,
        "skim_deferred_after_unlock": bool(defer_skim and unlock_info.get("unlocked")),
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
