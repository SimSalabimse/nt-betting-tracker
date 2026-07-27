"""
Live tennis parsers (Flashscore-like HTML / Firecrawl markdown / XHR).

PR-4: fill MIC critical keys form_or_rank_home/away + competition (and optional
surface / H2H). Offline-only; never hits the network.

Reuses shared Flashscore live helpers (bundle parts, merge, form letters, H2H).
"""
from __future__ import annotations

import re
from typing import Any

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
    _merge_two,
    _parse_form_letters,
    _parse_json_ld,
    _side_from_form,
    _split_match,
    _split_title_teams,
    _strip_tags,
    _walk_json_objects,
    parse_flashscore_xhr,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_tennis_bundle(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "tennis",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Parse a MatchFetchBundle into a tennis MIC fragment.

    Priority:
      1. XHR / embedded JSON
      2. summary_html + h2h_html live DOM
      3. Firecrawl markdown
      4. Shared football XHR walk as soft fallback (rank/form shapes overlap)
    """
    _ = sport, cfg
    html, markdown, h2h_html, xhrs, page_meta, url, method = _bundle_parts(bundle)

    fragments: list[dict[str, Any]] = []

    if xhrs:
        frag_x = parse_tennis_xhr(xhrs, match=match)
        if _fields(frag_x) or _sides_useful(frag_x):
            fragments.append(frag_x)
        # Shared XHR walker often sees the same home/away form+rank blobs
        frag_fs = parse_flashscore_xhr(xhrs, match=match)
        if _fields(frag_fs):
            # Map football-ish field tags → tennis form_or_rank credits later
            fragments.append(frag_fs)

    combined_html = html or ""
    if h2h_html and h2h_html not in combined_html:
        combined_html = f"{combined_html}\n{h2h_html}"
    if combined_html.strip():
        frag_h = parse_tennis_live_html(combined_html, match=match, page_meta=page_meta)
        if _fields(frag_h) or _sides_useful(frag_h):
            fragments.append(frag_h)

    if markdown and str(markdown).strip():
        frag_m = parse_tennis_markdown(str(markdown), match=match)
        if _fields(frag_m) or _sides_useful(frag_m):
            fragments.append(frag_m)

    merged = _merge_frag_list(fragments)
    merged = _normalize_tennis_fields(merged)

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
    merged = _normalize_tennis_fields(merged)
    if not merged.get("page_title") and page_meta.get("title"):
        merged["page_title"] = page_meta["title"]
    return merged


def parse_tennis_live_html(
    html: str,
    *,
    match: str = "",
    page_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse Flashscore-like tennis match HTML (players, rank, form, surface)."""
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
                r'data-testid=["\']home-player["\'][^>]*>([^<]+)',
                r'data-testid=["\']home-team["\'][^>]*>([^<]+)',
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
                r'data-testid=["\']away-player["\'][^>]*>([^<]+)',
                r'data-testid=["\']away-team["\'][^>]*>([^<]+)',
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

    # Competition / tournament
    comp = _extract_tennis_competition(html, title=title, page_meta=page_meta, text=text)
    if comp:
        out["competition"] = comp
        out["fields_contributed"].append("competition")

    # Surface → competition.format
    surface = _extract_surface(html, text)
    if surface:
        out["competition"] = {**(out.get("competition") or {}), "format": surface}
        out["fields_contributed"].append("surface")

    # Form (W/L strips — tennis rarely draws)
    home_form, away_form = _extract_tennis_form(html, text, home_name, away_name)
    home_side = _side_from_form(home_name, home_form)
    away_side = _side_from_form(away_name, away_form)

    # ATP / WTA rank
    home_rank = _extract_player_rank(html, text, home_name, side="home")
    away_rank = _extract_player_rank(html, text, away_name, side="away")
    if home_rank is not None:
        home_side["standings"] = {"rank": home_rank, "points": None}
        out["fields_contributed"].append("form_or_rank_home")
    if away_rank is not None:
        away_side["standings"] = {"rank": away_rank, "points": None}
        out["fields_contributed"].append("form_or_rank_away")

    if home_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_or_rank_home")
        out["fields_contributed"].append("form_home")
    if away_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_or_rank_away")
        out["fields_contributed"].append("form_away")

    # H2H
    h2h = _extract_h2h(html, text)
    if h2h and (h2h.get("n") or h2h.get("summary") or h2h.get("recent")):
        out["h2h"] = h2h
        if int(h2h.get("n") or 0) >= 1 or h2h.get("summary"):
            out["fields_contributed"].append("h2h")

    # JSON-LD
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
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def parse_tennis_markdown(md: str, *, match: str = "") -> dict[str, Any]:
    """Parse Firecrawl-style markdown for tennis match pages."""
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

    # Competition
    comp = ""
    m = re.search(
        r"(?:^|\n)(?:competition|tournament|event)\s*[:\-]\s*(.+)$",
        text,
        re.I | re.M,
    )
    if m:
        comp = m.group(1).strip()
    if not comp:
        heads = re.findall(r"^#{1,3}\s+(.+)$", text, re.M)
        for h in heads[1:]:
            hl = h.lower()
            if any(x in hl for x in ("atp", "wta", "challenger", "open", "masters", "grand")):
                comp = h.strip()
                break
            if "surface" in hl or "form" in hl or "h2h" in hl or "rank" in hl:
                continue
            if " vs " not in hl and len(h.strip()) >= 3:
                comp = h.strip()
                break
    if comp:
        out["competition"] = {"name": comp}
        out["fields_contributed"].append("competition")

    # Surface
    sm = re.search(
        r"(?:surface|court)\s*[:\-]?\s*(hard|clay|grass|carpet|indoor\s*hard)",
        text,
        re.I,
    )
    if sm:
        surface = re.sub(r"\s+", "_", sm.group(1).strip().lower())
        out["competition"] = {**(out.get("competition") or {}), "format": surface}
        out["fields_contributed"].append("surface")

    # Form
    home_form = _md_form_side(text, home_name, side="home")
    away_form = _md_form_side(text, away_name, side="away")
    if not home_form or not away_form:
        m = re.search(
            r"form\s*[:\-]?\s*([WL]{3,10})\s*[|/]\s*([WL]{3,10})",
            text,
            re.I,
        )
        if m:
            home_form = home_form or m.group(1)
            away_form = away_form or m.group(2)

    home_side = _side_from_form(home_name, home_form or "")
    away_side = _side_from_form(away_name, away_form or "")

    # Rank lines: "Arnaldi Rank: 36" / "ATP: 36" / "#36 Arnaldi"
    hr = _md_rank(text, home_name)
    ar = _md_rank(text, away_name)
    if hr is not None:
        home_side["standings"] = {"rank": hr, "points": None}
        out["fields_contributed"].append("form_or_rank_home")
    if ar is not None:
        away_side["standings"] = {"rank": ar, "points": None}
        out["fields_contributed"].append("form_or_rank_away")

    if home_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_or_rank_home")
        out["fields_contributed"].append("form_home")
    if away_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_or_rank_away")
        out["fields_contributed"].append("form_away")

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

    out["sides"] = {"home": home_side, "away": away_side}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def parse_tennis_xhr(
    xhrs: list[Any],
    *,
    match: str = "",
) -> dict[str, Any]:
    """Extract rank / form / tournament / H2H from tennis XHR JSON captures."""
    out = _empty_frag(publisher="flashscore", method="xhr_json")
    if not xhrs:
        return out

    home_name, away_name = _split_match(match) if match else ("", "")
    home_letters: list[str] = []
    away_letters: list[str] = []
    home_rank = away_rank = None
    h2h_recent: list[dict[str, Any]] = []
    comp_name = ""
    surface = ""

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
                "tourName",
            ):
                v = obj.get(k)
                if isinstance(v, str) and 3 <= len(v) <= 80 and not comp_name:
                    if v.lower() not in ("match", "summary", "tennis", "atp", "wta"):
                        if k != "name":
                            comp_name = v
                if isinstance(v, dict):
                    nm = v.get("name") or v.get("tournamentName")
                    if isinstance(nm, str) and 3 <= len(nm) <= 80:
                        comp_name = comp_name or nm
                    surf = v.get("surface") or v.get("court") or v.get("groundType")
                    if isinstance(surf, str) and surf.strip():
                        surface = surface or surf.strip().lower()

            for sk in ("surface", "court", "groundType", "ground"):
                if isinstance(obj.get(sk), str) and obj[sk].strip():
                    surface = surface or str(obj[sk]).strip().lower()

            if "home" in obj and isinstance(obj["home"], dict):
                r = _int(
                    obj["home"].get("rank")
                    or obj["home"].get("ranking")
                    or obj["home"].get("atpRank")
                    or obj["home"].get("wtaRank")
                )
                if r is not None:
                    home_rank = home_rank if home_rank is not None else r
                letters = _letters_from_any(
                    obj["home"].get("form")
                    or obj["home"].get("lastMatches")
                    or obj["home"].get("recentForm")
                )
                # Tennis W/L only — drop D if present in shared helper
                letters = [x for x in letters if x in ("W", "L")] or letters
                if len(letters) > len(home_letters):
                    home_letters = letters
                if obj["home"].get("name") and not home_name:
                    home_name = str(obj["home"]["name"])

            if "away" in obj and isinstance(obj["away"], dict):
                r = _int(
                    obj["away"].get("rank")
                    or obj["away"].get("ranking")
                    or obj["away"].get("atpRank")
                    or obj["away"].get("wtaRank")
                )
                if r is not None:
                    away_rank = away_rank if away_rank is not None else r
                letters = _letters_from_any(
                    obj["away"].get("form")
                    or obj["away"].get("lastMatches")
                    or obj["away"].get("recentForm")
                )
                letters = [x for x in letters if x in ("W", "L")] or letters
                if len(letters) > len(away_letters):
                    away_letters = letters
                if obj["away"].get("name") and not away_name:
                    away_name = str(obj["away"]["name"])

            # player1 / player2 alternate keys
            for pkey, is_home in (("player1", True), ("player2", False), ("p1", True), ("p2", False)):
                p = obj.get(pkey)
                if not isinstance(p, dict):
                    continue
                r = _int(p.get("rank") or p.get("ranking") or p.get("atpRank"))
                letters = _letters_from_any(p.get("form") or p.get("lastMatches"))
                nm = p.get("name")
                if is_home:
                    if r is not None and home_rank is None:
                        home_rank = r
                    if len(letters) > len(home_letters):
                        home_letters = letters
                    if nm and not home_name:
                        home_name = str(nm)
                else:
                    if r is not None and away_rank is None:
                        away_rank = r
                    if len(letters) > len(away_letters):
                        away_letters = letters
                    if nm and not away_name:
                        away_name = str(nm)

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
        home_side["standings"] = {"rank": home_rank, "points": None}
        out["fields_contributed"].append("form_or_rank_home")
    if away_rank is not None:
        away_side["standings"] = {"rank": away_rank, "points": None}
        out["fields_contributed"].append("form_or_rank_away")
    if len(home_letters) >= 3:
        out["fields_contributed"].append("form_or_rank_home")
        out["fields_contributed"].append("form_home")
    if len(away_letters) >= 3:
        out["fields_contributed"].append("form_or_rank_away")
        out["fields_contributed"].append("form_away")
    if comp_name:
        out["competition"] = {"name": comp_name}
        out["fields_contributed"].append("competition")
    if surface:
        surf = re.sub(r"\s+", "_", surface.lower())
        if surf in ("hard", "clay", "grass", "carpet", "indoor_hard", "indoor-hard"):
            surf = surf.replace("-", "_")
            out["competition"] = {**(out.get("competition") or {}), "format": surf}
            out["fields_contributed"].append("surface")
    if h2h_recent:
        out["h2h"] = {
            "n": len(h2h_recent),
            "summary": "",
            "recent": h2h_recent,
            "polarity": None,
        }
        out["fields_contributed"].append("h2h")
    out["sides"] = {"home": home_side, "away": away_side}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _sides_useful(frag: dict[str, Any] | None) -> bool:
    if not frag:
        return False
    for sk in ("home", "away"):
        side = (frag.get("sides") or {}).get(sk) or {}
        rf = side.get("recent_form") or {}
        if int(rf.get("n") or 0) >= 3 and rf.get("results"):
            return True
        if (side.get("standings") or {}).get("rank") is not None:
            return True
    if str((frag.get("competition") or {}).get("name") or "").strip():
        return True
    return False


