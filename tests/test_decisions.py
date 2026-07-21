from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import load_bets
from nt.config import load_config
from nt.decisions import (
    backfill_decisions_from_notes,
    learning_summary_for_ui,
    load_decisions,
    parse_notes_meta,
    resolve_decision,
    score_process,
)


def test_parse_notes_ev_and_learn():
    notes = "EV=0.055; EXPLORE; learn_EV+0.021; band <1.5 EV+0.009; explore tennis n=7"
    m = parse_notes_meta(notes)
    assert m["ev"] is not None
    assert abs(m["ev"] - 0.055) < 1e-6
    assert m["explore"] is True
    assert m["learning_ev_boost"] is not None
    assert abs(m["learning_ev_boost"] - 0.021) < 1e-6
    assert m["reasons"]


def test_parse_learn_stake():
    m = parse_notes_meta("EV=0.038; learn_stake×1.028; learn_EV+0.006")
    assert m["learning_stake_mult"] is not None
    assert abs(m["learning_stake_mult"] - 1.028) < 1e-6


def test_resolve_darderi_style_row():
    row = {
        "bet_id": "test_d1",
        "source": "recommend",
        "research_grade": "B",
        "decimal_odds": "1.47",
        "stake_nok": "10",
        "notes": "EV=0.055; EXPLORE; learn_EV+0.021; band <1.5 EV+0.009",
        "sport": "tennis",
        "result": "Pending",
    }
    d = resolve_decision(None, row, decisions_map={})
    assert d is not None
    assert d.get("ev") is not None
    assert abs(float(d["ev"]) - 0.055) < 1e-6
    proc = score_process(d, row)
    assert "thin meta" not in proc["label"].lower() or proc["score"] == "ok"
    # Should be recovered / engine shortlist, not pure thin
    assert proc["score"] in ("ok", "good")
    learn = learning_summary_for_ui(d, row, live_sport={"stake_mult": 1.0, "status": "thin"})
    assert "No learning snapshot (older" not in learn["at_place"]
    assert "0.021" in learn["at_place"] or "EV" in learn["at_place"]


def test_backfill_writes_file():
    cfg = load_config()
    rows = load_bets(ROOT / "data/bets.csv")
    rec = [r for r in rows if r.get("source") == "recommend"]
    assert rec, "expected recommend rows in ledger"
    result = backfill_decisions_from_notes(cfg, rows, only_missing=True)
    assert result["written"] >= 0
    decs = load_decisions(cfg)
    # After backfill, recommend rows with notes should resolve EV
    sample = next((r for r in rec if (r.get("notes") or "").strip()), None)
    assert sample
    d = resolve_decision(cfg, sample, decisions_map=decs)
    assert d is not None
    if "EV=" in (sample.get("notes") or ""):
        assert d.get("ev") is not None
