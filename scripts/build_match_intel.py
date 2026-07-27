#!/usr/bin/env python3
"""Convenience CLI: build Match Intelligence Cards (wraps run_nt research match-intel)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.match_intel.pipeline import run_match_intel_batch


def main() -> int:
    p = argparse.ArgumentParser(description="Build Match Intelligence Cards")
    p.add_argument("--odds", default=None, help="Odds dump path")
    p.add_argument("--matches", default=None, help='Match list "A vs B; C vs D"')
    p.add_argument("--sport", default=None)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--fixture-dir", default=None)
    p.add_argument("--allow-network", action="store_true", default=False)
    p.add_argument("--url", default=None, help="Explicit match page URL (PR-1)")
    p.add_argument("--max-matches", type=int, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.odds and not args.matches:
        print("--odds or --matches required", file=sys.stderr)
        return 2

    match_list = None
    if args.matches:
        match_list = [x.strip() for x in args.matches.replace("|", ";").split(";") if x.strip()]

    cfg = load_config()
    payload = run_match_intel_batch(
        cfg,
        odds_path=args.odds,
        matches=match_list,
        sport=args.sport,
        out_dir=args.out_dir,
        force=args.force,
        fixture_dir=args.fixture_dir,
        allow_network=True if args.allow_network else None,
        url=args.url,
        max_matches=args.max_matches,
    )
    import json

    if args.json:
        print(json.dumps(payload.get("summary"), indent=2))
    else:
        s = payload.get("summary") or {}
        print(f"n={s.get('n')} grades={s.get('grades')} out={s.get('out_dir')}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
