"""Dump selected lines from current odds for pack writing."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_parse import parse_odds_file

lines = parse_odds_file(ROOT / "inbox" / "current_odds_01.txt")
keys = [
    "van gerwen",
    "clayton",
    "falkenberg",
    "fenerbahce",
    "sturm",
    "jacquemot",
    "faria",
    "anderson",
    "mjallby",
    "göteborg",
    "goteborg",
    "thun",
    "astralis",
    "wildcard",
    "einfach",
    "duijvenbode",
]
for L in lines:
    m = str(L.match or "")
    sel = str(L.selection or "")
    blob = (m + " " + sel).lower()
    if not any(k in blob for k in keys):
        continue
    ko = str(L.kickoff or "")[:16]
    print(f"{ko} | {m[:42]:42} | {sel[:55]:55} | {L.decimal_odds}")
