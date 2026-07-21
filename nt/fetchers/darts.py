from __future__ import annotations

"""
Darts fetcher stub — structure ready; no stable free score API wired yet.

Returns None so draft falls back to manual with a clear reason.
Extend later (e.g. PDC / Sofascore-style sources) without touching the registry API.
"""

from nt.fetchers.base import MatchResult, ResultFetcher, SelectionVerdict
from nt.fetchers.markets import evaluate_match_winner_only
from nt.fetchers.names import split_match


class DartsFetcher(ResultFetcher):
    name = "darts"
    sport_keys = ("darts", "dar")

    def fetch_match(
        self,
        *,
        match: str,
        date: str | None = None,
        sport: str = "",
        home: str | None = None,
        away: str | None = None,
    ) -> MatchResult | None:
        # Placeholder: no reliable public API in this build
        return None

    def evaluate_selection(
        self,
        selection: str,
        result: MatchResult,
        *,
        market_type: str = "",
    ) -> SelectionVerdict:
        return evaluate_match_winner_only(selection, result)

    def suggest_for_bet(self, bet: dict) -> "FetchSuggestion":  # type: ignore[name-defined]
        from nt.fetchers.base import FetchSuggestion

        sug = super().suggest_for_bet(bet)
        if not sug.auto:
            sug.reason = (
                "Darts auto-fetch not wired yet (no stable free API). "
                "Enter outcome manually — structure ready for a future PDC/Sofascore source."
            )
            h, a = split_match(str(bet.get("match") or ""))
            sug.home = h or sug.home
            sug.away = a or sug.away
        return sug
