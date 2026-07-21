#!/usr/bin/env python3
"""Launch the local NT Betting Tracker desktop UI."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from desktop.app import main

if __name__ == "__main__":
    main()
