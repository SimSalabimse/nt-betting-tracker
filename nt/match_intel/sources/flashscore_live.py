"""
Live Flashscore (and Firecrawl markdown) → MIC field fragments.

PR-3: parse **real** Flashscore-like HTML/markdown/XHR shapes into form, H2H,
standings, competition — not only offline data-* fixtures.

Offline fixtures with data-* attributes remain handled by
``sources.flashscore.parse_flashscore_html`` (fallback after live extractors).

Never hits the network. Bundle / HTML / markdown only.
"""
from __future__ import annotations

import json
import re
from html import unescape
from typing import Any

from nt.match_intel.sources.flashscore import parse_flashscore_html

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_football_bundle(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "football",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Parse a MatchFetchBundle (or dict-like) into a MIC fragment.

    Priority:
      1. XHR / embedded JSON (structured)
      2. summary_html + h2h_html live DOM patterns
      3. Firecrawl markdown
      4. Offline data-* fallback (parse_flashscore_html)
      5. FotMob secondary if present on bundle and still thin
    """
    _ = sport, cfg  # reserved for multi-sport / config knobs
    html, markdown, h2h_html, xhrs, page_meta, url, method = _bundle_parts(bundle)

    fragments: list[dict[str, Any]] = []

    # 1) XHR JSON
    if xhrs:
        frag_x = parse_flashscore_xhr(xhrs, match=match)
        if _fields(frag_x):
            fragments.append(frag_x)

    # 2) Live HTML (summary + optional H2H resource)
    combined_html = html or ""
    if h2h_html and h2h_html not in combined_html:
        combined_html = f"{combined_html}\n{h2h_html}"
    if combined_html.strip():
        frag_h = parse_flashscore_live_html(combined_html, match=match, page_meta=page_meta)
        if _fields(frag_h) or frag_h.get("sides"):
            fragments.append(frag_h)

    # 3) Markdown (Firecrawl)
    if markdown and str(markdown).strip():
        frag_m = parse_flashscore_markdown(str(markdown), match=match)
        if _fields(frag_m) or frag_m.get("sides"):
            fragments.append(frag_m)

    # 4) Offline data-* fallback (tests / synthetic dumps that still use data-*)
    if combined_html.strip():
        frag_off = parse_flashscore_html(combined_html, match=match)
        if _fields(frag_off):
            fragments.append(frag_off)

    # 5) FotMob secondary when still thin on form/rank
    merged = _merge_frag_list(fragments)
    if _needs_fotmob_secondary(merged):
        try:
            from nt.match_intel.sources.fotmob import parse_fotmob_live_content

            fot_html = ""
            fot_md = ""
            # Bundle may carry fotmob resources under resources.fotmob_* or html tagged
            if isinstance(bundle, dict):
                res = bundle.get("resources") or {}
                fot_html = str(res.get("fotmob_html") or res.get("secondary_html") or "")
                fot_md = str(res.get("fotmob_markdown") or "")
            else:
                res = getattr(bundle, "resources", None) or {}
                if isinstance(res, dict):
                    fot_html = str(res.get("fotmob_html") or res.get("secondary_html") or "")
                    fot_md = str(res.get("fotmob_markdown") or "")
            if fot_html or fot_md:
                frag_f = parse_fotmob_live_content(
                    html=fot_html, markdown=fot_md, match=match
                )
                if _fields(frag_f):
                    merged = _merge_two(merged, frag_f)
        except Exception:  # noqa: BLE001
            pass

    if not merged.get("publisher"):
        merged["publisher"] = "flashscore"
    if not merged.get("method"):
        merged["method"] = method or "live_parse"
    if url:
        merged["url"] = url

    # Page meta names if sides still empty names
    home_side = (merged.get("sides") or {}).get("home") or {}
    away_side = (merged.get("sides") or {}).get("away") or {}
    if page_meta:
        if not home_side.get("name") and page_meta.get("home_name"):
            home_side = dict(home_side)
            home_side["name"] = page_meta["home_name"]
        if not away_side.get("name") and page_meta.get("away_name"):
            away_side = dict(away_side)
            away_side["name"] = page_meta["away_name"]
        if not (merged.get("competition") or {}).get("name") and page_meta.get(
            "competition_hint"
        ):
            merged["competition"] = {
                **(merged.get("competition") or {}),
                "name": page_meta["competition_hint"],
            }
            if "competition" not in merged.get("fields_contributed", []):
                merged.setdefault("fields_contributed", []).append("competition")
    # Fill names from match string
    if match:
        mh, ma = _split_match(match)
        if mh and not home_side.get("name"):
            home_side = dict(home_side)
            home_side["name"] = mh
        if ma and not away_side.get("name"):
            away_side = dict(away_side)
            away_side["name"] = ma
    merged["sides"] = {"home": home_side, "away": away_side}
    merged["fields_contributed"] = sorted(set(merged.get("fields_contributed") or []))
    if not merged.get("page_title") and page_meta.get("title"):
        merged["page_title"] = page_meta["title"]
    return merged


def parse_flashscore_live_html(
    html: str,
    *,
    match: str = "",
    page_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse Flashscore-like match HTML (real class names / JSON-LD / meta)."""
    out = _empty_frag(publisher="flashscore", method="live_html")
    if not html or not str(html).strip():
        return out

    page_meta = page_meta or {}
    text = _strip_tags(html)

    # --- identity / title ---
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

    # --- competition ---
    comp = _extract_competition(html, title=title, page_meta=page_meta)
    if comp:
        out["competition"] = comp
        out["fields_contributed"].append("competition")

    # --- form ---
    home_form, away_form = _extract_form_pairs(html, text, home_name, away_name)
    home_side = _side_from_form(home_name, home_form)
    away_side = _side_from_form(away_name, away_form)

    # --- standings / rank ---
    home_rank, home_pts, away_rank, away_pts = _extract_standings(
        html, text, home_name, away_name
    )
    if home_rank is not None:
        home_side["standings"] = {"rank": home_rank, "points": home_pts}
        out["fields_contributed"].append("standings_home")
    if away_rank is not None:
        away_side["standings"] = {"rank": away_rank, "points": away_pts}
        out["fields_contributed"].append("standings_away")

    if home_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_home")
    if away_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_away")

    # --- H2H ---
    h2h = _extract_h2h(html, text)
    if h2h and (h2h.get("n") or h2h.get("summary") or h2h.get("recent")):
        out["h2h"] = h2h
        if int(h2h.get("n") or 0) >= 1 or h2h.get("summary"):
            out["fields_contributed"].append("h2h")

    # --- referee (optional) ---
    ref = _first_attr(
        html,
        (
            r'(?:Referee|referee)[:\s]+([A-Za-zÀ-ÿ.\-\s]{3,40})',
            r'class="[^"]*referee[^"]*"[^>]*>([^<]+)',
            r'data-referee=["\']([^"\']+)',
        ),
    )
    if ref and len(ref) < 60 and "cookie" not in ref.lower():
        out["referee"] = {"name": ref.strip(), "cards_tendency": None, "notes": None}
        out["fields_contributed"].append("referee")

    # JSON-LD SportsEvent
    jld = _parse_json_ld(html)
    if jld:
        if not out["competition"].get("name") and jld.get("competition"):
            out["competition"] = {"name": jld["competition"]}
            out["fields_contributed"].append("competition")
        if jld.get("home") and not home_side.get("name"):
            home_side["name"] = jld["home"]
        if jld.get("away") and not away_side.get("name"):
            away_side["name"] = jld["away"]

    out["sides"] = {"home": home_side, "away": away_side}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def parse_flashscore_markdown(md: str, *, match: str = "") -> dict[str, Any]:
    """
    Parse Firecrawl-style markdown dumps of Flashscore match pages.

    Looks for headings, form letter lines, standings tables, H2H sections.
    """
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

    # Competition: line after title or "Competition:" label
    comp = _md_competition(text)
    if comp:
        out["competition"] = {"name": comp}
        out["fields_contributed"].append("competition")

    # Form blocks
    home_form = _md_form_for_side(text, home_name, side="home")
    away_form = _md_form_for_side(text, away_name, side="away")
    # Generic paired forms: Home form: / Away form:
    if not home_form:
        m = re.search(
            r"(?:home\s*form|form\s*home|last\s*5\s*home)\s*[:\-]?\s*([WDL\s,|/]{3,20})",
            text,
            re.I,
        )
        if m:
            home_form = m.group(1)
    if not away_form:
        m = re.search(
            r"(?:away\s*form|form\s*away|last\s*5\s*away)\s*[:\-]?\s*([WDL\s,|/]{3,20})",
            text,
            re.I,
        )
        if m:
            away_form = m.group(1)
    # Compact both: Form: WWDLW / LWDWL
    if not home_form or not away_form:
        m = re.search(
            r"form\s*[:\-]?\s*([WDL]{3,10})\s*[|/]\s*([WDL]{3,10})",
            text,
            re.I,
        )
        if m:
            home_form = home_form or m.group(1)
            away_form = away_form or m.group(2)

    home_side = _side_from_form(home_name, home_form or "")
    away_side = _side_from_form(away_name, away_form or "")

    # Standings: "Rank: 3 (40 pts)" near team name, or table rows
    hr, hp = _md_rank_for(text, home_name)
    ar, ap = _md_rank_for(text, away_name)
    if hr is None and ar is None:
        # Table-like: | 2 | Rosenborg | ... | 40 |
        for name, side_key in ((home_name, "home"), (away_name, "away")):
            if not name:
                continue
            m = re.search(
                rf"\|\s*(\d{{1,2}})\s*\|\s*{re.escape(name)}[^\n|]*\|\s*[^\n|]*\|\s*(\d{{1,3}})",
                text,
                re.I,
            )
            if not m:
                m = re.search(
                    rf"(?:^|\n)\s*(\d{{1,2}})\.?\s+{re.escape(name)}\b[^\n]*?\b(\d{{1,3}})\s*(?:pts|points)?",
                    text,
                    re.I,
                )
            if m:
                if side_key == "home":
                    hr, hp = _int(m.group(1)), _int(m.group(2))
                else:
                    ar, ap = _int(m.group(1)), _int(m.group(2))
    if hr is not None:
        home_side["standings"] = {"rank": hr, "points": hp}
        out["fields_contributed"].append("standings_home")
    if ar is not None:
        away_side["standings"] = {"rank": ar, "points": ap}
        out["fields_contributed"].append("standings_away")

    if home_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_home")
    if away_side.get("recent_form", {}).get("n", 0) >= 3:
        out["fields_contributed"].append("form_away")

    # H2H section
    h2h_n = 0
    h2h_recent: list[dict[str, Any]] = []
    h2h_sec = re.search(
        r"(?:^|\n)#{1,3}\s*H2H\b.*?(?=\n#{1,3}\s|\Z)",
        text,
        re.I | re.S,
    )
    block = h2h_sec.group(0) if h2h_sec else text
    for sm in re.finditer(r"(\d{4}-\d{2}-\d{2})?[^\n]{0,40}?(\d+\s*[-:]\s*\d+)", block):
        score = sm.group(2)
        h2h_recent.append(
            {"date": (sm.group(1) or "").strip(), "score": score, "competition": ""}
        )
        h2h_n += 1
        if h2h_n >= 8:
            break
    m_n = re.search(r"h2h[^.\n]{0,30}?\b(\d+)\b", text, re.I)
    if m_n:
        h2h_n = max(h2h_n, int(m_n.group(1)))
    if h2h_n or h2h_recent:
        out["h2h"] = {
            "n": h2h_n or len(h2h_recent),
            "summary": "",
            "recent": h2h_recent,
            "polarity": None,
        }
        if (h2h_n or len(h2h_recent)) >= 1:
            out["fields_contributed"].append("h2h")

    out["sides"] = {"home": home_side, "away": away_side}
    out["fields_contributed"] = sorted(set(out["fields_contributed"]))
    return out


def parse_flashscore_xhr(
    xhrs: list[Any],
    *,
    match: str = "",
) -> dict[str, Any]:
    """
    Extract form / standings / competition / H2H from captured XHR JSON list.

    Each item: {url, data} or raw dict/list payloads.
    Documented keys are fixture-driven; we probe common shapes without inventing API contracts.
    """
    out = _empty_frag(publisher="flashscore", method="xhr_json")
    if not xhrs:
        return out

    home_name, away_name = _split_match(match) if match else ("", "")
    home_letters: list[str] = []
    away_letters: list[str] = []
    home_rank = home_pts = away_rank = away_pts = None
    h2h_recent: list[dict[str, Any]] = []
    comp_name = ""

    for item in xhrs:
        data = item
        if isinstance(item, dict) and "data" in item:
            data = item.get("data")
        payloads = _walk_json_objects(data)
        for obj in payloads:
            if not isinstance(obj, dict):
                continue
            # competition / tournament
            for k in ("tournament", "competition", "league", "tournamentName", "name"):
                v = obj.get(k)
                if isinstance(v, str) and 3 <= len(v) <= 80 and not comp_name:
                    # Avoid generic labels
                    if v.lower() not in ("match", "summary", "football", "soccer"):
                        if k != "name" or obj.get("type") in (
                            "tournament",
                            "competition",
                            "league",
                        ):
                            if k in ("tournament", "competition", "league", "tournamentName"):
                                comp_name = v
                if isinstance(v, dict):
                    nm = v.get("name") or v.get("tournamentName")
                    if isinstance(nm, str) and 3 <= len(nm) <= 80:
                        comp_name = comp_name or nm

            # form arrays: form, lastMatches, recentForm, wdl
            for key, target in (
                ("homeForm", "home"),
                ("awayForm", "away"),
                ("formHome", "home"),
                ("formAway", "away"),
            ):
                if key in obj:
                    letters = _letters_from_any(obj[key])
                    if target == "home" and len(letters) > len(home_letters):
                        home_letters = letters
                    if target == "away" and len(letters) > len(away_letters):
                        away_letters = letters

            if "form" in obj and isinstance(obj["form"], dict):
                hf = _letters_from_any(obj["form"].get("home") or obj["form"].get("homeTeam"))
                af = _letters_from_any(obj["form"].get("away") or obj["form"].get("awayTeam"))
                if len(hf) > len(home_letters):
                    home_letters = hf
                if len(af) > len(away_letters):
                    away_letters = af

            # standings rank
            for side_key, rank_keys, pts_keys in (
                (
                    "home",
                    ("homeRank", "rankHome", "tablePosition"),
                    ("homePoints", "pointsHome", "pts"),
                ),
                (
                    "away",
                    ("awayRank", "rankAway", "tablePosition"),
                    ("awayPoints", "pointsAway", "pts"),
                ),
            ):
                for rk in rank_keys:
                    if rk in obj and obj[rk] is not None:
                        ri = _int(obj[rk])
                        if ri is not None:
                            if side_key == "home" and home_rank is None:
                                home_rank = ri
                            if side_key == "away" and away_rank is None:
                                # only if distinct key or separate object
                                if rk != "tablePosition" or side_key == "away":
                                    pass
            if "home" in obj and isinstance(obj["home"], dict):
                r = _int(obj["home"].get("rank") or obj["home"].get("tablePosition"))
                p = _int(obj["home"].get("points") or obj["home"].get("pts"))
                if r is not None:
                    home_rank = home_rank if home_rank is not None else r
                if p is not None:
                    home_pts = home_pts if home_pts is not None else p
                letters = _letters_from_any(
                    obj["home"].get("form") or obj["home"].get("lastMatches")
                )
                if len(letters) > len(home_letters):
                    home_letters = letters
                if obj["home"].get("name") and not home_name:
                    home_name = str(obj["home"]["name"])
            if "away" in obj and isinstance(obj["away"], dict):
                r = _int(obj["away"].get("rank") or obj["away"].get("tablePosition"))
                p = _int(obj["away"].get("points") or obj["away"].get("pts"))
                if r is not None:
                    away_rank = away_rank if away_rank is not None else r
                if p is not None:
                    away_pts = away_pts if away_pts is not None else p
                letters = _letters_from_any(
                    obj["away"].get("form") or obj["away"].get("lastMatches")
                )
                if len(letters) > len(away_letters):
                    away_letters = letters
                if obj["away"].get("name") and not away_name:
                    away_name = str(obj["away"]["name"])

            # H2H rows
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

    home_side = {
        "name": home_name,
        "recent_form": {
            "n": len(home_letters),
            "results": home_letters,
            "scores": [],
            "summary": " ".join(home_letters),
        },
    }
    away_side = {
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
        out["fields_contributed"].append("standings_home")
    if away_rank is not None:
        away_side["standings"] = {"rank": away_rank, "points": away_pts}
        out["fields_contributed"].append("standings_away")
    if len(home_letters) >= 3:
        out["fields_contributed"].append("form_home")
    if len(away_letters) >= 3:
        out["fields_contributed"].append("form_away")
    if comp_name:
        out["competition"] = {"name": comp_name}
        out["fields_contributed"].append("competition")
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


def _bundle_parts(
    bundle: Any,
) -> tuple[str, str, str, list[Any], dict[str, Any], str, str]:
    if bundle is None:
        return "", "", "", [], {}, "", ""
    if isinstance(bundle, dict):
        res = bundle.get("resources") or {}
        html = str(
            res.get("summary_html") or bundle.get("html") or bundle.get("summary_html") or ""
        )
        markdown = str(res.get("markdown") or bundle.get("markdown") or "")
        h2h_html = str(res.get("h2h_html") or bundle.get("h2h_html") or "")
        xhrs = list(res.get("xhr_json") or bundle.get("xhrs") or [])
        page_meta = dict(bundle.get("page_meta") or {})
        url = str(bundle.get("final_url") or bundle.get("url") or "")
        method = str(bundle.get("method") or "")
        return html, markdown, h2h_html, xhrs, page_meta, url, method

    res = getattr(bundle, "resources", None) or {}
    html = str(
        getattr(bundle, "summary_html", None)
        or (res.get("summary_html") if isinstance(res, dict) else None)
        or getattr(bundle, "html", "")
        or ""
    )
    markdown = str(
        getattr(bundle, "markdown", None)
        or (res.get("markdown") if isinstance(res, dict) else None)
        or ""
    )
    h2h_html = str((res.get("h2h_html") if isinstance(res, dict) else None) or "")
    xhrs = list(
        getattr(bundle, "xhrs", None)
        or (res.get("xhr_json") if isinstance(res, dict) else None)
        or []
    )
    page_meta = dict(getattr(bundle, "page_meta", None) or {})
    url = str(getattr(bundle, "final_url", None) or getattr(bundle, "url", "") or "")
    method = str(getattr(bundle, "method", "") or "")
    return html, markdown, h2h_html, xhrs, page_meta, url, method


def _empty_frag(*, publisher: str, method: str) -> dict[str, Any]:
    return {
        "competition": {},
        "sides": {"home": {}, "away": {}},
        "h2h": {},
        "referee": {},
        "fields_contributed": [],
        "page_title": "",
        "publisher": publisher,
        "method": method,
    }


def _fields(frag: dict[str, Any] | None) -> list[str]:
    if not frag:
        return []
    return list(frag.get("fields_contributed") or [])


def _needs_fotmob_secondary(merged: dict[str, Any]) -> bool:
    fields = set(merged.get("fields_contributed") or [])
    has_form = "form_home" in fields and "form_away" in fields
    has_rank = "standings_home" in fields or "standings_away" in fields or "standings_or_rank" in fields
    has_comp = "competition" in fields
    return not (has_form and has_comp and has_rank)


def _merge_frag_list(fragments: list[dict[str, Any]]) -> dict[str, Any]:
    out = _empty_frag(publisher="flashscore", method="live_parse")
    for frag in fragments:
        out = _merge_two(out, frag)
    return out


def _merge_two(base: dict[str, Any], frag: dict[str, Any]) -> dict[str, Any]:
    if not frag:
        return base
    out = dict(base)
    # competition fill-empty
    if frag.get("competition") and isinstance(frag["competition"], dict):
        name = str((frag["competition"] or {}).get("name") or "").strip()
        cur = dict(out.get("competition") or {})
        if name and not str(cur.get("name") or "").strip():
            out["competition"] = {**cur, **frag["competition"]}
        elif name:
            for k, v in frag["competition"].items():
                if v is not None and not cur.get(k):
                    cur[k] = v
            out["competition"] = cur
    # sides
    sides = {
        "home": dict((out.get("sides") or {}).get("home") or {}),
        "away": dict((out.get("sides") or {}).get("away") or {}),
    }
    fs = frag.get("sides") or {}
    for sk in ("home", "away"):
        patch = fs.get(sk) or {}
        if not isinstance(patch, dict):
            continue
        cur = sides[sk]
        if patch.get("name") and not cur.get("name"):
            cur["name"] = patch["name"]
        if isinstance(patch.get("recent_form"), dict):
            pr = patch["recent_form"]
            cr = dict(cur.get("recent_form") or {})
            if int(pr.get("n") or 0) > int(cr.get("n") or 0) or (
                int(pr.get("n") or 0) >= int(cr.get("n") or 0) and pr.get("results")
            ):
                cr.update({k: v for k, v in pr.items() if v is not None})
                cur["recent_form"] = cr
        if isinstance(patch.get("standings"), dict):
            st = dict(cur.get("standings") or {})
            st.update({k: v for k, v in patch["standings"].items() if v is not None})
            cur["standings"] = st
        if patch.get("rating") is not None and cur.get("rating") is None:
            cur["rating"] = patch["rating"]
        if isinstance(patch.get("injuries_suspensions"), list) and cur.get(
            "injuries_suspensions"
        ) is None:
            cur["injuries_suspensions"] = patch["injuries_suspensions"]
        sides[sk] = cur
    out["sides"] = sides
    # h2h prefer higher n
    if frag.get("h2h") and isinstance(frag["h2h"], dict):
        cur_h = out.get("h2h") or {}
        new_n = int((frag["h2h"] or {}).get("n") or 0)
        cur_n = int((cur_h or {}).get("n") or 0)
        if new_n > cur_n or (new_n and not cur_n):
            out["h2h"] = {**(cur_h or {}), **frag["h2h"]}
    if frag.get("referee") and isinstance(frag["referee"], dict) and frag["referee"].get("name"):
        if not (out.get("referee") or {}).get("name"):
            out["referee"] = frag["referee"]
    if frag.get("page_title") and not out.get("page_title"):
        out["page_title"] = frag["page_title"]
    if frag.get("method"):
        out["method"] = frag["method"]
    if frag.get("publisher"):
        out["publisher"] = frag["publisher"]
    if frag.get("url"):
        out["url"] = frag["url"]
    fields = list(out.get("fields_contributed") or [])
    fields.extend(frag.get("fields_contributed") or [])
    # Recompute form/standings credits from sides
    for sk, fk in (("home", "form_home"), ("away", "form_away")):
        n = int(((sides[sk].get("recent_form") or {}).get("n") or 0))
        if n >= 3 and fk not in fields:
            fields.append(fk)
    for sk, fk in (("home", "standings_home"), ("away", "standings_away")):
        if (sides[sk].get("standings") or {}).get("rank") is not None and fk not in fields:
            fields.append(fk)
    if (out.get("competition") or {}).get("name") and "competition" not in fields:
        fields.append("competition")
    if int((out.get("h2h") or {}).get("n") or 0) >= 1 and "h2h" not in fields:
        fields.append("h2h")
    out["fields_contributed"] = sorted(set(fields))
    return out


def _strip_tags(s: str) -> str:
    s = re.sub(r"<script[^>]*>.*?</script>", " ", s or "", flags=re.I | re.S)
    s = re.sub(r"<style[^>]*>.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    return _strip_tags(m.group(1)) if m else ""


def _first_attr(html: str, patterns: tuple[str, ...]) -> str | None:
    for pat in patterns:
        m = re.search(pat, html, flags=re.I | re.S)
        if m:
            val = _strip_tags(m.group(1)).strip()
            if val:
                return val
    return None


def _split_match(match: str) -> tuple[str, str]:
    m = (match or "").strip()
    for sep in (" vs ", " v ", " - ", " – ", " — "):
        if sep in m:
            a, b = m.split(sep, 1)
            return a.strip(), b.strip()
    return m, ""


def _split_title_teams(title: str) -> tuple[str, str]:
    t = re.sub(r"\s*\|\s*.*$", "", title or "").strip()
    t = re.sub(r"\s*-\s*Flashscore.*$", "", t, flags=re.I).strip()
    for sep in (" vs ", " vs. ", " v ", " - ", " – ", " — "):
        if sep in t.lower() or sep in t:
            # case-sensitive split attempt
            idx = t.lower().find(sep.strip().lower()) if sep.strip() else -1
            # better: try each
            pass
    for sep in (" vs. ", " vs ", " v ", " – ", " — ", " - "):
        if sep in t:
            a, b = t.split(sep, 1)
            # drop trailing competition after second team if "Team | Comp"
            b = re.split(r"\s*\|\s*", b, maxsplit=1)[0]
            return a.strip(), b.strip()
    m = re.match(r"(.+?)\s+vs\.?\s+(.+)", t, flags=re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", ""


def _extract_competition(
    html: str, *, title: str, page_meta: dict[str, Any]
) -> dict[str, Any]:
    hint = str(page_meta.get("competition_hint") or "").strip()
    if hint:
        return {"name": hint, "country": page_meta.get("country")}

    # meta / breadcrumb / tournament link
    candidates: list[str] = []
    for pat in (
        r'class="[^"]*(?:tournamentHeader|tournament|breadcrumb|wcl-breadcrumb)[^"]*"[^>]*>([^<]{3,60})',
        r'data-competition=["\']([^"\']+)',
        r'class="[^"]*event__title[^"]*"[^>]*>([^<]{3,60})',
        r'itemprop=["\']name["\'][^>]*content=["\']([^"\']+competition[^"\']*)',
        r'<a[^>]+href="[^"]*/football/[^"]+"/[^>]*>([^<]{3,50})</a>',
    ):
        for m in re.finditer(pat, html, flags=re.I):
            val = _strip_tags(m.group(1)).strip()
            if val and val.lower() not in (
                "football",
                "soccer",
                "home",
                "flashscore",
                "standings",
                "h2h",
            ):
                candidates.append(val)

    # Title segment: "Home vs Away | Eliteserien | Flashscore"
    if title and "|" in title:
        parts = [p.strip() for p in title.split("|")]
        for p in parts[1:]:
            pl = p.lower()
            if pl in ("flashscore", "livescore", "flashscore.com"):
                continue
            if " vs " in pl or " v " in pl:
                continue
            candidates.append(p)

    if candidates:
        # Prefer non-country-only short names
        name = candidates[0]
        country = None
        m_c = re.search(
            r'data-country=["\']([^"\']+)', html, flags=re.I
        ) or re.search(r'class="[^"]*country[^"]*"[^>]*>([^<]+)', html, flags=re.I)
        if m_c:
            country = _strip_tags(m_c.group(1)).strip()
        return {"name": name, "country": country}
    return {}


def _parse_form_letters(text: str) -> list[str]:
    letters = re.findall(r"\b([WDL])\b", (text or "").upper())
    if letters:
        return letters[:10]
    m = re.search(r"\b([WDL]{3,10})\b", (text or "").upper())
    if m:
        return list(m.group(1))
    # spaced form icons: W D L W W
    spaced = re.findall(r"(?<![A-Za-z])([WDL])(?![A-Za-z])", (text or "").upper())
    return spaced[:10]


def _side_from_form(name: str, form_text: str) -> dict[str, Any]:
    letters = _parse_form_letters(form_text or "")
    scores = re.findall(r"\b(\d+\s*[-:]\s*\d+)\b", form_text or "")
    return {
        "name": name or "",
        "recent_form": {
            "n": len(letters),
            "results": letters,
            "scores": scores,
            "summary": (form_text or "").strip(),
        },
    }


def _extract_form_pairs(
    html: str, text: str, home_name: str, away_name: str
) -> tuple[str, str]:
    home_form = ""
    away_form = ""

    # data-* still useful if mixed into live dumps
    m = re.search(r'data-home-form=["\']([^"\']+)', html, re.I)
    if m:
        home_form = m.group(1)
    m = re.search(r'data-away-form=["\']([^"\']+)', html, re.I)
    if m:
        away_form = m.group(1)

    # Flashscore form widgets
    patterns_home = (
        r'class="[^"]*form__home[^"]*"[^>]*>(.*?)</(?:div|ul|section)>',
        r'class="[^"]*duelParticipant__home[^"]*".*?'
        r'class="[^"]*wld[^"]*"[^>]*>(.*?)</div>',
        r'data-testid=["\']form-home["\'][^>]*>(.*?)</',
        r'class="[^"]*form-home[^"]*"[^>]*>(.*?)</',
    )
    patterns_away = (
        r'class="[^"]*form__away[^"]*"[^>]*>(.*?)</(?:div|ul|section)>',
        r'class="[^"]*duelParticipant__away[^"]*".*?'
        r'class="[^"]*wld[^"]*"[^>]*>(.*?)</div>',
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

    # formIcon / wld badge sequence containers
    if not home_form or not away_form:
        # Collect all wld badge texts in order
        badges = re.findall(
            r'class="[^"]*(?:wld|formIcon|form__wld)[^"]*"[^>]*>\s*([WDL])\s*<',
            html,
            re.I,
        )
        if len(badges) >= 6:
            # Assume first half home, second away if even
            mid = len(badges) // 2
            if not home_form:
                home_form = " ".join(badges[:mid][:5])
            if not away_form:
                away_form = " ".join(badges[mid : mid + 5])

    # last matches rows with win/draw/loss classes near team
    if home_name and not home_form:
        home_form = _form_from_last_matches(html, home_name)
    if away_name and not away_form:
        away_form = _form_from_last_matches(html, away_name)

    # Plain text "Home form: W W D L W"
    if not home_form:
        m = re.search(
            rf"(?:{re.escape(home_name)}\s+form|home\s*form)\s*[:\-]?\s*([WDL\s]{{5,20}})",
            text,
            re.I,
        )
        if m:
            home_form = m.group(1)
    if not away_form and away_name:
        m = re.search(
            rf"(?:{re.escape(away_name)}\s+form|away\s*form)\s*[:\-]?\s*([WDL\s]{{5,20}})",
            text,
            re.I,
        )
        if m:
            away_form = m.group(1)

    return home_form, away_form


def _form_from_last_matches(html: str, team: str) -> str:
    """Derive W/D/L from last-match rows when explicit form strip missing."""
    if not team:
        return ""
    # Rows that mention team and a score; look for result class
    letters: list[str] = []
    # class event__result or h2H__result near team
    for m in re.finditer(
        rf'{re.escape(team)}.{{0,200}}?class="[^"]*(?:wld--|form__|event__winner|--win|--draw|--loss)[^"]*"',
        html,
        re.I | re.S,
    ):
        chunk = m.group(0).lower()
        if "win" in chunk or "wld--w" in chunk or "--w" in chunk:
            letters.append("W")
        elif "draw" in chunk or "wld--d" in chunk:
            letters.append("D")
        elif "loss" in chunk or "lose" in chunk or "wld--l" in chunk:
            letters.append("L")
        if len(letters) >= 5:
            break
    # Score-based: "Team 2-1" vs "1-2 Team" heuristics when class="lastMatch"
    if len(letters) < 3:
        for m in re.finditer(
            rf'class="[^"]*lastMatch[^"]*"[^>]*>(.*?)</(?:div|tr|li)>',
            html,
            re.I | re.S,
        ):
            row = _strip_tags(m.group(1))
            if team.lower() not in row.lower():
                continue
            sm = re.search(r"(\d+)\s*[-:]\s*(\d+)", row)
            if not sm:
                continue
            a, b = int(sm.group(1)), int(sm.group(2))
            # If team appears before score → home in that row
            before = row.lower().find(team.lower()) < row.find(sm.group(0))
            gf, ga = (a, b) if before else (b, a)
            if gf > ga:
                letters.append("W")
            elif gf == ga:
                letters.append("D")
            else:
                letters.append("L")
            if len(letters) >= 5:
                break
    return " ".join(letters) if len(letters) >= 3 else ""


def _extract_standings(
    html: str, text: str, home_name: str, away_name: str
) -> tuple[int | None, int | None, int | None, int | None]:
    home_rank = home_pts = away_rank = away_pts = None

    m = re.search(r'data-home-rank=["\'](\d+)', html, re.I)
    if m:
        home_rank = int(m.group(1))
    m = re.search(r'data-away-rank=["\'](\d+)', html, re.I)
    if m:
        away_rank = int(m.group(1))
    m = re.search(r'data-home-points=["\'](\d+)', html, re.I)
    if m:
        home_pts = int(m.group(1))
    m = re.search(r'data-away-points=["\'](\d+)', html, re.I)
    if m:
        away_pts = int(m.group(1))

    # tableCellRank / table__cell--rank near team name
    for name, is_home in ((home_name, True), (away_name, False)):
        if not name:
            continue
        m = re.search(
            rf'(?:tableCellRank|table__cell--rank|rank)[^>]*>\s*(\d{{1,2}})\s*<[^>]{{0,80}}>.{{0,120}}?{re.escape(name)}'
            rf'|{re.escape(name)}.{{0,120}}?(?:tableCellRank|rank)[^>]*>\s*(\d{{1,2}})',
            html,
            re.I | re.S,
        )
        if m:
            r = _int(m.group(1) or m.group(2))
            if is_home and home_rank is None:
                home_rank = r
            if not is_home and away_rank is None:
                away_rank = r
        # "Rosenborg 3rd" / "Rank: 3"
        m2 = re.search(
            rf"{re.escape(name)}[^\n]{{0,40}}?(?:rank|position)[:\s#]*(\d{{1,2}})",
            text,
            re.I,
        )
        if not m2:
            m2 = re.search(
                rf"(?:rank|position)[:\s#]*(\d{{1,2}})[^\n]{{0,40}}?{re.escape(name)}",
                text,
                re.I,
            )
        if m2:
            r = _int(m2.group(1))
            if is_home and home_rank is None:
                home_rank = r
            if not is_home and away_rank is None:
                away_rank = r
        m3 = re.search(
            rf"{re.escape(name)}[^\n]{{0,60}}?(\d{{1,3}})\s*(?:pts|points)",
            text,
            re.I,
        )
        if m3:
            p = _int(m3.group(1))
            if is_home and home_pts is None:
                home_pts = p
            if not is_home and away_pts is None:
                away_pts = p

    return home_rank, home_pts, away_rank, away_pts


def _extract_h2h(html: str, text: str) -> dict[str, Any]:
    recent: list[dict[str, Any]] = []
    # Structured rows
    for m in re.finditer(
        r'class="[^"]*h2h__(?:row|entity)[^"]*"[^>]*>(.*?)</(?:div|a|tr)>',
        html,
        re.I | re.S,
    ):
        row = _strip_tags(m.group(1))
        sm = re.search(r"(\d+\s*[-:]\s*\d+)", row)
        dm = re.search(r"(\d{2}[./]\d{2}[./]\d{2,4}|\d{4}-\d{2}-\d{2})", row)
        recent.append(
            {
                "date": dm.group(1) if dm else "",
                "score": sm.group(1) if sm else row[:40],
                "competition": "",
            }
        )
        if len(recent) >= 8:
            break
    if not recent:
        for m in re.finditer(
            r'data-h2h-row[^>]*data-score=["\']([^"\']+)["\'][^>]*(?:data-date=["\']([^"\']*)["\'])?',
            html,
            re.I,
        ):
            recent.append({"date": m.group(2) or "", "score": m.group(1), "competition": ""})
    n = len(recent)
    m_n = re.search(r'data-h2h-n=["\'](\d+)', html, re.I)
    if m_n:
        n = max(n, int(m_n.group(1)))
    summary = ""
    m_s = re.search(r'data-h2h-summary=["\']([^"\']+)', html, re.I)
    if m_s:
        summary = m_s.group(1)
    if not summary and n:
        summary = f"Last {n} H2H meetings"
    polarity = None
    m_p = re.search(r'data-h2h-polarity=["\']([^"\']+)', html, re.I)
    if m_p:
        polarity = m_p.group(1)
    if not n and not summary:
        # text "Head to head (5)"
        m = re.search(r"head\s*to\s*head[^\d]{0,20}(\d+)", text, re.I)
        if m:
            n = int(m.group(1))
            summary = f"H2H n={n}"
    return {"n": n, "summary": summary, "recent": recent, "polarity": polarity}


def _parse_json_ld(html: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for obj in items:
            if not isinstance(obj, dict):
                continue
            t = str(obj.get("@type") or "")
            if "SportsEvent" in t or "Event" in t:
                name = str(obj.get("name") or "")
                if " vs " in name.lower() or " v " in name.lower():
                    th, ta = _split_title_teams(name)
                    if th:
                        out["home"] = th
                    if ta:
                        out["away"] = ta
                home = obj.get("homeTeam") or obj.get("home_team")
                away = obj.get("awayTeam") or obj.get("away_team")
                if isinstance(home, dict) and home.get("name"):
                    out["home"] = home["name"]
                if isinstance(away, dict) and away.get("name"):
                    out["away"] = away["name"]
                if isinstance(home, str):
                    out["home"] = home
                if isinstance(away, str):
                    out["away"] = away
                super_event = obj.get("superEvent") or obj.get("location")
                if isinstance(super_event, dict) and super_event.get("name"):
                    out["competition"] = super_event["name"]
                if obj.get("description") and not out.get("competition"):
                    # sometimes "Eliteserien match"
                    desc = str(obj.get("description") or "")
                    cm = re.search(r"([A-Z][A-Za-z0-9 .]{2,40})\s+match", desc)
                    if cm:
                        out["competition"] = cm.group(1).strip()
    return out


def _md_first_heading(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def _md_competition(text: str) -> str:
    m = re.search(
        r"(?:^|\n)(?:competition|tournament|league)\s*[:\-]\s*(.+)$",
        text,
        re.I | re.M,
    )
    if m:
        return m.group(1).strip()
    # Second heading often competition
    heads = re.findall(r"^#{1,3}\s+(.+)$", text, re.M)
    if len(heads) >= 2:
        h = heads[1].strip()
        if " vs " not in h.lower() and h.lower() not in ("form", "h2h", "standings"):
            return h
    # Line after title without markdown
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 2 and ("vs" in lines[0].lower() or lines[0].startswith("#")):
        cand = re.sub(r"^#+\s*", "", lines[1]).strip()
        if cand and " vs " not in cand.lower() and len(cand) < 60:
            if cand.lower() not in ("form", "h2h", "standings", "summary"):
                return cand
    return ""


def _md_form_for_side(text: str, name: str, *, side: str) -> str:
    if name:
        m = re.search(
            rf"{re.escape(name)}[^\n]{{0,30}}form\s*[:\-]?\s*([WDL\s,|/]{{3,20}})",
            text,
            re.I,
        )
        if m:
            return m.group(1)
        m = re.search(
            rf"form[^\n]{{0,20}}{re.escape(name)}\s*[:\-]?\s*([WDL\s,|/]{{3,20}})",
            text,
            re.I,
        )
        if m:
            return m.group(1)
    label = "home" if side == "home" else "away"
    m = re.search(
        rf"{label}\s*form\s*[:\-]?\s*([WDL\s,|/]{{3,20}})",
        text,
        re.I,
    )
    return m.group(1) if m else ""


def _md_rank_for(text: str, name: str) -> tuple[int | None, int | None]:
    if not name:
        return None, None
    m = re.search(
        rf"{re.escape(name)}[^\n]{{0,50}}?(?:rank|pos(?:ition)?)\s*[:#]?\s*(\d{{1,2}})"
        rf"(?:[^\n]{{0,30}}?(\d{{1,3}})\s*(?:pts|points))?",
        text,
        re.I,
    )
    if m:
        return _int(m.group(1)), _int(m.group(2)) if m.lastindex and m.lastindex >= 2 else None
    return None, None


def _letters_from_any(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return _parse_form_letters(val)
    if isinstance(val, list):
        out: list[str] = []
        for item in val:
            if isinstance(item, str) and item.upper()[:1] in "WDL":
                out.append(item.upper()[:1])
            elif isinstance(item, dict):
                r = item.get("result") or item.get("outcome") or item.get("wld")
                if isinstance(r, str) and r.upper()[:1] in "WDL":
                    out.append(r.upper()[:1])
                elif item.get("win") is True:
                    out.append("W")
                elif item.get("draw") is True:
                    out.append("D")
                elif item.get("loss") is True or item.get("lose") is True:
                    out.append("L")
        return out[:10]
    return []


def _walk_json_objects(data: Any, *, limit: int = 200) -> list[Any]:
    out: list[Any] = []
    stack = [data]
    while stack and len(out) < limit:
        cur = stack.pop()
        if isinstance(cur, dict):
            out.append(cur)
            for v in cur.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            for v in cur:
                if isinstance(v, (dict, list)):
                    stack.append(v)
    return out


def _int(x: Any) -> int | None:
    if x is None or str(x).strip() == "":
        return None
    try:
        return int(str(x).strip())
    except ValueError:
        return None
