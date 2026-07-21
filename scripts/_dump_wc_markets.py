"""Dump key SPA-ARG and board markets from latest odds."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
events = json.loads((ROOT / "data/odds/latest.json").read_text(encoding="utf-8"))

KEY_SUB = (
    "kampresultat",
    "totalt antall mål over/under",
    "begge lag scorer",
    "3-veis handicap",
    "1. omgang totalt",
    "dobbelt sjanse",
    "lag til å score 1",
    "vinner",
    "fulltid",
    "handikap 2-veis",
    "totalt antall over/under",
    "totalt antall mål",
    "legs",
    "vinner inkludert",
)


def show_event(e: dict) -> None:
    print("=" * 70)
    print(e.get("event"), "|", e.get("sport"), "|", e.get("start") or e.get("kickoff"))
    for m in e.get("markets", []):
        name = m.get("market", "")
        nl = name.lower()
        if not any(k in nl for k in KEY_SUB):
            continue
        outs = ", ".join(f"{o.get('outcome')}:{o.get('odds')}" for o in m.get("outcomes", [])[:10])
        print(f"  {name}: {outs}")


for e in events:
    show_event(e)
