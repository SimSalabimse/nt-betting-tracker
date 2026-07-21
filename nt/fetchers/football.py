from __future__ import annotations

"""Football result fetcher — TheSportsDB + ESPN multi-league scoreboards."""

from datetime import datetime, timedelta, timezone
from typing import Any

from nt.fetchers.base import MatchResult, ResultFetcher, SelectionVerdict
from nt.fetchers.http import http_get_json, qs
from nt.fetchers.markets import evaluate_football_like_selection
from nt.fetchers.names import (
    date_yyyymmdd,
    name_match_score,
    pair_match_score,
    split_match,
)


# ESPN soccer league keys (no API key). Ordered by NT relevance.
# Keep list short — draft auto-fetch runs per pending bet.
ESPN_SOCCER_LEAGUES_CORE = (
    "nor.1",
    "swe.1",
    "den.1",
    "eng.1",
    "esp.1",
    "ger.1",
    "ita.1",
    "fra.1",
    "uefa.champions",
    "uefa.europa",
)
ESPN_SOCCER_LEAGUES_EXTRA = (
    "ned.1",
    "por.1",
    "usa.1",
    "uefa.europa.conf",
    "fifa.world",
    "uefa.euro",
)


class FootballFetcher(ResultFetcher):
    name = "football"
    sport_keys = (
        "football",
        "soccer",
        "fotball",
        "fbl",
        "soccer_football",
        "",  # empty sport often football on NT dumps
    )

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

        # 1) TheSportsDB search first (1–3 HTTP calls, good for Nordics / named clubs)
        tdb = self._thesportsdb_search(h, a, date)
        if tdb:
            candidates.append(tdb)
            if tdb.home_score is not None and tdb.match_confidence >= 0.45:
                return tdb

        # 2) Livescore snapshot (one call)
        live = self._thesportsdb_livescore(h, a)
        if live:
            candidates.append(live)
            if live.home_score is not None and live.match_confidence >= 0.45:
                return live

        # 3) ESPN — only if still no scored match (can be slow / flaky offline)
        has_scored = any(
            m.home_score is not None and m.match_confidence >= 0.4 for m in candidates
        )
        if not has_scored:
            try:
                for mr in self._espn_candidates(h, a, date, extended=False):
                    candidates.append(mr)
                    if mr.home_score is not None and mr.match_confidence >= 0.55:
                        return mr
            except Exception:
                pass

        if not candidates:
            return None

        # Prefer finished + high match confidence + has scores
        def rank(m: MatchResult) -> tuple:
            has_score = 1 if m.home_score is not None and m.away_score is not None else 0
            return (has_score, 1 if m.finished else 0, m.match_confidence)

        candidates.sort(key=rank, reverse=True)
        best = candidates[0]
        if best.match_confidence < 0.28 and best.home_score is None:
            return None
        return best

    def evaluate_selection(
        self,
        selection: str,
        result: MatchResult,
        *,
        market_type: str = "",
    ) -> SelectionVerdict:
        return evaluate_football_like_selection(
            selection, result, market_type=market_type, sport_label="football"
        )

    # --- sources ---

    def _espn_candidates(
        self,
        home: str,
        away: str,
        date: str | None,
        *,
        extended: bool = False,
    ) -> list[MatchResult]:
        out: list[MatchResult] = []
        # Prefer bet date only (not ±1) for speed; expand if nothing found
        dates = self._date_window(date, tight=not extended)
        leagues = (
            ESPN_SOCCER_LEAGUES_CORE + ESPN_SOCCER_LEAGUES_EXTRA
            if extended
            else ESPN_SOCCER_LEAGUES_CORE
        )
        for d in dates:
            for league in leagues:
                url = (
                    f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}"
                    f"/scoreboard?dates={d}"
                )
                data = http_get_json(url, timeout=6.0)
                if not data or not isinstance(data, dict):
                    continue
                for ev in data.get("events") or []:
                    mr = self._parse_espn_event(ev, home, away)
                    if mr and mr.match_confidence >= 0.35:
                        out.append(mr)
                # Early exit if strong finished hit
                if any(m.finished and m.match_confidence >= 0.7 for m in out):
                    return out
        return out

    def _parse_espn_event(
        self, ev: dict[str, Any], home_q: str, away_q: str
    ) -> MatchResult | None:
        comps = ev.get("competitions") or []
        if not comps:
            return None
        comp = comps[0] if isinstance(comps[0], dict) else {}
        competitors = comp.get("competitors") or []
        home_c = away_c = None
        hs = aws = None
        for c in competitors:
            if not isinstance(c, dict):
                continue
            team = c.get("team") or {}
            name = str(team.get("displayName") or team.get("name") or "")
            score = c.get("score")
            try:
                sc = int(score) if score is not None and str(score) != "" else None
            except (TypeError, ValueError):
                sc = None
            if c.get("homeAway") == "home":
                home_c, hs = name, sc
            elif c.get("homeAway") == "away":
                away_c, aws = name, sc
        if not home_c or not away_c:
            return None
        conf = pair_match_score(home_q, away_q, home_c, away_c)
        if conf < 0.3:
            return None
        status_obj = (ev.get("status") or {}).get("type") or {}
        state = str(status_obj.get("state") or "")
        detail = str(status_obj.get("description") or status_obj.get("name") or "")
        finished = state == "post" or "final" in detail.lower() or detail.lower() in (
            "ft",
            "full time",
            "aet",
            "ft-pens",
        )
        events: list[str] = []
        # Light event hints from situation / notes if present
        note = str(comp.get("notes") or "")
        if note:
            events.append(note[:120])
        return MatchResult(
            home=home_c,
            away=away_c,
            home_score=hs,
            away_score=aws,
            score_text=f"{hs}-{aws}" if hs is not None and aws is not None else None,
            status=detail or state,
            finished=finished,
            start_time=str(ev.get("date") or "") or None,
            league=str((ev.get("league") or {}).get("name") or "") or None,
            source=f"espn:{((ev.get('league') or {}).get('slug') or 'soccer')}",
            match_confidence=round(conf, 3),
            events=events,
            extras={"espn_id": ev.get("id"), "name": ev.get("name")},
        )

    def _thesportsdb_search(
        self, home: str, away: str, date: str | None
    ) -> MatchResult | None:
        from urllib.parse import quote

        queries = [
            f"{home} vs {away}",
            f"{home} {away}",
            home,
        ]
        best: MatchResult | None = None
        best_conf = -1.0
        for q in queries:
            url = f"https://www.thesportsdb.com/api/v1/json/3/searchevents.php?e={quote(q)}"
            data = http_get_json(url)
            events = (data or {}).get("event") if isinstance(data, dict) else None
            if not events:
                continue
            for ev in events[:30]:
                if not isinstance(ev, dict):
                    continue
                # Prefer soccer
                sport = str(ev.get("strSport") or "").lower()
                if sport and sport not in ("soccer", "football", ""):
                    continue
                eh = str(ev.get("strHomeTeam") or "")
                ea = str(ev.get("strAwayTeam") or "")
                conf = pair_match_score(home, away, eh, ea)
                ed = str(ev.get("dateEvent") or "")[:10]
                if date and ed and date[:10] == ed:
                    conf += 0.2
                if conf < best_conf:
                    continue
                hs, aws = ev.get("intHomeScore"), ev.get("intAwayScore")
                try:
                    hsi = int(hs) if hs is not None and str(hs) != "" else None
                    asi = int(aws) if aws is not None and str(aws) != "" else None
                except (TypeError, ValueError):
                    hsi = asi = None
                status = str(ev.get("strStatus") or "")
                finished = bool(
                    hsi is not None
                    and asi is not None
                    and (
                        status.lower()
                        in ("match finished", "ft", "full time", "aet", "pen", "")
                        or status == ""
                    )
                )
                best_conf = conf
                best = MatchResult(
                    home=eh,
                    away=ea,
                    home_score=hsi,
                    away_score=asi,
                    score_text=f"{hsi}-{asi}" if hsi is not None and asi is not None else None,
                    status=status or ("FT" if finished else "unknown"),
                    finished=finished or (hsi is not None),
                    start_time=str(ev.get("strTimestamp") or ev.get("dateEvent") or "")
                    or None,
                    league=str(ev.get("strLeague") or "") or None,
                    source="thesportsdb",
                    match_confidence=round(min(conf, 1.0), 3),
                    extras={"idEvent": ev.get("idEvent")},
                )
        if best and best.match_confidence >= 0.28:
            return best
        return None

    def _thesportsdb_livescore(self, home: str, away: str) -> MatchResult | None:
        url = "https://www.thesportsdb.com/api/v1/json/3/livescore.php?s=Soccer"
        data = http_get_json(url, timeout=10.0)
        events = None
        if isinstance(data, dict):
            events = data.get("events") or data.get("event")
        if not events:
            return None
        best = None
        best_conf = 0.0
        for ev in events:
            if not isinstance(ev, dict):
                continue
            eh = str(ev.get("strHomeTeam") or "")
            ea = str(ev.get("strAwayTeam") or "")
            conf = pair_match_score(home, away, eh, ea)
            if conf < 0.4 or conf < best_conf:
                continue
            try:
                hsi = int(ev["intHomeScore"]) if ev.get("intHomeScore") not in (None, "") else None
                asi = int(ev["intAwayScore"]) if ev.get("intAwayScore") not in (None, "") else None
            except (TypeError, ValueError, KeyError):
                hsi = asi = None
            best_conf = conf
            st = str(ev.get("strStatus") or "")
            finished = st.lower() in ("ft", "match finished", "aet")
            best = MatchResult(
                home=eh,
                away=ea,
                home_score=hsi,
                away_score=asi,
                score_text=f"{hsi}-{asi}" if hsi is not None and asi is not None else None,
                status=st,
                finished=finished,
                source="thesportsdb:livescore",
                match_confidence=round(conf, 3),
            )
        return best

    @staticmethod
    def _date_window(date: str | None, *, tight: bool = True) -> list[str]:
        """YYYYMMDD list. tight=True → bet day (+ today); else ±1 day."""
        out: list[str] = []
        base = date_yyyymmdd(date)
        if base:
            try:
                dt = datetime.strptime(base, "%Y%m%d")
                deltas = (0,) if tight else (0, -1, 1)
                for delta in deltas:
                    out.append((dt + timedelta(days=delta)).strftime("%Y%m%d"))
            except ValueError:
                out.append(base)
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if today not in out:
            out.append(today)
        return out[:4]