def _normalize_tennis_fields(frag: dict[str, Any]) -> dict[str, Any]:
    """Ensure form_or_rank_* credits from form n≥3 or rank; drop football-only noise tags."""
    out = dict(frag)
    fields = list(out.get("fields_contributed") or [])
    sides = out.get("sides") or {}
    for sk, fok in (("home", "form_or_rank_home"), ("away", "form_or_rank_away")):
        side = sides.get(sk) or {}
        n = int((side.get("recent_form") or {}).get("n") or 0)
        results = (side.get("recent_form") or {}).get("results") or []
        has_rank = (side.get("standings") or {}).get("rank") is not None
        if (n >= 3 and results) or has_rank:
            if fok not in fields:
                fields.append(fok)
    if (out.get("competition") or {}).get("name") and "competition" not in fields:
        fields.append("competition")
    fmt = str((out.get("competition") or {}).get("format") or "").lower()
    if fmt in ("hard", "clay", "grass", "carpet", "indoor_hard") and "surface" not in fields:
        fields.append("surface")
    if int((out.get("h2h") or {}).get("n") or 0) >= 1 and "h2h" not in fields:
        fields.append("h2h")
    out["fields_contributed"] = sorted(set(fields))
    return out


def _extract_tennis_competition(
    html: str,
    *,
    title: str,
    page_meta: dict[str, Any],
    text: str,
) -> dict[str, Any]:
    hint = str(page_meta.get("competition_hint") or "").strip()
    if hint:
        return {"name": hint, "country": page_meta.get("country")}

    candidates: list[str] = []
    for pat in (
        r'class="[^"]*(?:tournamentHeader|tournament|breadcrumb|wcl-breadcrumb|event__title)[^"]*"[^>]*>([^<]{3,60})',
        r'data-competition=["\']([^"\']+)',
        r'data-tournament=["\']([^"\']+)',
        r'<a[^>]+href="[^"]*/tennis/[^"]+"/[^>]*>([^<]{3,50})</a>',
    ):
        for m in re.finditer(pat, html, flags=re.I):
            val = _strip_tags(m.group(1)).strip()
            if val and val.lower() not in (
                "tennis",
                "home",
                "flashscore",
                "standings",
                "h2h",
                "atp",
                "wta",
            ):
                candidates.append(val)

    if title and "|" in title:
        parts = [p.strip() for p in title.split("|")]
        for p in parts[1:]:
            pl = p.lower()
            if pl in ("flashscore", "livescore", "flashscore.com", "tennis"):
                continue
            if " vs " in pl or " v " in pl:
                continue
            candidates.append(p)

    # Plain text tournament label
    m = re.search(
        r"(?:tournament|competition|event)\s*[:\-]\s*([A-Za-z0-9 .&'\-]{3,50})",
        text,
        re.I,
    )
    if m:
        candidates.append(m.group(1).strip())

    if candidates:
        return {"name": candidates[0]}
    return {}


