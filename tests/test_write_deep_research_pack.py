"""Atomic deep_research_v1 pack writer — validation + ESR keys + idempotent write."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.research import validate_deep_research_payload, write_deep_research_pack


def _good_payload(**overrides) -> dict:
    base = {
        "match": "Milwaukee Brewers vs Colorado Rockies",
        "selection": "Colorado Rockies +2.5",
        "sport": "baseball",
        "league": "MLB",
        "decimal_odds_ref": 1.85,
        "p_model": 0.58,
        "summary": (
            "Series game 2 after Brewers covered -1.5 behind ace. Today pitcher change: "
            "Brewers go to opener after short rest; Rockies start number-two with rest."
        ),
        "failure_modes": "Brewers stack early; Rockies bullpen collapses.",
        "availability_status": "predicted",
        "availability_notes": "Probables listed; ace scratched (injury / lineup change).",
        "lineup_status": "changed",
        "lineup_notes": "Pitcher change on favourite side; ace out for this start.",
        "context_risk": "medium",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "market_family": "handicap_baseball",
        "scan_agents": ["C"],
        "sources": [
            {
                "url": "https://www.mlb.com/example-probables",
                "takeaway": "Brewers opener listed; ace pushed — lineup change",
                "kind": "lineup",
                "side": "home",
            },
            {
                "url": "https://www.espn.com/example-preview",
                "takeaway": "Rockies SP number-two confirmed, five days rest",
                "kind": "lineup",
                "side": "away",
            },
            {
                "url": "https://www.baseball-reference.com/example-h2h",
                "takeaway": "H2H last season mixed; no automatic dog edge",
                "kind": "h2h",
                "side": "both",
            },
            {
                "url": "https://www.mlb.com/standings",
                "takeaway": "Brewers clearly higher standings; ranking gap large",
                "kind": "ranking",
                "side": "both",
            },
        ],
        "opposite_side_check": {
            "evaluated": True,
            "opposite_selection": "Milwaukee Brewers heavy fav HC (minus run line)",
            "one_liner": (
                "Fav HC is ranking-default, but pitcher change and rest advantage "
                "remove the game-1 script — dog RL selected for material SP delta."
            ),
            "why_not_opposite": "Brewers minus HC still prices residual ranking edge.",
        },
        "form_continuity": {
            "checked": True,
            "flip_risk_suspected": True,
            "prior_anchor_note": "Live ledger: Brewers -1.5 Win prior game",
            "why_flip": (
                "Starting pitcher change on the Brewers after game-1 ace cover; "
                "Rockies hold rest advantage and confirmed lineup vs opener game."
            ),
            "strong_signals_claimed": ["S1_injury_lineup", "S2_why_flip", "S4_structural"],
            "form_continuity_triggered": True,
        },
        "signals": {
            "ranking_seed": {
                "filled": True,
                "strength": "positive",
                "note": "Brewers higher standings",
            }
        },
        "feh_checklist": {
            "higher_ranked_side": "favourite",
            "ranking_confidence": 0.8,
            "why_this_side_not_opposite": "Dog RL selected for SP and rest structural flip.",
        },
        "deep_research": {
            "schema_version": "deep_research_v1",
            "tooling": {
                "exa_queries": 5,
                "firecrawl_pages": 1,
                "fallback_web": False,
                "budget_profile": "standard",
            },
            "match_context": {"competition": "MLB", "series_context": "game 2"},
            "recent_form": {"conclusion": "Flip is structural SP-driven"},
            "h2h": "Recent H2H mixed.",
            "ranking_strength_gap": {
                "gap_summary": "Brewers stronger",
                "higher_ranked_side": "favourite",
            },
            "natural_markets": "Totals depend on SP.",
            "key_risks": ["Brewers offense still covers without ace"],
            "verdict": {
                "label": "Acceptable",
                "base_ev_estimate": 0.07,
                "form_continuity_triggered": True,
                "rationale": "Clear SP structural flip.",
            },
        },
        "notes": "deep_research_v1; ESR both-sides",
    }
    base.update(overrides)
    return base


def test_rejects_empty_takeaways():
    payload = _good_payload()
    payload["sources"] = [
        {"url": "https://a.example", "takeaway": ""},
        {"url": "https://b.example", "takeaway": "   "},
        {"url": "https://c.example", "takeaway": "short"},
        {"url": "https://d.example", "takeaway": "ok takeaway here"},
    ]
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("takeaway" in e.lower() for e in v["errors"])


def test_rejects_missing_opposite():
    payload = _good_payload()
    del payload["opposite_side_check"]
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("opposite" in e.lower() for e in v["errors"])

    payload = _good_payload()
    payload["opposite_side_check"] = {
        "evaluated": False,
        "opposite_selection": "other",
        "one_liner": "x" * 25,
    }
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("evaluated" in e.lower() for e in v["errors"])


def test_rejects_non_gate_availability():
    payload = _good_payload(availability_status="changed")
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("availability_status" in e for e in v["errors"])


def test_writes_esr_keys(tmp_path: Path):
    cfg = load_config()
    cfg = {**cfg, "paths": {**(cfg.get("paths") or {}), "evidence": str(tmp_path / "evidence")}}
    res = write_deep_research_pack(cfg, _good_payload())
    assert res["ok"] is True
    assert res["esr_keys_present"] is True
    path = Path(res["path"])
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["model_name"] == "agent_deep_research"
    assert data["availability_status"] == "predicted"
    assert data["lineup_status"] == "changed"
    assert data["opposite_side_check"]["evaluated"] is True
    assert data["deep_research"]["schema_version"] == "deep_research_v1"
    assert data["form_continuity"]["checked"] is True
    assert data["scan_agents"] == ["C"]
    assert data["market_family"] == "handicap_baseball"
    assert data["feh_checklist"]["higher_ranked_side"] == "favourite"
    assert data["signals"]["ranking_seed"]["filled"] is True
    assert len([s for s in data["sources"] if s.get("takeaway")]) >= 4
    assert data["research_gates"]["availability_status"] == "predicted"
    assert data["research_gates"]["lineup_status"] == "changed"


def test_weak_phrase_warn_not_fail(tmp_path: Path):
    cfg = load_config()
    cfg = {**cfg, "paths": {**(cfg.get("paths") or {}), "evidence": str(tmp_path / "evidence")}}
    payload = _good_payload(
        summary="Rockies +2.5 is an easier line after Brewers won; fade the favourite."
    )
    # Keep why_flip structural so flip-risk validation still passes.
    v = validate_deep_research_payload(payload)
    assert v["ok"] is True
    assert v["warnings"]
    assert any("weak-phrase" in w.lower() for w in v["warnings"])

    res = write_deep_research_pack(cfg, payload)
    assert res["ok"] is True
    assert res["warnings"]
    assert Path(res["path"]).is_file()


def test_idempotent_overwrite(tmp_path: Path):
    cfg = load_config()
    cfg = {**cfg, "paths": {**(cfg.get("paths") or {}), "evidence": str(tmp_path / "evidence")}}
    p1 = _good_payload(p_model=0.55)
    r1 = write_deep_research_pack(cfg, p1, filename="idem.json")
    assert r1["ok"] is True
    path = Path(r1["path"])
    p2 = _good_payload(p_model=0.61, summary=_good_payload()["summary"] + " Updated SP note.")
    r2 = write_deep_research_pack(cfg, p2, filename="idem.json")
    assert r2["ok"] is True
    assert Path(r2["path"]) == path
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["p_model"] == 0.61
    assert "Updated SP note" in data["summary"]


def test_flip_risk_requires_why_flip():
    payload = _good_payload()
    payload["form_continuity"] = {
        "checked": True,
        "flip_risk_suspected": True,
        "why_flip": "short",
    }
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("why_flip" in e for e in v["errors"])


def test_rejects_empty_summary_and_failure_modes():
    payload = _good_payload(summary="", failure_modes="")
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("summary" in e for e in v["errors"])
    assert any("failure_modes" in e for e in v["errors"])


def test_rejects_hollow_deep_research_sections():
    payload = _good_payload()
    payload["deep_research"] = {
        "schema_version": "deep_research_v1",
        "match_context": {},
        "recent_form": "",
        "h2h": "   ",
        "ranking_strength_gap": {},
        "natural_markets": "",
        "key_risks": [],
        "verdict": {},
    }
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("hollow" in e or "empty" in e for e in v["errors"])


def test_rejects_missing_form_continuity_checked():
    payload = _good_payload()
    del payload["form_continuity"]
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("form_continuity" in e for e in v["errors"])

    payload = _good_payload()
    payload["form_continuity"] = {"checked": False, "flip_risk_suspected": False}
    v = validate_deep_research_payload(payload)
    assert v["ok"] is False
    assert any("checked" in e for e in v["errors"])


def test_checklist_failure_modes_written_honest(tmp_path: Path):
    """Validator rejects empty failure_modes; good pack sets checklist true."""
    cfg = load_config()
    cfg = {**cfg, "paths": {**(cfg.get("paths") or {}), "evidence": str(tmp_path / "evidence")}}
    res = write_deep_research_pack(cfg, _good_payload())
    assert res["ok"] is True
    data = json.loads(Path(res["path"]).read_text(encoding="utf-8"))
    assert data["checklist"].get("failure_modes_written") is True
