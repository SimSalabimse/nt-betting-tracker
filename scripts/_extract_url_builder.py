"""Extract URL builder A(hostKey, path) for services/subscription."""
from __future__ import annotations

import re
from pathlib import Path

t = Path("artifacts/js/app.js").read_text(encoding="utf-8", errors="ignore")

# Find function A used as A("subscription","/listen") and A(P,"/content/get")
for m in re.finditer(r'A\("subscription"', t):
    print("sub call", repr(t[max(0, m.start() - 100) : m.start() + 80]))

for m in re.finditer(r'function A\(|A=function|var A=|,\s*A=function', t):
    print("A def?", repr(t[max(0, m.start() - 20) : m.start() + 200])[:220])

# Search for hosts.services usage in URL construction
for m in re.finditer(r"hosts\.(services|subscription|servername|ip)", t):
    print("hosts", repr(t[max(0, m.start() - 80) : m.start() + 150])[:230])

# Look for wss protocol construction
for m in re.finditer(r'\"wss\"|\'wss\'|protocol.*subscription|subscription.*protocol', t):
    print("proto", repr(t[max(0, m.start() - 60) : m.start() + 120])[:200])

# Find initialize call site with e.services e.subscriptions
for m in re.finditer(r"e\.services|e\.subscriptions|subscriptions:", t):
    print("initcfg", repr(t[max(0, m.start() - 120) : m.start() + 180])[:250])
