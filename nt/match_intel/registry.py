"""
Sport → live parser registry.

PR-3: football ready=True (Flashscore live + data-* fallback + FotMob secondary).
Tennis / other sports join in later PRs with ready=True in the same PR (KD-17).
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


LIVE_PARSERS: dict[str, LiveParserSpec] = {
    "football": LiveParserSpec(
        ready=True,
        parse=_parse_football_live,
        sources=["flashscore", "fotmob"],
        notes="PR-3: live Flashscore HTML/markdown/XHR + offline data-* fallback; FotMob secondary",
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
