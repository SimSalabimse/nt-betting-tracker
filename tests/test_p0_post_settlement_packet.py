"""P0 PostSettlementPacket validation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.post_settlement_packet import (
    is_strict_packet_required,
    validate_settle_item,
)


def test_non_strict_allows_empty():
    ok, errs, _ = validate_settle_item(
        {"bet_id": "b1", "variance_tag": "expected", "score": ""}
    )
    assert ok
    assert not errs
    assert not is_strict_packet_required({"variance_tag": "expected"})


def test_strict_process_error_requires_fields():
    assert is_strict_packet_required({"variance_tag": "process_error"})
    ok, errs, _ = validate_settle_item(
        {"bet_id": "b1", "variance_tag": "process_error", "score": "2-1"}
    )
    assert not ok
    assert any("lineup" in e for e in errs)
    assert any("root" in e for e in errs)


def test_strict_complete_ok():
    ok, errs, pkt = validate_settle_item(
        {
            "bet_id": "b1",
            "variance_tag": "process_error",
            "actual_score": "1-0",
            "actual_lineup_status": "confirmed",
            "predicted_vs_actual_xi_delta": "key striker started as predicted",
            "script_realized": "conflict",
            "process_root_cause": "script",
        }
    )
    assert ok, errs
    assert pkt["actual_score"] == "1-0"


def test_poor_retro_strict():
    assert is_strict_packet_required({"research_quality_retro": "poor"})
    ok, errs, _ = validate_settle_item(
        {
            "bet_id": "b2",
            "research_quality_retro": "poor",
            "score": "",
            "actual_lineup_status": "n/a",
            "predicted_vs_actual_xi_delta": "n/a",
            "script_realized": "n/a",
            "process_root_cause": "info",
        }
    )
    assert not ok
    assert any("actual_score" in e for e in errs)
