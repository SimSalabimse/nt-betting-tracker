from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MatchResult:
    """Normalized finished (or live) match result from any source."""

    home: str
    away: str
    home_score: int | float | None = None
    away_score: int | float | None = None
    score_text: str | None = None  # "2-1", "6-4 3-6 7-6", etc.
    status: str = ""  # FT, Final, Completed, Live, ...
    finished: bool = False
    start_time: str | None = None
    league: str | None = None
    source: str = ""
    match_confidence: float = 0.0  # how well names matched the bet
    events: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SelectionVerdict:
    outcome: str | None  # win | loss | push | refund | None
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FetchSuggestion:
    """Full suggestion returned to settle draft / UI."""

    bet_id: str | None
    match: str
    selection: str
    sport: str
    auto: bool = False
    outcome: str | None = None
    score: str | None = None
    confidence: float = 0.0
    reason: str = ""
    source: str | None = None
    needs_manual: bool = True
    home: str | None = None
    away: str | None = None
    status: str | None = None
    finished: bool | None = None
    start_time: str | None = None
    events: list[str] = field(default_factory=list)
    match_confidence: float = 0.0
    fetch: dict[str, Any] | None = None
    fetcher: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # keep legacy keys used by settle.py / LuminaNT
        return d


class ResultFetcher(ABC):
    """
    Sport-specific result fetcher.

    Implement:
      - sport_keys: aliases this fetcher handles
      - fetch_match: pull raw result for a bet/match
      - evaluate_selection: map result → win/loss for the selection
    """

    name: str = "base"
    sport_keys: tuple[str, ...] = ()

    @abstractmethod
    def fetch_match(
        self,
        *,
        match: str,
        date: str | None = None,
        sport: str = "",
        home: str | None = None,
        away: str | None = None,
    ) -> MatchResult | None:
        """Return best MatchResult or None if nothing found."""

    @abstractmethod
    def evaluate_selection(
        self,
        selection: str,
        result: MatchResult,
        *,
        market_type: str = "",
    ) -> SelectionVerdict:
        """Map fetched result to bet outcome."""

    def supports(self, sport: str) -> bool:
        s = (sport or "").strip().lower()
        return s in self.sport_keys

    def suggest_for_bet(self, bet: dict[str, Any]) -> FetchSuggestion:
        match = str(bet.get("match") or "")
        selection = str(bet.get("selection") or "")
        sport = str(bet.get("sport") or "").strip().lower()
        date = str(bet.get("date") or "") or None
        bid = bet.get("bet_id")

        base = FetchSuggestion(
            bet_id=str(bid) if bid else None,
            match=match,
            selection=selection,
            sport=sport or self.name,
            fetcher=self.name,
        )

        try:
            result = self.fetch_match(
                match=match,
                date=date,
                sport=sport,
            )
        except Exception as ex:  # noqa: BLE001
            base.reason = f"fetch error: {ex}"
            base.needs_manual = True
            return base

        if result is None:
            base.reason = f"No {self.name} result found"
            base.needs_manual = True
            return base

        base.home = result.home
        base.away = result.away
        base.score = result.score_text or (
            f"{result.home_score}-{result.away_score}"
            if result.home_score is not None and result.away_score is not None
            else None
        )
        base.status = result.status
        base.finished = result.finished
        base.start_time = result.start_time
        base.events = list(result.events or [])
        base.source = result.source
        base.match_confidence = float(result.match_confidence or 0)
        base.fetch = result.to_dict()

        if not result.finished and result.home_score is None:
            base.reason = f"Match not finished (status={result.status or 'unknown'})"
            base.needs_manual = True
            return base

        try:
            verdict = self.evaluate_selection(
                selection,
                result,
                market_type=str(bet.get("market_type") or ""),
            )
        except Exception as ex:  # noqa: BLE001
            base.reason = f"map error: {ex}"
            base.needs_manual = True
            return base

        if verdict.outcome is None:
            base.reason = verdict.reason or "Could not map selection to result"
            base.confidence = float(verdict.confidence or 0) * max(
                0.3, float(result.match_confidence or 0.5)
            )
            base.needs_manual = True
            return base

        conf = float(verdict.confidence or 0) * max(
            0.35, min(1.0, float(result.match_confidence or 0.75))
        )
        if not result.finished:
            conf *= 0.7
            base.reason = f"(not confirmed FT) {verdict.reason}"
        else:
            base.reason = verdict.reason

        base.auto = True
        base.outcome = verdict.outcome
        base.confidence = round(conf, 3)
        base.needs_manual = conf < 0.55 or not result.finished
        return base
