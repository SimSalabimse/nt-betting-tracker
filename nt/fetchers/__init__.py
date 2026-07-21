from __future__ import annotations

"""
Multi-sport result auto-fetch for settlement assist.

Architecture:
  ResultFetcher (base) → sport modules → registry → suggest_results_for_pending()

Public API (stable for settle / LuminaNT):
  - suggest_result_for_bet(bet)
  - suggest_results_for_pending(bets)
  - list_fetchers()
  - evaluate_selection_from_score(...)  # football-oriented alias
"""

from nt.fetchers.markets import evaluate_selection_from_score
from nt.fetchers.registry import (
    get_fetcher,
    list_fetchers,
    suggest_result_for_bet,
    suggest_results_for_pending,
)

__all__ = [
    "evaluate_selection_from_score",
    "get_fetcher",
    "list_fetchers",
    "suggest_result_for_bet",
    "suggest_results_for_pending",
]
