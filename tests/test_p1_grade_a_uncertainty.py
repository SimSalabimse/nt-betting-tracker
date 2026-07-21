"""P1: Grade A requires p_model_sd / CI / multi-model."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import grade_evidence


def _cfg() -> dict:
    return {
        "selection": {
            "high_odds_threshold": 2.5,
            "grade_a_require_uncertainty": True,
            "min_research_sources": {"default": 3, "grade_A": 6, "high_odds": 8},
        },
        "research": {"gates": {"enabled": False}},
    }


def _pack(**extra):
    base = {
        "match": "A vs B",
        "selection": "A to Win",
        "p_model": 0.62,
        "summary": "Solid edge from form and H2H.",
        "failure_modes": "Injury, rain.",
        "sources": [
            {"name": f"s{i}", "url": f"https://ex/{i}", "kind": "stats", "takeaway": "ok"}
            for i in range(6)
        ],
    }
    base.update(extra)
    return base


def test_point_p_model_only_is_b_not_a():
    g, issues = grade_evidence(_pack(), _cfg(), 1.85)
    assert g == "B"
    assert any("grade_A requires" in i for i in issues)


def test_p_model_sd_allows_a():
    g, _ = grade_evidence(_pack(p_model_sd=0.04), _cfg(), 1.85)
    assert g == "A"


def test_ci_allows_a():
    g, _ = grade_evidence(
        _pack(p_model_ci_low=0.55, p_model_ci_high=0.70),
        _cfg(),
        1.85,
    )
    assert g == "A"


def test_multi_source_probs_allow_a():
    sources = [
        {"name": "m1", "url": "https://a", "kind": "model", "takeaway": "x", "p_model": 0.60},
        {"name": "m2", "url": "https://b", "kind": "model", "takeaway": "y", "prob": 0.64},
        {"name": "s3", "url": "https://c", "kind": "stats", "takeaway": "z"},
        {"name": "s4", "url": "https://d", "kind": "stats", "takeaway": "z"},
        {"name": "s5", "url": "https://e", "kind": "stats", "takeaway": "z"},
        {"name": "s6", "url": "https://f", "kind": "stats", "takeaway": "z"},
    ]
    g, _ = grade_evidence(_pack(sources=sources), _cfg(), 1.85)
    assert g == "A"
