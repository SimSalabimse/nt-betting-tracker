"""
Live esports parsers (LoL / CS style Flashscore-like HTML / markdown / XHR).

PR-5a: fill form_home / form_away / competition (+ optional ranking / roster / H2H).
"""
from __future__ import annotations

from typing import Any

from nt.match_intel.sources.multi_sport_live import (
    parse_multi_sport_bundle,
    parse_multi_sport_live_html,
    parse_multi_sport_markdown,
    parse_multi_sport_xhr,
)


def parse_esports_bundle(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "esports",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return parse_multi_sport_bundle(bundle, match=match, sport="esports", cfg=cfg)


def parse_esports_live_html(
    html: str,
    *,
    match: str = "",
    page_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return parse_multi_sport_live_html(
        html, match=match, sport="esports", page_meta=page_meta
    )


def parse_esports_markdown(md: str, *, match: str = "") -> dict[str, Any]:
    return parse_multi_sport_markdown(md, match=match, sport="esports")


def parse_esports_xhr(xhrs: list[Any], *, match: str = "") -> dict[str, Any]:
    return parse_multi_sport_xhr(xhrs, match=match, sport="esports")
