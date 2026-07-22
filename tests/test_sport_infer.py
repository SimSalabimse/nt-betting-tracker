"""Sport inference: collector multi-signal + odds_parse darts/snooker fix."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_parse import _infer_sport, parse_odds_file


def test_infer_sport_respects_sport_tag_darts():
    chunk = [
        "Vinner",
        "Rock, Josh",
        "1.70",
        "Woodhouse, Luke",
        "2.05",
        "Sport: Darts",
        "Kick-off: 2026-07-18 20:00",
        "Event: Rock, Josh - Woodhouse, Luke",
    ]
    assert _infer_sport("Rock, Josh", "Woodhouse, Luke", chunk) == "darts"


def test_infer_sport_darts_from_180s_not_snooker():
    """Comma names alone used to force snooker — 180s markets must win."""
    chunk = [
        "Vinner",
        "Rock, Josh",
        "1.70",
        "Woodhouse, Luke",
        "2.05",
        "Legs handikap -2.5",
        "Rock, Josh -2.5",
        "2.10",
        "Totalt antall 180s 10.5",
        "Over 10.5",
        "1.95",
        "Utsjekk",
        "Nei",
        "1.10",
    ]
    assert _infer_sport("Rock, Josh", "Woodhouse, Luke", chunk) == "darts"


def test_infer_sport_snooker_frame_cues():
    chunk = [
        "Vinner",
        "Fu, Marco",
        "1.80",
        "OSullivan, Ronnie",
        "1.90",
        "Frame handikap -2.5",
        "Fu, Marco -2.5",
        "1.95",
        "Totalt antall frames 17.5",
        "Over 17.5",
        "1.85",
    ]
    assert _infer_sport("Fu, Marco", "OSullivan, Ronnie", chunk) == "snooker"


def test_infer_sport_comma_names_without_cues_are_unknown():
    """Phase 3: comma 'Last, First' alone must not force snooker (darts share format)."""
    chunk = ["Vinner", "Fu, Marco", "1.80", "Trump, Judd", "1.90"]
    assert _infer_sport("Fu, Marco", "Trump, Judd", chunk) == "unknown"


def test_infer_sport_football_straffer_not_basketball():
    """WC 'ekstraomg./straffer' must not map to basketball (bare 'straffer' trap)."""
    chunk = [
        "HUB",
        "Spania",
        "1.38",
        "Uavgjort",
        "2.10",
        "Argentina",
        "2.80",
        "Sammenlagtvinner inkl. ekstraomg./straffer",
        "Spania",
        "1.38",
        "Argentina",
        "2.80",
        "Ekstraomganger: 1. mål",
        "Spania",
        "1.82",
        "Begge lag scorer",
        "Nei",
        "1.04",
    ]
    assert _infer_sport("Spania", "Argentina", chunk) == "football"


def test_infer_sport_basketball_inkludert_overtid():
    """OT board → canonical basketball (not nba subtype)."""
    chunk = [
        "Vinner (inkludert overtid/straffer)",
        "Memphis Grizzlies",
        "1.45",
        "Golden State Warriors",
        "2.35",
    ]
    assert _infer_sport("Memphis Grizzlies", "Golden State Warriors", chunk) == "basketball"


def test_normalize_sport_aliases():
    from nt.sport_taxonomy import normalize_sport

    assert normalize_sport("Darts") == "darts"
    assert normalize_sport("nba") == "basketball"
    assert normalize_sport("WNBA") == "basketball"
    assert normalize_sport("LoL") == "esports"
    assert normalize_sport("Counter-Strike") == "esports"
    assert normalize_sport("Fotball") == "football"
    assert normalize_sport("ishockey") == "ice_hockey"
    assert normalize_sport(None) == "unknown"
    assert normalize_sport("Football Rating 8") == "football"


def test_parse_darts_block_from_fixture(tmp_path: Path):
    dump = """Vinner
Rock, Josh
1.70
Woodhouse, Luke
2.05
Sport: Darts
Kick-off: 2026-07-18 20:00
Event: Rock, Josh - Woodhouse, Luke
Legs handikap -2.5
Rock, Josh -2.5
2.10
Totalt antall 180s 10.5
Over 10.5
1.95



Vinner
Fu, Marco
1.80
Trump, Judd
1.95
Sport: Snooker
Kick-off: 2026-07-18 21:00
Event: Fu, Marco - Trump, Judd
Frame handikap -2.5
Fu, Marco -2.5
1.90
"""
    p = tmp_path / "darts_snooker.txt"
    p.write_text(dump, encoding="utf-8")
    rows = parse_odds_file(p)
    assert rows
    sports = {c.match: c.sport for c in rows}
    assert any(s == "darts" for s in sports.values())
    rock = [c for c in rows if "Rock" in c.match]
    assert rock
    assert all(c.sport == "darts" for c in rock)


def test_collector_resolve_sport_darts_keywords():
    # Import collector module without running main.
    # artifacts/ is gitignored — collector may be absent on CI clones.
    import importlib.util

    collector_path = ROOT / "artifacts" / "multi_sport_collector.py"
    if not collector_path.is_file():
        pytest.skip(
            "artifacts/multi_sport_collector.py not present "
            "(gitignored operational tool; local/desk copies only)"
        )

    spec = importlib.util.spec_from_file_location(
        "multi_sport_collector",
        collector_path,
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Avoid executing side effects that need network: module sets NOW at import — OK
    spec.loader.exec_module(mod)

    ev = {
        "name": "Rock, Josh - Woodhouse, Luke",
        "participantname_home": "Rock, Josh",
        "participantname_away": "Woodhouse, Luke",
        "idfosporttype": "DAR",
        "sporttypename": "Darts",
        "tournamentname": "World Matchplay",
    }
    markets = [
        {"name": "Vinner", "selections": []},
        {"name": "Legs handikap -2.5", "selections": []},
        {"name": "Totalt antall 180s 10.5", "selections": []},
        {"name": "Utsjekk", "selections": []},
    ]
    info = mod.resolve_sport(ev, markets=markets, nav_sport="Darts")
    assert info["sport"] == "Darts"
    assert info["sport_confidence"] in ("high", "medium")

    # Even without DAR code, market keywords must win over snooker-ish names
    ev2 = {**ev, "idfosporttype": "", "sporttypename": ""}
    info2 = mod.resolve_sport(ev2, markets=markets, nav_sport=None)
    assert info2["sport"] == "Darts"
    assert info2["sport_source"] == "market_keyword"
