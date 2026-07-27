"""Light unit tests for nt.market_family (PR0 dep; no portfolio wiring)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.market_family import market_family
from nt.live_ledger import assert_not_archive_path, filter_live_rows


def test_tennis_totals_share_family_across_lines() -> None:
    assert (
        market_family(sport="tennis", selection="Totalt antall games 22.5: Over 22.5")
        == "tennis_totals"
    )
    assert (
        market_family(sport="tennis", selection="Totalt antall games 21.5: Under 21.5")
        == "tennis_totals"
    )


def test_football_totals_and_btts() -> None:
    assert (
        market_family(
            sport="football",
            selection="Totalt antall mål - over/under 2.5: Over 2.5",
        )
        == "football_totals"
    )
    assert (
        market_family(sport="football", selection="Begge lag scorer: Ja")
        == "football_btts"
    )


def test_ml_and_empty() -> None:
    assert market_family(sport="tennis", selection="Vinner: Sinner") == "tennis_ml"
    assert market_family() == "other"


def test_live_ledger_filter_and_archive_guard() -> None:
    rows = [
        {"source": "era_archive", "id": "a"},
        {"source": "live", "id": "b"},
        {"id": "c"},
    ]
    out = filter_live_rows(rows)
    assert [r["id"] for r in out] == ["b", "c"]
    assert filter_live_rows([]) == []
    assert_not_archive_path("data/bets.csv")
    try:
        assert_not_archive_path("history/archives/foo.csv")
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
