"""Print all SPA-ARG markets (compact) and selection formats."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
events = json.loads((ROOT / "data/odds/latest.json").read_text(encoding="utf-8"))
spa = next(e for e in events if e.get("event") == "Spania - Argentina")
print("n_markets", len(spa.get("markets", [])))
for m in spa.get("markets", []):
    name = m.get("market", "")
    outs = m.get("outcomes", [])
    if len(outs) > 12:
        s = ", ".join(f"{o.get('outcome')}:{o.get('odds')}" for o in outs[:6]) + f" ... (+{len(outs)-6})"
    else:
        s = ", ".join(f"{o.get('outcome')}:{o.get('odds')}" for o in outs)
    print(f"{name}: {s}")
