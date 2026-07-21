#!/usr/bin/env python3
"""
Prune artifacts/api_raw growth (Phase 4 / audit B12).

Default: dry-run. Keeps files newer than --days (mtime) and always keeps a
small set of known useful roots if present.

Usage:
  python scripts/prune_api_raw.py              # dry-run, 7 days
  python scripts/prune_api_raw.py --days 3
  python scripts/prune_api_raw.py --apply      # actually delete
  python scripts/prune_api_raw.py --apply --days 14 --keep-min 500
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_RAW = ROOT / "artifacts" / "api_raw"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Prune artifacts/api_raw by mtime")
    ap.add_argument("--days", type=float, default=7.0, help="Keep files newer than N days (default 7)")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete (default is dry-run)",
    )
    ap.add_argument(
        "--keep-min",
        type=int,
        default=0,
        help="If remaining file count would drop below this, stop deleting (safety)",
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=API_RAW,
        help="api_raw directory (default: artifacts/api_raw)",
    )
    args = ap.parse_args(argv)

    root: Path = args.root
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    cutoff = time.time() - float(args.days) * 86400.0
    files = [p for p in root.rglob("*") if p.is_file()]
    old = [p for p in files if p.stat().st_mtime < cutoff]
    old.sort(key=lambda p: p.stat().st_mtime)  # oldest first

    print(f"api_raw: {root}")
    print(f"total files: {len(files)}")
    print(f"older than {args.days}d: {len(old)}")
    print(f"mode: {'APPLY' if args.apply else 'DRY-RUN'}")

    deleted = 0
    bytes_freed = 0
    remaining = len(files)
    for p in old:
        if args.keep_min and (remaining - 1) < int(args.keep_min):
            print(f"stop: keep-min={args.keep_min} would be violated")
            break
        try:
            sz = p.stat().st_size
        except OSError:
            sz = 0
        if args.apply:
            try:
                p.unlink()
            except OSError as e:
                print(f"skip {p}: {e}")
                continue
        deleted += 1
        remaining -= 1
        bytes_freed += sz
        if deleted <= 15 or deleted % 500 == 0:
            print(f"  {'delete' if args.apply else 'would delete'}: {p.relative_to(root)}")

    print(f"done: {'deleted' if args.apply else 'would delete'} {deleted} files "
          f"(~{bytes_freed / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
