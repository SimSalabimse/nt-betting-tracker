"""Deep probe of NT app.js + live/in-play content endpoints."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "artifacts/js/app.js").read_text(encoding="utf-8", errors="ignore")

patterns = [
    r"wss?://[^\s\"']+",
    r"WebSocket",
    r"subscription",
    r"SET_INPLAY",
    r"getInPlay",
    r"inPlayEvent",
    r"fullMarkets",
    r"callMidtierFetch\(\"[^\"]+\"",
    r"contentId:\{type:\"[^\"]+\"",
    r"type:\"[a-zA-Z]+\"",
]

for pat in patterns:
    ms = list(re.finditer(pat, text))
    print(f"=== {pat}  n={len(ms)}")
    for m in ms[:12]:
        s = text[max(0, m.start() - 40) : m.start() + 100]
        print(" ", repr(s.replace("\n", " "))[:160])

# Unique content types from callMidtierFetch("TYPE"
ctypes = sorted(set(re.findall(r'callMidtierFetch\("([A-Za-z0-9]+)"', text)))
print("\nCONTENT TYPES:", ctypes)

# Poseidon methods
methods = sorted(set(re.findall(r"Poseidon\.([A-Za-z0-9_]+)\s*=", text)))
print("\nPOSEIDON METHODS sample:", methods[:60])

API = "https://www-opr1.sport2.norsk-tipping.no/services/content/get"
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
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


# Try every content type with live event id / empty / region
live_id = "8528632.1"
prematch_id = "8528637.1"
print("\n=== TRY ALL CONTENT TYPES on live/prematch ids ===")
for ctype in ctypes:
    for cid in [live_id, prematch_id, "1355", "FBL", ""]:
        if cid == "" and ctype not in ("sportTypeList",):
            continue
        try:
            p = call(ctype, cid or " ")
        except Exception as e:
            print(ctype, cid, "EXC", e)
            continue
        et = p.get("errorType")
        data = p.get("data")
        if et in ("CONTENT_TYPE_NOT_FOUND",):
            break  # type invalid
        if et in ("CONTENT_NOT_FOUND", "INTERNAL_ERROR") and not data:
            continue
        blob = json.dumps(data, ensure_ascii=False) if data is not None else ""
        n_m = 0
        if isinstance(data, dict):
            n_m = len(data.get("markets") or [])
        print(
            f"{ctype}/{cid}: et={et} dtype={type(data).__name__} "
            f"len={len(blob)} markets={n_m} spania={'Spania' in blob}"
        )
        if n_m > 0 or ("Spania" in blob and len(blob) > 500):
            out = ROOT / "artifacts" / "api_raw" / "spa_arg_live" / f"{ctype}_{cid}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(p, ensure_ascii=False)[:500000], encoding="utf-8")
            print("  SAVED", out.name)
