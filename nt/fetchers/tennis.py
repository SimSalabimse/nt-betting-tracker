from __future__ import annotations

"""Tennis result fetcher — ESPN ATP/WTA scoreboards + TheSportsDB search."""

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from nt.fetchers.base import MatchResult, ResultFetcher, SelectionVerdict
from nt.fetchers.http import http_get_json
from nt.fetchers.markets import evaluate_tennis_selection
from nt.fetchers.names import (
    date_yyyymmdd,
    name_match_score,
    pair_match_score,
    split_match,
)

ESPN_TENNIS_TOURS = ("atp", "wta")  # skip "all" — slower duplicate


class TennisFetcher(ResultFetcher):
    name = "tennis"
    sport_keys = ("tennis", "tns", "atp", "wta")

    def fetch_match(
        self,
        *,
        match: str,
        date: str | None = None,
        sport: str = "",
        home: str | None = None,
        away: str | None = None,
    ) -> MatchResult | None:
        p1, p2 = home or split_match(match)[0], away or split_match(match)[1]
        if not p1:
            return None

        candidates: list[MatchResult] = []

        # TheSportsDB first (few calls)
        tdb = self._thesportsdb_tennis(p1, p2, date)
        if tdb:
            candidates.append(tdb)
            if tdb.home_score is not None and tdb.match_confidence >= 0.45:
                return tdb

        # ESPN ATP/WTA (date-scoped)
        try:
            for mr in self._espn_tennis(p1, p2, date):
                candidates.append(mr)
                if mr.home_score is not None and mr.match_confidence >= 0.55:
                    return mr
        except Exception:
            pass

        if not candidates:
            return None

        def rank(m: MatchResult) -> tuple:
            has = 1 if m.home_score is not None else 0
            return (has, 1 if m.finished else 0, m.match_confidence)

        candidates.sort(key=rank, reverse=True)
        best = candidates[0]
        if best.match_confidence < 0.3:
            return None
        return best

    def evaluate_selection(
        self,
        selection: str,
        result: MatchResult,
        *,
        market_type: str = "",
    ) -> SelectionVerdict:
        return evaluate_tennis_selection(selection, result, market_type=market_type)

    def _espn_tennis(
        self, p1: str, p2: str, date: str | None
    ) -> list[MatchResult]:
        out: list[MatchResult] = []
        dates = self._dates(date, tight=True)
        for d in dates:
            for tour in ESPN_TENNIS_TOURS:
                url = (
                    f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}"
                    f"/scoreboard?dates={d}"
                )
                data = http_get_json(url, timeout=6.0)
                if not data or not isinstance(data, dict):
                    continue
                # Tennis scoreboard nests groups → events
                events = list(data.get("events") or [])
                for group in data.get("groups") or []:
                    if isinstance(group, dict):
                        events.extend(group.get("events") or [])
                for ev in events:
                    if not isinstance(ev, dict):
                        continue
                    mr = self._parse_espn_tennis_event(ev, p1, p2)
                    if mr and mr.match_confidence >= 0.35:
                        out.append(mr)
                if any(m.finished and m.match_confidence >= 0.75 for m in out):
                    return out
        return out

    def _parse_espn_tennis_event(
        self, ev: dict[str, Any], p1: str, p2: str
    ) -> MatchResult | None:
        comps = ev.get("competitions") or []
        if not comps:
            return None
        comp = comps[0] if isinstance(comps[0], dict) else {}
        competitors = comp.get("competitors") or []
        names: list[tuple[str, str | None, bool]] = []
        # (name, score sets, winner?)
        home_name = away_name = None
        hs = aws = None
        winner_name = None
        for i, c in enumerate(competitors):
            if not isinstance(c, dict):
                continue
            ath = c.get("athlete") or c.get("team") or {}
            name = str(
                ath.get("displayName")
                or ath.get("fullName")
                or ath.get("name")
                or c.get("name")
                or ""
            )
            # Tennis often uses linescores for sets
            lines = c.get("linescores") or []
            sets_won = None
            try:
                if c.get("score") not in (None, ""):
                    sets_won = int(float(c.get("score")))
            except (TypeError, ValueError):
                sets_won = None
            if sets_won is None and lines:
                # count sets won from linescores if winner flags present
                won = 0
                for ln in lines:
                    if isinstance(ln, dict) and ln.get("winner"):
                        won += 1
                if won:
                    sets_won = won
            is_winner = bool(c.get("winner"))
            if is_winner:
                winner_name = name
            if c.get("homeAway") == "home" or i == 0:
                home_name, hs = name, sets_won
            else:
                away_name, aws = name, sets_won

        if not home_name or not away_name:
            return None

        conf = pair_match_score(p1, p2, home_name, away_name)
        # Also try reversed player order in match string
        conf = max(conf, pair_match_score(p1, p2, away_name, home_name) * 0.98)
        if conf < 0.32:
            return None

        status_obj = (ev.get("status") or {}).get("type") or {}
        state = str(status_obj.get("state") or "")
        detail = str(status_obj.get("description") or status_obj.get("name") or "")
        finished = state == "post" or "final" in detail.lower()

        # Build set score text from linescores if available
        score_text = None
        if hs is not None and aws is not None:
            score_text = f"{hs}-{aws}"
        set_bits: list[str] = []
        try:
            h_lines = (competitors[0] or {}).get("linescores") or []
            a_lines = (competitors[1] or {}).get("linescores") or []
            for i in range(max(len(h_lines), len(a_lines))):
                hv = h_lines[i].get("value") if i < len(h_lines) and isinstance(h_lines[i], dict) else None
                av = a_lines[i].get("value") if i < len(a_lines) and isinstance(a_lines[i], dict) else None
                if hv is not None and av is not None:
                    set_bits.append(f"{int(hv)}-{int(av)}")
        except Exception:
            set_bits = []
        if set_bits:
            score_text = " ".join(set_bits) if not score_text else f"{score_text} ({' '.join(set_bits)})"

        return MatchResult(
            home=home_name,
            away=away_name,
            home_score=hs,
            away_score=aws,
            score_text=score_text,
            status=detail or state,
            finished=finished,
            start_time=str(ev.get("date") or "") or None,
            league=str((ev.get("season") or {}).get("slug") or "tennis") or None,
            source="espn:tennis",
            match_confidence=round(conf, 3),
            extras={"winner": winner_name, "espn_id": ev.get("id"), "sets": set_bits},
        )

    def _thesportsdb_tennis(
        self, p1: str, p2: str, date: str | None
    ) -> MatchResult | None:
        for q in (f"{p1} vs {p2}", p1, p2):
            url = f"https://www.thesportsdb.com/api/v1/json/3/searchevents.php?e={quote(q)}"
            data = http_get_json(url)
            events = (data or {}).get("event") if isinstance(data, dict) else None
            if not events:
                continue
            best = None
            best_conf = 0.0
            for ev in events[:25]:
                if not isinstance(ev, dict):
                    continue
                sport = str(ev.get("strSport") or "").lower()
                if sport and "tennis" not in sport:
                    continue
                eh = str(ev.get("strHomeTeam") or "")
                ea = str(ev.get("strAwayTeam") or "")
                conf = pair_match_score(p1, p2, eh, ea)
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
                st = str(ev.get("strStatus") or "")
                finished = hsi is not None and asi is not None
                best_conf = conf
                best = MatchResult(
                    home=eh,
                    away=ea,
                    home_score=hsi,
                    away_score=asi,
                    score_text=f"{hsi}-{asi}" if hsi is not None and asi is not None else None,
                    status=st or ("FT" if finished else ""),
                    finished=finished,
                    start_time=str(ev.get("dateEvent") or "") or None,
                    league=str(ev.get("strLeague") or "") or None,
                    source="thesportsdb:tennis",
                    match_confidence=round(min(conf, 1.0), 3),
                )
            if best:
                return best
        return None

    @staticmethod
    def _dates(date: str | None, *, tight: bool = True) -> list[str]:
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
        return out[:3]
