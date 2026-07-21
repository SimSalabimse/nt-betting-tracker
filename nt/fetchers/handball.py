from __future__ import annotations

"""Handball fetcher — TheSportsDB search (best-effort)."""

from urllib.parse import quote

from nt.fetchers.base import MatchResult, ResultFetcher, SelectionVerdict
from nt.fetchers.http import http_get_json
from nt.fetchers.markets import evaluate_football_like_selection
from nt.fetchers.names import pair_match_score, split_match


class HandballFetcher(ResultFetcher):
    name = "handball"
    sport_keys = ("handball", "hbl", "handballe")

    def fetch_match(
        self,
        *,
        match: str,
        date: str | None = None,
        sport: str = "",
        home: str | None = None,
        away: str | None = None,
    ) -> MatchResult | None:
        h, a = home or split_match(match)[0], away or split_match(match)[1]
        if not h:
            return None
        for q in (f"{h} vs {a}", h):
            url = f"https://www.thesportsdb.com/api/v1/json/3/searchevents.php?e={quote(q)}"
            data = http_get_json(url)
            events = (data or {}).get("event") if isinstance(data, dict) else None
            if not events:
                continue
            best = None
            best_conf = 0.0
            for ev in events[:20]:
                if not isinstance(ev, dict):
                    continue
                sp = str(ev.get("strSport") or "").lower()
                if sp and "handball" not in sp:
                    continue
                eh = str(ev.get("strHomeTeam") or "")
                ea = str(ev.get("strAwayTeam") or "")
                conf = pair_match_score(h, a, eh, ea)
                ed = str(ev.get("dateEvent") or "")[:10]
                if date and ed and date[:10] == ed:
                    conf += 0.15
                if conf < 0.35 or conf < best_conf:
                    continue
                try:
                    hsi = int(ev["intHomeScore"]) if ev.get("intHomeScore") not in (None, "") else None
                    asi = int(ev["intAwayScore"]) if ev.get("intAwayScore") not in (None, "") else None
                except (TypeError, ValueError, KeyError):
                    hsi = asi = None
                best_conf = conf
                best = MatchResult(
                    home=eh,
                    away=ea,
                    home_score=hsi,
                    away_score=asi,
                    score_text=f"{hsi}-{asi}" if hsi is not None and asi is not None else None,
                    status=str(ev.get("strStatus") or ""),
                    finished=hsi is not None and asi is not None,
                    start_time=str(ev.get("dateEvent") or "") or None,
                    league=str(ev.get("strLeague") or "") or None,
                    source="thesportsdb:handball",
                    match_confidence=round(min(conf, 1.0), 3),
                )
            if best:
                return best
        return None

    def evaluate_selection(
        self,
        selection: str,
        result: MatchResult,
        *,
        market_type: str = "",
    ) -> SelectionVerdict:
        return evaluate_football_like_selection(
            selection, result, market_type=market_type, sport_label="handball"
        )
