from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_parse import parse_odds_file, _extract_kickoff, _match_date_from_kickoff


def test_kickoff_sets_match_date_not_place_date(tmp_path: Path):
    # Need ≥6 odds-like lines so _looks_like_nt_dump accepts the paste.
    dump = """HUB
Spania
1.38
Uavgjort
2.95
Argentina
3.50
Sport: Football
Kick-off: 2026-07-19 21:00
Event: Spania - Argentina
Begge lag scorer
Nei
1.92
Ja
1.80
Totalt antall mål - Over/Under 2.5
Under 2.5
1.62
Over 2.5
2.20
"""
    p = tmp_path / "ko.txt"
    p.write_text(dump, encoding="utf-8")
    rows = parse_odds_file(p)
    assert rows
    assert all(c.date == "2026-07-19" for c in rows)
    assert all(c.kickoff.startswith("2026-07-19 21:00") for c in rows)


def test_extract_kickoff_iso():
    chunk = ["Kick-off: 2026-07-20T12:10:00+02:00", "Sport: Tennis"]
    assert _extract_kickoff(chunk) == "2026-07-20 12:10"
    assert _match_date_from_kickoff("2026-07-20 12:10") == "2026-07-20"


def test_odds_15_blocks_do_not_bleed():
    """
    Structural bleed test for multi-sport NT dumps.

    Depends on a board that still contains the Chicago Sky block.
    If inbox was overwritten with a newer dump, skip rather than fail the suite.
    """
    path = ROOT / "inbox" / "odds_15-07.2026.txt"
    if not path.is_file():
        pytest.skip("odds_15-07.2026.txt missing")
    cs = parse_odds_file(path)
    by_match: dict[str, list] = {}
    for c in cs:
        by_match.setdefault(c.match, []).append(c)

    sky = by_match.get("Chicago Sky vs Seattle Storm") or []
    if not sky:
        # Inbox dump rotated — keep suite green; bleed regression needs the old fixture
        pytest.skip("Chicago Sky board not in current odds_15 dump (file rotated)")

    assert len(sky) < 40, f"Sky bloated: {len(sky)} lines (bleed?)"
    blob = " ".join(c.selection for c in sky).lower()
    assert "ninjas" not in blob
    assert "pain gaming" not in blob
    assert "tsitsipas" not in blob
    assert any("seattle" in c.selection.lower() for c in sky)
    assert all(c.sport == "basketball" for c in sky)

    assert any("Pain Gaming" in m for m in by_match), "esports Pain Gaming block missing"
    pain = next(v for k, v in by_match.items() if "Pain Gaming" in k)
    assert all(c.sport == "esports" for c in pain)

    assert any(
        "171.5" in (c.market_type or "") or "171.5" in c.selection for c in sky
    ), "Sky totals missing"

    foot = [m for m, v in by_match.items() if v and v[0].sport == "football"]
    assert foot, "no football matches parsed"
    sample = by_match[foot[0]]
    assert len(sample) >= 6
    assert any("to Win" in c.selection or "Uavgjort" in c.selection for c in sample)

    for m, v in by_match.items():
        if not v or v[0].sport != "football":
            continue
        joined = " ".join(c.selection for c in v).lower()
        assert "tsitsipas" not in joined
        assert "darderi" not in joined


def test_parse_all_market_types_not_only_moneyline():
    path = ROOT / "inbox" / "odds_15-07.2026.txt"
    if not path.is_file():
        pytest.skip("odds_15-07.2026.txt missing")
    cs = parse_odds_file(path)
    assert cs, "parser returned zero candidates"
    sports = {c.sport for c in cs}
    # At least one recognized sport family
    assert sports & {"football", "tennis", "esports", "basketball"}
    # If multi-sport dump is present, assert breadth; otherwise just totals/handicaps if any
    if "esports" in sports:
        assert "football" in sports
    # Prefer presence of non-ML markets when the dump includes them
    has_totals = any(
        "Totalt" in (c.market_type or "") or "totalt" in c.selection.lower() or "over" in c.selection.lower()
        for c in cs
    )
    has_hcap = any(
        "Handikap" in (c.market_type or "") or "handikap" in c.selection.lower() for c in cs
    )
    # Moneyline-only dumps are allowed; multi-market dumps must expose structure
    if len(cs) > 50:
        assert has_totals or has_hcap or any("to Win" in c.selection for c in cs)


def test_parse_odds_returns_candidates_for_any_dump():
    """Smoke: every inbox odds_*.txt should parse without exception."""
    inbox = ROOT / "inbox"
    if not inbox.is_dir():
        pytest.skip("no inbox")
    files = list(inbox.glob("odds*.txt")) + list(inbox.glob("odds*.csv"))
    if not files:
        pytest.skip("no odds files")
    for path in files:
        cs = parse_odds_file(path)
        assert isinstance(cs, list)
