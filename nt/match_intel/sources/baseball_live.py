"""
Live baseball parsers (Flashscore-like HTML / markdown / XHR).

PR-5c: form_home/away + competition + standings_or_rank (+ optional H2H/injuries/rest).
"""
from __future__ import annotations

from typing import Any

from nt.match_intel.sources.multi_sport_live import (
    parse_multi_sport_bundle,
    parse_multi_sport_live_html,
    parse_multi_sport_markdown,
    parse_multi_sport_xhr,
)


def parse_baseball_bundle(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "baseball",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return parse_multi_sport_bundle(bundle, match=match, sport="baseball", cfg=cfg)


def parse_baseball_live_html(
    html: str,
    *,
    match: str = "",
    page_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return parse_multi_sport_live_html(
        html, match=match, sport="baseball", page_meta=page_meta
    )


def parse_baseball_markdown(md: str, *, match: str = "") -> dict[str, Any]:
    return parse_multi_sport_markdown(md, match=match, sport="baseball")


def parse_baseball_xhr(xhrs: list[Any], *, match: str = "") -> dict[str, Any]:
    return parse_multi_sport_xhr(xhrs, match=match, sport="baseball")
