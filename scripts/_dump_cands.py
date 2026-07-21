#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_parse import parse_odds_file

cs = parse_odds_file(ROOT / "inbox" / "current_odds_01.txt")
want = (
    "Navone",
    "Muller, Alexandre",
    "Fu, Marco",
    "Haotian",
    "Highfield",
    "Badosa",
    "Costoulas",
    "Carabelli",
    "FEARX",
    "1W Team",
    "Cheung",
    "Ferreira",
    "Van Assche",
    "Brion",
    "Arcred",
)
for c in cs:
    if any(x in c.match for x in want):
        print(f"{c.decimal_odds:5.2f} | {c.match[:42]:42} | {c.selection}")
