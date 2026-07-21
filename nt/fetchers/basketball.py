from __future__ import annotations

"""Basketball result fetcher — ESPN NBA/WNBA (+ NCAAM best-effort)."""

from datetime import datetime, timedelta, timezone
from typing import Any

from nt.fetchers.base import MatchResult, ResultFetcher, SelectionVerdict
from nt.fetchers.http import http_get_json
from nt.fetchers.markets import evaluate_basketball_selection
from nt.fetchers.names import date_yyyymmdd, pair_match_score, split_match

ESPN_BBALL = (
    ("basketball", "nba"),
    ("basketball", "wnba"),
    ("basketball", "mens-college-basketball"),
)


class BasketballFetcher(ResultFetcher):
    name = "basketball"
    sport_keys = ("basketball", "nba", "wnba", "bsk", "basket")

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
        candidates: list[MatchResult] = []
        for d in self._dates(date):
            for sport_path, league in ESPN_BBALL:
                url = (
                    f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/{league}"
                    f"/scoreboard?dates={d}"
                )
                data = http_get_json(url, timeout=10.0)
                if not isinstance(data, dict):
                    continue
                for ev in data.get("events") or []:
                    mr = self._parse_espn(ev, h, a, source=f"espn:{league}")
                    if mr and mr.match_confidence >= 0.35:
                        candidates.append(mr)
        if not candidates:
            return None
        candidates.sort(
            key=lambda m: (
                1 if m.home_score is not None else 0,
                1 if m.finished else 0,
                m.match_confidence,
            ),
            reverse=True,
        )
        return candidates[0]

    def evaluate_selection(
        self,
        selection: str,
        result: MatchResult,
        *,
        market_type: str = "",
    ) -> SelectionVerdict:
        return evaluate_basketball_selection(
            selection, result, market_type=market_type
        )

    def _parse_espn(
        self, ev: dict[str, Any], home_q: str, away_q: str, *, source: str
    ) -> MatchResult | None:
        comps = ev.get("competitions") or []
        if not comps:
            return None
        comp = comps[0]
        competitors = comp.get("competitors") or []
        home_c = away_c = None
        hs = aws = None
        for c in competitors:
            team = c.get("team") or {}
            name = str(team.get("displayName") or team.get("name") or "")
            try:
                sc = int(float(c["score"])) if c.get("score") not in (None, "") else None
            except (TypeError, ValueError, KeyError):
                sc = None
            if c.get("homeAway") == "home":
                home_c, hs = name, sc
            else:
                away_c, aws = name, sc
        if not home_c or not away_c:
            return None
        conf = pair_match_score(home_q, away_q, home_c, away_c)
        if conf < 0.32:
            return None
        status_obj = (ev.get("status") or {}).get("type") or {}
        state = str(status_obj.get("state") or "")
        detail = str(status_obj.get("description") or "")
        finished = state == "post" or "final" in detail.lower()
        return MatchResult(
            home=home_c,
            away=away_c,
            home_score=hs,
            away_score=aws,
            score_text=f"{hs}-{aws}" if hs is not None and aws is not None else None,
            status=detail or state,
            finished=finished,
            start_time=str(ev.get("date") or "") or None,
            source=source,
            match_confidence=round(conf, 3),
        )

    @staticmethod
    def _dates(date: str | None) -> list[str]:
        out: list[str] = []
        base = date_yyyymmdd(date)
        if base:
            try:
                dt = datetime.strptime(base, "%Y%m%d")
                for delta in (0, -1, 1):
                    out.append((dt + timedelta(days=delta)).strftime("%Y%m%d"))
            except ValueError:
                out.append(base)
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if today not in out:
            out.append(today)
        return out[:4]
