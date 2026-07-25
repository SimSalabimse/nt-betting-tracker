"""Live-ledger isolation: filter era_archive + refuse archive paths."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.live_ledger import (
    ARCHIVE_PATH_MARKERS,
    assert_not_archive_path,
    filter_live_rows,
)


def test_archive_path_markers():
    assert "history/archives" in ARCHIVE_PATH_MARKERS
    assert "history/rounds" in ARCHIVE_PATH_MARKERS


def test_filter_live_rows_drops_era_archive():
    rows = [
        {"match": "A", "source": "live", "result": "Pending"},
        {"match": "B", "source": "era_archive", "result": "Pending"},
        {"match": "C", "source": "ERA_ARCHIVE", "result": "Win"},
        {"match": "D", "result": "Pending"},  # no source → live
    ]
    out = filter_live_rows(rows)
    assert [r["match"] for r in out] == ["A", "D"]


def test_filter_live_rows_empty():
    assert filter_live_rows(None) == []
    assert filter_live_rows([]) == []


def test_assert_not_archive_path_ok():
    assert_not_archive_path("data/bets.csv")
    assert_not_archive_path(ROOT / "data" / "bets.csv")


@pytest.mark.parametrize(
    "bad",
    [
        "history/archives/bets_old.csv",
        r"C:\repo\history\archives\x.csv",
        "history/rounds/round_001.md",
        "foo/history/rounds/bar",
    ],
)
def test_assert_not_archive_path_refuses(bad: str):
    with pytest.raises(RuntimeError, match="archive"):
        assert_not_archive_path(bad)


def test_load_bets_refuses_archive_path(tmp_path: Path):
    """Production load_bets wires assert_not_archive_path (Issue 4)."""
    from nt.bets_io import load_bets

    # Nested under a synthetic history/archives path segment
    arch = tmp_path / "history" / "archives" / "bets_old.csv"
    arch.parent.mkdir(parents=True, exist_ok=True)
    arch.write_text("bet_id,date,match,selection,decimal_odds,stake_nok,result\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="archive"):
        load_bets(arch)
