"""
Shared Flashscore-like live parsers for multi-sport MIC (PR-5).

Offline-safe: HTML / Firecrawl markdown / XHR only. Used by thin wrappers:
  esports_live, snooker_live, darts_live, baseball_live.

Critical-key modes:
  form          → form_home / form_away (+ optional standings for baseball)
  form_or_rank  → form n≥3 or rank/rating (snooker, darts)
"""
from __future__ import annotations

import re
from typing import Any, Literal

from nt.match_intel.sources.flashscore_live import (
    _bundle_parts,
    _empty_frag,
    _extract_h2h,
    _extract_title,
    _fields,
    _first_attr,
    _int,
    _letters_from_any,
    _md_first_heading,
    _merge_frag_list,
    _parse_form_letters,
    _parse_json_ld,
    _side_from_form,
    _split_match,
    _split_title_teams,
    _strip_tags,
    _walk_json_objects,
    parse_flashscore_xhr,
)

Mode = Literal["form", "form_or_rank"]

# Sport → critical field mode + optional extras
SPORT_PROFILES: dict[str, dict[str, Any]] = {
    "esports": {
        "mode": "form",
        "need_standings": False,  # ranking is optional
        "path_hint": "esports",
        "comp_keywords": (
            "esl",
            "blast",
            "iem",
            "major",
            "lcs",
            "lec",
            "lck",
            "lpl",
            "worlds",
            "cs2",
            "cs:go",
            "lol",
            "dota",
            "valorant",
            "pro league",
            "masters",
        ),
    },
    "snooker": {
        "mode": "form_or_rank",
        "need_standings": False,
        "path_hint": "snooker",
        "comp_keywords": (
            "world championship",
            "masters",
            "uk championship",
            "ranking",
            "championship",
            "open",
            "snooker",
        ),
    },
    "darts": {
        "mode": "form_or_rank",
        "need_standings": False,
        "path_hint": "darts",
        "comp_keywords": (
            "pdc",
            "world championship",
            "premier league",
            "players championship",
            "masters",
            "grand slam",
            "european",
            "darts",
        ),
    },
    "baseball": {
        "mode": "form",
        "need_standings": True,
        "path_hint": "baseball",
        "comp_keywords": (
            "mlb",
            "american league",
            "national league",
            "world series",
            "division",
            "baseball",
            "npb",
            "kbo",
        ),
    },
}


