"""Smoke tests for multi-sport fetchers (offline market mapping + registry)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.fetchers import list_fetchers, evaluate_selection_from_score
from nt.fetchers.base import MatchResult
from nt.fetchers.markets import (
    evaluate_basketball_selection,
    evaluate_tennis_selection,
)
from nt.fetchers.registry import get_fetcher, resolve_fetcher


def test_registry() -> None:
    names = {f["name"] for f in list_fetchers()}
    assert "football" in names
    assert "tennis" in names
    assert "basketball" in names
    assert get_fetcher("tennis").name == "tennis"
    assert resolve_fetcher({"sport": "darts"}).name == "darts"
    assert resolve_fetcher({"sport": "football"}).name == "football"
    print("registry OK", sorted(names))


def test_football_markets() -> None:
    assert evaluate_selection_from_score("Over 2.5", "H", "A", 2, 1)["outcome"] == "win"
    assert evaluate_selection_from_score("Under 2.5", "H", "A", 1, 0)["outcome"] == "win"
    r = evaluate_selection_from_score(
        "Handikap 3-veis 0:1: Viking -1", "Viking", "Sandefjord", 2, 0
    )
    assert r["outcome"] == "win"
    print("football markets OK")


def test_tennis_markets() -> None:
    mr = MatchResult(
        home="Aspinall, Nathan",
        away="Cullen, Joe",
        home_score=2,
        away_score=0,
        score_text="2-0",
        finished=True,
        match_confidence=0.9,
        source="test",
    )
    v = evaluate_tennis_selection("Vinner: Aspinall, Nathan", mr)
    assert v.outcome == "win"
    v2 = evaluate_tennis_selection("Totalt antall sett: Over 2.5", mr)
    assert v2.outcome == "loss"  # 2 sets total
    print("tennis markets OK", v.reason)


def test_basketball_markets() -> None:
    mr = MatchResult(
        home="Boston Celtics",
        away="Orlando Magic",
        home_score=110,
        away_score=98,
        finished=True,
        match_confidence=0.9,
        source="test",
    )
    v = evaluate_basketball_selection("Vinner: Boston Celtics", mr)
    assert v.outcome == "win"
    v2 = evaluate_basketball_selection("Totalt antall poeng: Over 200.5", mr)
    assert v2.outcome == "win"  # 208
    print("basketball markets OK")


if __name__ == "__main__":
    test_registry()
    test_football_markets()
    test_tennis_markets()
    test_basketball_markets()
    print("ALL OK")
