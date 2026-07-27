"""
Flashscore HTML → MIC field fragments.

Offline-first: accepts raw HTML string (from fixtures or Firecrawl dump).
Uses BeautifulSoup when installed; otherwise regex/stdlib HTML parsing.
Never hits the network.
"""
from __future__ import annotations

import re
from html import unescape
from typing import Any


def _soup(html: str):
    try:
        from bs4 import BeautifulSoup  # type: ignore

        return BeautifulSoup(html, "html.parser")
    except Exception:  # noqa: BLE001
        return None


def _text_between(html: str, start_pat: str, end_pat: str) -> str:
    m = re.search(start_pat + r"(.*?)" + end_pat, html, flags=re.I | re.S)
    return m.group(1) if m else ""


def _strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_form_letters(text: str) -> list[str]:
    """Extract W/D/L sequence from form strip text."""
    letters = re.findall(r"\b([WDL])\b", text.upper())
    if letters:
        return letters
    # compact form like WWDLW
    m = re.search(r"\b([WDL]{3,10})\b", text.upper())
    if m:
        return list(m.group(1))
    return []


def _parse_scores(text: str) -> list[str]:
    return re.findall(r"\b(\d+\s*[-:]\s*\d+)\b", text)


def parse_flashscore_html(html: str, *, match: str = "") -> dict[str, Any]:
    """
    Parse a Flashscore-like match page HTML into partial MIC fields.

    Expected optional data-* / class hooks used in offline fixtures:
      data-competition, data-home-form, data-away-form, data-home-rank,
      data-away-rank, data-h2h, data-home-name, data-away-name,
      .form-home / .form-away, .standings-home / .standings-away
    """
    out: dict[str, Any] = {
        "competition": {},
        "sides": {"home": {}, "away": {}},
        "h2h": {},
        "referee": {},
        "fields_contributed": [],
        "page_title": "",
        "publisher": "flashscore",
        "method": "bs4" if _soup(html) else "regex",
    }
    if not html or not str(html).strip():
        return out

    soup = _soup(html)
    if soup is not None:
        return _parse_with_bs4(soup, out, match=match)
    return _parse_with_regex(html, out, match=match)


