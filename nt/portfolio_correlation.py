"""
P1 soft correlation keys: league / script family / kickoff window.

Also re-exports market_family (coarse diversify hard-cap family).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from nt.market_family import market_family  # noqa: F401  — re-export


def league_key(
    *,
    evidence: dict[str, Any] | None = None,
    match: str = "",
    sport: str = "",
    notes: str = "",
) -> str:
    """
    Known league/competition key, or 'unknown' (unknown does not consume league caps).
    """
    ev = evidence or {}
    for k in ("competition", "league", "tournament", "series"):
        v = str(ev.get(k) or "").strip().lower()
        if v:
            return re.sub(r"[^a-z0-9]+", "_", v)[:48]

    blob = f"{match} {notes} {ev.get('summary') or ''}".lower()
    # Lightweight league fingerprints
    patterns = [
        (r"eliteserien|obos-ligaen", "eliteserien"),
        (r"premier league|epl\b", "premier_league"),
        (r"la liga|laliga", "la_liga"),
        (r"serie a\b", "serie_a"),
        (r"bundesliga", "bundesliga"),
        (r"ligue 1", "ligue_1"),
        (r"champions league|\bucl\b", "ucl"),
        (r"europa league|\buel\b", "uel"),
        (r"world cup|\bfifa\b|wc 20", "world_cup"),
        (r"wimbledon|roland garros|us open|australian open", "tennis_slam"),
        (r"atp\b", "atp"),
        (r"wta\b", "wta"),
        (r"nba\b", "nba"),
        (r"wnba\b", "wnba"),
        (r"pdc\b|premier league darts", "pdc"),
    ]
    for pat, key in patterns:
        if re.search(pat, blob):
            return key
    return "unknown"


def script_family(
    *,
    selection: str = "",
    market_type: str = "",
    market_key: str = "",
    evidence: dict[str, Any] | None = None,
) -> str:
    """Coarse script bucket for soft correlation."""
    ev = evidence or {}
    lean = str(ev.get("script_lean") or "").strip().lower()
    if lean in ("cagey", "open", "shootout", "grind"):
        # map lean + market
        pass
    from nt.analytics import infer_market

    mk = (market_key or infer_market(selection, market_type) or "").lower()
    sel = (selection or "").lower()

    if "btts" in mk or "begge" in sel:
        if "nei" in sel or "no" in sel:
            return "btts_no"
        return "btts_yes"
    if "under" in mk or "under" in sel:
        return "totals_under"
    if "over" in mk or "over" in sel:
        return "totals_over"
    if "handikap" in mk or "handicap" in mk or "hc" == mk:
        return "handicap"
    if mk in ("ml", "match_result", "winner") or "vinner" in sel or "to win" in sel:
        # crude fav/dog: not enough odds here — single bucket
        return "match_winner"
    if "clean" in mk or "nullen" in sel:
        return "clean_sheet"
    return mk or "other"


def parse_kickoff_hour(kickoff: str) -> float | None:
    """
    Parse kickoff to a comparable hour timestamp (UTC hours since epoch).
    Accepts 'YYYY-MM-DD HH:MM' or ISO.
    """
    ko = (kickoff or "").strip()
    if not ko:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ):
        try:
            raw = ko.replace("Z", "")
            if fmt.endswith("Z"):
                raw = ko.replace("Z", "")
            dt = datetime.strptime(raw[: len("2026-07-21T19:00:00")], fmt.replace("Z", ""))
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp() / 3600.0
        except ValueError:
            continue
    try:
        raw = ko.replace("Z", "+00:00") if "Z" in ko else ko
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp() / 3600.0
    except ValueError:
        return None


def count_ko_window(
    candidate_hour: float | None,
    open_hours: list[float | None],
    *,
    window_hours: float,
) -> int:
    """How many open/picked kickoffs fall within ±window of candidate."""
    if candidate_hour is None:
        return 0
    n = 0
    for h in open_hours:
        if h is None:
            continue
        if abs(h - candidate_hour) <= window_hours + 1e-9:
            n += 1
    return n
