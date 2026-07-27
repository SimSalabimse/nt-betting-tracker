"""
Sport → live parser registry.

PR-3: football ready=True (Flashscore live + data-* fallback + FotMob secondary).
PR-4: tennis ready=True + v1_sports append (KD-17).
PR-5: esports / snooker / darts / baseball ready=True + v1_sports append (KD-17).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# parse(bundle, *, match, sport, cfg) -> fragment dict
ParseFn = Callable[..., dict[str, Any]]


@dataclass
class LiveParserSpec:
    ready: bool = False
    parse: ParseFn | None = None
    sources: list[str] = field(default_factory=list)
    notes: str = ""


def _parse_football_live(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "football",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from nt.match_intel.sources.flashscore_live import parse_football_bundle

    return parse_football_bundle(bundle, match=match, sport=sport, cfg=cfg)


def _parse_tennis_live(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "tennis",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from nt.match_intel.sources.tennis_live import parse_tennis_bundle

    return parse_tennis_bundle(bundle, match=match, sport=sport, cfg=cfg)


def _parse_esports_live(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "esports",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from nt.match_intel.sources.esports_live import parse_esports_bundle

    return parse_esports_bundle(bundle, match=match, sport=sport, cfg=cfg)


def _parse_snooker_live(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "snooker",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from nt.match_intel.sources.snooker_live import parse_snooker_bundle

    return parse_snooker_bundle(bundle, match=match, sport=sport, cfg=cfg)


def _parse_darts_live(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "darts",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from nt.match_intel.sources.darts_live import parse_darts_bundle

    return parse_darts_bundle(bundle, match=match, sport=sport, cfg=cfg)


def _parse_baseball_live(
    bundle: Any,
    *,
    match: str = "",
    sport: str = "baseball",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from nt.match_intel.sources.baseball_live import parse_baseball_bundle

    return parse_baseball_bundle(bundle, match=match, sport=sport, cfg=cfg)


LIVE_PARSERS: dict[str, LiveParserSpec] = {
    "football": LiveParserSpec(
        ready=True,
        parse=_parse_football_live,
        sources=["flashscore", "fotmob"],
        notes="PR-3: live Flashscore HTML/markdown/XHR + offline data-* fallback; FotMob secondary",
    ),
    "tennis": LiveParserSpec(
        ready=True,
        parse=_parse_tennis_live,
        sources=["flashscore"],
        notes="PR-4: live tennis form/rank/competition/surface/H2H from HTML/markdown/XHR",
    ),
    "esports": LiveParserSpec(
        ready=True,
        parse=_parse_esports_live,
        sources=["flashscore"],
        notes="PR-5a: LoL/CS form + competition (+ ranking/roster/H2H optional)",
    ),
    "snooker": LiveParserSpec(
        ready=True,
        parse=_parse_snooker_live,
        sources=["flashscore"],
        notes="PR-5b: form_or_rank + competition (+ H2H optional)",
    ),
    "darts": LiveParserSpec(
        ready=True,
        parse=_parse_darts_live,
        sources=["flashscore"],
        notes="PR-5b: form_or_rank + competition (+ H2H optional)",
    ),
    "baseball": LiveParserSpec(
        ready=True,
        parse=_parse_baseball_live,
        sources=["flashscore"],
        notes="PR-5c: form + competition + standings_or_rank (+ H2H optional)",
    ),
}


def get_live_parser(sport: str) -> LiveParserSpec | None:
    key = (sport or "").strip().lower()
    return LIVE_PARSERS.get(key)


def is_live_parser_ready(sport: str) -> bool:
    spec = get_live_parser(sport)
    return bool(spec and spec.ready and callable(spec.parse))


def register_live_parser(sport: str, spec: LiveParserSpec) -> None:
    """Test / PR helper to swap registry entries."""
    LIVE_PARSERS[(sport or "").strip().lower()] = spec
