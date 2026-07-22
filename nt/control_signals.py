"""
P0: ControlSignals — primary closed-loop actuators after process misses.

Store: data/state/control_signals.jsonl (append-only; active = non-expired).

Kinds:
  - temp_gate_raise → min_ev raise + force confirmed lineup (TTL 7–14 days)
  - force_coverage_priority → deep-queue research pressure (band / prefer weights)
  - force_clearability_priority → raise clearable-track floor (ops-only week 1;
    auto-emit off by default)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from nt.bets_io import utc_now
from nt.config import path_from_config

# Non-revoke signal kinds that can be active
SIGNAL_KINDS = (
    "temp_gate_raise",
    "force_coverage_priority",
    "force_clearability_priority",
)

COVERAGE_SPORT = "coverage"
CLEARABILITY_SPORT = "clearability"


def control_signals_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    learn = cfg.get("learning") or {}
    raw = dict(learn.get("control_signals") or {})
    # Back-compat: also read process_gate knobs for min_ev/max
    pg = dict(learn.get("process_gate") or {})
    ttl = float(raw.get("ttl_days") or 10)
    ttl = max(7.0, min(14.0, ttl))

    cov_raw = dict(raw.get("coverage_priority") or {})
    cov_ttl = float(cov_raw.get("ttl_days") or 5)
    cov_ttl = max(4.0, min(7.0, cov_ttl))

    cl_raw = dict(raw.get("clearability_priority") or {})
    cl_ttl = float(cl_raw.get("ttl_days") or 5)
    cl_ttl = max(4.0, min(7.0, cl_ttl))

    prefer = cov_raw.get("prefer") or ["alt_totals", "dogs", "handicaps", "period"]
    if not isinstance(prefer, list):
        prefer = ["alt_totals", "dogs", "handicaps", "period"]

    return {
        "enabled": bool(raw.get("enabled", True)),
        "min_ev_raise": float(
            raw.get("min_ev_raise") or pg.get("min_ev_raise") or 0.02
        ),
        "max_raise": float(raw.get("max_raise") or pg.get("max_raise") or 0.05),
        "ttl_days": ttl,
        "force_confirmed_lineup": bool(raw.get("force_confirmed_lineup", True)),
        "coverage_priority": {
            "enabled": bool(cov_raw.get("enabled", True)),
            "ttl_days": cov_ttl,
            "min_deep_packs": int(cov_raw.get("min_deep_packs") or 8),
            "target_odds_band": str(cov_raw.get("target_odds_band") or "1.85-2.60"),
            "prefer": [str(x) for x in prefer],
            "near_empty_max_picks": int(cov_raw.get("near_empty_max_picks") or 1),
            "min_no_pmodel_reject_share": float(
                cov_raw.get("min_no_pmodel_reject_share") or 0.70
            ),
            "min_mid_unresearched": int(cov_raw.get("min_mid_unresearched") or 3),
            "coverage_preferred_share": float(
                cov_raw.get("coverage_preferred_share") or 0.55
            ),
            "weight_boost": float(cov_raw.get("weight_boost") or 30.0),
            # Auto-revoke when coverage level=ok and mid_unresearched_n==0
            "auto_revoke_when_ok": bool(cov_raw.get("auto_revoke_when_ok", True)),
        },
        "clearability_priority": {
            # Ops-only emit week 1 — default auto-emit OFF
            "enabled": bool(cl_raw.get("enabled", True)),
            "auto_emit": bool(cl_raw.get("auto_emit", False)),
            "auto_emit_min_consecutive": int(
                cl_raw.get("auto_emit_min_consecutive") or 2
            ),
            "ttl_days": cl_ttl,
            "weight_boost": float(cl_raw.get("weight_boost") or 35.0),
            "clearable_floor_boost": float(cl_raw.get("clearable_floor_boost") or 0.15),
        },
    }


def control_signals_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("control_signals_jsonl"):
        return path_from_config(cfg, "control_signals_jsonl")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "control_signals.jsonl"


def _parse_ts(s: str) -> datetime | None:
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def load_all_signals(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = control_signals_path(cfg)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    except Exception:
        return []
    return out


def load_active_signals(
    cfg: dict[str, Any],
    *,
    kinds: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Non-expired, non-revoked signals.

    kinds: filter to these kinds (default: all SIGNAL_KINDS).
    Pass kinds=("temp_gate_raise",) for legacy temp-gate-only consumers.
    """
    want = {str(k) for k in (kinds if kinds is not None else SIGNAL_KINDS)}
    now = _now()
    all_recs = load_all_signals(cfg)
    # Tombstones: (ts, sport|*, market|*, revoke_kind|*)
    revokes: list[tuple[datetime, str, str, str]] = []
    for rec in all_recs:
        if str(rec.get("kind") or "") != "revoke":
            continue
        ts = _parse_ts(str(rec.get("ts") or "")) or now
        r_kind = str(rec.get("revoke_kind") or rec.get("signal_kind") or "").strip() or "*"
        if rec.get("revoke_all"):
            revokes.append((ts, "*", "*", r_kind))
            continue
        sp = str(rec.get("sport") or "").strip().lower() or "*"
        mk = str(rec.get("market") or "").strip().lower() or "*"
        revokes.append((ts, sp, mk, r_kind))

    active: list[dict[str, Any]] = []
    for rec in all_recs:
        if rec.get("revoked"):
            continue
        kind = str(rec.get("kind") or "")
        if kind not in want:
            continue
        exp = _parse_ts(str(rec.get("expires_at") or ""))
        if exp and exp < now:
            continue
        sp = str(rec.get("sport") or "").strip().lower()
        mk = str(rec.get("market") or "").strip().lower() or ""
        sig_ts = _parse_ts(str(rec.get("ts") or "")) or now
        killed = False
        for r_ts, r_sp, r_mk, r_kind in revokes:
            if r_ts < sig_ts:
                continue  # revoke only kills signals already present
            if r_kind not in ("*", "") and r_kind != kind:
                continue
            if r_sp == "*" or r_sp == sp:
                if r_mk in ("*", "") or r_mk == mk or not mk:
                    killed = True
                    break
        if killed:
            continue
        active.append(rec)
    return active


