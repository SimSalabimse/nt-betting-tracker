"""
HV Research Regime v3 §2 — pack odds snapshot integrity (PR3).

T6: missing snapshot / inferred / drift reject place
T7: soft-key newest researched_at/mtime wins
Dual-write: scaffold/write_research_pack stamps both odds fields
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_parse import Candidate, attach_evidence
from nt.pack_freshness import (
    apply_odds_snapshot_fields,
    odds_drift_rel,
    pack_odds_snapshot,
    placeable_odds_snapshot,
)
from nt.portfolio import Candidate as PortCandidate
from nt.portfolio import build_portfolio
from nt.research import scaffold_evidence, write_research_pack


def _cfg(**pi_extra) -> dict:
    return {
        "norsk_tipping": {"min_stake_nok": 10.0},
        "capital_v2": {"enabled": False},
        "selection": {
            "probability_haircut": 0.03,
            "standard_min_ev": 0.02,
            "strong_min_ev": 0.015,
            "absolute_min_ev": 0.01,
            "strong_min_sources": 8,
            "grade_c_placeable": True,
            "grade_c_require_core_reason": True,
            "grade_c_min_sources": 4,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.05,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {"min_sample": 99},
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
            "grade_a_require_uncertainty": False,
        },
        "learning": {"enabled": False},
        "risk": {},
        "research": {
            "pack_integrity": {
                "stale_odds_rel_threshold": 0.03,
                "require_odds_at_research_for_place": True,
                **pi_extra,
            },
            "gates": {
                "enabled": True,
                "reject_script_conflict": True,
                "reject_base_rate_conflict": True,
                "require_availability_status": True,
                "predicted_availability_ok": True,
                "require_availability_research_if_predicted": True,
                "high_context_require_confirmed": False,
            },
        },
        "phases": {
            "1A": {
                "stake_min": 10,
                "stake_max": 12,
                "max_bets_per_round": 5,
            }
        },
    }


def _phase() -> dict:
    return {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 5,
        "max_doubles_per_round": 0,
        "daily_risk_pct": 0.12,
        "daily_risk_floor": 40,
        "daily_risk_ceil": 80,
    }


def _risk() -> dict:
    return {
        "can_bet": True,
        "remaining_risk_nok": 80.0,
        "reasons": [],
    }


def _strong_pack(
    *,
    p_model: float = 0.62,
    odds_at_research: float | None = 2.0,
    decimal_odds_ref: float | None = 2.0,
    inferred: bool = False,
    researched_at: str | None = "2026-07-20T12:00:00Z",
) -> dict:
    sources = [
        {
            "url": f"https://example.com/{i}",
            "takeaway": "solid form edge and script fit",
            "kind": "stats" if i > 0 else "injury",
        }
        for i in range(8)
    ]
    pack: dict = {
        "match": "Home vs Away",
        "selection": "Over 2.5",
        "sport": "football",
        "p_model": p_model,
        "summary": "Clear core reason: high xG both sides, confirmed open game script.",
        "failure_modes": "early red card kills over script",
        "sources": sources,
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": (
            "No key absences; full attack expected for domestic fixture. "
            "Minutes load normal; fitness OK."
        ),
        "lineup_status": "predicted",
        "lineup_notes": "No key absences; full attack expected; minutes load normal.",
        "script_lean": "high_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
    }
    if odds_at_research is not None:
        pack["odds_at_research"] = odds_at_research
    if decimal_odds_ref is not None:
        pack["decimal_odds_ref"] = decimal_odds_ref
    if inferred:
        pack["odds_snapshot_inferred"] = True
    if researched_at is not None:
        pack["researched_at"] = researched_at
    return pack


def _cand(odds: float, pack: dict, p_model: float | None = None) -> PortCandidate:
    return PortCandidate(
        date="2026-07-22",
        match=str(pack.get("match") or "Home vs Away"),
        selection=str(pack.get("selection") or "Over 2.5"),
        decimal_odds=odds,
        sport="football",
        p_model=p_model if p_model is not None else float(pack["p_model"]),
        evidence=pack,
    )


# --- unit helpers ---


def test_pack_odds_snapshot_prefers_odds_at_research():
    assert pack_odds_snapshot({"odds_at_research": 1.95, "decimal_odds_ref": 2.10}) == 1.95
    assert pack_odds_snapshot({"decimal_odds_ref": 2.10}) == 2.10
    assert pack_odds_snapshot({}) is None
    assert pack_odds_snapshot(None) is None


def test_odds_drift_rel():
    assert odds_drift_rel(2.0, 2.0) == pytest.approx(0.0)
    assert odds_drift_rel(2.0, 2.06) == pytest.approx(0.03)
    assert odds_drift_rel(2.0, 2.10) == pytest.approx(0.05)
    assert odds_drift_rel(None, 2.0) is None


# --- T6 place law ---


def test_t6_inflated_p_missing_snapshot_rejects_place():
    """Inflated p_model + board odds present but no snapshot → missing_odds_snapshot."""
    pack = _strong_pack(p_model=0.75, odds_at_research=None, decimal_odds_ref=None)
    # strip any residual
    pack.pop("odds_at_research", None)
    pack.pop("decimal_odds_ref", None)
    board = 2.0
    ok, reason = placeable_odds_snapshot(pack, board, _cfg())
    assert ok is False
    assert reason == "missing_odds_snapshot"

    picked, rejects = build_portfolio(
        _cfg(), [_cand(board, pack)], _phase(), _risk(), []
    )
    assert picked == []
    assert any(r.get("reason") == "missing_odds_snapshot" for r in rejects)


def test_t6_inferred_flag_rejects_place():
    pack = _strong_pack(odds_at_research=2.0, inferred=True)
    ok, reason = placeable_odds_snapshot(pack, 2.0, _cfg())
    assert ok is False
    assert reason == "odds_snapshot_inferred"

    picked, rejects = build_portfolio(
        _cfg(), [_cand(2.0, pack)], _phase(), _risk(), []
    )
    assert picked == []
    assert any(r.get("reason") == "odds_snapshot_inferred" for r in rejects)


def test_t6_drift_ge_3pct_rejects_place():
    # snap 2.00, board 2.06 → exactly 3% → hard reject (>= thr)
    pack = _strong_pack(odds_at_research=2.0, decimal_odds_ref=2.0)
    ok, reason = placeable_odds_snapshot(pack, 2.06, _cfg())
    assert ok is False
    assert reason == "stale_odds_drift"

    picked, rejects = build_portfolio(
        _cfg(), [_cand(2.06, pack)], _phase(), _risk(), []
    )
    assert picked == []
    assert any(r.get("reason") == "stale_odds_drift" for r in rejects)


def test_t6_dual_write_present_drift_ok_placeable():
    pack = _strong_pack(p_model=0.62, odds_at_research=2.0, decimal_odds_ref=2.0)
    # board 2.05 → drift 2.5% < 3%
    ok, reason = placeable_odds_snapshot(pack, 2.05, _cfg())
    assert ok is True
    assert reason == ""

    picked, rejects = build_portfolio(
        _cfg(), [_cand(2.05, pack)], _phase(), _risk(), []
    )
    assert len(picked) == 1
    assert picked[0].stake_nok >= 10
    assert not any(
        r.get("reason") in ("missing_odds_snapshot", "stale_odds_drift", "odds_snapshot_inferred")
        for r in rejects
    )


def test_never_stamps_board_odds_into_snapshot_for_place():
    """Missing snapshot + board odds present still rejects — no same-step stamp."""
    pack = _strong_pack(odds_at_research=None, decimal_odds_ref=None)
    pack.pop("odds_at_research", None)
    pack.pop("decimal_odds_ref", None)
    board = 1.95
    ok, reason = placeable_odds_snapshot(pack, board, _cfg())
    assert ok is False
    assert reason == "missing_odds_snapshot"
    # helper must not mutate pack with board odds
    assert pack_odds_snapshot(pack) is None


# --- dual-write write path ---


def test_scaffold_dual_write_odds(tmp_path: Path):
    cfg = {
        "paths": {"evidence": str(tmp_path / "evidence")},
    }
    res = scaffold_evidence(
        cfg,
        match="A vs B",
        selection="Over 2.5",
        p_model=None,
        odds=1.90,
        write=True,
        overwrite=True,
    )
    assert res["ok"]
    pack = res["pack"]
    assert pack["decimal_odds_ref"] == 1.90
    assert pack["odds_at_research"] == 1.90
    assert pack.get("researched_at")
    data = json.loads(Path(res["path"]).read_text(encoding="utf-8"))
    assert data["odds_at_research"] == 1.90
    assert data["decimal_odds_ref"] == 1.90


def test_write_research_pack_dual_write(tmp_path: Path):
    cfg = {"paths": {"evidence": str(tmp_path / "evidence")}}
    res = write_research_pack(
        cfg,
        match="A vs B",
        selection="BTTS Nei",
        p_model=0.58,
        sport="football",
        odds=1.85,
        summary="Low scoring domestic script with confirmed injuries noted.",
        failure_modes="late equalizer",
        availability_notes="No key attackers out; full back line expected.",
    )
    assert res["ok"]
    data = json.loads(Path(res["path"]).read_text(encoding="utf-8"))
    assert data["decimal_odds_ref"] == 1.85
    assert data["odds_at_research"] == 1.85
    assert data.get("researched_at")


def test_apply_odds_snapshot_fields_clears_inferred():
    pack: dict = {"odds_snapshot_inferred": True}
    apply_odds_snapshot_fields(pack, 2.0, stamp_researched_at=True)
    assert pack["odds_at_research"] == 2.0
    assert pack["decimal_odds_ref"] == 2.0
    assert pack["odds_snapshot_inferred"] is False
    assert pack.get("researched_at")


# --- T7 newest soft-key wins ---


def test_t7_newest_soft_key_wins(tmp_path: Path):
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    match = "Burruchaga, Roman Andres vs Merida, Daniel"
    # Older pack: Vinner form, lower p_model
    old = {
        "match": match,
        "selection": "Vinner: Merida, Daniel",
        "sport": "tennis",
        "p_model": 0.55,
        "summary": "old pack",
        "failure_modes": "upset",
        "sources": [{"url": "https://example.com/old", "takeaway": "old"}],
        "odds_at_research": 1.55,
        "decimal_odds_ref": 1.55,
        "researched_at": "2026-07-01T10:00:00Z",
    }
    # Newer pack: to-win form, higher p_model — same soft key
    new = {
        "match": match,
        "selection": "Merida, Daniel to Win",
        "sport": "tennis",
        "p_model": 0.71,
        "summary": "new pack",
        "failure_modes": "upset",
        "sources": [{"url": "https://example.com/new", "takeaway": "new"}],
        "odds_at_research": 1.55,
        "decimal_odds_ref": 1.55,
        "researched_at": "2026-07-20T18:00:00Z",
    }
    (ev_dir / "merida_old.json").write_text(
        json.dumps(old, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ev_dir / "merida_new.json").write_text(
        json.dumps(new, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # Ensure mtimes don't invert researched_at preference (researched_at is SSOT)
    now = time.time()
    os.utime(ev_dir / "merida_old.json", (now - 1000, now - 1000))
    os.utime(ev_dir / "merida_new.json", (now - 10, now - 10))

    c = Candidate(
        date="2026-07-20",
        match=match,
        selection="Merida, Daniel to Win",
        decimal_odds=1.55,
        sport="tennis",
    )
    attach_evidence([c], ev_dir)
    assert c.evidence is not None
    assert c.p_model == pytest.approx(0.71)
    assert c.evidence.get("board_odds_at_attach") == pytest.approx(1.55)
    # Must not invent snapshot from board when present; here pack has snapshot
    assert pack_odds_snapshot(c.evidence) == pytest.approx(1.55)


def test_attach_diagnostics_missing_snapshot_no_stamp(tmp_path: Path):
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    pack = {
        "match": "X vs Y",
        "selection": "X ML",
        "p_model": 0.60,
        "summary": "no odds fields",
        "failure_modes": "x",
        "sources": [{"url": "https://example.com", "takeaway": "a"}],
    }
    (ev_dir / "x.json").write_text(json.dumps(pack) + "\n", encoding="utf-8")
    c = Candidate(
        date="2026-07-22",
        match="X vs Y",
        selection="X ML",
        decimal_odds=1.80,
        sport="football",
    )
    attach_evidence([c], ev_dir)
    assert c.evidence is not None
    assert c.evidence.get("odds_snapshot_missing") is True
    assert c.evidence.get("board_odds_at_attach") == pytest.approx(1.80)
    # Never stamp board into placeable fields
    assert "odds_at_research" not in c.evidence or c.evidence.get("odds_at_research") is None
    assert pack_odds_snapshot(c.evidence) is None
    ok, reason = placeable_odds_snapshot(c.evidence, 1.80, _cfg())
    assert ok is False
    assert reason == "missing_odds_snapshot"
