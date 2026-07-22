"""PR1 place-path hard gates + PR2 filter/group bet_ids (forensic grain)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.analytics import filter_rows, group_stats_with_ids, infer_market
from nt.decisions import (
    append_decision,
    append_evidence_link,
    backfill_decisions_from_notes,
    densify_market_keys,
    load_decisions,
    load_evidence_links,
    normalize_decision_record,
    parse_notes_meta,
)
from nt.portfolio import Candidate, build_portfolio


def test_parse_notes_p_model_dual_write():
    m = parse_notes_meta("p_model=0.6200; EV=0.055; EXPLORE")
    assert m["p_model"] is not None
    assert abs(float(m["p_model"]) - 0.62) < 1e-6
    assert abs(float(m["ev"]) - 0.055) < 1e-6


def test_normalize_decision_fills_market_key(tmp_path: Path):
    rec = normalize_decision_record(
        {
            "bet_id": "x1",
            "selection": "BTTS Ja",
            "market_type": "Begge lag scorer",
            "p_model": 0.7,
            "ev": 0.05,
        }
    )
    assert rec["market_key"] == infer_market("BTTS Ja", "Begge lag scorer")
    assert rec["p_model_source"] == "engine"
    assert rec["schema_version"] == 1
    assert rec["evidence_match"] == "none"


def test_append_decision_and_evidence_link(tmp_path: Path, monkeypatch):
    cfg = {
        "paths": {
            "state_dir": str(tmp_path),
            "decisions_jsonl": str(tmp_path / "bet_decisions.jsonl"),
            "evidence_links_jsonl": str(tmp_path / "evidence_links.jsonl"),
        }
    }

    # path_from_config uses resolve(ROOT/...) — monkeypatch via absolute paths in decisions helpers
    from nt import decisions as decmod

    monkeypatch.setattr(decmod, "decisions_path", lambda c: Path(c["paths"]["decisions_jsonl"]))
    monkeypatch.setattr(decmod, "evidence_links_path", lambda c: Path(c["paths"]["evidence_links_jsonl"]))

    written = append_decision(
        cfg,
        {
            "bet_id": "abc123",
            "selection": "Over 2.5",
            "market_type": "Totalt antall mål - over/under 2.5",
            "p_model": 0.65,
            "ev": 0.04,
            "evidence_path": "evidence/foo.json",
        },
    )
    assert written["market_key"]
    assert written["p_model"] == 0.65
    assert written["evidence_match"] == "hard"

    append_evidence_link(
        cfg,
        {
            "bet_id": "abc123",
            "evidence_path": "evidence/foo.json",
            "match_method": "place_hard",
            "confidence": 1.0,
            "p_model_at_link": 0.65,
        },
    )
    links = load_evidence_links(cfg)
    assert links["abc123"]["evidence_path"] == "evidence/foo.json"
    decs = load_decisions(cfg)
    assert decs["abc123"]["market_key"]


def test_backfill_dry_run_no_write(tmp_path: Path, monkeypatch):
    from nt import decisions as decmod

    monkeypatch.setattr(decmod, "decisions_path", lambda c: Path(c["paths"]["decisions_jsonl"]))
    cfg = {
        "paths": {
            "decisions_jsonl": str(tmp_path / "bet_decisions.jsonl"),
            "state_dir": str(tmp_path),
        }
    }
    rows = [
        {
            "bet_id": "b1",
            "source": "recommend",
            "selection": "Team A to Win",
            "market_type": "HUB",
            "notes": "EV=0.05; p_model=0.61",
            "sport": "football",
            "research_grade": "B",
            "decimal_odds": "1.80",
            "stake_nok": "10",
        }
    ]
    r = backfill_decisions_from_notes(cfg, rows, only_missing=True, dry_run=True)
    assert r["dry_run"] is True
    assert r["written"] == 1
    assert not Path(cfg["paths"]["decisions_jsonl"]).exists()

    r2 = densify_market_keys(cfg, rows, dry_run=True)
    assert r2["dry_run"] is True
    assert r2["written"] >= 1


def test_filter_rows_multi_and_bet_ids():
    rows = [
        {"bet_id": "1", "sport": "football", "odds_band": "1.5-1.8", "result": "Win", "phase": "2", "research_grade": "B", "source": "recommend", "selection": "BTTS Ja", "market_type": "Begge lag scorer", "date": "2026-07-10", "match": "A vs B", "notes": ""},
        {"bet_id": "2", "sport": "tennis", "odds_band": "1.8-2.2", "result": "Loss", "phase": "2", "research_grade": "B", "source": "recommend", "selection": "Vinner: X", "market_type": "Vinner", "date": "2026-07-11", "match": "C vs D", "notes": ""},
        {"bet_id": "3", "sport": "football", "odds_band": "1.5-1.8", "result": "Loss", "phase": "1A", "research_grade": "A", "source": "era_archive", "selection": "Over 2.5", "market_type": "", "date": "2026-07-12", "match": "E vs F", "notes": "id-check"},
    ]
    # multi sport
    f = filter_rows(rows, sport=["football", "tennis"])
    assert len(f) == 3
    f2 = filter_rows(rows, sport="football", result=["Win", "Loss"])
    assert {r["bet_id"] for r in f2} == {"1", "3"}
    # live shortcut
    live = filter_rows(rows, source="live")
    assert {r["bet_id"] for r in live} == {"1", "2"}
    # bet_ids drill
    drilled = filter_rows(rows, bet_ids=["1", "3"])
    assert [r["bet_id"] for r in drilled] == ["1", "3"]
    # id: query
    by_id = filter_rows(rows, query="id:2")
    assert len(by_id) == 1 and by_id[0]["bet_id"] == "2"
    # market multi
    m = filter_rows(rows, market=["BTTS"])
    assert any(r["bet_id"] == "1" for r in m)


def test_group_stats_with_ids_cap_and_drill():
    rows = [
        {"bet_id": f"b{i}", "sport": "football" if i % 2 == 0 else "tennis", "result": "Win", "stake_nok": "10", "p_l_nok": "5", "decimal_odds": "1.8"}
        for i in range(10)
    ]
    g = group_stats_with_ids(rows, "sport", id_cap=3)
    assert "football" in g and "tennis" in g
    assert g["football"]["bet_ids_truncated"] is True or len(g["football"]["bet_ids"]) <= 3
    assert g["football"]["n"] == 5
    # grain law: filter back by ids
    ids = g["football"]["bet_ids"]
    back = filter_rows(rows, bet_ids=ids)
    assert all(r["sport"] == "football" for r in back)
    assert len(back) == len(ids)


def test_portfolio_notes_include_p_model():
    """Scored recommendations dual-write p_model into notes for recovery."""
    from nt.config import load_config

    cfg = load_config()
    # Lower haircut noise for unit certainty
    cfg = dict(cfg)
    cfg["selection"] = dict(cfg["selection"])
    cfg["selection"]["probability_haircut"] = 0.0
    cfg["selection"]["standard_min_ev"] = 0.01
    cfg["learning"] = dict(cfg.get("learning") or {})
    cfg["learning"]["enabled"] = False
    phase = {
        "phase_id": "2",
        "stake_min": 10,
        "stake_max": 15,
        "max_bets_per_round": 5,
    }
    risk = {"can_bet": True, "remaining_risk_nok": 100.0, "daily_risk_cap_nok": 100.0}
    c = Candidate(
        date="2026-07-17",
        match="Test vs Opp",
        selection="BTTS Ja",
        decimal_odds=1.90,
        sport="football",
        market_type="Begge lag scorer",
        p_model=0.62,
        evidence={
            "p_model": 0.62,
            "summary": "unit pack for forensic p_model notes",
            "failure_modes": "x",
            "context_risk": "low",
            "availability_status": "predicted",
            "availability_notes": "expected full strength",
            "script_lean": "competitive",
            "selection_vs_script": "agree",
            "base_rate_conflict": False,
            "sources": [
                {"url": f"https://e.com/{i}", "takeaway": "t", "kind": "stats"}
                for i in range(8)
            ],
            "odds_at_research": 1.90,
            "decimal_odds_ref": 1.90,
        },
        evidence_path="evidence/test_btts.json",
    )
    picked, rejects = build_portfolio(cfg, [c], phase, risk, [], learning={})
    assert picked, f"expected pick with high EV; rejects={rejects}"
    assert "p_model=" in picked[0].notes
    assert abs(picked[0].p_model - 0.62) < 1e-6
    assert picked[0].evidence_path == "evidence/test_btts.json"
    assert picked[0].market_key
