"""P0 ControlSignals temp_gate_raise."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.control_signals import (
    active_temp_gate_overlay,
    emit_temp_gate_raise,
    load_active_signals,
)
from nt.process_gates import process_gate_raise, upsert_process_error_gates


def _cfg(tmp: Path) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {
            "state_dir": str(state),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
        },
        "learning": {
            "control_signals": {
                "enabled": True,
                "min_ev_raise": 0.02,
                "max_raise": 0.05,
                "ttl_days": 10,
                "force_confirmed_lineup": True,
            }
        },
    }


def test_emit_active_overlay(tmp_path: Path):
    cfg = _cfg(tmp_path)
    out = emit_temp_gate_raise(
        cfg, sport="tennis", market="Handicap", bet_id="b1", source="process_error"
    )
    assert out["ok"]
    active = load_active_signals(cfg)
    assert len(active) >= 1
    ov = active_temp_gate_overlay(cfg, sport="tennis")
    assert ov["min_ev_raise"] >= 0.02
    assert ov["force_confirmed_lineup"] is True
    assert process_gate_raise(cfg, sport="tennis") >= 0.02


def test_n1_process_error_emits(tmp_path: Path):
    """Even single process_error forces temp_gate_raise."""
    cfg = _cfg(tmp_path)
    upsert_process_error_gates(cfg, sport="football", market="BTTS", bet_id="only1")
    assert process_gate_raise(cfg, sport="football") >= 0.02


def test_stack_capped(tmp_path: Path):
    cfg = _cfg(tmp_path)
    for i in range(5):
        emit_temp_gate_raise(cfg, sport="darts", bet_id=f"x{i}")
    assert process_gate_raise(cfg, sport="darts") == 0.05


def test_revoke_kills_active(tmp_path: Path):
    from nt.control_signals import revoke_signals

    cfg = _cfg(tmp_path)
    emit_temp_gate_raise(cfg, sport="tennis", bet_id="b1")
    assert process_gate_raise(cfg, sport="tennis") >= 0.02
    out = revoke_signals(cfg, sport="tennis", actor="pytest")
    assert out["ok"]
    assert process_gate_raise(cfg, sport="tennis") == 0.0
    assert load_active_signals(cfg) == []
