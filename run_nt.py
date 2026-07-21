#!/usr/bin/env python3
"""CLI entry that works on Windows (built-in ``nt`` module shadowing)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
