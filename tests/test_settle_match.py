"""P0: _match_bet never silently picks pending[0] on ambiguity."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.settle import _match_bet, _match_fail_reason


def _row(
    bet_id: str,
    match: str,
    selection: str,
    *,
    result: str = "Pending",
) -> dict[str, str]:
    return {
        "bet_id": bet_id,
        "match": match,
        "selection": selection,
        "result": result,
        "stake_nok": "10",
        "decimal_odds": "1.80",
    }


def test_match_by_bet_id():
    rows = [
        _row("a1", "Alice vs Bob", "Alice to Win"),
        _row("a2", "Alice vs Bob", "Over 2.5"),
    ]
    hit = _match_bet(rows, {"bet_id": "a2", "outcome": "win"})
    assert hit is not None
    assert hit["bet_id"] == "a2"


def test_unique_selection_match():
    rows = [
        _row("a1", "Alice vs Bob", "Alice to Win"),
        _row("a2", "Alice vs Bob", "Over 2.5"),
    ]
    hit = _match_bet(
        rows,
        {"match": "Alice vs Bob", "selection": "over 2.5", "outcome": "loss"},
    )
    assert hit is not None
    assert hit["bet_id"] == "a2"


def test_ambiguous_pending_returns_none_not_first():
    rows = [
        _row("a1", "Clayton vs Anderson", "Over 18.5"),
        _row("a2", "Clayton vs Anderson", "Under 18.5"),
    ]
    hit = _match_bet(
        rows,
        {"match": "Clayton vs Anderson", "outcome": "win"},
    )
    assert hit is None
    reason = _match_fail_reason(rows, {"match": "Clayton vs Anderson", "outcome": "win"})
    assert "ambiguous" in reason.lower()
    assert "bet_id" in reason.lower()


def test_no_match_reason():
    rows = [_row("a1", "Foo vs Bar", "Foo to Win")]
    hit = _match_bet(rows, {"match": "Zzz vs Qqq", "selection": "win", "outcome": "loss"})
    assert hit is None
    reason = _match_fail_reason(
        rows, {"match": "Zzz vs Qqq", "selection": "win", "outcome": "loss"}
    )
    assert "no matching" in reason.lower()
