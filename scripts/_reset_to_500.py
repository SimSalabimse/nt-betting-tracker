"""Clean reset: archive ledger, empty bets.csv, equity back to baseline 500."""
from __future__ import annotations

import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401
from nt.bets_io import BET_HEADER
bets = ROOT / "data" / "bets.csv"
arch = ROOT / "history" / "archives"
arch.mkdir(parents=True, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
if bets.exists() and bets.stat().st_size > 50:
    dest = arch / f"bets_pre_reset_{ts}.csv"
    shutil.copy2(bets, dest)
    print(f"archived -> {dest}")

with bets.open("w", encoding="utf-8", newline="") as f:
    csv.DictWriter(f, fieldnames=BET_HEADER).writeheader()
print("ledger cleared")

cfg = ROOT / "config.yaml"
text = cfg.read_text(encoding="utf-8")
text2 = re.sub(r'era_start:\s*"[0-9-]+"', 'era_start: "2026-07-19"', text)
cfg.write_text(text2, encoding="utf-8")
print("era_start -> 2026-07-19")

# Soft-reset learning state (optional file)
learn = ROOT / "data" / "state" / "learning.json"
if learn.exists():
    learn.write_text(
        '{\n  "updated_at": null,\n  "n_settled": 0,\n  "note": "reset 2026-07-19 clean 500"\n}\n',
        encoding="utf-8",
    )
    print("learning.json reset")