def revoke_signals(
    cfg: dict[str, Any],
    *,
    sport: str = "",
    market: str = "",
    revoke_all: bool = False,
    actor: str = "cli",
    reason: str = "manual_expire",
    revoke_kind: str = "",
) -> dict[str, Any]:
    """
    Append revoke tombstone so matching active signals stop applying.

    revoke_kind: optional filter (e.g. force_coverage_priority). Empty = any kind
    matching sport/market (legacy).
    """
    rec = {
        "kind": "revoke",
        "ts": utc_now(),
        "sport": (sport or "").strip().lower() or None,
        "market": (market or "").strip().lower() or None,
        "revoke_all": bool(revoke_all),
        "revoke_kind": (revoke_kind or "").strip() or None,
        "actor": actor,
        "reason": reason,
        "schema_version": 1,
    }
    if not revoke_all and not rec["sport"]:
        return {"ok": False, "error": "sport required unless --all"}
    path = _append_signal(cfg, rec)
    still = load_active_signals(cfg)
    return {"ok": True, "revoke": rec, "path": str(path), "n_active_remaining": len(still)}


def _append_signal(cfg: dict[str, Any], rec: dict[str, Any]) -> Path:
    path = control_signals_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def emit_temp_gate_raise(
    cfg: dict[str, Any],
    *,
    sport: str,
    market: str = "",
    bet_id: str = "",
    source: str = "process_error",
    process_root_cause: str = "",
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Emit temp_gate_raise for sport (and market if known).
    Always allowed on n=1 — primary closed-loop after process miss.
    """
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return {"ok": False, "reason": "disabled"}

    sp = (sport or "").strip().lower() or "unknown"
    mk = (market or "").strip().lower()
    if mk in ("", "unknown"):
        mk = ""

    ttl_days = float(cs["ttl_days"])
    expires = (_now() + timedelta(days=ttl_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise_amt = float(cs["min_ev_raise"])
    max_raise = float(cs["max_raise"])

    # Stack: sum prior active raises for same sport, then add, cap
    active = load_active_signals(cfg, kinds=("temp_gate_raise",))
    prior = 0.0
    for a in active:
        if str(a.get("sport") or "").lower() == sp:
            prior = max(prior, float(a.get("min_ev_raise") or 0))
        if mk and str(a.get("market") or "").lower() == mk:
            prior = max(prior, float(a.get("min_ev_raise") or 0))
    stacked = min(max_raise, prior + raise_amt if prior > 0 else raise_amt)

    root = process_root_cause or (
        str((packet or {}).get("process_root_cause") or "") if packet else ""
    )

    rec = {
        "kind": "temp_gate_raise",
        "ts": utc_now(),
        "expires_at": expires,
        "ttl_days": ttl_days,
        "sport": sp,
        "market": mk or None,
        "min_ev_raise": round(stacked, 4),
        "force_confirmed_lineup": bool(cs["force_confirmed_lineup"]),
        "source": source,
        "bet_id": bet_id or None,
        "process_root_cause": root or None,
        "schema_version": 1,
    }
    path = _append_signal(cfg, rec)
    return {"ok": True, "signal": rec, "path": str(path)}


def active_temp_gate_overlay(
    cfg: dict[str, Any],
    *,
    sport: str = "",
    market: str = "",
) -> dict[str, Any]:
    """
    Aggregate overlay for a candidate sport/market.
    Returns min_ev_raise (capped) and force_confirmed_lineup.
    """
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return {
            "min_ev_raise": 0.0,
            "force_confirmed_lineup": False,
            "n_signals": 0,
            "sources": [],
        }

    sp = (sport or "").strip().lower()
    mk = (market or "").strip().lower()
    raise_amt = 0.0
    force = False
    sources: list[str] = []
    n = 0
    for a in load_active_signals(cfg, kinds=("temp_gate_raise",)):
        a_sp = str(a.get("sport") or "").lower()
        a_mk = str(a.get("market") or "").lower()
        hit = False
        if sp and a_sp == sp:
            hit = True
        if mk and a_mk and a_mk == mk:
            hit = True
        if not hit:
            continue
        n += 1
        raise_amt = max(raise_amt, float(a.get("min_ev_raise") or 0))
        if a.get("force_confirmed_lineup"):
            force = True
        sources.append(str(a.get("source") or "temp_gate_raise"))

    max_raise = float(cs["max_raise"])
    return {
        "min_ev_raise": min(max_raise, raise_amt),
        "force_confirmed_lineup": force,
        "n_signals": n,
        "sources": sources[:8],
    }


# ---------------------------------------------------------------------------
# force_coverage_priority
# ---------------------------------------------------------------------------


def emit_force_coverage_priority(
    cfg: dict[str, Any],
    *,
    source: str = "research_starvation",
    reason: str = "",
    mid_unresearched_n: int | None = None,
    n_picked: int | None = None,
) -> dict[str, Any]:
    """
    Emit force_coverage_priority (sport=coverage).
    Raises next deep-queue mid/alt weights; does not invent p_model or soften EV.
    """
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return {"ok": False, "reason": "disabled"}
    cov = cs["coverage_priority"]
    if not cov.get("enabled", True):
        return {"ok": False, "reason": "coverage_priority_disabled"}

    # Skip re-emit if already active
    existing = load_active_signals(cfg, kinds=("force_coverage_priority",))
    if existing:
        return {
            "ok": True,
            "reason": "already_active",
            "signal": existing[-1],
            "emitted": False,
        }

    ttl_days = float(cov["ttl_days"])
    expires = (_now() + timedelta(days=ttl_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec = {
        "kind": "force_coverage_priority",
        "ts": utc_now(),
        "expires_at": expires,
        "ttl_days": ttl_days,
        "sport": COVERAGE_SPORT,
        "market": None,
        "target_odds_band": cov["target_odds_band"],
        "prefer": list(cov["prefer"]),
        "min_deep_packs": int(cov["min_deep_packs"]),
        "coverage_preferred_share": float(cov["coverage_preferred_share"]),
        "weight_boost": float(cov["weight_boost"]),
        "source": source,
        "reason": reason or None,
        "mid_unresearched_n": mid_unresearched_n,
        "n_picked": n_picked,
        "schema_version": 1,
    }
    path = _append_signal(cfg, rec)
    return {"ok": True, "signal": rec, "path": str(path), "emitted": True}


def active_coverage_priority_overlay(
    cfg: dict[str, Any],
    *,
    coverage_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Coverage overlay for deep-queue promotion weights.

    No-op when coverage level=ok AND mid_unresearched_n==0 (hygiene), even if a
    historical force_coverage signal is still non-expired. Caller may also
    auto-revoke via maybe_auto_revoke_coverage.
    """
    inactive = {
        "active": False,
        "no_op": False,
        "force_coverage_emitted": False,
        "force_coverage_overlay_active": False,
        "n_signals": 0,
        "sources": [],
        "target_odds_band": "1.85-2.60",
        "prefer": [],
        "min_deep_packs": 8,
        "coverage_preferred_share": 0.55,
        "weight_boost": 30.0,
        "expires_at": None,
    }
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return dict(inactive)
    cov = cs["coverage_priority"]
    if not cov.get("enabled", True):
        return dict(inactive)

    active = load_active_signals(cfg, kinds=("force_coverage_priority",))
    emitted = bool(active)
    if not active:
        return {**inactive, "force_coverage_emitted": False}

    # Hygiene: recovered coverage → overlay no-op (still report signal history)
    health = coverage_health
    if health is None:
        try:
            from nt.coverage_health import load_coverage_health

            health = load_coverage_health(cfg)
        except Exception:
            health = None

    level = str((health or {}).get("level") or "").lower()
    try:
        mid_u = int((health or {}).get("mid_unresearched_n") or 0)
    except (TypeError, ValueError):
        mid_u = 0

    no_op = level == "ok" and mid_u == 0
    latest = active[-1]
    sources = [str(a.get("source") or "force_coverage_priority") for a in active]

    base = {
        "active": not no_op,
        "no_op": no_op,
        "force_coverage_emitted": emitted,
        "force_coverage_overlay_active": not no_op,
        "n_signals": len(active),
        "sources": sources[:8],
        "target_odds_band": str(
            latest.get("target_odds_band") or cov["target_odds_band"]
        ),
        "prefer": list(latest.get("prefer") or cov["prefer"]),
        "min_deep_packs": int(latest.get("min_deep_packs") or cov["min_deep_packs"]),
        "coverage_preferred_share": float(
            latest.get("coverage_preferred_share")
            if latest.get("coverage_preferred_share") is not None
            else cov["coverage_preferred_share"]
        ),
        "weight_boost": float(
            latest.get("weight_boost")
            if latest.get("weight_boost") is not None
            else cov["weight_boost"]
        ),
        "expires_at": latest.get("expires_at"),
    }
    return base


def maybe_auto_revoke_coverage(
    cfg: dict[str, Any],
    *,
    coverage_health: dict[str, Any] | None = None,
    actor: str = "engine",
) -> dict[str, Any]:
    """
    Auto-revoke active force_coverage_priority when coverage recovered:
    level=ok AND mid_unresearched_n==0.

    Config: learning.control_signals.coverage_priority.auto_revoke_when_ok (default True).
    """
    cs = control_signals_cfg(cfg)
    cov = cs["coverage_priority"]
    if not cov.get("auto_revoke_when_ok", True):
        return {"ok": True, "revoked": False, "reason": "auto_revoke_disabled"}

    active = load_active_signals(cfg, kinds=("force_coverage_priority",))
    if not active:
        return {"ok": True, "revoked": False, "reason": "no_active_coverage_signal"}

    health = coverage_health
    if health is None:
        try:
            from nt.coverage_health import load_coverage_health

            health = load_coverage_health(cfg)
        except Exception:
            health = None
    if not health:
        return {"ok": True, "revoked": False, "reason": "no_coverage_health"}

    level = str(health.get("level") or "").lower()
    try:
        mid_u = int(health.get("mid_unresearched_n") or 0)
    except (TypeError, ValueError):
        mid_u = 0

    if level != "ok" or mid_u != 0:
        return {
            "ok": True,
            "revoked": False,
            "reason": "coverage_not_recovered",
            "level": level,
            "mid_unresearched_n": mid_u,
        }

    out = revoke_signals(
        cfg,
        sport=COVERAGE_SPORT,
        revoke_kind="force_coverage_priority",
        actor=actor,
        reason="coverage_recovered",
    )
    return {
        "ok": bool(out.get("ok")),
        "revoked": bool(out.get("ok")),
        "reason": "coverage_recovered",
        "revoke": out.get("revoke"),
        "path": out.get("path"),
    }


# ---------------------------------------------------------------------------
# force_clearability_priority (ops-only default; auto_emit off week 1)
# ---------------------------------------------------------------------------


def emit_force_clearability_priority(
    cfg: dict[str, Any],
    *,
    source: str = "manual",
    reason: str = "",
    actor: str = "ops",
) -> dict[str, Any]:
    """
    Emit force_clearability_priority (sport=clearability).

    Default: ops/manual only (auto_emit=False). Does not change haircut, min_ev,
    or invent p_model — only raises clearable-track promotion weight.
    """
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return {"ok": False, "reason": "disabled"}
    cl = cs["clearability_priority"]
    if not cl.get("enabled", True):
        return {"ok": False, "reason": "clearability_priority_disabled"}

    existing = load_active_signals(cfg, kinds=("force_clearability_priority",))
    if existing:
        return {
            "ok": True,
            "reason": "already_active",
            "signal": existing[-1],
            "emitted": False,
        }

    ttl_days = float(cl["ttl_days"])
    expires = (_now() + timedelta(days=ttl_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec = {
        "kind": "force_clearability_priority",
        "ts": utc_now(),
        "expires_at": expires,
        "ttl_days": ttl_days,
        "sport": CLEARABILITY_SPORT,
        "market": None,
        "weight_boost": float(cl["weight_boost"]),
        "clearable_floor_boost": float(cl["clearable_floor_boost"]),
        "source": source,
        "reason": reason or None,
        "actor": actor,
        "schema_version": 1,
    }
    path = _append_signal(cfg, rec)
    return {"ok": True, "signal": rec, "path": str(path), "emitted": True}


def active_clearability_priority_overlay(cfg: dict[str, Any]) -> dict[str, Any]:
    """Overlay for clearability / dual-track floor boost."""
    inactive = {
        "active": False,
        "force_clearability_active": False,
        "n_signals": 0,
        "sources": [],
        "weight_boost": 0.0,
        "clearable_floor_boost": 0.0,
        "expires_at": None,
    }
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return dict(inactive)
    cl = cs["clearability_priority"]
    if not cl.get("enabled", True):
        return dict(inactive)

    active = load_active_signals(cfg, kinds=("force_clearability_priority",))
    if not active:
        return dict(inactive)

    latest = active[-1]
    return {
        "active": True,
        "force_clearability_active": True,
        "n_signals": len(active),
        "sources": [str(a.get("source") or "force_clearability_priority") for a in active][
            :8
        ],
        "weight_boost": float(
            latest.get("weight_boost")
            if latest.get("weight_boost") is not None
            else cl["weight_boost"]
        ),
        "clearable_floor_boost": float(
            latest.get("clearable_floor_boost")
            if latest.get("clearable_floor_boost") is not None
            else cl["clearable_floor_boost"]
        ),
        "expires_at": latest.get("expires_at"),
    }


def maybe_auto_emit_clearability(
    cfg: dict[str, Any],
    *,
    starvation_kind: str = "",
    consecutive_clearability_miss: int = 0,
    source: str = "clearability_miss",
) -> dict[str, Any]:
    """
    Optional auto-emit after N consecutive clearability_miss place-capable runs.
    Default auto_emit=False (ops-only week 1).
    """
    cs = control_signals_cfg(cfg)
    cl = cs["clearability_priority"]
    if not cl.get("auto_emit", False):
        return {"ok": True, "emitted": False, "reason": "auto_emit_off"}
    if str(starvation_kind) != "clearability_miss":
        return {"ok": True, "emitted": False, "reason": "not_clearability_miss"}
    need = int(cl.get("auto_emit_min_consecutive") or 2)
    if int(consecutive_clearability_miss) < need:
        return {
            "ok": True,
            "emitted": False,
            "reason": "below_consecutive_threshold",
            "need": need,
            "have": int(consecutive_clearability_miss),
        }
    return emit_force_clearability_priority(
        cfg,
        source=source,
        reason=f"auto:{consecutive_clearability_miss}_consecutive_clearability_miss",
        actor="engine",
    )
