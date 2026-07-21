"""P1: light research never auto-promotes to deep."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.light_research import auto_light_assess, tiers_cfg


def _cfg() -> dict:
    return {
        "selection": {
            "standard_min_ev": 0.03,
            "probability_haircut": 0.05,
            "high_odds_threshold": 2.5,
        },
        "research": {"tiers": {"auto_promote_to_deep": False}},
    }


def test_auto_pass_does_not_promote():
    rec = auto_light_assess(
        match="A vs B",
        selection="A to Win",
        sport="tennis",
        odds=1.85,
        cfg=_cfg(),
        has_deep=False,
        has_p=False,
        p_model=None,
        score=95,
    )
    assert rec.verdict == "pass"
    assert rec.promote_to_deep is False


def test_fail_demotes():
    rec = auto_light_assess(
        match="A vs B",
        selection="Over 5.5",
        sport="football",
        odds=1.20,
        cfg=_cfg(),
        has_deep=False,
        has_p=False,
        p_model=None,
        score=50,
    )
    assert rec.verdict == "fail"
    assert rec.promote_to_deep is False


def test_tiers_default_no_auto_promote():
    t = tiers_cfg({"research": {}})
    assert t.get("auto_promote_to_deep") is False
