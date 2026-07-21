"""P1 process_error → temporary min_ev raise closed loop."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.process_gates import (
    load_process_gates,
    note_clean_settlement,
    process_gate_raise,
    upsert_process_error_gates,
)


def _cfg(tmp: Path) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {"state_dir": str(state), "process_gates_json": str(state / "process_gates.json")},
        "learning": {
            "process_gate": {
                "enabled": True,
                "min_ev_raise": 0.02,
                "max_raise": 0.05,
                "ttl_hours": 48,
                "clear_after_clean_settles": 2,
            }
        },
    }


def test_upsert_and_raise(tmp_path: Path):
    cfg = _cfg(tmp_path)
    out = upsert_process_error_gates(cfg, sport="tennis", market="handicap", bet_id="b1")
    assert out["ok"]
    assert process_gate_raise(cfg, sport="tennis") == 0.02
    assert process_gate_raise(cfg, market_key="handicap") == 0.02
    assert process_gate_raise(cfg, sport="football") == 0.0


def test_stack_capped(tmp_path: Path):
    cfg = _cfg(tmp_path)
    for _ in range(5):
        upsert_process_error_gates(cfg, sport="darts", bet_id="x")
    assert process_gate_raise(cfg, sport="darts") == 0.05


def test_clean_settles_clear(tmp_path: Path):
    cfg = _cfg(tmp_path)
    upsert_process_error_gates(cfg, sport="tennis", bet_id="b1")
    note_clean_settlement(cfg, sport="tennis")
    assert process_gate_raise(cfg, sport="tennis") == 0.02
    note_clean_settlement(cfg, sport="tennis")
    assert process_gate_raise(cfg, sport="tennis") == 0.0
