#!/usr/bin/env python3
"""CLI: historical replay of last N settled under current capital rules."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.historical_replay import replay_last_settled, render_replay_markdown


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay last N settled under capital_v2+Kelly")
    ap.add_argument("-n", type=int, default=40, help="Number of settled tickets (default 40)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--out",
        type=str,
        default="",
        help="Write markdown report path (default artifacts/HISTORICAL_REPLAY_VALIDATION.md)",
    )
    args = ap.parse_args()
    cfg = load_config()
    report = replay_last_settled(cfg, n=args.n)
    md = render_replay_markdown(report)
    out = Path(args.out) if args.out else ROOT / "artifacts" / "HISTORICAL_REPLAY_VALIDATION.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(md)
        print(f"\nWrote {out}")
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
