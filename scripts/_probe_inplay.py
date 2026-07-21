"""Probe app.js for content types; try fetching live SPA-ARG."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "artifacts/js/app.js").read_text(encoding="utf-8", errors="ignore")
for pat in ["inPlay", "InPlay", "liveEvent", "foEvent", "eventWith", "contentId", "idfoevent"]:
    ms = list(re.finditer(pat, text))
    print(pat, len(ms))
    for m in ms[:5]:
        print(" ", repr(text[max(0, m.start() - 40) : m.start() + 60]))

# extract quoted CamelCase content-ish strings
cands = sorted(
    {
        t
        for t in re.findall(r'"([A-Za-z][A-Za-z0-9]{2,40})"', text)
        if any(x in t.lower() for x in ("event", "market", "play", "live", "coupon", "group"))
    }
)
print("candidates", cands[:100])

API = "https://www-opr1.sport2.norsk-tipping.no/services/content/get"
H = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "poseidon": "oddsen",
    "Origin": "https://www.norsk-tipping.no",
    "Referer": "https://www.norsk-tipping.no/sport/oddsen/sportsbook/",
}


def call(ctype: str, cid: str) -> dict:
    body = json.dumps(
        {
            "contentId": {"type": ctype, "id": str(cid)},
            "clientContext": {"language": "NO", "ipAddress": "0.0.0.0"},
        }
    ).encode()
    req = urllib.request.Request(API, data=body, headers=H, method="POST")
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode())


# Try VM 2026 market groups
for ctype, cid in [
    ("boNavigationList", "1355/78622.1"),
    ("boNavigationList", "1355/78621.1"),
    ("boNavigationList", "1355/42978.1"),
]:
    try:
        p = call(ctype, cid)
        data = p.get("data") or {}
        print("\n", ctype, cid, "err", p.get("errorType"))
        if isinstance(data, dict):
            # look for event ids / market groups
            blob = json.dumps(data, ensure_ascii=False)
            if "Spania" in blob or "Argentina" in blob or "852863" in blob:
                print("  FOUND SPA/ARG in response!")
                # extract event ids near Spania
                for m in re.finditer(r".{0,30}Spania.{0,80}", blob):
                    print(" ", m.group()[:120])
            mgs = data.get("fwmarketgroups") or data.get("marketgroups") or []
            print("  marketgroups", len(mgs) if isinstance(mgs, list) else type(mgs))
            children = data.get("bonavigationnodes") or []
            print("  children", len(children))
            for ch in (children or [])[:15]:
                print("   ", ch.get("name"), ch.get("idfwbonavigation"))
    except Exception as e:
        print(ctype, cid, e)
