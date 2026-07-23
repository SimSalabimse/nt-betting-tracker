"""PR-1: predictability / variance taxonomy + learning_weight."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.post_settlement_packet import build_packet_from_item, validate_settle_item
from nt.settlement_taxonomy import (
    auto_classify_taxonomy,
    compute_learning_weight,
    is_process_error_class,
    map_legacy_labels,
    normalize_variance_class,
)


def test_compute_learning_weight_formula():
    # systematic × highly = 1.0
    assert compute_learning_weight("highly_predictable", "systematic_script_form") == 1.0
    # research_process_miss × moderately = 0.95 * 0.75 = 0.7125
    assert compute_learning_weight(
        "moderately_predictable", "research_process_miss"
    ) == pytest.approx(0.7125)
    # true_randomness × unpredictable = 0.05 * 0.20 = 0.01
    assert compute_learning_weight(
        "unpredictable_from_available_info", "true_randomness"
    ) == pytest.approx(0.01)
    # unknown × weakly = 0.40 * 0.45 = 0.18
    assert compute_learning_weight(
        "weakly_predictable", "unknown"
    ) == pytest.approx(0.18)
    # one_off × highly still tiny
    assert compute_learning_weight(
        "highly_predictable", "one_off_injury_late"
    ) == pytest.approx(0.10)
    # clamp
    assert 0.0 <= compute_learning_weight(None, None) <= 1.0


def test_legacy_map_process_error():
    m = map_legacy_labels(variance_tag="process_error", research_quality_retro="poor")
    assert m["variance_class"] == "research_process_miss"
    assert m["predictability"] in (
        "moderately_predictable",
        "highly_predictable",
    )
    assert normalize_variance_class("research_miss") == "research_process_miss"
    assert normalize_variance_class("expected") == "systematic_script_form"
    assert normalize_variance_class("variance") == "true_randomness"
    assert is_process_error_class("process_error")
    assert is_process_error_class("research_process_miss")
    assert not is_process_error_class("true_randomness")


def test_auto_classify_injury_notes():
    tax = auto_classify_taxonomy(
        {"notes": "late injury to star striker in warm-up"},
        classified_by="backfill",
    )
    assert tax["variance_class"] == "one_off_injury_late"
    assert tax["learning_weight"] <= 0.10
    assert tax["classified_by"] == "backfill"


def test_auto_classify_poor_process():
    tax = auto_classify_taxonomy(
        {
            "variance_tag": "process_error",
            "research_quality_retro": "poor",
            "notes": "missed rotation signal",
        },
        classified_by="agent",
    )
    assert tax["variance_class"] == "research_process_miss"
    assert tax["predictability"] == "moderately_predictable"
    assert tax["learning_weight"] == pytest.approx(0.7125)
    assert tax["learning_weight"] >= 0.5  # should allow temp_gate


def test_auto_classify_default_unknown_weak():
    tax = auto_classify_taxonomy({"notes": "settled ok"}, classified_by="auto")
    assert tax["variance_class"] == "unknown"
    assert tax["predictability"] == "weakly_predictable"
    assert tax["learning_weight"] == pytest.approx(0.18)


def test_packet_soft_fills_taxonomy():
    ok, errs, pkt = validate_settle_item(
        {"bet_id": "t1", "variance_tag": "expected", "score": "1-0"}
    )
    assert ok
    assert not errs
    assert pkt["predictability"] in (
        "highly_predictable",
        "moderately_predictable",
        "weakly_predictable",
        "unpredictable_from_available_info",
    )
    assert pkt["variance_class"]
    assert 0.0 <= float(pkt["learning_weight"]) <= 1.0
    assert "pred:" in __import__(
        "nt.post_settlement_packet", fromlist=["packet_to_notes_blob"]
    ).packet_to_notes_blob(pkt) or pkt.get("predictability")


def test_packet_explicit_taxonomy_respected():
    pkt = build_packet_from_item(
        {
            "bet_id": "t2",
            "variance_tag": "expected",
            "predictability": "unpredictable_from_available_info",
            "variance_class": "one_off_referee",
            "classified_by": "agent",
            "classification_notes": "soft pen gift 89'",
        }
    )
    assert pkt["variance_class"] == "one_off_referee"
    assert pkt["predictability"] == "unpredictable_from_available_info"
    assert pkt["learning_weight"] == pytest.approx(0.02)  # 0.10 * 0.20
    assert pkt["classified_by"] == "agent"


def test_control_signal_skips_low_weight(tmp_path: Path):
    """process_error with low learning_weight must not emit temp_gate_raise."""
    from nt.settlement_review import analyze_settled_batch

    state = tmp_path / "state"
    state.mkdir()
    bets = tmp_path / "bets.csv"
    # Minimal bets header + one settled loss
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,source,notes,created_at,updated_at\n"
        "loww1,2026-07-20,Late Injury FC vs Other,Home Win,1.90,10,Loss,-10,0,"
        "B,1.8-2.2,football,HUB,1A,recommend,"
        "late injury star out warm-up,2026-07-20T10:00:00Z,2026-07-20T12:00:00Z\n",
        encoding="utf-8",
    )
    (state / "settlement_reviews.jsonl").write_text("", encoding="utf-8")
    (state / "control_signals.jsonl").write_text("", encoding="utf-8")
    cfg = {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "settlement_reviews_jsonl": str(state / "settlement_reviews.jsonl"),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
            "learning_json": str(state / "learning.json"),
            "learning_proposals_json": str(state / "learning_proposals.json"),
            "outbox": str(tmp_path / "outbox"),
        },
        "learning": {
            "enabled": True,
            "auto_apply_proposals": False,
            "min_learning_weight_for_gate": 0.5,
            "control_signals": {
                "enabled": True,
                "min_learning_weight_for_gate": 0.5,
                "ttl_days": 10,
                "min_ev_raise": 0.02,
                "max_raise": 0.05,
            },
        },
    }
    items = [
        {
            "bet_id": "loww1",
            "result": "Loss",
            "variance_tag": "process_error",
            "research_quality_retro": "poor",
            "notes": "late injury star out warm-up",
            "predictability": "unpredictable_from_available_info",
            "variance_class": "one_off_injury_late",
            "classified_by": "agent",
        }
    ]
    rep = analyze_settled_batch(cfg, items)
    assert rep["reviews"]
    rev = rep["reviews"][0]
    assert rev["variance_class"] == "one_off_injury_late"
    assert float(rev["learning_weight"]) < 0.5
    # Gate emit skipped
    cs = rep.get("control_signals") or []
    assert any(e.get("skipped") for e in cs), cs
    # No active temp_gate in file from this emit
    cs_path = state / "control_signals.jsonl"
    body = cs_path.read_text(encoding="utf-8") if cs_path.is_file() else ""
    assert "temp_gate_raise" not in body or "one_off" in body  # no raise line expected
    assert "temp_gate_raise" not in body


def test_control_signal_emits_high_weight_process(tmp_path: Path):
    from nt.settlement_review import analyze_settled_batch

    state = tmp_path / "state"
    state.mkdir()
    bets = tmp_path / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,source,notes,created_at,updated_at\n"
        "hiw1,2026-07-20,Miss FC vs Other,Under 2.5,2.10,10,Loss,-10,0,"
        "B,1.8-2.2,football,HUB,1A,recommend,"
        "process miss rotation,2026-07-20T10:00:00Z,2026-07-20T12:00:00Z\n",
        encoding="utf-8",
    )
    (state / "settlement_reviews.jsonl").write_text("", encoding="utf-8")
    (state / "control_signals.jsonl").write_text("", encoding="utf-8")
    cfg = {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "settlement_reviews_jsonl": str(state / "settlement_reviews.jsonl"),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
            "learning_json": str(state / "learning.json"),
            "learning_proposals_json": str(state / "learning_proposals.json"),
            "outbox": str(tmp_path / "outbox"),
        },
        "learning": {
            "enabled": True,
            "auto_apply_proposals": False,
            "min_learning_weight_for_gate": 0.5,
            "control_signals": {
                "enabled": True,
                "min_learning_weight_for_gate": 0.5,
                "ttl_days": 10,
                "min_ev_raise": 0.02,
                "max_raise": 0.05,
                "force_confirmed_lineup": True,
            },
        },
    }
    items = [
        {
            "bet_id": "hiw1",
            "result": "Loss",
            "variance_tag": "process_error",
            "research_quality_retro": "poor",
            "notes": "missed rotation under",
            "predictability": "moderately_predictable",
            "variance_class": "research_process_miss",
            "classified_by": "agent",
            "process_root_cause": "script",
            "actual_score": "3-1",
            "actual_lineup_status": "confirmed",
            "predicted_vs_actual_xi_delta": "rotated midfield",
            "script_realized": "conflict",
        }
    ]
    rep = analyze_settled_batch(cfg, items)
    rev = rep["reviews"][0]
    assert rev["variance_class"] == "research_process_miss"
    assert float(rev["learning_weight"]) >= 0.5
    cs = rep.get("control_signals") or []
    assert any(not e.get("skipped") and e.get("ok") is not False for e in cs), cs
    body = (state / "control_signals.jsonl").read_text(encoding="utf-8")
    assert "temp_gate_raise" in body


def test_learning_weight_multiplies_sample(tmp_path: Path):
    """One-off loss should not tank sport mult as hard as full-weight loss."""
    from nt.learning import compute_learning

    state = tmp_path / "state"
    state.mkdir()
    # Two football losses + several wins so min_sample can move mults with weight
    header = (
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,source,notes,created_at,updated_at\n"
    )
    lines = [header]
    # 15 football wins
    for i in range(15):
        lines.append(
            f"w{i},2026-07-01,Win Match {i},Home,1.90,10,Win,9,19,"
            f"B,1.8-2.2,football,HUB,1A,recommend,,2026-07-01T10:00:00Z,2026-07-01T12:00:00Z\n"
        )
    # one huge process loss
    lines.append(
        "loss_full,2026-07-15,Process Miss,Under 2.5,2.00,50,Loss,-50,0,"
        "B,1.8-2.2,football,HUB,1A,recommend,,2026-07-15T10:00:00Z,2026-07-15T12:00:00Z\n"
    )
    bets = tmp_path / "bets.csv"
    bets.write_text("".join(lines), encoding="utf-8")

    # Reviews: full weight process miss
    rev_full = state / "reviews_full.jsonl"
    rev_full.write_text(
        json.dumps(
            {
                "bet_id": "loss_full",
                "variance_class": "research_process_miss",
                "predictability": "highly_predictable",
                "learning_weight": 0.95,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cfg_full = {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "settlement_reviews_jsonl": str(rev_full),
        },
        "learning": {
            "enabled": True,
            "min_sample": 8,
            "weight_mode": "equal",  # isolate taxonomy multiplier
            "half_life_days": 0,
        },
    }
    # Reviews: one-off near-zero weight
    rev_one = state / "reviews_one.jsonl"
    rev_one.write_text(
        json.dumps(
            {
                "bet_id": "loss_full",
                "variance_class": "one_off_injury_late",
                "predictability": "unpredictable_from_available_info",
                "learning_weight": 0.02,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cfg_one = {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "settlement_reviews_jsonl": str(rev_one),
        },
        "learning": {
            "enabled": True,
            "min_sample": 8,
            "weight_mode": "equal",
            "half_life_days": 0,
        },
    }
    from nt.bets_io import load_bets

    rows = load_bets(bets)
    full = compute_learning(rows, cfg_full)
    one = compute_learning(rows, cfg_one)
    roi_full = float((full.get("sports") or {}).get("football", {}).get("roi_blended") or 0)
    roi_one = float((one.get("sports") or {}).get("football", {}).get("roi_blended") or 0)
    # With tiny weight on the -50 loss, ROI should be better (less negative influence)
    assert roi_one > roi_full