def _parse_with_bs4(soup: Any, out: dict[str, Any], *, match: str) -> dict[str, Any]:
    title_el = soup.find("title")
    if title_el:
        out["page_title"] = title_el.get_text(" ", strip=True)

    # data attributes on root mic-fixture or body
    root = soup.find(attrs={"data-mic": True}) or soup.find("body") or soup

    def _attr(name: str) -> str | None:
        el = soup.find(attrs={name: True})
        if el is not None:
            return el.get(name)
        if root is not None and root.has_attr(name):
            return root.get(name)
        return None

    comp = _attr("data-competition")
    if comp:
        out["competition"] = {"name": comp, "country": _attr("data-country")}
        out["fields_contributed"].append("competition")

    home_name = _attr("data-home-name") or ""
    away_name = _attr("data-away-name") or ""
    if not home_name or not away_name:
        # try event header
        h1 = soup.find(class_=re.compile(r"event|match|participant", re.I))
        if h1:
            out["page_title"] = out["page_title"] or h1.get_text(" ", strip=True)

    home_form = _attr("data-home-form") or ""
    away_form = _attr("data-away-form") or ""
    home_form_el = soup.find(class_=re.compile(r"form[-_]?home", re.I))
    away_form_el = soup.find(class_=re.compile(r"form[-_]?away", re.I))
    if home_form_el and not home_form:
        home_form = home_form_el.get_text(" ", strip=True)
    if away_form_el and not away_form:
        away_form = away_form_el.get_text(" ", strip=True)

    home_side = _side_from_form(home_name, home_form, _attr("data-home-scores") or "")
    away_side = _side_from_form(away_name, away_form, _attr("data-away-scores") or "")

    home_rank = _attr("data-home-rank")
    away_rank = _attr("data-away-rank")
    home_pts = _attr("data-home-points")
    away_pts = _attr("data-away-points")
    if home_rank is not None:
        home_side["standings"] = {
            "rank": _int(home_rank),
            "points": _int(home_pts) if home_pts is not None else None,
        }
        out["fields_contributed"].append("standings_home")
    if away_rank is not None:
        away_side["standings"] = {
            "rank": _int(away_rank),
            "points": _int(away_pts) if away_pts is not None else None,
        }
        out["fields_contributed"].append("standings_away")

    if home_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_home")
    if away_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_away")

    # H2H
    h2h_n = _attr("data-h2h-n")
    h2h_summary = _attr("data-h2h-summary") or ""
    h2h_el = soup.find(class_=re.compile(r"h2h", re.I))
    if h2h_el and not h2h_summary:
        h2h_summary = h2h_el.get_text(" ", strip=True)
    recent = []
    for row in soup.select("[data-h2h-row], .h2h-row"):
        recent.append(
            {
                "date": row.get("data-date") or "",
                "score": row.get("data-score") or row.get_text(" ", strip=True),
                "competition": row.get("data-competition") or "",
            }
        )
    if h2h_n or h2h_summary or recent:
        n = _int(h2h_n) if h2h_n is not None else max(len(recent), 1 if h2h_summary else 0)
        polarity = _attr("data-h2h-polarity")
        out["h2h"] = {
            "n": n or 0,
            "summary": h2h_summary,
            "recent": recent,
            "polarity": polarity,
        }
        if n and n >= 1:
            out["fields_contributed"].append("h2h")

    # Injuries
    injuries_home = []
    injuries_away = []
    for el in soup.select("[data-injury-side=home] .injury, .injury-home li, [data-injury='home']"):
        injuries_home.append(
            {
                "player": el.get("data-player") or el.get_text(" ", strip=True),
                "status": el.get("data-status") or "out",
                "reason": el.get("data-reason") or "injury",
                "source": "flashscore",
            }
        )
    for el in soup.select("[data-injury-side=away] .injury, .injury-away li, [data-injury='away']"):
        injuries_away.append(
            {
                "player": el.get("data-player") or el.get_text(" ", strip=True),
                "status": el.get("data-status") or "out",
                "reason": el.get("data-reason") or "injury",
                "source": "flashscore",
            }
        )
    # Explicit empty injuries section marked fetched
    inj_section = soup.find(attrs={"data-injuries-fetched": True}) or soup.find(
        class_=re.compile(r"injur", re.I)
    )
    if injuries_home or injuries_away or inj_section is not None:
        home_side["injuries_suspensions"] = injuries_home
        away_side["injuries_suspensions"] = injuries_away
        out["fields_contributed"].append("injuries")

    # Home/away split
    home_split = _attr("data-home-wdl")
    away_split = _attr("data-away-wdl")
    if home_split or away_split:
        home_side["home_away_split"] = {
            "home_wdl": home_split,
            "away_wdl": None,
            "notes": None,
        }
        away_side["home_away_split"] = {
            "home_wdl": None,
            "away_wdl": away_split,
            "notes": None,
        }
        out["fields_contributed"].append("home_away_split")

    # Rest days
    home_rest = _attr("data-home-rest")
    away_rest = _attr("data-away-rest")
    if home_rest is not None:
        home_side["rest_days"] = _int(home_rest)
        out["fields_contributed"].append("rest_days")
    if away_rest is not None:
        away_side["rest_days"] = _int(away_rest)
        if "rest_days" not in out["fields_contributed"]:
            out["fields_contributed"].append("rest_days")

    # Referee
    ref_name = _attr("data-referee")
    if ref_name:
        out["referee"] = {"name": ref_name, "cards_tendency": None, "notes": None}
        out["fields_contributed"].append("referee")

    # Motivation tags
    tags = _attr("data-motivation-tags")
    if tags:
        out["motivation_situational"] = {
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "notes": _attr("data-motivation-notes"),
            "final": False,
            "relegation_battle": "relegation" in tags.lower(),
            "title_race": "title" in tags.lower(),
        }
        out["fields_contributed"].append("motivation")

    if home_name:
        home_side["name"] = home_name
    if away_name:
        away_side["name"] = away_name

    out["sides"] = {"home": home_side, "away": away_side}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def _parse_with_regex(html: str, out: dict[str, Any], *, match: str) -> dict[str, Any]:
    def attr(name: str) -> str | None:
        m = re.search(rf'{re.escape(name)}=["\']([^"\']+)["\']', html, flags=re.I)
        return m.group(1) if m else None

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    if title_m:
        out["page_title"] = _strip_tags(title_m.group(1))

    comp = attr("data-competition")
    if comp:
        out["competition"] = {"name": comp, "country": attr("data-country")}
        out["fields_contributed"].append("competition")

    home_name = attr("data-home-name") or ""
    away_name = attr("data-away-name") or ""
    home_side = _side_from_form(
        home_name, attr("data-home-form") or "", attr("data-home-scores") or ""
    )
    away_side = _side_from_form(
        away_name, attr("data-away-form") or "", attr("data-away-scores") or ""
    )

    # class-based form blocks
    home_block = _text_between(html, r'class=["\'][^"\']*form-home[^"\']*["\'][^>]*>', r"</")
    away_block = _text_between(html, r'class=["\'][^"\']*form-away[^"\']*["\'][^>]*>', r"</")
    if home_block and not home_side.get("recent_form", {}).get("results"):
        home_side = _side_from_form(home_name, _strip_tags(home_block), "")
    if away_block and not away_side.get("recent_form", {}).get("results"):
        away_side = _side_from_form(away_name, _strip_tags(away_block), "")

    hr, ar = attr("data-home-rank"), attr("data-away-rank")
    if hr is not None:
        home_side["standings"] = {"rank": _int(hr), "points": _int(attr("data-home-points") or "")}
        out["fields_contributed"].append("standings_home")
    if ar is not None:
        away_side["standings"] = {"rank": _int(ar), "points": _int(attr("data-away-points") or "")}
        out["fields_contributed"].append("standings_away")

    if home_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_home")
    if away_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_away")

    h2h_n = attr("data-h2h-n")
    h2h_summary = attr("data-h2h-summary") or ""
    if h2h_n or h2h_summary:
        n = _int(h2h_n) if h2h_n is not None else (1 if h2h_summary else 0)
        out["h2h"] = {
            "n": n or 0,
            "summary": h2h_summary,
            "recent": [],
            "polarity": attr("data-h2h-polarity"),
        }
        if n and n >= 1:
            out["fields_contributed"].append("h2h")

    if attr("data-injuries-fetched") is not None or re.search(r"injury", html, re.I):
        # Prefer explicit lists; empty list still counts if data-injuries-fetched
        home_side["injuries_suspensions"] = []
        away_side["injuries_suspensions"] = []
        # single injury rows
        for m in re.finditer(
            r'data-injury=["\']home["\'][^>]*>([^<]+)', html, flags=re.I
        ):
            home_side["injuries_suspensions"].append(
                {"player": _strip_tags(m.group(1)), "status": "out", "reason": "injury", "source": "flashscore"}
            )
        for m in re.finditer(
            r'data-injury=["\']away["\'][^>]*>([^<]+)', html, flags=re.I
        ):
            away_side["injuries_suspensions"].append(
                {"player": _strip_tags(m.group(1)), "status": "out", "reason": "injury", "source": "flashscore"}
            )
        if attr("data-injuries-fetched") is not None or home_side["injuries_suspensions"] or away_side["injuries_suspensions"]:
            out["fields_contributed"].append("injuries")

    home_split, away_split = attr("data-home-wdl"), attr("data-away-wdl")
    if home_split or away_split:
        home_side["home_away_split"] = {"home_wdl": home_split, "away_wdl": None, "notes": None}
        away_side["home_away_split"] = {"home_wdl": None, "away_wdl": away_split, "notes": None}
        out["fields_contributed"].append("home_away_split")

    if attr("data-home-rest") is not None:
        home_side["rest_days"] = _int(attr("data-home-rest") or "0")
        out["fields_contributed"].append("rest_days")
    if attr("data-away-rest") is not None:
        away_side["rest_days"] = _int(attr("data-away-rest") or "0")
        if "rest_days" not in out["fields_contributed"]:
            out["fields_contributed"].append("rest_days")

    ref = attr("data-referee")
    if ref:
        out["referee"] = {"name": ref, "cards_tendency": None, "notes": None}
        out["fields_contributed"].append("referee")

    tags = attr("data-motivation-tags")
    if tags:
        out["motivation_situational"] = {
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "notes": attr("data-motivation-notes"),
            "final": False,
            "relegation_battle": "relegation" in tags.lower(),
            "title_race": "title" in tags.lower(),
        }
        out["fields_contributed"].append("motivation")

    if home_name:
        home_side["name"] = home_name
    if away_name:
        away_side["name"] = away_name
    out["sides"] = {"home": home_side, "away": away_side}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def _side_from_form(name: str, form_text: str, scores_text: str) -> dict[str, Any]:
    letters = _parse_form_letters(form_text)
    scores = _parse_scores(scores_text or form_text)
    n = len(letters)
    return {
        "name": name or "",
        "recent_form": {
            "n": n,
            "results": letters,
            "scores": scores,
            "summary": form_text.strip() if form_text else "",
        },
    }


def _int(x: str | None) -> int | None:
    if x is None or str(x).strip() == "":
        return None
    try:
        return int(str(x).strip())
    except ValueError:
        return None
