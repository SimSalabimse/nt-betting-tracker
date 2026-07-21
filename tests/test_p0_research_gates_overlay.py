"""P0 research_gates ControlSignals overlay — force confirmed."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.control_signals import emit_temp_gate_raise
from nt.research_gates import evaluate_research_gates


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
                "ttl_days": 10,
                "force_confirmed_lineup": True,
            }
        },
        "research": {"gates": {"enabled": True}},
        "selection": {"high_odds_threshold": 2.5},
    }


def test_force_confirmed_blocks_predicted_totals(tmp_path: Path):
    cfg = _cfg(tmp_path)
    emit_temp_gate_raise(cfg, sport="football", market="Totals Under", bet_id="b1")
    pack = {
        "match": "A vs B",
        "selection": "Under 2.5",
        "sport": "football",
        "p_model": 0.55,
        "summary": "x" * 40,
        "failure_modes": "y" * 20,
        "availability_status": "predicted",
        "availability_notes": "expected XI with possible rest " + ("z" * 30),
        "script_lean": "low_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "context_risk": "low",
        "sources": [
            {"url": f"https://ex.com/{i}", "takeaway": "injury news", "kind": "injury"}
            for i in range(6)
        ],
    }
    hard, soft = evaluate_research_gates(
        pack, cfg, selection="Under 2.5", sport="football", odds=1.90
    )
    assert any("control_signal" in h or "confirmed" in h.lower() for h in hard)
    assert any("control_signal" in s for s in soft)
