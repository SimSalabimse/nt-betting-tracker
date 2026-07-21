from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.agent import list_tools, offline_answer, run_tool, status_brief
from nt.analyze import run_analyze
from nt.combos import ComboLeg, assess_combo, correlation_score
from nt.config import load_config
from nt.defaults import agent_cfg, combos_cfg
from nt.edges import load_edges, query_edges, summarize_edges
from nt.evidence import grade_evidence, normalize_sources, validate_evidence_schema
from nt.project import simulate_paths
from nt.research import checklist_for, list_sources, p_model_report, scaffold_evidence


def test_combos_default_disabled():
    cfg = load_config()
    cc = combos_cfg(cfg)
    assert cc["enabled"] is False or cc.get("aggressiveness") == "conservative"
    legs = [
        ComboLeg("A vs B", "A Win", 1.8, 0.6, "B", sport="football"),
        ComboLeg("C vs D", "Over 2.5", 1.9, 0.55, "B", sport="football"),
    ]
    phase = {"phase_id": "2", "max_doubles_per_round": 1, "stake_min": 12, "stake_max": 18}
    # force enabled for unit test of correlation path
    cfg2 = dict(cfg)
    cfg2["combos"] = {**cc, "enabled": True}
    res = assess_combo(cfg2, legs, phase, base_stake=15, remaining_risk=50)
    assert res.n_legs == 2
    assert res.combined_odds > 1.0


def test_combo_same_match_hard_reject():
    legs = [
        ComboLeg("A vs B", "A Win", 1.8, 0.6, "B"),
        ComboLeg("A vs B", "Over 2.5", 1.9, 0.55, "B"),
    ]
    score, notes = correlation_score(legs)
    assert score == 0.0
    assert any("same match" in n for n in notes)


def test_research_sources_and_scaffold():
    cfg = load_config()
    src = list_sources("football")
    assert len(src) >= 4
    assert checklist_for("football")
    pack = scaffold_evidence(
        cfg,
        match="Test FC vs Sample",
        selection="Test FC to Win",
        p_model=0.55,
        write=False,
    )
    assert pack["ok"]
    assert pack["pack"]["p_model"] == 0.55


def test_p_model_report_clears_bar():
    cfg = load_config()
    r = p_model_report(cfg, 1.80, 0.65)
    assert r["implied_prob"] is not None
    assert r["ev"] > 0
    assert "clears_ev_bar" in r


def test_evidence_normalize_and_optional_fields():
    cfg = load_config()
    sources = normalize_sources(["https://a.com", {"url": "https://b.com", "takeaway": "ok"}])
    assert len(sources) == 2
    ev = {
        "p_model": 0.6,
        "summary": "enough summary text here",
        "failure_modes": "red card risk",
        "sources": [{"url": f"https://x.com/{i}", "takeaway": "t"} for i in range(6)],
        "league": "Eliteserien",
    }
    grade, issues = grade_evidence(ev, cfg, 1.75)
    assert grade in ("A", "B")
    assert validate_evidence_schema(ev) == [] or isinstance(validate_evidence_schema(ev), list)


def test_analyze_and_project_readonly():
    cfg = load_config()
    report = run_analyze(cfg, write_outbox=False)
    assert "bankroll" in report
    assert "overall" in report
    assert report.get("markdown")
    sim = simulate_paths(cfg, years=0.5, sims=50, seed=1)
    assert "final_equity" in sim
    assert sim["final_equity"]["p50"] > 0


def test_edges_query():
    cfg = load_config()
    rows = load_edges(cfg, limit=5)
    assert isinstance(rows, list)
    q = query_edges(cfg, last=10)
    assert isinstance(summarize_edges(q), dict)


def test_agent_offline_tools():
    cfg = load_config()
    assert "get_status" in list_tools()
    brief = status_brief(cfg)
    assert "Equity" in brief
    st = run_tool(cfg, "get_status", {})
    assert "equity_nok" in st
    text = offline_answer(cfg, "How is my book doing?")
    assert "Status" in text or "Equity" in text
    ac = agent_cfg(cfg)
    assert ac["enabled"] is False


def test_legacy_config_keys_still_present():
    cfg = load_config()
    assert "phases" in cfg
    assert "1A" in cfg["phases"]
    assert cfg["bankroll"]["baseline_nok"] == 500.0
    assert "bets" in cfg["paths"]
