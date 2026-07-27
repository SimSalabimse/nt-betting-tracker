"""
Sport → live parser registry.

PR-1/PR-2: football may be in v1_sports with ready=False (fetch-for-instrumentation).
Live parse (ready=True) ships in PR-3+.
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


# Interim: football registered but not ready (PR-1 instrumentation path).
LIVE_PARSERS: dict[str, LiveParserSpec] = {
    "football": LiveParserSpec(
        ready=False,
        parse=None,
        sources=["flashscore", "fotmob"],
        notes="PR-1/PR-2: fetch+match only; live parse in PR-3",
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
