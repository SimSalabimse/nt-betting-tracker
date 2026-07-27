"""
Match Intelligence pipeline: build MIC cards for board matches.

Control flow (Appendix B):
  fixtures/html → offline parse
  else if not allow_network → network_disabled
  else → fetch (+ optional URL) → match_confidence → live parse or live_parser_not_ready

PR-1: football registry ready=False → after successful fetch+name match → live_parser_not_ready
       (raw bundle still cached). No URL discovery (PR-2).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from nt.match_intel.io import atomic_write_json, mic_path, read_mic, write_mic
from nt.match_intel.matching import match_confidence
from nt.match_intel.registry import get_live_parser, is_live_parser_ready
from nt.match_intel.schema import (
    apply_process_miss,
    empty_mic_skeleton,
    finalize_coverage,
    mic_match_key,
    side_dict,
)
from nt.match_intel.sources.flashscore import parse_flashscore_html
from nt.match_intel.sources.fotmob import parse_fotmob_html
from nt.match_intel.sources.nt import parse_nt_context
from nt.sport_taxonomy import normalize_sport


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _finalize_card(card: dict[str, Any], *, t0: float) -> dict[str, Any]:
    """Coverage grade + process_miss taxonomy + duration (grade math unchanged)."""
    finalize_coverage(card)
    apply_process_miss(card)
    card["extraction"]["duration_ms"] = int((time.perf_counter() - t0) * 1000)
    card["updated_at"] = _utc_now_iso()
    return card


def _mic_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    research = (cfg or {}).get("research") or {}
    mi = research.get("match_intel") or {}
    return dict(mi) if isinstance(mi, dict) else {}


def _deep_merge_side(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (patch or {}).items():
        if v is None:
            continue
        if k == "recent_form" and isinstance(v, dict):
            cur = dict(out.get("recent_form") or {})
            # Prefer higher n / form credit
            cur_n = int(cur.get("n") or 0)
            new_n = int(v.get("n") or 0)
            if new_n > cur_n or (new_n >= cur_n and v.get("results")):
                cur.update({kk: vv for kk, vv in v.items() if vv is not None})
            out["recent_form"] = cur
        elif k == "standings" and isinstance(v, dict):
            cur = dict(out.get("standings") or {})
            cur.update({kk: vv for kk, vv in v.items() if vv is not None})
            out["standings"] = cur
        elif k == "home_away_split" and isinstance(v, dict):
            cur = dict(out.get("home_away_split") or {})
            cur.update({kk: vv for kk, vv in v.items() if vv is not None})
            out["home_away_split"] = cur
        elif k == "injuries_suspensions" and isinstance(v, list):
            out["injuries_suspensions"] = v
        elif k == "name" and v:
            out["name"] = v
        elif k == "rating" and v is not None:
            out["rating"] = v
        elif k == "rest_days" and v is not None:
            out["rest_days"] = v
        else:
            if not out.get(k):
                out[k] = v
    return out


def merge_fragments(card: dict[str, Any], frag: dict[str, Any]) -> dict[str, Any]:
    """Merge a source fragment into the MIC card (higher-priority should be applied first)."""
    if not frag:
        return card
    if frag.get("competition") and isinstance(frag["competition"], dict):
        name = str((frag["competition"] or {}).get("name") or "").strip()
        if name and not str((card.get("competition") or {}).get("name") or "").strip():
            card["competition"] = {**(card.get("competition") or {}), **frag["competition"]}
        elif name:
            # fill missing subfields only
            cur = dict(card.get("competition") or {})
            for k, v in frag["competition"].items():
                if v is not None and not cur.get(k):
                    cur[k] = v
            card["competition"] = cur

    sides = card.setdefault("sides", {"home": side_dict(), "away": side_dict()})
    frag_sides = frag.get("sides") or {}
    for sk in ("home", "away"):
        if sk in frag_sides and isinstance(frag_sides[sk], dict):
            sides[sk] = _deep_merge_side(sides.get(sk) or side_dict(), frag_sides[sk])

    if frag.get("h2h") and isinstance(frag["h2h"], dict):
        cur_h = card.get("h2h") or {}
        new_n = int((frag["h2h"] or {}).get("n") or 0)
        cur_n = int((cur_h or {}).get("n") or 0)
        if new_n > cur_n or (new_n and not cur_n):
            card["h2h"] = {**(cur_h or {}), **frag["h2h"]}

    if frag.get("referee") and isinstance(frag["referee"], dict) and frag["referee"].get("name"):
        if not (card.get("referee") or {}).get("name"):
            card["referee"] = frag["referee"]

    if frag.get("motivation_situational") and isinstance(frag["motivation_situational"], dict):
        if not (card.get("motivation_situational") or {}).get("tags"):
            card["motivation_situational"] = frag["motivation_situational"]

    if frag.get("kickoff_local") and not card.get("kickoff_local"):
        card["kickoff_local"] = frag["kickoff_local"]
    if frag.get("kickoff_utc") and not card.get("kickoff_utc"):
        card["kickoff_utc"] = frag["kickoff_utc"]

    # Record source
    fields = list(frag.get("fields_contributed") or [])
    if fields or frag.get("publisher"):
        sources = list(card.get("sources") or [])
        sources.append(
            {
                "url": frag.get("url") or "",
                "publisher": frag.get("publisher") or "unknown",
                "fetched_at": _utc_now_iso(),
                "method": frag.get("method") or "parse",
                "fields_contributed": fields,
            }
        )
        card["sources"] = sources
    return card


def _apply_html_sources(
    card: dict[str, Any],
    *,
    html_by_source: dict[str, str] | None,
    match: str,
) -> dict[str, Any]:
    html_by_source = html_by_source or {}
    if "flashscore" in html_by_source and html_by_source["flashscore"]:
        frag = parse_flashscore_html(html_by_source["flashscore"], match=match)
        # match confidence vs page title
        title = frag.get("page_title") or ""
        home = (frag.get("sides") or {}).get("home", {}).get("name") or ""
        away = (frag.get("sides") or {}).get("away", {}).get("name") or ""
        page_teams = f"{home} vs {away}" if home and away else title
        if page_teams:
            conf, _score = match_confidence(match, page_teams)
            card.setdefault("extraction", {})
            card["extraction"]["match_confidence"] = conf
            if conf == "fuzzy":
                card["extraction"]["needs_review"] = True
            elif conf == "exact":
                card["extraction"]["needs_review"] = False
                card["extraction"]["match_confidence"] = "exact"
            elif conf == "none" and (home or away or title):
                card["extraction"]["match_confidence"] = "none"
                card["extraction"]["needs_review"] = True
                card["extraction"].setdefault("errors", []).append("low_name_match")
        card = merge_fragments(card, frag)
        card.setdefault("extraction", {})
        if card["extraction"].get("primary_method") in (None, "failed", "skeleton", "stub"):
            card["extraction"]["primary_method"] = frag.get("method") or "bs4"
    if "fotmob" in html_by_source and html_by_source["fotmob"]:
        frag = parse_fotmob_html(html_by_source["fotmob"], match=match)
        card = merge_fragments(card, frag)
        card.setdefault("extraction", {})
        fb = list(card["extraction"].get("fallbacks_used") or [])
        if "fotmob" not in fb:
            fb.append("fotmob")
        card["extraction"]["fallbacks_used"] = fb
    return card


def _split_sides_simple(match: str) -> tuple[str, str]:
    m = (match or "").strip()
    for sep in (" vs ", " v ", " - ", " – ", " — "):
        if sep in m:
            a, b = m.split(sep, 1)
            return a.strip(), b.strip()
    return m, ""


def _name_match_from_bundle(match: str, bundle: Any) -> str:
    """Return match_confidence label from fetch bundle identity / body tokens."""
    page_teams = ""
    try:
        page_teams = bundle.identity_text() if bundle is not None else ""
    except Exception:  # noqa: BLE001
        page_teams = ""
    if page_teams:
        conf, _score = match_confidence(match, page_teams)
        return conf

    html = ""
    try:
        html = (bundle.summary_html or bundle.html or bundle.markdown or "").lower()
    except Exception:  # noqa: BLE001
        html = ""
    if len(html) > 200:
        home, away = _split_sides_simple(match)
        if home and away and home.lower() in html and away.lower() in html:
            return "fuzzy"
    return "none"


def _guess_source_from_url(url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:  # noqa: BLE001
        return "other_public"
    if "flashscore" in host:
        return "flashscore"
    if "fotmob" in host:
        return "fotmob"
    if "sofascore" in host:
        return "sofascore"
    return "other_public"


def _record_fetch_source(card: dict[str, Any], *, url: str, method: str) -> None:
    sources = list(card.get("sources") or [])
    sources.append(
        {
            "url": url,
            "publisher": _guess_source_from_url(url),
            "fetched_at": _utc_now_iso(),
            "method": method or "fetch",
            "fields_contributed": [],
        }
    )
    card["sources"] = sources


def _live_network_path(
    card: dict[str, Any],
    *,
    match: str,
    sport_n: str,
    mi: dict[str, Any],
    key: str,
    url: str | None,
    force: bool,
) -> dict[str, Any]:
    """
    Fetch → name match → live parse or live_parser_not_ready.

    PR-1: requires explicit url (CLI --url); discovery is PR-2.
    """
    card.setdefault("extraction", {})
    urls: list[str] = []
    if url and str(url).strip():
        urls.append(str(url).strip())

    if not urls:
        # No discovery in PR-1
        card["extraction"]["primary_method"] = "failed"
        card["extraction"]["errors"] = ["url_not_found"]
        card["extraction"]["needs_review"] = True
        return card

    from nt.match_intel.fetch.router import fetch_match_bundle

    last_errors: list[str] = []
    matched_bundle = None
    matched_conf = "none"

    for u in urls:
        bundle = fetch_match_bundle(
            u,
            mi_cfg=mi,
            match_key=key,
            source=_guess_source_from_url(u),
            sport=sport_n,
            use_cache=True,
            force=force,
        )
        method = bundle.method or "fetch"
        card["extraction"]["primary_method"] = method

        if not bundle.ok:
            err = bundle.error or "fetch_failed"
            # Normalize taxonomy codes
            if err in (
                "timeout",
                "circuit_open",
                "blocked",
                "playwright_not_installed",
                "js_shell_empty",
                "wrong_backend",
                "firecrawl_not_installed",
                "firecrawl_not_configured",
            ):
                # Map firecrawl-specific to fetch_failed for process_miss priority when needed
                mapped = err
                if err.startswith("firecrawl_"):
                    mapped = "fetch_failed"
                last_errors.append(mapped)
            else:
                last_errors.append("fetch_failed" if err == "empty_url" else err)
            # Still record attempted source
            _record_fetch_source(card, url=u, method=method)
            continue

        # Successful fetch — raw already in fetch cache via router
        _record_fetch_source(card, url=bundle.final_url or u, method=method)
        conf = _name_match_from_bundle(match, bundle)
        card["extraction"]["match_confidence"] = conf
        if conf == "none":
            last_errors.append("low_name_match")
            card["extraction"]["needs_review"] = True
            continue

        matched_bundle = bundle
        matched_conf = conf
        if conf == "fuzzy":
            card["extraction"]["needs_review"] = True
        elif conf in ("exact", "alias"):
            card["extraction"]["needs_review"] = False
        break

    if matched_bundle is None:
        card["extraction"]["primary_method"] = card["extraction"].get("primary_method") or "failed"
        # Dedupe errors, prefer specific
        errs = []
        for e in last_errors:
            if e not in errs:
                errs.append(e)
        card["extraction"]["errors"] = errs or ["fetch_failed"]
        card["extraction"]["needs_review"] = True
        return card

    card["extraction"]["match_confidence"] = matched_conf
    # Only AFTER successful fetch + name match → live parse or live_parser_not_ready
    if is_live_parser_ready(sport_n):
        spec = get_live_parser(sport_n)
        assert spec is not None and callable(spec.parse)
        try:
            frag = spec.parse(matched_bundle, match=match, sport=sport_n, cfg=mi)
            if frag:
                card = merge_fragments(card, frag)
            card["extraction"]["errors"] = [
                e
                for e in (card["extraction"].get("errors") or [])
                if e not in ("no_source", "network_disabled", "url_not_found")
            ]
        except Exception:  # noqa: BLE001
            card["extraction"]["errors"] = ["parse_empty"]
            card["extraction"]["needs_review"] = True
        return card

    # PR-1/PR-2 football interim (ready=False)
    card["extraction"]["errors"] = ["live_parser_not_ready"]
    card["extraction"]["needs_review"] = True
    # Attach fetch method for ops visibility
    if matched_bundle.method:
        card["extraction"]["primary_method"] = matched_bundle.method
    return card


def build_match_intel(
    match: str,
    *,
    sport: str = "football",
    cfg: dict[str, Any] | None = None,
    odds_file: str | None = None,
    competition: str | None = None,
    kickoff: str | None = None,
    html_by_source: dict[str, str] | None = None,
    fixture_dir: Path | str | None = None,
    force: bool = False,
    write: bool = True,
    out_dir: Path | str | None = None,
    url: str | None = None,
    allow_network: bool | None = None,
) -> dict[str, Any]:
    """
    Build one MIC card for a match.

    - Offline html_by_source / fixture_dir always wins (tests).
    - Network path when allow_network and URL (or later discovery).
    - Non-v1 sports: skeleton with parser_not_implemented (no network).
    """
    t0 = time.perf_counter()
    mi = _mic_cfg(cfg)
    sport_n = normalize_sport(sport) or (sport or "football").strip().lower()
    v1 = [str(s).lower() for s in (mi.get("v1_sports") or ["football"])]
    out = Path(out_dir or mi.get("out_dir") or "outbox/match_intel")

    # CLI / caller override for allow_network
    if allow_network is not None:
        mi = dict(mi)
        mi["allow_network"] = bool(allow_network)

    # TTL cache
    key = mic_match_key(match)
    existing_path = mic_path(out, match, match_key=key)
    if not force and existing_path.is_file():
        ttl_h = float(mi.get("ttl_hours") or 6)
        try:
            age_s = time.time() - existing_path.stat().st_mtime
            if age_s < ttl_h * 3600:
                cached = read_mic(existing_path)
                if cached:
                    cached["_cache_hit"] = True
                    return cached
        except OSError:
            pass

    card = empty_mic_skeleton(
        match,
        sport=sport_n,
        odds_file=odds_file,
        errors=[],
        primary_method="skeleton",
        match_confidence="none",
        needs_review=True,
    )
    card["extraction"]["errors"] = []

    # NT odds context (always free)
    nt_frag = parse_nt_context(
        match=match, competition=competition, sport=sport_n, kickoff=kickoff
    )
    card = merge_fragments(card, nt_frag)

    if sport_n not in v1:
        card["extraction"]["primary_method"] = "stub"
        card["extraction"]["errors"] = ["parser_not_implemented"]
        card["extraction"]["needs_review"] = True
        _finalize_card(card, t0=t0)
        if write:
            write_mic(card, out, match_key=key)
            card["_path"] = str(mic_path(out, match, match_key=key))
        return card

    # --- offline always wins (tests / operator paste) ---
    html_map: dict[str, str] = dict(html_by_source or {})
    if fixture_dir:
        fd = Path(fixture_dir)
        for src, name in (
            ("flashscore", f"{key}_flashscore.html"),
            ("flashscore", f"{key}.html"),
            ("fotmob", f"{key}_fotmob.html"),
        ):
            p = fd / name
            if p.is_file() and src not in html_map:
                try:
                    html_map[src] = p.read_text(encoding="utf-8")
                except OSError:
                    pass

    if html_map:
        card = _apply_html_sources(card, html_by_source=html_map, match=match)
        if not card["extraction"].get("errors"):
            card["extraction"]["needs_review"] = card["extraction"].get(
                "match_confidence"
            ) not in ("exact", "alias")
            if card["extraction"].get("match_confidence") in ("exact", "alias", "fuzzy"):
                card["extraction"]["errors"] = [
                    e
                    for e in (card["extraction"].get("errors") or [])
                    if e not in ("no_source",)
                ]
        card["match_key"] = key
        _finalize_card(card, t0=t0)
        if write:
            path = write_mic(card, out, match_key=key)
            card["_path"] = str(path)
        return card

    net_on = bool(mi.get("allow_network"))
    if not net_on:
        card["extraction"]["primary_method"] = "failed"
        card["extraction"]["errors"] = ["network_disabled", "no_source"]
        card["extraction"]["needs_review"] = True
        card["match_key"] = key
        _finalize_card(card, t0=t0)
        if write:
            path = write_mic(card, out, match_key=key)
            card["_path"] = str(path)
        return card

    # --- live path: always fetch + match for v1 sports when network on ---
    card = _live_network_path(
        card,
        match=match,
        sport_n=sport_n,
        mi=mi,
        key=key,
        url=url,
        force=force,
    )

    card["match_key"] = key
    _finalize_card(card, t0=t0)

    if write:
        path = write_mic(card, out, match_key=key)
        card["_path"] = str(path)
    return card


def unique_matches_from_odds(
    odds_path: Path | str,
    *,
    sport_filter: str | None = None,
    max_matches: int | None = None,
) -> list[dict[str, Any]]:
    """Parse odds file → unique match list with sport/competition hints."""
    from nt.odds_parse import parse_odds_file

    rows = parse_odds_file(Path(odds_path))
    seen: dict[str, dict[str, Any]] = {}
    for c in rows:
        m = (c.match or "").strip()
        if not m:
            continue
        key = mic_match_key(m)
        if key in seen:
            continue
        sp = normalize_sport(getattr(c, "sport", None) or "") or "unknown"
        if sport_filter and sport_filter not in ("all", "*"):
            if sp != normalize_sport(sport_filter):
                continue
        seen[key] = {
            "match": m,
            "match_key": key,
            "sport": sp,
            "competition": None,
            "kickoff": getattr(c, "kickoff", None) or None,
        }
        if max_matches and len(seen) >= max_matches:
            break
    return list(seen.values())


def run_match_intel_batch(
    cfg: dict[str, Any],
    *,
    odds_path: Path | str | None = None,
    matches: list[str] | None = None,
    sport: str | None = None,
    out_dir: Path | str | None = None,
    force: bool = False,
    write: bool = True,
    html_by_source: dict[str, dict[str, str]] | None = None,
    fixture_dir: Path | str | None = None,
    max_matches: int | None = None,
    url: str | None = None,
    allow_network: bool | None = None,
    urls_by_match: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Build MICs for an odds board or explicit match list.

    Returns summary with grades and paths.
    """
    mi = _mic_cfg(cfg)
    # Apply CLI overrides into a shallow cfg copy for builders
    if allow_network is not None or url is not None:
        cfg = dict(cfg or {})
        research = dict(cfg.get("research") or {})
        mi2 = dict(research.get("match_intel") or {})
        if allow_network is not None:
            mi2["allow_network"] = bool(allow_network)
        research["match_intel"] = mi2
        cfg["research"] = research
        mi = mi2

    out = Path(out_dir or mi.get("out_dir") or "outbox/match_intel")
    cap = max_matches or int(mi.get("max_board_matches") or mi.get("max_matches_per_run") or 40)

    work: list[dict[str, Any]] = []
    if matches:
        for m in matches:
            m = (m or "").strip()
            if not m:
                continue
            work.append(
                {
                    "match": m,
                    "match_key": mic_match_key(m),
                    "sport": sport or mi.get("default_sport") or "football",
                    "competition": None,
                    "url": (urls_by_match or {}).get(mic_match_key(m))
                    or (urls_by_match or {}).get(m)
                    or url,
                }
            )
    elif odds_path:
        work = unique_matches_from_odds(
            odds_path,
            sport_filter=sport if sport and sport != "all" else None,
            max_matches=cap,
        )
        if not work and sport and sport != "all":
            work = unique_matches_from_odds(odds_path, max_matches=cap)
        for w in work:
            w["url"] = (urls_by_match or {}).get(w.get("match_key") or "") or (
                urls_by_match or {}
            ).get(w.get("match") or "") or url
    else:
        return {"ok": False, "error": "odds_or_matches_required", "cards": [], "summary": {}}

    work = work[:cap]
    cards: list[dict[str, Any]] = []
    grade_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    error_counts: dict[str, int] = {}
    sport_counts: dict[str, int] = {}
    process_miss_n = 0
    budget_exhausted_n = 0
    playwright_missing = False
    fetched_ok_n = 0

    for item in work:
        m = item["match"]
        sp = sport or item.get("sport") or "football"
        html_map = None
        if html_by_source:
            html_map = html_by_source.get(item["match_key"]) or html_by_source.get(m)
        card = build_match_intel(
            m,
            sport=sp,
            cfg=cfg,
            odds_file=str(odds_path) if odds_path else None,
            competition=item.get("competition"),
            kickoff=item.get("kickoff"),
            html_by_source=html_map,
            fixture_dir=fixture_dir,
            force=force,
            write=write,
            out_dir=out,
            url=item.get("url") or url,
            allow_network=allow_network,
        )
        cards.append(card)
        g = str((card.get("coverage") or {}).get("grade") or "F")
        grade_counts[g] = grade_counts.get(g, 0) + 1
        sp_c = str(card.get("sport") or sp or "unknown")
        sport_counts[sp_c] = sport_counts.get(sp_c, 0) + 1
        ext = card.get("extraction") or {}
        if ext.get("process_miss"):
            process_miss_n += 1
        method = str(ext.get("primary_method") or "")
        if method in ("firecrawl", "playwright", "http", "cache") and "live_parser_not_ready" in (
            ext.get("errors") or []
        ):
            fetched_ok_n += 1
        for err in ext.get("errors") or []:
            e = str(err)
            error_counts[e] = error_counts.get(e, 0) + 1
            if e == "budget_exhausted":
                budget_exhausted_n += 1
            if e == "playwright_not_installed":
                playwright_missing = True

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    summary: dict[str, Any] = {
        "n": len(cards),
        "grades": grade_counts,
        "process_miss_n": process_miss_n,
        "budget_exhausted_n": budget_exhausted_n,
        "fetched_ok_n": fetched_ok_n,
        "errors": error_counts,
        "sports": sport_counts,
        "playwright_missing": playwright_missing,
        "out_dir": str(out),
        "odds": str(odds_path) if odds_path else None,
        "index_day": day,
    }

    if write:
        index_path = Path(out) / f"_index_{day}.json"
        index_payload = {
            "n": summary["n"],
            "grades": grade_counts,
            "process_miss_n": process_miss_n,
            "budget_exhausted_n": budget_exhausted_n,
            "fetched_ok_n": fetched_ok_n,
            "matched_n": sum(
                1
                for c in cards
                if str((c.get("extraction") or {}).get("match_confidence") or "")
                in ("exact", "alias", "fuzzy")
            ),
            "errors": error_counts,
            "sports": sport_counts,
            "playwright_missing": playwright_missing,
        }
        try:
            atomic_write_json(index_path, index_payload)
            summary["index_path"] = str(index_path)
        except OSError:
            pass

    return {"ok": True, "cards": cards, "summary": summary}
