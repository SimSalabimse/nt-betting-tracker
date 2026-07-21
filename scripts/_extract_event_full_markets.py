"""Find eventFullMarkets subscribe flow and host wiring in 71.js / app.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in ["71.js", "app.js", "101.js"]:
    t = (ROOT / "artifacts" / "js" / name).read_text(encoding="utf-8", errors="ignore")
    print(f"\n#### {name}")
    for m in re.finditer(r"eventFullMarkets", t):
        print(repr(t[max(0, m.start() - 120) : m.start() + 250])[:280])
        print("---")
    for m in re.finditer(r"hosts\.(services|subscription|servername)", t):
        print("host", repr(t[max(0, m.start() - 80) : m.start() + 120])[:200])
    for m in re.finditer(r"opr\d|sport2\.norsk|subscription", t):
        if m.start() > 0 and "opr" in m.group().lower() or "sport2" in m.group().lower():
            print("hosty", repr(t[max(0, m.start() - 40) : m.start() + 100])[:180])
