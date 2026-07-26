"""critique_pack soft-warns deep packs missing opposite_side_check (PR5 polish)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.research import (
    critique_pack,
    deep_pack_opposite_side_warnings,
    _is_deep_research_pack,
)


def _minimal_deep_pack(**overrides) -> dict:
    base = {
        "match": "Team A vs Team B",
        "selection": "Team B +1.5",
        "sport": "football",
        "p_model": 0.55,
        "p_model_sd": 0.04,
        "summary": "Deep pack fixture for critique soft-warn opposite-side path.",
        "failure_modes": "Favourite covers anyway.",
        "sources": [
            {"url": "https://example.com/a", "takeaway": "note a"},
            {"url": "https://example.com/b", "takeaway": "note b"},
            {"url": "https://example.com/c", "takeaway": "note c"},
            {"url": "https://example.com/d", "takeaway": "note d"},
        ],
        "model_name": "agent_deep_research",
        "notes": "deep_research_v1",
        "deep_research": {"schema_version": "deep_research_v1", "match_context": "x" * 10},
        "availability_status": "predicted",
        "context_risk": "low",
        "script_lean": "neutral",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
    }
    base.update(overrides)
    return base


def test_is_deep_research_pack_detection():
    assert _is_deep_research_pack(_minimal_deep_pack()) is True
    assert _is_deep_research_pack({"model_name": "agent_research"}) is False
    assert _is_deep_research_pack({"deep_research": {}}) is True
    assert _is_deep_research_pack({"notes": "deep_research_v1 scaffold"}) is True


def test_soft_warn_missing_opposite():
    ev = _minimal_deep_pack()
    assert "opposite_side_check" not in ev
    warns = deep_pack_opposite_side_warnings(ev)
    assert len(warns) == 1
    assert "missing opposite_side_check" in warns[0]
    assert "soft" in warns[0].lower()


def test_soft_warn_evaluated_false():
    ev = _minimal_deep_pack(
        opposite_side_check={
            "evaluated": False,
            "opposite_selection": "Team A -1.5",
            "one_liner": "x" * 25,
        }
    )
    warns = deep_pack_opposite_side_warnings(ev)
    assert len(warns) == 1
    assert "evaluated" in warns[0].lower()


def test_no_warn_when_evaluated_true():
    ev = _minimal_deep_pack(
        opposite_side_check={
            "evaluated": True,
            "opposite_selection": "Team A -1.5",
            "one_liner": "Fav HC is the ranking default; dog selected for SP rest.",
        }
    )
    assert deep_pack_opposite_side_warnings(ev) == []


def test_shallow_pack_no_opposite_warn():
    ev = {
        "match": "A vs B",
        "selection": "A ML",
        "model_name": "agent_research",
        "p_model": 0.5,
        "summary": "Shallow scaffold",
        "failure_modes": "x",
        "sources": [],
    }
    assert deep_pack_opposite_side_warnings(ev) == []


def test_critique_pack_soft_only_not_hard_fail(tmp_path: Path):
    cfg = load_config()
    pack = _minimal_deep_pack()  # no opposite_side_check
    path = tmp_path / "deep_missing_opp.json"
    path.write_text(json.dumps(pack), encoding="utf-8")

    result = critique_pack(cfg, path, odds=1.85)
    assert result["ok"] is True  # soft path — never hard fail on missing opposite
    notes = " ".join(result.get("quality_notes") or [])
    assert "opposite_side_check" in notes
    assert "soft" in notes.lower()
    # Grade comes from grade_evidence; missing opposite must not alone force F via critique
    assert result["grade"] in ("A", "B", "C", "F")
    # If F, it must be for other reasons — issues must not claim opposite hard-fail
    issues_blob = " ".join(str(i) for i in (result.get("issues") or [])).lower()
    assert "opposite_side_check" not in issues_blob
