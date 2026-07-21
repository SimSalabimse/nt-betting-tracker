from __future__ import annotations

"""Sport → ResultFetcher registry and public suggest helpers."""

from typing import Any

from nt.fetchers.base import FetchSuggestion, ResultFetcher
from nt.fetchers.basketball import BasketballFetcher
from nt.fetchers.darts import DartsFetcher
from nt.fetchers.football import FootballFetcher
from nt.fetchers.handball import HandballFetcher
from nt.fetchers.tennis import TennisFetcher

# Singleton instances (stateless fetchers)
_FETCHERS: list[ResultFetcher] = [
    FootballFetcher(),
    TennisFetcher(),
    BasketballFetcher(),
    HandballFetcher(),
    DartsFetcher(),
]

_BY_KEY: dict[str, ResultFetcher] = {}
for _f in _FETCHERS:
    for _k in _f.sport_keys:
        if _k:  # don't map empty string alone until fallback
            _BY_KEY[_k.lower()] = _f


def list_fetchers() -> list[dict[str, Any]]:
    return [
        {
            "name": f.name,
            "sport_keys": list(f.sport_keys),
            "module": f.__class__.__module__,
        }
        for f in _FETCHERS
    ]


def get_fetcher(sport: str | None) -> ResultFetcher | None:
    s = (sport or "").strip().lower()
    if s in _BY_KEY:
        return _BY_KEY[s]
    # fuzzy contains
    for key, fetcher in _BY_KEY.items():
        if key and key in s:
            return fetcher
    # Heuristic from match text later; default None
    return None


def resolve_fetcher(bet: dict[str, Any]) -> ResultFetcher:
    """Pick best fetcher from sport field + match heuristics."""
    sport = str(bet.get("sport") or "").strip().lower()
    f = get_fetcher(sport)
    if f:
        return f
    match = str(bet.get("match") or "").lower()
    sel = str(bet.get("selection") or "").lower()
    blob = f"{match} {sel} {sport}"
    if any(k in blob for k in ("tennis", "atp", "wta", "open")):
        # weak tennis signal — only if two person-like names
        if "," in match or " vs " in match:
            return TennisFetcher()
    if any(k in blob for k in ("nba", "wnba", "lakers", "celtics", "basket")):
        return BasketballFetcher()
    if "handball" in blob:
        return HandballFetcher()
    if "dart" in blob:
        return DartsFetcher()
    # Default football (most NT volume)
    return FootballFetcher()


def suggest_result_for_bet(bet: dict[str, Any]) -> dict[str, Any]:
    fetcher = resolve_fetcher(bet)
    suggestion: FetchSuggestion = fetcher.suggest_for_bet(bet)
    d = suggestion.to_dict()
    d["fetcher"] = fetcher.name
    return d


def suggest_results_for_pending(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from nt.bets_io import is_open_risk

    pending = [b for b in bets if is_open_risk(b.get("result"))]
    return [suggest_result_for_bet(b) for b in pending]


def register_fetcher(fetcher: ResultFetcher) -> None:
    """Allow plugins/tests to add a fetcher at runtime."""
    _FETCHERS.append(fetcher)
    for k in fetcher.sport_keys:
        if k:
            _BY_KEY[k.lower()] = fetcher
