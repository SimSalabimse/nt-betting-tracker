"""Find where midTier hosts (services + subscription) are initialized."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in ["app.js", "101.js", "71.js", "5.js", "58.js", "64.js"]:
    p = ROOT / "artifacts" / "js" / name
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    print(f"\n#### {name}")
    for pat in [
        r"hosts\.services\s*=",
        r"initialize\([^)]{0,200}\)",
        r"subscription[\"']?\s*[:=]\s*[\"'][^\"']+",
        r"services[\"']?\s*[:=]\s*[\"']https?://[^\"']+",
        r"sport2\.norsk-tipping\.no[^\"']{0,80}",
        r"midTier\.initialize",
        r"ContentServices\.get",
        r"subscribeAndGet",
        r"WebSocket",
        r"new\s+WebSocket",
        r"wss:",
    ]:
        ms = list(re.finditer(pat, t))
        if not ms:
            continue
        print(f"  {pat} n={len(ms)}")
        for m in ms[:8]:
            print("   ", repr(t[max(0, m.start() - 60) : m.start() + 140])[:220])
