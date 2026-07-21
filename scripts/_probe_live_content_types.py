"""Probe live-specific Poseidon content types discovered in 71.js."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "api_raw" / "live_probe"
OUT.mkdir(parents=True, exist_ok=True)

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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


# From 71.js subscribeAndGet calls:
ctypes = [
    "eventFullMarkets",
    "liveDataExtended",
    "liveDataSummaryAdvancedListBySportType",
    "inplaySportListBySportType",
    "liveDataSummary",
    "liveData",
    "inPlayEventList",
    "inplayEventList",
    "eventListInPlay",
]

# id shapes from JS: "", sport type, sport/page, event id
ids = [
    "",
    "FBL",
    "FBL/1",
    "FBL/0",
    "FBL/20",
    "1",
    "0",
    "8528637.1",
    "8528632.1",
    "1355",
    "1355/FBL",
]

for ctype in ctypes:
    type_ok = False
    for cid in ids:
        try:
            p = call(ctype, cid if cid != "" else " ")
        except Exception as e:
            print(ctype, cid, "EXC", e)
            continue
        et = p.get("errorType")
        data = p.get("data")
        if et == "CONTENT_TYPE_NOT_FOUND":
            print(ctype, "TYPE_BAD")
            break
        type_ok = True
        blob = json.dumps(data, ensure_ascii=False) if data is not None else ""
        n_m = 0
        if isinstance(data, dict):
            n_m = len(data.get("markets") or data.get("events") or [])
        elif isinstance(data, list):
            n_m = len(data)
        # skip pure not found empty
        if et in ("CONTENT_NOT_FOUND",) and n_m == 0 and len(blob) < 100:
            continue
        if et == "INTERNAL_ERROR" and n_m == 0:
            continue
        print(
            f"{ctype}/{cid!r}: et={et} dtype={type(data).__name__} "
            f"n={n_m} len={len(blob)} spania={'Spania' in blob}"
        )
        if len(blob) > 200 or n_m > 0:
            fp = OUT / f"{ctype}_{cid.replace('/', '_') or 'empty'}.json"
            fp.write_text(json.dumps(p, ensure_ascii=False)[:500000], encoding="utf-8")
            print("  saved", fp.name)
            # print sample keys
            if isinstance(data, dict):
                print("  keys", list(data.keys())[:20])
            elif isinstance(data, list) and data:
                print("  [0]", str(data[0])[:200])
    if type_ok:
        print()