def _extract_surface(html: str, text: str) -> str | None:
    m = re.search(
        r'(?:data-surface|data-court)=["\']([^"\']+)',
        html,
        re.I,
    )
    if m:
        return _norm_surface(m.group(1))
    m = re.search(
        r'class="[^"]*surface[^"]*"[^>]*>([^<]{3,20})',
        html,
        re.I,
    )
    if m:
        return _norm_surface(m.group(1))
    m = re.search(
        r"\b(hard|clay|grass|carpet|indoor\s*hard)\b(?:\s*court)?",
        text,
        re.I,
    )
    if m:
        return _norm_surface(m.group(1))
    return None


def _norm_surface(raw: str) -> str | None:
    s = re.sub(r"\s+", "_", (raw or "").strip().lower())
    s = s.replace("-", "_")
    if s in ("hard", "clay", "grass", "carpet", "indoor_hard"):
        return s
    if "hard" in s and "indoor" in s:
        return "indoor_hard"
    if "clay" in s:
        return "clay"
    if "grass" in s:
        return "grass"
    if "carpet" in s:
        return "carpet"
    if "hard" in s:
        return "hard"
    return None


def _extract_tennis_form(
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
                # Prefer W/L; keep D if present
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
            rf"(?:{re.escape(home_name)}\s+form|home\s*form|player\s*1\s*form)\s*[:\-]?\s*([WDL\s]{{5,20}})",
            text,
            re.I,
        )
        if m:
            home_form = m.group(1)
    if away_name and not away_form:
        m = re.search(
            rf"(?:{re.escape(away_name)}\s+form|away\s*form|player\s*2\s*form)\s*[:\-]?\s*([WDL\s]{{5,20}})",
            text,
            re.I,
        )
        if m:
            away_form = m.group(1)

    return home_form, away_form