def parse_multi_sport_bundle(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Parse MatchFetchBundle → MIC fragment for a registered multi-sport.

    Priority: sport XHR → shared football XHR walk → live HTML (+ h2h) → markdown.
    """
    _ = cfg
    sport_n = (sport or "").strip().lower()
    profile = SPORT_PROFILES.get(sport_n) or {
        "mode": "form",
        "need_standings": False,
        "path_hint": sport_n or "sport",
        "comp_keywords": (),
    }

    html, markdown, h2h_html, xhrs, page_meta, url, method = _bundle_parts(bundle)
    fragments: list[dict[str, Any]] = []

    if xhrs:
        frag_x = parse_multi_sport_xhr(xhrs, match=match, sport=sport_n)
        if _fields(frag_x) or _sides_useful(frag_x, profile):
            fragments.append(frag_x)
        frag_fs = parse_flashscore_xhr(xhrs, match=match)
        if _fields(frag_fs):
            fragments.append(frag_fs)

    combined_html = html or ""
    if h2h_html and h2h_html not in combined_html:
        combined_html = f"{combined_html}\n{h2h_html}"
    if combined_html.strip():
        frag_h = parse_multi_sport_live_html(
            combined_html, match=match, sport=sport_n, page_meta=page_meta
        )
        if _fields(frag_h) or _sides_useful(frag_h, profile):
            fragments.append(frag_h)

    if markdown and str(markdown).strip():
        frag_m = parse_multi_sport_markdown(str(markdown), match=match, sport=sport_n)
        if _fields(frag_m) or _sides_useful(frag_m, profile):
            fragments.append(frag_m)

    merged = _merge_frag_list(fragments)
    merged = _normalize_fields(merged, profile)

    if not merged.get("publisher"):
        merged["publisher"] = "flashscore"
    if not merged.get("method"):
        merged["method"] = method or "live_parse"
    if url:
        merged["url"] = url

    home_side = dict((merged.get("sides") or {}).get("home") or {})
    away_side = dict((merged.get("sides") or {}).get("away") or {})
    if page_meta:
        if not home_side.get("name") and page_meta.get("home_name"):
            home_side["name"] = page_meta["home_name"]
        if not away_side.get("name") and page_meta.get("away_name"):
            away_side["name"] = page_meta["away_name"]
        if not (merged.get("competition") or {}).get("name") and page_meta.get(
            "competition_hint"
        ):
            merged["competition"] = {
                **(merged.get("competition") or {}),
                "name": page_meta["competition_hint"],
            }
    if match:
        mh, ma = _split_match(match)
        if mh and not home_side.get("name"):
            home_side["name"] = mh
        if ma and not away_side.get("name"):
            away_side["name"] = ma
    merged["sides"] = {"home": home_side, "away": away_side}
    merged = _normalize_fields(merged, profile)
    if not merged.get("page_title") and page_meta.get("title"):
        merged["page_title"] = page_meta["title"]
    return merged


def parse_multi_sport_live_html(
    html: str,
    *,
    match: str = "",
    sport: str = "",
    page_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse Flashscore-like multi-sport match HTML."""
    sport_n = (sport or "").strip().lower()
    profile = SPORT_PROFILES.get(sport_n) or {
        "mode": "form",
        "need_standings": False,
        "path_hint": sport_n,
        "comp_keywords": (),
    }
    out = _empty_frag(publisher="flashscore", method="live_html")
    if not html or not str(html).strip():
        return out

    page_meta = page_meta or {}
    text = _strip_tags(html)
    title = _extract_title(html) or str(page_meta.get("title") or "")
    out["page_title"] = title

    home_name = (
        str(page_meta.get("home_name") or "").strip()
        or _first_attr(
            html,
            (
                r'class="[^"]*duelParticipant__home[^"]*"[^>]*>.*?'
                r'class="[^"]*participant__participantName[^"]*"[^>]*>([^<]+)',
                r'data-testid=["\']home-team["\'][^>]*>([^<]+)',
                r'data-testid=["\']home-player["\'][^>]*>([^<]+)',
                r'class="[^"]*homeParticipant[^"]*"[^>]*>([^<]+)',
                r'itemprop=["\']homeTeam["\'][^>]*>.*?<span[^>]*>([^<]+)',
            ),
        )
        or ""
    )
    away_name = (
        str(page_meta.get("away_name") or "").strip()
        or _first_attr(
            html,
            (
                r'class="[^"]*duelParticipant__away[^"]*"[^>]*>.*?'
                r'class="[^"]*participant__participantName[^"]*"[^>]*>([^<]+)',
                r'data-testid=["\']away-team["\'][^>]*>([^<]+)',
                r'data-testid=["\']away-player["\'][^>]*>([^<]+)',
                r'class="[^"]*awayParticipant[^"]*"[^>]*>([^<]+)',
                r'itemprop=["\']awayTeam["\'][^>]*>.*?<span[^>]*>([^<]+)',
            ),
        )
        or ""
    )
    if (not home_name or not away_name) and title:
        th, ta = _split_title_teams(title)
        home_name = home_name or th
        away_name = away_name or ta
    if (not home_name or not away_name) and match:
        mh, ma = _split_match(match)
        home_name = home_name or mh
        away_name = away_name or ma

    comp = _extract_competition(html, title=title, page_meta=page_meta, text=text, profile=profile)
    if comp:
        out["competition"] = comp
        out["fields_contributed"].append("competition")

    # Optional game/format hint for esports (map pool / title)
    game = _extract_game_or_format(html, text, sport_n)
    if game:
        out["competition"] = {**(out.get("competition") or {}), "format": game}
        if sport_n == "esports":
            out["fields_contributed"].append("roster_notes")  # may be filled later
            out.setdefault("other_high_signal", []).append(
                {"fact": f"game/format: {game}", "source": "flashscore"}
            )

    home_form, away_form = _extract_form(html, text, home_name, away_name)
    home_side = _side_from_form(home_name, home_form)
    away_side = _side_from_form(away_name, away_form)

    home_rank = _extract_rank(html, text, home_name, side="home")
    away_rank = _extract_rank(html, text, away_name, side="away")
    if home_rank is not None:
        home_side["standings"] = {"rank": home_rank, "points": None}
    if away_rank is not None:
        away_side["standings"] = {"rank": away_rank, "points": None}

    # Standings table (baseball / team sports)
    if profile.get("need_standings") or not home_side.get("standings"):
        ranks = _extract_standings_table(html, home_name, away_name)
        if ranks.get("home") is not None and not home_side.get("standings"):
            home_side["standings"] = {
                "rank": ranks["home"],
                "points": ranks.get("home_pts"),
            }
        if ranks.get("away") is not None and not away_side.get("standings"):
            away_side["standings"] = {
                "rank": ranks["away"],
                "points": ranks.get("away_pts"),
            }

    # Esports optional ranking_or_rating via rank or rating attr
    home_rating = _extract_rating(html, text, home_name, side="home")
    away_rating = _extract_rating(html, text, away_name, side="away")
    if home_rating is not None:
        home_side["rating"] = home_rating
    if away_rating is not None:
        away_side["rating"] = away_rating

    # Roster notes (esports)
    roster = _extract_roster_notes(html, text)
    if roster:
        out.setdefault("other_high_signal", []).append(
            {"fact": f"roster: {roster}", "source": "flashscore"}
        )
        out["fields_contributed"].append("roster_notes")

    h2h = _extract_h2h(html, text)
    if h2h and (h2h.get("n") or h2h.get("summary") or h2h.get("recent")):
        out["h2h"] = h2h
        if int(h2h.get("n") or 0) >= 1 or h2h.get("summary"):
            out["fields_contributed"].append("h2h")

    jld = _parse_json_ld(html)
    if jld:
        if not (out.get("competition") or {}).get("name") and jld.get("competition"):
            out["competition"] = {
                **(out.get("competition") or {}),
                "name": jld["competition"],
            }
            out["fields_contributed"].append("competition")
        if jld.get("home") and not home_side.get("name"):
            home_side["name"] = jld["home"]
        if jld.get("away") and not away_side.get("name"):
            away_side["name"] = jld["away"]

    out["sides"] = {"home": home_side, "away": away_side}
    out = _normalize_fields(out, profile)
    return out


def parse_multi_sport_markdown(
    md: str,
    *,
    match: str = "",
    sport: str = "",
) -> dict[str, Any]:
    """Parse Firecrawl-style markdown for multi-sport match pages."""
    sport_n = (sport or "").strip().lower()
    profile = SPORT_PROFILES.get(sport_n) or {
        "mode": "form",
        "need_standings": False,
        "path_hint": sport_n,
        "comp_keywords": (),
    }
    out = _empty_frag(publisher="flashscore", method="markdown")
    if not md or not str(md).strip():
        return out

    text = str(md)
    out["page_title"] = _md_first_heading(text) or ""

    home_name, away_name = "", ""
    if match:
        home_name, away_name = _split_match(match)
    if (not home_name or not away_name) and out["page_title"]:
        th, ta = _split_title_teams(out["page_title"])
        home_name = home_name or th
        away_name = away_name or ta

    comp = ""
    m = re.search(
        r"(?:^|\n)(?:competition|tournament|event|league)\s*[:\-]\s*(.+)$",
        text,
        re.I | re.M,
    )
    if m:
        comp = m.group(1).strip()
    if not comp:
        heads = re.findall(r"^#{1,3}\s+(.+)$", text, re.M)
        kws = tuple(profile.get("comp_keywords") or ())
        for h in heads[1:]:
            hl = h.lower()
            if any(x in hl for x in kws) or (
                " vs " not in hl and len(h.strip()) >= 3 and "form" not in hl and "h2h" not in hl
            ):
                if "form" in hl or "h2h" in hl or "rank" in hl or "standings" in hl:
                    continue
                comp = h.strip()
                break
    if comp:
        out["competition"] = {"name": comp}
        out["fields_contributed"].append("competition")

    game_m = re.search(
        r"(?:game|title|discipline|format)\s*[:\-]?\s*(CS2?|CS:GO|LoL|Dota\s*2|Valorant|MLB)",
        text,
        re.I,
    )
    if game_m:
        g = game_m.group(1).strip()
        out["competition"] = {**(out.get("competition") or {}), "format": g}

    home_form = _md_form_side(text, home_name, side="home")
    away_form = _md_form_side(text, away_name, side="away")
    if not home_form or not away_form:
        m = re.search(
            r"form\s*[:\-]?\s*([WLD]{3,10})\s*[|/]\s*([WLD]{3,10})",
            text,
            re.I,
        )
        if m:
            home_form = home_form or m.group(1)
            away_form = away_form or m.group(2)

    home_side = _side_from_form(home_name, home_form or "")
    away_side = _side_from_form(away_name, away_form or "")

    hr = _md_rank(text, home_name)
    ar = _md_rank(text, away_name)
    if hr is not None:
        home_side["standings"] = {"rank": hr, "points": None}
    if ar is not None:
        away_side["standings"] = {"rank": ar, "points": None}

    # H2H
    h2h_n = 0
    h2h_recent: list[dict[str, Any]] = []
    h2h_sec = re.search(
        r"(?:^|\n)#{1,3}\s*H2H\b.*?(?=\n#{1,3}\s|\Z)",
        text,
        re.I | re.S,
    )
    block = h2h_sec.group(0) if h2h_sec else text
    for sm2 in re.finditer(
        r"(\d{4}-\d{2}-\d{2})?[^\n]{0,60}?(\d+\s*[-:]\s*\d+(?:\s*[-:]\s*\d+)*)",
        block,
    ):
        h2h_recent.append(
            {
                "date": (sm2.group(1) or "").strip(),
                "score": sm2.group(2),
                "competition": "",
            }
        )
        h2h_n += 1
        if h2h_n >= 8:
            break
    if h2h_n or h2h_recent:
        out["h2h"] = {
            "n": h2h_n or len(h2h_recent),
            "summary": "",
            "recent": h2h_recent,
            "polarity": None,
        }
        out["fields_contributed"].append("h2h")

    roster_m = re.search(r"(?:roster|lineup|stand-?in)\s*[:\-]\s*(.+)$", text, re.I | re.M)
    if roster_m:
        out.setdefault("other_high_signal", []).append(
            {"fact": f"roster: {roster_m.group(1).strip()}", "source": "flashscore"}
        )
        out["fields_contributed"].append("roster_notes")

    out["sides"] = {"home": home_side, "away": away_side}
    out = _normalize_fields(out, profile)
    return out


def parse_multi_sport_xhr(
    xhrs: list[Any],
    *,
    match: str = "",
    sport: str = "",
) -> dict[str, Any]:
    """Extract form / rank / competition / H2H from multi-sport XHR JSON."""
    sport_n = (sport or "").strip().lower()
    profile = SPORT_PROFILES.get(sport_n) or {
        "mode": "form",
        "need_standings": False,
        "path_hint": sport_n,
        "comp_keywords": (),
    }
    out = _empty_frag(publisher="flashscore", method="xhr_json")
    if not xhrs:
        return out

    home_name, away_name = _split_match(match) if match else ("", "")
    home_letters: list[str] = []
    away_letters: list[str] = []
    home_rank = away_rank = None
    home_pts = away_pts = None
    h2h_recent: list[dict[str, Any]] = []
    comp_name = ""
    game_fmt = ""
    roster_note = ""

    for item in xhrs:
        data = item
        if isinstance(item, dict) and "data" in item:
            data = item.get("data")
        for obj in _walk_json_objects(data):
            if not isinstance(obj, dict):
                continue

            for k in (
                "tournament",
                "competition",
                "event",
                "tournamentName",
                "league",
                "leagueName",
            ):
                v = obj.get(k)
                if isinstance(v, str) and 3 <= len(v) <= 80 and not comp_name:
                    if v.lower() not in (
                        "match",
                        "summary",
                        sport_n,
                        "home",
                        "away",
                    ):
                        comp_name = v
                if isinstance(v, dict):
                    nm = v.get("name") or v.get("tournamentName") or v.get("leagueName")
                    if isinstance(nm, str) and 3 <= len(nm) <= 80:
                        comp_name = comp_name or nm

            for gk in ("game", "discipline", "title", "sportEvent", "format"):
                if isinstance(obj.get(gk), str) and obj[gk].strip() and not game_fmt:
                    game_fmt = str(obj[gk]).strip()

            if isinstance(obj.get("rosterNote") or obj.get("roster"), str):
                roster_note = roster_note or str(obj.get("rosterNote") or obj.get("roster"))

            if "home" in obj and isinstance(obj["home"], dict):
                r = _int(
                    obj["home"].get("rank")
                    or obj["home"].get("ranking")
                    or obj["home"].get("position")
                    or obj["home"].get("seed")
                )
                if r is not None:
                    home_rank = home_rank if home_rank is not None else r
                pts = _int(obj["home"].get("points") or obj["home"].get("pts"))
                if pts is not None:
                    home_pts = home_pts if home_pts is not None else pts
                letters = _letters_from_any(
                    obj["home"].get("form")
                    or obj["home"].get("lastMatches")
                    or obj["home"].get("recentForm")
                )
                if len(letters) > len(home_letters):
                    home_letters = letters
                if obj["home"].get("name") and not home_name:
                    home_name = str(obj["home"]["name"])

            if "away" in obj and isinstance(obj["away"], dict):
                r = _int(
                    obj["away"].get("rank")
                    or obj["away"].get("ranking")
                    or obj["away"].get("position")
                    or obj["away"].get("seed")
                )
                if r is not None:
                    away_rank = away_rank if away_rank is not None else r
                pts = _int(obj["away"].get("points") or obj["away"].get("pts"))
                if pts is not None:
                    away_pts = away_pts if away_pts is not None else pts
                letters = _letters_from_any(
                    obj["away"].get("form")
                    or obj["away"].get("lastMatches")
                    or obj["away"].get("recentForm")
                )
                if len(letters) > len(away_letters):
                    away_letters = letters
                if obj["away"].get("name") and not away_name:
                    away_name = str(obj["away"]["name"])

            for hk in ("h2h", "headToHead", "lastMeetings"):
                rows = obj.get(hk)
                if isinstance(rows, list):
                    for row in rows[:8]:
                        if not isinstance(row, dict):
                            continue
                        score = (
                            row.get("score")
                            or row.get("result")
                            or (
                                f"{row.get('homeScore', row.get('home_score', ''))}-"
                                f"{row.get('awayScore', row.get('away_score', ''))}"
                            )
                        )
                        h2h_recent.append(
                            {
                                "date": str(row.get("date") or row.get("startTime") or ""),
                                "score": str(score or "").strip(),
                                "competition": str(
                                    row.get("competition") or row.get("tournament") or ""
                                ),
                            }
                        )

    home_side: dict[str, Any] = {
        "name": home_name,
        "recent_form": {
            "n": len(home_letters),
            "results": home_letters,
            "scores": [],
            "summary": " ".join(home_letters),
        },
    }
    away_side: dict[str, Any] = {
        "name": away_name,
        "recent_form": {
            "n": len(away_letters),
            "results": away_letters,
            "scores": [],
            "summary": " ".join(away_letters),
        },
    }
    if home_rank is not None:
        home_side["standings"] = {"rank": home_rank, "points": home_pts}
    if away_rank is not None:
        away_side["standings"] = {"rank": away_rank, "points": away_pts}
    if comp_name:
        out["competition"] = {"name": comp_name}
        out["fields_contributed"].append("competition")
    if game_fmt:
        out["competition"] = {**(out.get("competition") or {}), "format": game_fmt}
    if h2h_recent:
        out["h2h"] = {
            "n": len(h2h_recent),
            "summary": "",
            "recent": h2h_recent,
            "polarity": None,
        }
        out["fields_contributed"].append("h2h")
    if roster_note:
        out.setdefault("other_high_signal", []).append(
            {"fact": f"roster: {roster_note}", "source": "flashscore"}
        )
        out["fields_contributed"].append("roster_notes")
    out["sides"] = {"home": home_side, "away": away_side}
    out = _normalize_fields(out, profile)
    return out


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _sides_useful(frag: dict[str, Any] | None, profile: dict[str, Any]) -> bool:
    if not frag:
        return False
    for sk in ("home", "away"):
        side = (frag.get("sides") or {}).get(sk) or {}
        rf = side.get("recent_form") or {}
        if int(rf.get("n") or 0) >= 3 and rf.get("results"):
            return True
        if (side.get("standings") or {}).get("rank") is not None:
            return True
        if side.get("rating") is not None:
            return True
    if str((frag.get("competition") or {}).get("name") or "").strip():
        return True
    return False


def _normalize_fields(frag: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Tag fields_contributed from side facts for coverage credit."""
    out = dict(frag)
    fields = list(out.get("fields_contributed") or [])
    sides = out.get("sides") or {}
    mode = profile.get("mode") or "form"
    need_standings = bool(profile.get("need_standings"))

    for sk, form_key, for_key in (
        ("home", "form_home", "form_or_rank_home"),
        ("away", "form_away", "form_or_rank_away"),
    ):
        side = sides.get(sk) or {}
        n = int((side.get("recent_form") or {}).get("n") or 0)
        results = (side.get("recent_form") or {}).get("results") or []
        has_rank = (side.get("standings") or {}).get("rank") is not None
        has_rating = side.get("rating") is not None
        if n >= 3 and results:
            if form_key not in fields:
                fields.append(form_key)
            if mode == "form_or_rank" and for_key not in fields:
                fields.append(for_key)
        if mode == "form_or_rank" and (has_rank or has_rating) and for_key not in fields:
            fields.append(for_key)
        if has_rank or has_rating:
            if "standings_or_rank" not in fields:
                fields.append("standings_or_rank")
            if "ranking_or_rating" not in fields:
                fields.append("ranking_or_rating")
            if sk == "home" and "standings_home" not in fields:
                fields.append("standings_home")
            if sk == "away" and "standings_away" not in fields:
                fields.append("standings_away")

    if (out.get("competition") or {}).get("name") and "competition" not in fields:
        fields.append("competition")
    if int((out.get("h2h") or {}).get("n") or 0) >= 1 and "h2h" not in fields:
        fields.append("h2h")

    # Ensure standings_or_rank when baseball needs it and either side ranked
    if need_standings:
        for sk in ("home", "away"):
            if ((sides.get(sk) or {}).get("standings") or {}).get("rank") is not None:
                if "standings_or_rank" not in fields:
                    fields.append("standings_or_rank")
                break

    # Roster notes already tagged; ensure list unique
    out["fields_contributed"] = sorted(set(fields))
    return out


def _extract_competition(
    html: str,
    *,
    title: str,
    page_meta: dict[str, Any],
    text: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    hint = str(page_meta.get("competition_hint") or "").strip()
    if hint:
        return {"name": hint, "country": page_meta.get("country")}

    path_hint = str(profile.get("path_hint") or "sport")
    candidates: list[str] = []
    for pat in (
        r'class="[^"]*(?:tournamentHeader|tournament|breadcrumb|wcl-breadcrumb|event__title|leagueHeader)[^"]*"[^>]*>([^<]{3,60})',
        r'data-competition=["\']([^"\']+)',
        r'data-tournament=["\']([^"\']+)',
        r'data-league=["\']([^"\']+)',
        rf'<a[^>]+href="[^"]*/{re.escape(path_hint)}/[^"]*"[^>]*>([^<]{{3,50}})</a>',
    ):
        for m in re.finditer(pat, html, flags=re.I):
            val = _strip_tags(m.group(1)).strip()
            if val and val.lower() not in (
                path_hint,
                "home",
                "flashscore",
                "standings",
                "h2h",
                "sport",
            ):
                candidates.append(val)

    if title and "|" in title:
        parts = [p.strip() for p in title.split("|")]
        for p in parts[1:]:
            pl = p.lower()
            if pl in ("flashscore", "livescore", "flashscore.com", path_hint):
                continue
            if " vs " in pl or " v " in pl:
                continue
            candidates.append(p)

    m = re.search(
        r"(?:tournament|competition|event|league)\s*[:\-]\s*([A-Za-z0-9 .&'\-]{3,50})",
        text,
        re.I,
    )
    if m:
        candidates.append(m.group(1).strip())

    if candidates:
        return {"name": candidates[0]}
    return {}


def _extract_game_or_format(html: str, text: str, sport: str) -> str | None:
    m = re.search(
        r'(?:data-game|data-discipline|data-title)=["\']([^"\']+)',
        html,
        re.I,
    )
    if m:
        return m.group(1).strip()
    m = re.search(
        r"\b(CS2|CS:GO|Counter-Strike(?:\s*2)?|LoL|League of Legends|Dota\s*2|Valorant)\b",
        text,
        re.I,
    )
    if m:
        return m.group(1).strip()
    if sport == "baseball":
        m = re.search(r"\b(MLB|NPB|KBO)\b", text, re.I)
        if m:
            return m.group(1).upper()
    return None


def _extract_form(
    html: str, text: str, home_name: str, away_name: str
) -> tuple[str, str]:
    home_form = ""
    away_form = ""

    m = re.search(r'data-home-form=["\']([^"\']+)', html, re.I)
    if m:
        home_form = m.group(1)
    m = re.search(r'data-away-form=["\']([^"\']+)', html, re.I)
    if m:
        away_form = m.group(1)

    patterns_home = (
        r'class="[^"]*form__home[^"]*"[^>]*>(.*?)</(?:div|ul|section)>',
        r'data-testid=["\']form-home["\'][^>]*>(.*?)</',
        r'class="[^"]*form-home[^"]*"[^>]*>(.*?)</',
    )
    patterns_away = (
        r'class="[^"]*form__away[^"]*"[^>]*>(.*?)</(?:div|ul|section)>',
        r'data-testid=["\']form-away["\'][^>]*>(.*?)</',
        r'class="[^"]*form-away[^"]*"[^>]*>(.*?)</',
    )
    if not home_form:
        for pat in patterns_home:
            m = re.search(pat, html, re.I | re.S)
            if m:
                letters = _parse_form_letters(_strip_tags(m.group(1)))
                if len(letters) >= 3:
                    home_form = " ".join(letters)
                    break
    if not away_form:
        for pat in patterns_away:
            m = re.search(pat, html, re.I | re.S)
            if m:
                letters = _parse_form_letters(_strip_tags(m.group(1)))
                if len(letters) >= 3:
                    away_form = " ".join(letters)
                    break

    if not home_form or not away_form:
        badges = re.findall(
            r'class="[^"]*(?:wld|formIcon|form__wld)[^"]*"[^>]*>\s*([WDL])\s*<',
            html,
            re.I,
        )
        if len(badges) >= 6:
            mid = len(badges) // 2
            if not home_form:
                home_form = " ".join(badges[:mid][:5])
            if not away_form:
                away_form = " ".join(badges[mid : mid + 5])

    if home_name and not home_form:
        m = re.search(
            rf"(?:{re.escape(home_name)}\s+form|home\s*form)\s*[:\-]?\s*([WDL\s]{{5,20}})",
            text,
            re.I,
        )
        if m:
            home_form = m.group(1)
    if away_name and not away_form:
        m = re.search(
            rf"(?:{re.escape(away_name)}\s+form|away\s*form)\s*[:\-]?\s*([WDL\s]{{5,20}})",
            text,
            re.I,
        )
        if m:
            away_form = m.group(1)

    return home_form, away_form


def _extract_rank(html: str, text: str, name: str, *, side: str) -> int | None:
    if side == "home":
        m = re.search(r'data-home-rank=["\'](\d+)', html, re.I)
        if m:
            return int(m.group(1))
        m = re.search(
            r'class="[^"]*duelParticipant__home[^"]*".*?'
            r'class="[^"]*(?:participant__participantRank|rank|seed)[^"]*"[^>]*>\s*#?\s*(\d{1,4})',
            html,
            re.I | re.S,
        )
        if m:
            return int(m.group(1))
        m = re.search(
            r"(?:home|player\s*1)\s*(?:rank|ranking|seed)\s*[:#]?\s*(\d{1,4})",
            text,
            re.I,
        )
        if m:
            return int(m.group(1))
    else:
        m = re.search(r'data-away-rank=["\'](\d+)', html, re.I)
        if m:
            return int(m.group(1))
        m = re.search(
            r'class="[^"]*duelParticipant__away[^"]*".*?'
            r'class="[^"]*(?:participant__participantRank|rank|seed)[^"]*"[^>]*>\s*#?\s*(\d{1,4})',
            html,
            re.I | re.S,
        )
        if m:
            return int(m.group(1))
        m = re.search(
            r"(?:away|player\s*2)\s*(?:rank|ranking|seed)\s*[:#]?\s*(\d{1,4})",
            text,
            re.I,
        )
        if m:
            return int(m.group(1))

    if name:
        for pat in (
            rf"{re.escape(name)}[^\n]{{0,40}}?(?:rank|ranking|seed)[:\s#]*(\d{{1,4}})",
            rf"(?:rank|ranking|seed)[:\s#]*(\d{{1,4}})[^\n]{{0,40}}?{re.escape(name)}",
            rf"{re.escape(name)}[^\n]{{0,20}}?#\s*(\d{{1,4}})",
            rf"#\s*(\d{{1,4}})[^\n]{{0,20}}?{re.escape(name)}",
        ):
            m = re.search(pat, text, re.I)
            if m:
                return int(m.group(1))
    return None


def _extract_rating(html: str, text: str, name: str, *, side: str) -> float | None:
    attr = "data-home-rating" if side == "home" else "data-away-rating"
    m = re.search(rf'{attr}=["\']([0-9.]+)', html, re.I)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    if name:
        m = re.search(
            rf"{re.escape(name)}[^\n]{{0,30}}?rating[:\s]*([0-9.]+)",
            text,
            re.I,
        )
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


def _extract_standings_table(
    html: str, home_name: str, away_name: str
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    # Rows: rank | name | pts
    for m in re.finditer(
        r'(?:table__cell--rank|tableCellRank|rank)[^>]*>\s*(\d{1,3})\s*<.*?'
        r'(?:table__cell--name|name)[^>]*>\s*([^<]{2,40})\s*<.*?'
        r'(?:table__cell--points|points)[^>]*>\s*(\d+)',
        html,
        re.I | re.S,
    ):
        rank = int(m.group(1))
        nm = _strip_tags(m.group(2)).strip()
        pts = int(m.group(3))
        if home_name and home_name.lower() in nm.lower():
            out["home"] = rank
            out["home_pts"] = pts
        if away_name and away_name.lower() in nm.lower():
            out["away"] = rank
            out["away_pts"] = pts

    # Simpler data attributes
    m = re.search(r'data-home-rank=["\'](\d+)', html, re.I)
    if m and "home" not in out:
        out["home"] = int(m.group(1))
    m = re.search(r'data-away-rank=["\'](\d+)', html, re.I)
    if m and "away" not in out:
        out["away"] = int(m.group(1))
    return out


def _extract_roster_notes(html: str, text: str) -> str | None:
    m = re.search(
        r'(?:data-roster|data-lineup)=["\']([^"\']+)',
        html,
        re.I,
    )
    if m:
        return m.group(1).strip()
    m = re.search(
        r"(?:roster|line-?up|stand-?in)\s*[:\-]\s*([^\n]{5,80})",
        text,
        re.I,
    )
    if m:
        return m.group(1).strip()
    return None


def _md_form_side(text: str, name: str, *, side: str) -> str:
    if name:
        m = re.search(
            rf"{re.escape(name)}\s+form\s*[:\-]?\s*([WDL\s,|/]{{5,20}})",
            text,
            re.I,
        )
        if m:
            return m.group(1)
    label = "home" if side == "home" else "away"
    m = re.search(
        rf"(?:{label}\s*form|form\s*{label}|last\s*5\s*{label})\s*[:\-]?\s*([WDL\s,|/]{{3,20}})",
        text,
        re.I,
    )
    return m.group(1) if m else ""


def _md_rank(text: str, name: str) -> int | None:
    if not name:
        return None
    for pat in (
        rf"{re.escape(name)}[^\n]{{0,30}}?(?:rank|ranking|seed)[:\s#]*(\d{{1,4}})",
        rf"(?:rank|ranking|seed)[:\s#]*(\d{{1,4}})[^\n]{{0,30}}?{re.escape(name)}",
        rf"{re.escape(name)}\s*#\s*(\d{{1,4}})",
        rf"#\s*(\d{{1,4}})\s*{re.escape(name)}",
    ):
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(1))
    return None
