#!/usr/bin/env python3
"""Run capital_v2 Phase 2.5 Monte-Carlo suite and write report to outbox."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_mc import format_report, run_core_suite


def main() -> int:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    n_paths = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    suite = run_core_suite(seed=seed, n_paths=n_paths)
    # Drop non-JSON results for file
    payload = {
        k: v
        for k, v in suite.items()
        if k != "results"
    }
    outbox = ROOT / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    md = format_report(suite)
    (outbox / "CAPITAL_V2_MC_REPORT.md").write_text(md + "\n", encoding="utf-8")
    (outbox / "CAPITAL_V2_MC_REPORT.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(md)
    print(f"\nWrote outbox/CAPITAL_V2_MC_REPORT.md and .json")
    print(f"all_clear={suite['all_clear']} violations={suite['total_violations_all_scenarios']}")
    return 0 if suite["all_clear"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
