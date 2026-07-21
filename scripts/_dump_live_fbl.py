"""Dump live FBL markets from liveDataSummaryAdvancedListBySportType + eventFullMarkets."""
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


def odds(sel: dict) -> float | None:
    for a, b in (
        ("currentpriceup", "currentpricedown"),
        ("priceup", "pricedown"),
    ):
        if a in sel and b in sel:
            try:
                v = round(1.0 + float(sel[a]) / float(sel[b]), 2)
                if 1.01 <= v <= 1000:
                    return v
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return None


def dump_markets(markets: list, limit: int = 40) -> None:
    for m in markets[:limit]:
        name = m.get("name") or m.get("marketname") or m.get("idfomarkettype") or "?"
        outs = []
        for s in m.get("selections") or []:
            o = odds(s)
            if o is None:
                continue
            lab = s.get("name") or s.get("hadvalue") or s.get("shortname") or "?"
            outs.append(f"{lab}:{o}")
        if outs:
            print(f"  {name}: {', '.join(outs[:10])}")


p = call("liveDataSummaryAdvancedListBySportType", "FBL")
(OUT / "live_FBL_full.json").write_text(
    json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8"
)
events = p.get("data") or []
print("n_events", len(events))
live_ids = []
for ev in events:
    eid = ev.get("idfoevent")
    live_ids.append(eid)
    print(
        "EVENT",
        eid,
        ev.get("name"),
        "n_markets",
        len(ev.get("markets") or []),
        "sport",
        ev.get("idfosporttype"),
    )
    dump_markets(ev.get("markets") or [], limit=30)

for cid in live_ids + ["8528635.1", "8528635"]:
    if not cid:
        continue
    p2 = call("eventFullMarkets", cid)
    (OUT / f"efm_{cid}.json").write_text(
        json.dumps(p2, ensure_ascii=False)[:800000], encoding="utf-8"
    )
    d = p2.get("data")
    print(
        "eventFullMarkets",
        cid,
        "err",
        p2.get("errorType"),
        "type",
        type(d).__name__,
    )
    if isinstance(d, dict):
        mk = d.get("markets") or []
        print("  markets", len(mk), "numMarkets", d.get("numMarkets"), "name", d.get("name"))
        dump_markets(mk, limit=50)
