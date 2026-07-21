"""Tiered light research coverage."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.light_research import auto_light_assess, coverage_stats, run_light_research


def test_auto_light_mid_band_pass():
    cfg = load_config()
    rec = auto_light_assess(
        match="A vs B",
        selection="Vinner: A",
        sport="tennis",
        odds=1.70,
        cfg=cfg,
        score=95,
    )
    assert rec.verdict == "pass"
    # P1: light pass never auto-promotes — agent/manual only
    assert rec.promote_to_deep is False
    assert rec.rough_p_needed is not None


def test_auto_light_short_odds_fail():
    cfg = load_config()
    rec = auto_light_assess(
        match="A vs B",
        selection="Over 0.5",
        sport="football",
        odds=1.20,
        cfg=cfg,
    )
    assert rec.verdict == "fail"
    assert rec.promote_to_deep is False


def test_run_light_coverage_on_fake_shortlist(tmp_path, monkeypatch):
    cfg = load_config()
    # Point outbox to tmp
    cfg = dict(cfg)
    paths = dict(cfg.get("paths") or {})
    paths["outbox"] = str(tmp_path)
    cfg["paths"] = paths

    shortlist = []
    sports = ["basketball"] * 6 + ["tennis"] * 3 + ["football"] * 3 + ["snooker"] * 2
    for i, sp in enumerate(sports):
        shortlist.append(
            {
                "match": f"Match {i}",
                "selection": f"Vinner: Team{i}",
                "sport": sp,
                "decimal_odds": 1.55 + (i % 5) * 0.08,
                "score": 100 - i,
                "has_evidence": False,
                "has_p_model": False,
            }
        )
    payload = run_light_research(cfg, Path("inbox/fake.txt"), shortlist, write=True)
    assert payload["assessed_n"] >= int(0.7 * len(shortlist))
    assert payload["stats"]["light_coverage_pct"] >= 70
    # basketball has 6 lines → min 3 light
    by_sp = payload["stats"]["by_sport"]
    assert by_sp.get("basketball", 0) >= 3
    assert (tmp_path / "light_research").exists() or any(tmp_path.rglob("*.json"))
