"""P1 soft correlation helpers + portfolio caps."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.portfolio_correlation import (
    count_ko_window,
    league_key,
    parse_kickoff_hour,
    script_family,
)


def test_league_key_from_evidence():
    assert league_key(evidence={"competition": "Eliteserien"}) == "eliteserien"
    assert league_key(match="Foo vs Bar") == "unknown"


def test_league_key_from_blob():
    assert "premier" in league_key(match="Arsenal vs Chelsea Premier League")


def test_script_family_btts_under():
    assert script_family(selection="BTTS Nei", market_type="") == "btts_no"
    assert script_family(selection="Totalt antall mål - Over Under 2.5: Under 2.5") == "totals_under"


def test_ko_window_counts():
    h0 = parse_kickoff_hour("2026-07-21 19:00")
    h1 = parse_kickoff_hour("2026-07-21 20:00")
    h2 = parse_kickoff_hour("2026-07-21 23:00")
    assert h0 is not None and h1 is not None
    assert count_ko_window(h0, [h1, h2], window_hours=3) == 1
    assert count_ko_window(h0, [h1, h2], window_hours=5) >= 1
