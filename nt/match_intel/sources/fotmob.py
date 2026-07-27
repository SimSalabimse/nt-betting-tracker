"""FotMob HTML/JSON fragment parser (football) — offline + live secondary."""
from __future__ import annotations

import json
import re
from html import unescape
from typing import Any


def parse_fotmob_html(html: str, *, match: str = "") -> dict[str, Any]:
    """
    Parse FotMob-like HTML or embedded JSON for form/ratings/injuries.

    Supports:
    - data-* attributes (same spirit as flashscore fixtures)
    - <script type="application/json" id="mic-fotmob">…</script>
    - Live-ish markdown/HTML patterns via parse_fotmob_live_content
    """
    out: dict[str, Any] = {
        "competition": {},
        "sides": {"home": {}, "away": {}},
        "h2h": {},
        "fields_contributed": [],
        "publisher": "fotmob",
        "method": "regex",
        "page_title": "",
    }
    if not html or not str(html).strip():
        return out

    # Embedded JSON block
    m = re.search(
        r'<script[^>]+id=["\']mic-fotmob["\'][^>]*>(.*?)</script>',
        html,
        flags=re.I | re.S,
    )
    if m:
        try:
            data = json.loads(m.group(1).strip())
            return _from_json(data, out)
        except json.JSONDecodeError:
            pass

    def attr(name: str) -> str | None:
        mm = re.search(rf'{re.escape(name)}=["\']([^"\']+)["\']', html, flags=re.I)
        return mm.group(1) if mm else None

    home_name = attr("data-home-name") or ""
    away_name = attr("data-away-name") or ""
    home: dict[str, Any] = {"name": home_name}
    away: dict[str, Any] = {"name": away_name}

    hr = attr("data-home-rating")
    ar = attr("data-away-rating")
    if hr is not None:
        try:
            home["rating"] = float(hr)
            out["fields_contributed"].append("standings_or_rank")
        except ValueError:
            pass
    if ar is not None:
        try:
            away["rating"] = float(ar)
            if "standings_or_rank" not in out["fields_contributed"]:
                out["fields_contributed"].append("standings_or_rank")
        except ValueError:
            pass

    home_form = attr("data-home-form") or ""
    away_form = attr("data-away-form") or ""
    if home_form:
        letters = list(re.sub(r"[^WDL]", "", home_form.upper()))
        home["recent_form"] = {
            "n": len(letters),
            "results": letters,
            "scores": [],
            "summary": home_form,
        }
        if len(letters) >= 3:
            out["fields_contributed"].append("form_home")
    if away_form:
        letters = list(re.sub(r"[^WDL]", "", away_form.upper()))
        away["recent_form"] = {
            "n": len(letters),
            "results": letters,
            "scores": [],
            "summary": away_form,
        }
        if len(letters) >= 3:
            out["fields_contributed"].append("form_away")

    comp = attr("data-competition")
    if comp:
        out["competition"] = {"name": comp}
        out["fields_contributed"].append("competition")

    # If data-* thin, try live content patterns on same HTML
    if not out["fields_contributed"]:
        live = parse_fotmob_live_content(html=html, markdown="", match=match)
        if live.get("fields_contributed"):
            return live

    out["sides"] = {"home": home, "away": away}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def parse_fotmob_live_content(
    *,
    html: str = "",
    markdown: str = "",
    match: str = "",
) -> dict[str, Any]:
    """
    Secondary live extract for FotMob HTML or Firecrawl markdown.

    Used when Flashscore is thin on form/rank. Patterns are fixture-driven
    (realistic class names / markdown labels), not a full FotMob SPA reverse.
    """
    out: dict[str, Any] = {
        "competition": {},
        "sides": {"home": {}, "away": {}},
        "h2h": {},
        "fields_contributed": [],
        "publisher": "fotmob",
        "method": "live",
        "page_title": "",
    }
    blob = (html or "") + "\n" + (markdown or "")
    if not blob.strip():
        return out

    # Prefer offline data-* / embedded JSON first
    if html and (
        "data-home-form" in html
        or "mic-fotmob" in html
        or "data-home-name" in html
    ):
        offline = parse_fotmob_html(html, match=match)
        if offline.get("fields_contributed"):
            offline["method"] = "live_or_offline"
            return offline

    home_name, away_name = _split_match(match)
    text = _strip_tags(blob)

    m_title = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    if m_title:
        out["page_title"] = _strip_tags(m_title.group(1))
    elif markdown:
        mh = re.search(r"^#\s+(.+)$", markdown, re.M)
        if mh:
            out["page_title"] = mh.group(1).strip()

    # Competition
    m = re.search(
        r"(?:competition|league|tournament)\s*[:\-]\s*([^\n<]{3,50})",
        blob,
        re.I,
    )
    if m:
        out["competition"] = {"name": m.group(1).strip()}
        out["fields_contributed"].append("competition")
    else:
        m = re.search(
            r'class="[^"]*(?:LeagueHeader|league-header|competition)[^"]*"[^>]*>([^<]{3,50})',
            html or "",
            re.I,
        )
        if m:
            out["competition"] = {"name": _strip_tags(m.group(1))}
            out["fields_contributed"].append("competition")

    # Form
    home_form = _find_form(blob, home_name, "home")
    away_form = _find_form(blob, away_name, "away")
    home: dict[str, Any] = {"name": home_name}
    away: dict[str, Any] = {"name": away_name}
    if home_form:
        letters = list(re.sub(r"[^WDL]", "", home_form.upper()))
        home["recent_form"] = {
            "n": len(letters),
            "results": letters,
            "scores": [],
            "summary": home_form,
        }
        if len(letters) >= 3:
            out["fields_contributed"].append("form_home")
    if away_form:
        letters = list(re.sub(r"[^WDL]", "", away_form.upper()))
        away["recent_form"] = {
            "n": len(letters),
            "results": letters,
            "scores": [],
            "summary": away_form,
        }
        if len(letters) >= 3:
            out["fields_contributed"].append("form_away")

    # Rank / rating
    for name, side in ((home_name, home), (away_name, away)):
        if not name:
            continue
        m = re.search(
            rf"{re.escape(name)}[^\n]{{0,40}}?(?:rank|pos)\s*[:#]?\s*(\d{{1,2}})",
            text,
            re.I,
        )
        if m:
            side["standings"] = {"rank": int(m.group(1)), "points": None}
            out["fields_contributed"].append("standings_or_rank")
        m = re.search(
            rf"{re.escape(name)}[^\n]{{0,40}}?rating\s*[:#]?\s*(\d+(?:\.\d+)?)",
            text,
            re.I,
        )
        if m:
            try:
                side["rating"] = float(m.group(1))
                out["fields_contributed"].append("standings_or_rank")
            except ValueError:
                pass

    out["sides"] = {"home": home, "away": away}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def _find_form(blob: str, name: str, side: str) -> str:
    if name:
        m = re.search(
            rf"{re.escape(name)}[^\n]{{0,30}}form\s*[:\-]?\s*([WDL\s,|/]{{3,20}})",
            blob,
            re.I,
        )
        if m:
            return m.group(1)
    m = re.search(
        rf"{side}\s*form\s*[:\-]?\s*([WDL\s,|/]{{3,20}})",
        blob,
        re.I,
    )
    return m.group(1) if m else ""


def _split_match(match: str) -> tuple[str, str]:
    m = (match or "").strip()
    for sep in (" vs ", " v ", " - ", " – ", " — "):
        if sep in m:
            a, b = m.split(sep, 1)
            return a.strip(), b.strip()
    return m, ""


def _strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _from_json(data: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return out
    if data.get("competition"):
        out["competition"] = (
            data["competition"]
            if isinstance(data["competition"], dict)
            else {"name": str(data["competition"])}
        )
        out["fields_contributed"].append("competition")
    sides = data.get("sides") or {}
    if isinstance(sides, dict):
        out["sides"] = sides
        for label, key in (("home", "form_home"), ("away", "form_away")):
            side = sides.get(label) or {}
            rf = side.get("recent_form") or {}
            if isinstance(rf, dict) and int(rf.get("n") or 0) >= 3:
                out["fields_contributed"].append(key)
            if side.get("rating") is not None or (side.get("standings") or {}).get("rank") is not None:
                out["fields_contributed"].append("standings_or_rank")
    if data.get("h2h"):
        out["h2h"] = data["h2h"]
        out["fields_contributed"].append("h2h")
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    out["method"] = "json"
    return out
