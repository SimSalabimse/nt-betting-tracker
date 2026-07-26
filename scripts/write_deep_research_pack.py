#!/usr/bin/env python3
"""
Atomic writer for deep_research_v1 evidence packs (ESR Stage 2).

Only allowed final pack write path for /deep-research. Do not use bare
``research write-pack`` after this helper — re-run with full payload instead.

Usage (from tracker root)::

    python scripts/write_deep_research_pack.py --payload outbox/deep_research/slug.payload.json
    python scripts/write_deep_research_pack.py --payload - < payload.json
    type payload.json | python scripts/write_deep_research_pack.py --stdin
    python scripts/write_deep_research_pack.py path/to/payload.json --odds-ref 1.85

Stdout: JSON ``{ok, path, esr_keys_present, warnings, errors}``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.research import write_deep_research_pack


def _load_payload(path: str | None, use_stdin: bool) -> dict:
    if use_stdin or path in (None, "", "-"):
        raw = sys.stdin.read()
        if not raw.strip():
            raise SystemExit("empty stdin — pass --payload PATH or pipe JSON")
        data = json.loads(raw)
    else:
        p = Path(path)
        if not p.is_file():
            raise SystemExit(f"payload not found: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("payload must be a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="write_deep_research_pack.py",
        description=(
            "Atomically write a complete deep_research_v1 evidence pack. "
            "Validates ≥4 sources with takeaways, opposite_side_check, deep_research "
            "block; warns on weak phrases. Gate-canonical availability_status only."
        ),
    )
    parser.add_argument(
        "payload_positional",
        nargs="?",
        default=None,
        help="JSON payload path (optional if --payload / --stdin)",
    )
    parser.add_argument(
        "--payload",
        "-p",
        default=None,
        help="JSON payload path, or '-' for stdin",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read payload JSON from stdin",
    )
    parser.add_argument(
        "--odds-ref",
        type=float,
        default=None,
        help="Override decimal_odds_ref on the pack",
    )
    parser.add_argument(
        "--filename",
        default=None,
        help="Evidence filename (default: safe match_selection.json)",
    )
    parser.add_argument(
        "--evidence-dir",
        default=None,
        help="Override evidence directory (default: config paths.evidence)",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Fail if target path already exists (default: idempotent overwrite)",
    )
    args = parser.parse_args(argv)

    path_arg = args.payload if args.payload is not None else args.payload_positional
    if args.stdin or path_arg == "-":
        use_stdin = True
        path_arg = None
    elif path_arg is None:
        if not sys.stdin.isatty():
            use_stdin = True
        else:
            parser.error("provide --payload PATH, a positional path, or --stdin")
    else:
        use_stdin = False

    try:
        payload = _load_payload(path_arg, use_stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "errors": [f"invalid JSON: {e}"]}), file=sys.stdout)
        return 2

    cfg = load_config()
    res = write_deep_research_pack(
        cfg,
        payload,
        odds=args.odds_ref,
        filename=args.filename,
        evidence_dir=args.evidence_dir,
        overwrite=not args.no_overwrite,
    )
    out = {
        "ok": res.get("ok"),
        "path": res.get("path"),
        "esr_keys_present": res.get("esr_keys_present"),
        "warnings": res.get("warnings") or [],
        "errors": res.get("errors") or [],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
