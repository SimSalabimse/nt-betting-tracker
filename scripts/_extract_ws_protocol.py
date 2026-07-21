"""Extract WebSocket / subscription host + message shapes from NT sportsbook JS."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js_dir = ROOT / "artifacts" / "js"

for name in ["app.js", "101.js", "71.js", "288.js"]:
    p = js_dir / name
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    print(f"\n######## {name} len={len(t)}")
    for pat in [
        r"hosts\.subscription[^;]{0,200}",
        r"subscription[^\"']{0,30}https?://[^\"']+",
        r"wss?://[^\"'\s]+",
        r"hosts:\s*\{[^}]{0,500}\}",
        r"registerCallback[^}]{0,300}",
        r"CONTENT_CHANGE[^}]{0,200}",
        r"/listen",
        r"/content",
        r"managePendingSubscriptions",
        r"idfomarket",
        r"inplay",
        r"IN_PLAY",
        r"liveEvents",
        r"getInPlay",
        r"fullMarkets",
        r"subscribeTo",
    ]:
        ms = list(re.finditer(pat, t, flags=re.I))
        if not ms:
            continue
        print(f"--- {pat} n={len(ms)}")
        for m in ms[:6]:
            print(repr(t[max(0, m.start() - 50) : m.start() + 180])[:200])
