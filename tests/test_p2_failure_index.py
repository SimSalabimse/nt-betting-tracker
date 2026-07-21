"""P2 failure index rebuild + query."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.failure_index import query_failures, rebuild_failure_index


def _cfg(tmp: Path) -> dict:
    data = tmp / "data"
    state = tmp / "state"
    ev = tmp / "evidence"
    data.mkdir()
    state.mkdir()
    ev.mkdir()
    bets = data / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,notes,source,created_at,updated_at\n"
        "b1,2026-07-01,TeamA vs TeamB,Under 2.5,1.90,10,Loss,-10,0,B,1.8-2.2,football,"
        "totals,,rotation injury notes,rec,,, \n"
        "b2,2026-07-02,X vs Y,A to Win,1.70,10,Win,7,17,A,1.5-1.8,tennis,,,,,\n",
        encoding="utf-8",
    )
    (ev / "pack1.json").write_text(
        json.dumps(
            {
                "match": "TeamA vs TeamB",
                "selection": "Under 2.5",
                "failure_modes": "Late rotation bronze high GPG",
                "summary": "Cagey expected",
                "p_model": 0.55,
                "sources": [],
            }
        ),
        encoding="utf-8",
    )
    (data / "edges.jsonl").write_text("", encoding="utf-8")
    return {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "evidence": str(ev),
            "edges_jsonl": str(data / "edges.jsonl"),
            "failure_index_json": str(state / "failure_index.json"),
        }
    }


def test_rebuild_and_query(tmp_path: Path):
    cfg = _cfg(tmp_path)
    out = rebuild_failure_index(cfg)
    assert out["n_docs"] >= 2
    hits = query_failures(cfg, q="rotation", limit=10)
    assert any("rotation" in (h.get("text") or "").lower() for h in hits)
    losses = query_failures(cfg, q="", kind="bet", limit=10)
    assert any(h.get("kind") == "bet" for h in losses)
