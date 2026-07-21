"""
P1/P0: Temporary min_ev raises after process_error.

P0: Primary store is ControlSignals (control_signals.jsonl).
This module remains a thin bridge so portfolio + older tests keep working.
"""
from __future__ import annotations

from typing import Any

from nt.control_signals import (
    active_temp_gate_overlay,
    emit_temp_gate_raise,
    load_active_signals,
)


def process_gate_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    from nt.control_signals import control_signals_cfg

    cs = control_signals_cfg(cfg)
    learn = cfg.get("learning") or {}
    raw = dict(learn.get("process_gate") or {})
    return {
        "enabled": bool(raw.get("enabled", cs["enabled"])),
        "min_ev_raise": float(raw.get("min_ev_raise") or cs["min_ev_raise"]),
        "max_raise": float(raw.get("max_raise") or cs["max_raise"]),
        # Legacy hours field; ControlSignals uses days (7–14)
        "ttl_hours": float(raw.get("ttl_hours") or cs["ttl_days"] * 24),
        "clear_after_clean_settles": int(raw.get("clear_after_clean_settles", 3)),
    }


def process_gates_path(cfg: dict[str, Any]):
    """Legacy path — active signals live in control_signals.jsonl."""
    from nt.control_signals import control_signals_path

    return control_signals_path(cfg)


def load_process_gates(cfg: dict[str, Any]) -> dict[str, Any]:
    """Compatibility shape: gates list derived from active control signals."""
    gates = []
    for a in load_active_signals(cfg):
        sp = str(a.get("sport") or "")
        mk = str(a.get("market") or "") or None
        if sp:
            gates.append(
                {
                    "id": f"sport:{sp}",
                    "scope": "sport",
                    "key": sp,
                    "min_ev_raise": a.get("min_ev_raise"),
                    "expires_at": a.get("expires_at"),
                    "source_bet_ids": [a["bet_id"]] if a.get("bet_id") else [],
                    "reason": a.get("source") or "temp_gate_raise",
                    "force_confirmed_lineup": a.get("force_confirmed_lineup"),
                }
            )
        if mk:
            gates.append(
                {
                    "id": f"market:{mk}",
                    "scope": "market",
                    "key": mk,
                    "min_ev_raise": a.get("min_ev_raise"),
                    "expires_at": a.get("expires_at"),
                    "reason": a.get("source") or "temp_gate_raise",
                }
            )
    return {"gates": gates, "updated_at": None, "backend": "control_signals"}


def save_process_gates(cfg: dict[str, Any], payload: dict[str, Any]):
    """No-op for JSON path — ControlSignals is append-only JSONL."""
    from nt.control_signals import control_signals_path

    return control_signals_path(cfg)


def upsert_process_error_gates(
    cfg: dict[str, Any],
    *,
    sport: str,
    market: str = "",
    bet_id: str = "",
    source: str = "process_error",
    process_root_cause: str = "",
    packet: dict | None = None,
) -> dict[str, Any]:
    """Emit ControlSignals temp_gate_raise (primary closed loop)."""
    return emit_temp_gate_raise(
        cfg,
        sport=sport,
        market=market,
        bet_id=bet_id,
        source=source,
        process_root_cause=process_root_cause,
        packet=packet,
    )


def note_clean_settlement(cfg: dict[str, Any], *, sport: str = "", market: str = "") -> None:
    """
    P0: TTL-only expiry on ControlSignals.
    Clean settles no longer clear early (signals last full TTL).
    Kept as no-op for call-site compatibility.
    """
    return None


def process_gate_raise(
    cfg: dict[str, Any],
    *,
    sport: str = "",
    market_key: str = "",
) -> float:
    """Extra min_ev required from active ControlSignals temp_gate_raise."""
    ov = active_temp_gate_overlay(cfg, sport=sport, market=market_key)
    return float(ov.get("min_ev_raise") or 0.0)
