"""
P0: ControlSignals — primary closed-loop actuators after process misses.

Store: data/state/control_signals.jsonl (append-only; active = non-expired).
Signal: temp_gate_raise → min_ev raise + force confirmed lineup (TTL 7–14 days).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config


def control_signals_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    learn = cfg.get("learning") or {}
    raw = dict(learn.get("control_signals") or {})
    # Back-compat: also read process_gate knobs for min_ev/max
    pg = dict(learn.get("process_gate") or {})
    ttl = float(raw.get("ttl_days") or 10)
    ttl = max(7.0, min(14.0, ttl))
    return {
        "enabled": bool(raw.get("enabled", True)),
        "min_ev_raise": float(
            raw.get("min_ev_raise") or pg.get("min_ev_raise") or 0.02
        ),
        "max_raise": float(raw.get("max_raise") or pg.get("max_raise") or 0.05),
        "ttl_days": ttl,
        "force_confirmed_lineup": bool(raw.get("force_confirmed_lineup", True)),
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


def load_active_signals(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Non-expired, non-revoked temp_gate_raise (and future types)."""
    now = _now()
    all_recs = load_all_signals(cfg)
    # Tombstones: (ts, sport|*, market|*)
    revokes: list[tuple[datetime, str, str]] = []
    for rec in all_recs:
        if str(rec.get("kind") or "") != "revoke":
            continue
        ts = _parse_ts(str(rec.get("ts") or "")) or now
        if rec.get("revoke_all"):
            revokes.append((ts, "*", "*"))
            continue
        sp = str(rec.get("sport") or "").strip().lower() or "*"
        mk = str(rec.get("market") or "").strip().lower() or "*"
        revokes.append((ts, sp, mk))

    active: list[dict[str, Any]] = []
    for rec in all_recs:
        if rec.get("revoked"):
            continue
        if str(rec.get("kind") or "") != "temp_gate_raise":
            continue
        exp = _parse_ts(str(rec.get("expires_at") or ""))
        if exp and exp < now:
            continue
        sp = str(rec.get("sport") or "").strip().lower()
        mk = str(rec.get("market") or "").strip().lower() or ""
        sig_ts = _parse_ts(str(rec.get("ts") or "")) or now
        killed = False
        for r_ts, r_sp, r_mk in revokes:
            if r_ts < sig_ts:
                continue  # revoke only kills signals already present
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
) -> dict[str, Any]:
    """Append revoke tombstone so matching active temp_gate_raise stop applying."""
    rec = {
        "kind": "revoke",
        "ts": utc_now(),
        "sport": (sport or "").strip().lower() or None,
        "market": (market or "").strip().lower() or None,
        "revoke_all": bool(revoke_all),
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
    active = load_active_signals(cfg)
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
    for a in load_active_signals(cfg):
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
