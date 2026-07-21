"""
P1: Temporary min_ev raises after process_error settlements (closed loop).

State: data/state/process_gates.json
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config


def process_gate_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    learn = cfg.get("learning") or {}
    raw = dict(learn.get("process_gate") or {})
    return {
        "enabled": bool(raw.get("enabled", True)),
        "min_ev_raise": float(raw.get("min_ev_raise", 0.02)),
        "max_raise": float(raw.get("max_raise", 0.05)),
        "ttl_hours": float(raw.get("ttl_hours", 48)),
        "clear_after_clean_settles": int(raw.get("clear_after_clean_settles", 3)),
    }


def process_gates_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("process_gates_json"):
        return path_from_config(cfg, "process_gates_json")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "process_gates.json"


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


def load_process_gates(cfg: dict[str, Any]) -> dict[str, Any]:
    path = process_gates_path(cfg)
    if not path.is_file():
        return {"gates": [], "updated_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"gates": [], "updated_at": None}
        gates = list(data.get("gates") or [])
        now = datetime.now(timezone.utc)
        live = []
        for g in gates:
            exp = _parse_ts(str(g.get("expires_at") or ""))
            if exp and exp < now:
                continue
            live.append(g)
        data["gates"] = live
        return data
    except Exception:
        return {"gates": [], "updated_at": None}


def save_process_gates(cfg: dict[str, Any], payload: dict[str, Any]) -> Path:
    path = process_gates_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["updated_at"] = utc_now()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def upsert_process_error_gates(
    cfg: dict[str, Any],
    *,
    sport: str,
    market: str = "",
    bet_id: str = "",
) -> dict[str, Any]:
    """Raise min_ev for sport (and market if known) after a process_error settlement."""
    pg = process_gate_cfg(cfg)
    if not pg["enabled"]:
        return {"ok": False, "reason": "disabled"}

    payload = load_process_gates(cfg)
    gates = list(payload.get("gates") or [])
    raise_amt = float(pg["min_ev_raise"])
    max_raise = float(pg["max_raise"])
    ttl = timedelta(hours=float(pg["ttl_hours"]))
    expires = (datetime.now(timezone.utc) + ttl).strftime("%Y-%m-%dT%H:%M:%SZ")

    keys: list[tuple[str, str]] = []
    sp = (sport or "").strip().lower() or "unknown"
    if sp and sp != "unknown":
        keys.append(("sport", sp))
    mk = (market or "").strip().lower()
    if mk and mk not in ("", "unknown"):
        keys.append(("market", mk))

    touched: list[str] = []
    for scope, key in keys:
        gid = f"{scope}:{key}"
        found = None
        for g in gates:
            if g.get("scope") == scope and str(g.get("key") or "") == key:
                found = g
                break
        if found is None:
            found = {
                "id": gid,
                "scope": scope,
                "key": key,
                "min_ev_raise": raise_amt,
                "hits": 1,
                "clean_settles": 0,
                "expires_at": expires,
                "source_bet_ids": [bet_id] if bet_id else [],
                "reason": "process_error settlement",
            }
            gates.append(found)
        else:
            found["hits"] = int(found.get("hits") or 0) + 1
            found["min_ev_raise"] = min(
                max_raise,
                float(found.get("min_ev_raise") or 0) + raise_amt,
            )
            found["expires_at"] = expires
            found["clean_settles"] = 0
            ids = list(found.get("source_bet_ids") or [])
            if bet_id and bet_id not in ids:
                ids.append(bet_id)
            found["source_bet_ids"] = ids[-12:]
        touched.append(gid)

    payload["gates"] = gates
    save_process_gates(cfg, payload)
    return {"ok": True, "touched": touched, "gates": gates}


def note_clean_settlement(cfg: dict[str, Any], *, sport: str = "", market: str = "") -> None:
    """Decrement clean counter; clear gate after enough clean settles."""
    pg = process_gate_cfg(cfg)
    if not pg["enabled"]:
        return
    need = int(pg["clear_after_clean_settles"])
    payload = load_process_gates(cfg)
    gates = list(payload.get("gates") or [])
    if not gates:
        return
    sp = (sport or "").strip().lower()
    mk = (market or "").strip().lower()
    keep: list[dict[str, Any]] = []
    for g in gates:
        scope = g.get("scope")
        key = str(g.get("key") or "")
        match = (scope == "sport" and key == sp) or (scope == "market" and key == mk)
        if not match:
            keep.append(g)
            continue
        clean = int(g.get("clean_settles") or 0) + 1
        if clean >= need:
            continue  # drop
        g = dict(g)
        g["clean_settles"] = clean
        keep.append(g)
    payload["gates"] = keep
    save_process_gates(cfg, payload)


def process_gate_raise(
    cfg: dict[str, Any],
    *,
    sport: str = "",
    market_key: str = "",
) -> float:
    """Extra min_ev required given active process gates."""
    pg = process_gate_cfg(cfg)
    if not pg["enabled"]:
        return 0.0
    payload = load_process_gates(cfg)
    raise_amt = 0.0
    sp = (sport or "").strip().lower()
    mk = (market_key or "").strip().lower()
    for g in payload.get("gates") or []:
        scope = g.get("scope")
        key = str(g.get("key") or "")
        if scope == "sport" and key == sp:
            raise_amt = max(raise_amt, float(g.get("min_ev_raise") or 0))
        if scope == "market" and key == mk:
            raise_amt = max(raise_amt, float(g.get("min_ev_raise") or 0))
        if scope == "global":
            raise_amt = max(raise_amt, float(g.get("min_ev_raise") or 0))
    return min(float(pg["max_raise"]), raise_amt)
