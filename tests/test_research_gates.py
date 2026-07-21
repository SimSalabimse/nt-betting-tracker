"""Multi-sport research gates — FRA–ENG lessons + 12h board balance."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.evidence import evaluate_research_gates, football_selection_family, grade_evidence


def _sources(n=5, extra=None):
    out = [
        {"url": f"https://example.com/{i}", "takeaway": f"note {i}", "kind": "stats"}
        for i in range(n)
    ]
    if extra:
        out.extend(extra)
    return out


def _pack(**kwargs):
    base = {
        "match": "Team A vs Team B",
        "selection": "BTTS Nei",
        "sport": "Football",
        "league": "Eliteserien",
        "p_model": 0.55,
        "summary": "x" * 30,
        "failure_modes": "risk",
        "sources": _sources(),
    }
    base.update(kwargs)
    return base


def test_family_parser():
    assert football_selection_family("BTTS Nei") == "btts_no"
    assert football_selection_family("Totalt antall mål - Over/Under 2.5: Over 2.5") == "totals_over"
    assert football_selection_family("Totalt antall mål - Over/Under 3.5: Under 3.5") == "totals_under"


def test_football_missing_blocks():
    cfg = load_config()
    ev = _pack(lineup_status="missing", script_lean="neutral")
    grade, issues = grade_evidence(ev, cfg, 2.65, selection="BTTS Nei", sport="football")
    assert grade == "F"
    assert any("availability" in i.lower() or "lineup" in i.lower() or "missing" in i.lower() for i in issues)


def test_football_domestic_predicted_ok():
    cfg = load_config()
    ev = _pack(
        selection="Totalt antall mål - Over/Under 2.5: Under 2.5",
        lineup_status="predicted",
        rotation_risk="low",
        context_risk="low",
        script_lean="low_scoring",
        selection_vs_script="agree",
        lineup_notes="Stable XIs; one CB suspended",
        sources=_sources(
            5,
            [{"url": "https://ex.com/inj", "takeaway": "Home CB suspended", "kind": "injury"}],
        ),
        p_model=0.62,
    )
    grade, issues = grade_evidence(ev, cfg, 1.90, selection=ev["selection"], sport="football")
    assert grade in ("A", "B"), (grade, issues)


def test_football_high_scoring_blocks_under():
    cfg = load_config()
    ev = _pack(
        match="Frankrike vs England",
        league="FIFA World Cup bronze",
        selection="Totalt antall mål - Over/Under 3.5: Under 3.5",
        lineup_status="confirmed",
        context_risk="high",
        script_lean="high_scoring",
        lineup_notes="Confirmed: FRA rotated full back four; ENG attacking setup midfield and front",
        sources=_sources(
            4,
            [
                {"url": "https://ex.com/inj", "takeaway": "Saliba out", "kind": "injury"},
                {"url": "https://ex.com/xi", "takeaway": "Rotated back 4", "kind": "lineup"},
            ],
        ),
    )
    grade, issues = grade_evidence(ev, cfg, 1.67, selection=ev["selection"], sport="football")
    assert grade == "F"
    assert any("script" in i.lower() or "high" in i.lower() for i in issues)


def test_football_high_context_thin_notes_blocked():
    cfg = load_config()
    ev = _pack(
        match="Frankrike vs England",
        league="World Cup",
        selection="BTTS Nei",
        lineup_status="predicted",
        context_risk="high",
        script_lean="neutral",
        lineup_notes="",
        sources=_sources(
            4,
            [
                {"url": "https://ex.com/inj", "takeaway": "Some doubts", "kind": "injury"},
                {"url": "https://ex.com/xi", "takeaway": "Expected XI", "kind": "lineup"},
            ],
        ),
    )
    grade, issues = grade_evidence(ev, cfg, 2.65, selection="BTTS Nei", sport="football")
    assert grade == "F"
    assert any("notes" in i.lower() or "context" in i.lower() or "tier" in i.lower() for i in issues)


def test_tennis_games_over_missing_fitness_blocked():
    cfg = load_config()
    ev = _pack(
        match="Rublev vs Darderi",
        sport="Tennis",
        league="ATP",
        selection="Totalt antall game over/under 22.5: Over 22.5",
        availability_status="missing",
        script_lean="long_match",
        sources=_sources(6),
    )
    grade, issues = grade_evidence(ev, cfg, 1.85, selection=ev["selection"], sport="tennis")
    assert grade == "F"


def test_tennis_retirement_blocks_overs():
    cfg = load_config()
    ev = _pack(
        match="Player A vs Player B",
        sport="Tennis",
        selection="Totalt antall game over/under 22.5: Over 22.5",
        availability_status="predicted",
        context_risk="high",
        script_lean="retirement_risk",
        availability_notes="A played 3h yesterday; hip tape; retirement risk elevated for long match path",
        sources=_sources(
            5,
            [{"url": "https://ex.com/fit", "takeaway": "Hip issue", "kind": "fitness"}],
        ),
    )
    grade, issues = grade_evidence(ev, cfg, 1.90, selection=ev["selection"], sport="tennis")
    assert grade == "F"
    assert any("retirement" in i.lower() or "script" in i.lower() for i in issues)


def test_basketball_b2b_prop_no_minutes_blocked():
    cfg = load_config()
    ev = _pack(
        match="Lakers vs Warriors",
        sport="Basketball",
        league="NBA",
        selection="LeBron James points over/under 24.5: Over 24.5",
        availability_status="missing",
        context_risk="high",
        summary="Back-to-back second night for Lakers",
        sources=_sources(6),
    )
    grade, issues = grade_evidence(ev, cfg, 1.90, selection=ev["selection"], sport="basketball")
    assert grade == "F"


def test_basketball_predicted_total_ok():
    cfg = load_config()
    notes = (
        "Both teams full strength injury report; not on B2B; expected starters 32+ min. "
        "Pace mid; total lean slight under."
    )
    ev = _pack(
        match="Celtics vs Bucks",
        sport="Basketball",
        league="NBA",
        selection="Totalt 220.5: Under 220.5",
        availability_status="predicted",
        context_risk="low",
        script_lean="low_pace",
        selection_vs_script="agree",
        availability_notes=notes,
        sources=_sources(
            5,
            [{"url": "https://ex.com/inj", "takeaway": "No key outs on report", "kind": "injury"}],
        ),
        p_model=0.58,
    )
    grade, issues = grade_evidence(ev, cfg, 1.91, selection=ev["selection"], sport="basketball")
    assert grade in ("A", "B"), (grade, issues)


def test_basketball_star_rest_blocks_prop_over():
    cfg = load_config()
    ev = _pack(
        match="Team vs Team",
        sport="Basketball",
        selection="Star Player points over/under 28.5: Over 28.5",
        availability_status="predicted",
        script_lean="star_rest",
        availability_notes="Star listed questionable; load management likely on second night of B2B travel set",
        sources=_sources(
            5,
            [{"url": "https://ex.com/inj", "takeaway": "Questionable", "kind": "injury"}],
        ),
    )
    grade, issues = grade_evidence(ev, cfg, 1.87, selection=ev["selection"], sport="basketball")
    assert grade == "F"
    assert any("star_rest" in i or "script" in i.lower() for i in issues)


def test_darts_ml_not_blocked_without_lineup():
    cfg = load_config()
    ev = {
        "match": "Aspinall vs Cullen",
        "selection": "Vinner: Aspinall, Nathan",
        "sport": "darts",
        "p_model": 0.58,
        "summary": "Seed should cover",
        "failure_modes": "upset",
        "sources": _sources(6),
    }
    grade, _ = grade_evidence(ev, cfg, 1.50, selection=ev["selection"], sport="darts")
    assert grade in ("A", "B")


def test_base_rate_conflict():
    cfg = load_config()
    ev = _pack(
        selection="Totalt antall mål - Over/Under 3.5: Under 3.5",
        lineup_status="predicted",
        base_rate_conflict=True,
        sources=_sources(
            5,
            [{"url": "https://ex.com/inj", "takeaway": "No absences", "kind": "injury"}],
        ),
    )
    grade, issues = grade_evidence(ev, cfg, 1.67, selection=ev["selection"], sport="football")
    assert grade == "F"
    assert any("base_rate" in i for i in issues)


def test_evaluate_api_tuple():
    cfg = load_config()
    ev = _pack(lineup_status="missing")
    hard, soft = evaluate_research_gates(ev, cfg, selection="BTTS Nei", sport="football", odds=2.65)
    assert hard
    assert isinstance(soft, list)
