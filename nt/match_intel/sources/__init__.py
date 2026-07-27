"""Free-source adapters for Match Intelligence (Flashscore / FotMob / NT stubs)."""
from __future__ import annotations

from nt.match_intel.sources.baseball_live import parse_baseball_bundle
from nt.match_intel.sources.darts_live import parse_darts_bundle
from nt.match_intel.sources.esports_live import parse_esports_bundle
from nt.match_intel.sources.flashscore import parse_flashscore_html
from nt.match_intel.sources.flashscore_live import parse_football_bundle
from nt.match_intel.sources.fotmob import parse_fotmob_html, parse_fotmob_live_content
from nt.match_intel.sources.nt import parse_nt_context
from nt.match_intel.sources.snooker_live import parse_snooker_bundle
from nt.match_intel.sources.tennis_live import parse_tennis_bundle

__all__ = [
    "parse_baseball_bundle",
    "parse_darts_bundle",
    "parse_esports_bundle",
    "parse_flashscore_html",
    "parse_football_bundle",
    "parse_fotmob_html",
    "parse_fotmob_live_content",
    "parse_nt_context",
    "parse_snooker_bundle",
    "parse_tennis_bundle",
]
