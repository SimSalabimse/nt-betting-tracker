"""Norsk Tipping public context — competition labels from odds dump only (v1)."""
from __future__ import annotations

from typing import Any


def parse_nt_context(
    *,
    match: str = "",
    competition: str | None = None,
    sport: str | None = None,
    kickoff: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a partial MIC fragment from NT odds metadata (no network).

    Used as priority-1 context when competition is already on the odds paste.
    """
    out: dict[str, Any] = {
        "competition": {},
        "fields_contributed": [],
        "publisher": "norsk_tipping",
        "method": "odds_context",
        "kickoff_local": kickoff,
    }
    name = (competition or "").strip()
    if name:
        out["competition"] = {
            "name": name,
            "country": None,
            "tier": None,
            "format": None,
            "importance": None,
            "series_context": None,
        }
        out["fields_contributed"].append("competition")
    if extra and isinstance(extra, dict):
        for k, v in extra.items():
            if k not in out or not out[k]:
                out[k] = v
    return out
