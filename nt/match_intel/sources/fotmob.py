"""FotMob HTML/JSON fragment parser (football) — offline only."""
from __future__ import annotations

import json
import re
from typing import Any


def parse_fotmob_html(html: str, *, match: str = "") -> dict[str, Any]:
    """
    Parse FotMob-like HTML or embedded JSON for form/ratings/injuries.

    Supports:
    - data-* attributes (same spirit as flashscore fixtures)
    - <script type="application/json" id="mic-fotmob">…</script>
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

    out["sides"] = {"home": home, "away": away}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


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
