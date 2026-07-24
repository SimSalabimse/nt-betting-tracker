#!/usr/bin/env python3
"""
FEH cleanup inventory (PR1) — report only, do not delete aggressively.

Outputs CSV/JSON rows: path, line, snippet, classification
  research_ok | place_risk | docs | delete | archive | ship_blocker

Golden hotspots (minimum set) are always emitted even if regex misses.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

Classification = str

# Golden expected classifications (design doc)
GOLDEN: list[dict[str, str]] = [
    {
        "path": "nt/light_research.py",
        "snippet": "promo_mid_band_boost / mid_band",
        "classification": "research_ok",
        "note": "queue ranking only",
    },
    {
        "path": "nt/light_research.py",
        "snippet": "cov_prefer_dogs / coverage dog preference",
        "classification": "research_ok",
        "note": "research composition",
    },
    {
        "path": "nt/bankroll_regime.py",
        "snippet": "mid_odds prefer sort",
        "classification": "research_ok",
        "note": "regime research sort",
    },
    {
        "path": "nt/portfolio.py",
        "snippet": "explore / temp_ev_relax",
        "classification": "place_risk",
        "note": "until FEH F first",
    },
    {
        "path": "artifacts/_upgrade_packs_grade_b.py",
        "snippet": "upgrade packs to Grade B",
        "classification": "delete",
        "note": "quarantine before place ownership (PR2)",
    },
    {
        "path": "artifacts/_scan_midband.py",
        "snippet": "midband soft dog scan",
        "classification": "archive",
        "note": "quarantine / archive before place ownership",
    },
    {
        "path": "AGENTS.md",
        "snippet": "preferred band as place quality",
        "classification": "docs",
        "note": "docs rewrite PR6",
    },
    {
        "path": "nt/evidence_hierarchy",
        "snippet": "package sources required (no pyc-only ship)",
        "classification": "research_ok",
        "note": "golden reminder; live ship_blocker only from _hierarchy_status when broken",
    },
]

SCAN_PATTERNS: list[tuple[str, re.Pattern[str], Classification]] = [
    ("nt/light_research.py", re.compile(r"promo_mid_band|mid_band_boost|cov_prefer_dogs"), "research_ok"),
    ("nt/bankroll_regime.py", re.compile(r"mid_odds|prefer.*band", re.I), "research_ok"),
    ("nt/portfolio.py", re.compile(r"temp_ev_relax|EXPLORE_REGIME|regime_explore"), "place_risk"),
    ("artifacts/_upgrade_packs_grade_b.py", re.compile(r"."), "delete"),
    ("artifacts/_scan_midband.py", re.compile(r"."), "archive"),
]

REQUIRED_PY = (
    "__init__.py",
    "types.py",
    "normalize.py",
    "h2h_normalize.py",
    "cards.py",
    "score.py",
)


def _hierarchy_status() -> list[dict[str, object]]:
    pkg = ROOT / "nt" / "evidence_hierarchy"
    rows: list[dict[str, object]] = []
    missing = [n for n in REQUIRED_PY if not (pkg / n).is_file()]
    pyc_only = False
    if pkg.is_dir():
        pycs = list((pkg / "__pycache__").glob("*.pyc")) if (pkg / "__pycache__").is_dir() else []
        pys = list(pkg.glob("*.py"))
        pyc_only = bool(pycs) and not pys
    cls = "ship_blocker" if (missing or pyc_only) else "research_ok"
    rows.append(
        {
            "path": "nt/evidence_hierarchy",
            "line": 0,
            "snippet": (
                f"missing={missing}; pyc_only={pyc_only}; "
                f"py_count={len(list(pkg.glob('*.py'))) if pkg.is_dir() else 0}"
            ),
            "classification": cls,
            "note": "CI import guard target",
        }
    )
    return rows


def _scan_file(rel: str, pat: re.Pattern[str], classification: Classification) -> list[dict]:
    path = ROOT / rel
    if not path.is_file():
        return [
            {
                "path": rel,
                "line": 0,
                "snippet": "(file missing)",
                "classification": classification,
                "note": "path not present",
            }
        ]
    out: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [
            {
                "path": rel,
                "line": 0,
                "snippet": f"read_error:{exc}",
                "classification": classification,
                "note": "",
            }
        ]
    for i, line in enumerate(lines, 1):
        if pat.search(line):
            out.append(
                {
                    "path": rel,
                    "line": i,
                    "snippet": line.strip()[:160],
                    "classification": classification,
                    "note": "regex hit",
                }
            )
            if len(out) >= 12:
                break
    if not out:
        out.append(
            {
                "path": rel,
                "line": 0,
                "snippet": "(pattern not found; golden still applies)",
                "classification": classification,
                "note": "no regex hit",
            }
        )
    return out


def build_inventory() -> list[dict]:
    rows: list[dict] = []
    # Golden always present
    for g in GOLDEN:
        rows.append(
            {
                "path": g["path"],
                "line": 0,
                "snippet": g["snippet"],
                "classification": g["classification"],
                "note": g.get("note", "golden"),
            }
        )
    rows.extend(_hierarchy_status())
    for rel, pat, cls in SCAN_PATTERNS:
        rows.extend(_scan_file(rel, pat, cls))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="FEH cleanup inventory (report only)")
    ap.add_argument("--json", type=Path, default=None, help="Write JSON report path")
    ap.add_argument("--csv", type=Path, default=None, help="Write CSV report path")
    ap.add_argument(
        "--fail-on-ship-blocker",
        action="store_true",
        help="Exit 1 if evidence_hierarchy sources missing",
    )
    args = ap.parse_args()
    rows = build_inventory()

    # stdout summary
    by_cls: dict[str, int] = {}
    for r in rows:
        by_cls[str(r["classification"])] = by_cls.get(str(r["classification"]), 0) + 1
    print("FEH cleanup inventory")
    print(f"  rows: {len(rows)}")
    for k, v in sorted(by_cls.items()):
        print(f"  {k}: {v}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        print(f"  wrote {args.json}")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f, fieldnames=["path", "line", "snippet", "classification", "note"]
            )
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"  wrote {args.csv}")

    if args.fail_on_ship_blocker:
        blockers = [r for r in rows if r.get("classification") == "ship_blocker"]
        # Only fail when hierarchy sources actually missing
        hier = [r for r in blockers if "missing=" in str(r.get("snippet")) and "missing=[]" not in str(r.get("snippet"))]
        pyc = [r for r in blockers if "pyc_only=True" in str(r.get("snippet"))]
        if hier or pyc:
            print("SHIP BLOCKER: evidence_hierarchy sources incomplete", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
