from __future__ import annotations

"""
Backward-compatible facade for multi-sport result auto-fetch.

Implementation lives in ``nt.fetchers`` (modular ResultFetcher registry).
"""

from typing import Any

# Re-export public API
from nt.fetchers import (  # noqa: F401
    evaluate_selection_from_score,
    get_fetcher,
    list_fetchers,
    suggest_result_for_bet,
    suggest_results_for_pending,
)
from nt.fetchers.football import FootballFetcher

# Legacy alias used by older scripts/tests
def fetch_football_score(match: str, *, date: str | None = None) -> dict[str, Any]:
    """Legacy shape: {ok, score, home_goals, ...}."""
    fetcher = FootballFetcher()
    home, away = match, ""
    from nt.fetchers.names import split_match

    h, a = split_match(match)
    mr = fetcher.fetch_match(match=match, date=date, home=h, away=a)
    if not mr:
        return {
            "ok": False,
            "error": "no events found (auto-fetch unavailable)",
            "score": None,
            "source": "football_fetcher",
        }
    if mr.home_score is None or mr.away_score is None:
        return {
            "ok": False,
            "error": f"score not posted yet (status={mr.status or 'unknown'})",
            "score": None,
            "event": {"home": mr.home, "away": mr.away, "status": mr.status},
            "source": mr.source,
            "match_confidence": mr.match_confidence,
        }
    return {
        "ok": True,
        "score": mr.score_text or f"{mr.home_score}-{mr.away_score}",
        "home_goals": int(mr.home_score),
        "away_goals": int(mr.away_score),
        "home": mr.home,
        "away": mr.away,
        "date": mr.start_time,
        "status": mr.status,
        "finished": mr.finished,
        "source": mr.source,
        "match_confidence": mr.match_confidence,
        "league": mr.league,
        "events": mr.events,
    }


__all__ = [
    "evaluate_selection_from_score",
    "fetch_football_score",
    "get_fetcher",
    "list_fetchers",
    "suggest_result_for_bet",
    "suggest_results_for_pending",
]
