"""Phase 5: research write-pack CLI path + sport normalize on scaffold."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.research import write_research_pack


def test_write_research_pack(tmp_path: Path, monkeypatch):
    cfg = load_config()
    # Point evidence at temp
    cfg = {**cfg, "paths": {**(cfg.get("paths") or {}), "evidence": str(tmp_path / "evidence")}}

    res = write_research_pack(
        cfg,
        match="Home vs Away",
        selection="BTTS Nei",
        p_model=0.58,
        sport="Fotball",
        odds=1.85,
        summary="Low scoring domestic script with confirmed injuries.",
        failure_modes="late equalizer",
        availability_status="predicted",
        availability_notes="No key attackers out; full back line expected.",
        context_risk="low",
        script_lean="low_scoring",
        selection_vs_script="agree",
    )
    assert res["ok"] is True
    path = Path(res["path"])
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["sport"] == "football"  # normalized
    assert data["p_model"] == 0.58
    assert data["availability_status"] == "predicted"
    assert data["research_gates"]["selection_vs_script"] == "agree"
    # HV v3 dual-write odds snapshot
    assert data["decimal_odds_ref"] == 1.85
    assert data["odds_at_research"] == 1.85
    assert data.get("researched_at")
