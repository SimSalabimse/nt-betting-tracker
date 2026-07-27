"""Free-source adapters for Match Intelligence (Flashscore / FotMob / NT stubs)."""
from __future__ import annotations

from nt.match_intel.sources.flashscore import parse_flashscore_html
from nt.match_intel.sources.flashscore_live import parse_football_bundle
from nt.match_intel.sources.fotmob import parse_fotmob_html, parse_fotmob_live_content
from nt.match_intel.sources.nt import parse_nt_context

__all__ = [
    "parse_flashscore_html",
    "parse_football_bundle",
    "parse_fotmob_html",
    "parse_fotmob_live_content",
    "parse_nt_context",
]