def _extract_player_rank(
    html: str, text: str, name: str, *, side: str
) -> int | None:
    """ATP/WTA style rank near player name or side-scoped data attributes."""
    if side == "home":
        m = re.search(r'data-home-rank=["\'](\d+)', html, re.I)
        if m:
            return int(m.group(1))
    else:
        m = re.search(r'data-away-rank=["\'](\d+)', html, re.I)
        if m:
            return int(m.group(1))

    # participant rank badge next to home/away block
    if side == "home":
        m = re.search(
            r'class="[^"]*duelParticipant__home[^"]*".*?'
            r'class="[^"]*(?:participant__participantRank|rank|atpRank|wtaRank)[^"]*"[^>]*>\s*#?\s*(\d{1,3})',
            html,
            re.I | re.S,
        )
        if m:
            return int(m.group(1))
    else:
        m = re.search(
            r'class="[^"]*duelParticipant__away[^"]*".*?'
            r'class="[^"]*(?:participant__participantRank|rank|atpRank|wtaRank)[^"]*"[^>]*>\s*#?\s*(\d{1,3})',
            html,
            re.I | re.S,
        )
        if m:
            return int(m.group(1))

    if name:
        for pat in (
            rf"{re.escape(name)}[^\n]{{0,40}}?(?:rank|ranking|atp|wta)[:\s#]*(\d{{1,3}})",
            rf"(?:rank|ranking|atp|wta)[:\s#]*(\d{{1,3}})[^\n]{{0,40}}?{re.escape(name)}",
            rf"{re.escape(name)}[^\n]{{0,20}}?#\s*(\d{{1,3}})",
            rf"#\s*(\d{{1,3}})[^\n]{{0,20}}?{re.escape(name)}",
        ):
            m = re.search(pat, text, re.I)
            if m:
                return int(m.group(1))

    # Side-labeled: Home rank: 12 / Player 1 rank: 12
    if side == "home":
        m = re.search(
            r"(?:home|player\s*1)\s*(?:rank|ranking)\s*[:#]?\s*(\d{1,3})",
            text,
            re.I,
        )
        if m:
            return int(m.group(1))
    else:
        m = re.search(
            r"(?:away|player\s*2)\s*(?:rank|ranking)\s*[:#]?\s*(\d{1,3})",
            text,
            re.I,
        )
        if m:
            return int(m.group(1))
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
        rf"{re.escape(name)}[^\n]{{0,30}}?(?:rank|ranking|atp|wta)[:\s#]*(\d{{1,3}})",
        rf"(?:rank|ranking|atp|wta)[:\s#]*(\d{{1,3}})[^\n]{{0,30}}?{re.escape(name)}",
        rf"{re.escape(name)}\s*#\s*(\d{{1,3}})",
        rf"#\s*(\d{{1,3}})\s*{re.escape(name)}",
    ):
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(1))
    return None
