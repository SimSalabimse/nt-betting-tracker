"""
Live darts parsers (Flashscore-like HTML / markdown / XHR).

PR-5b: form_or_rank_home/away + competition (+ optional H2H / rest_days).
"""
from __future__ import annotations

from typing import Any

from nt.match_intel.sources.multi_sport_live import (
    parse_multi_sport_bundle,
    parse_multi_sport_live_html,
    parse_multi_sport_markdown,
    parse_multi_sport_xhr,
)


def parse_darts_bundle(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "darts",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return parse_multi_sport_bundle(bundle, match=match, sport="darts", cfg=cfg)


def parse_darts_live_html(
    html: str,
    *,
    match: str = "",
    page_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return parse_multi_sport_live_html(
        html, match=match, sport="darts", page_meta=page_meta
    )


def parse_darts_markdown(md: str, *, match: str = "") -> dict[str, Any]:
    return parse_multi_sport_markdown(md, match=match, sport="darts")


def parse_darts_xhr(xhrs: list[Any], *, match: str = "") -> dict[str, Any]:
    return parse_multi_sport_xhr(xhrs, match=match, sport="darts")
