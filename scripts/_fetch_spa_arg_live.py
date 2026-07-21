"""Fetch live Spania-Argentina event markets from NT Poseidon (incl. in-play/ET)."""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API = "https://www-opr1.sport2.norsk-tipping.no/services/content/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "poseidon": "oddsen",
    "Origin": "https://www.norsk-tipping.no",
    "Referer": "https://www.norsk-tipping.no/sport/oddsen/sportsbook/",
}
REGION = "1355"
EVENT_ID = "8528637.1"  # pre-match id from earlier collect
OUT = ROOT / "inbox" / "spa_arg_live_odds.txt"
RAW = ROOT / "artifacts" / "api_raw" / "spa_arg_live"


def call_api(content_type: str, content_id: str) -> dict:
    body = json.dumps(
        {
            "contentId": {"type": content_type, "id": str(content_id)},
            "clientContext": {"language": "NO", "ipAddress": "0.0.0.0"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def frac_to_decimal(up, down):
    try:
        u, d = float(up), float(down)
        if d == 0:
            return None
        v = round(1.0 + u / d, 2)
        return v if 1.01 <= v <= 1000 else None
    except (TypeError, ValueError):
        return None


def selection_odds(sel: dict) -> float | None:
    for a, b in (
        ("currentpriceup", "currentpricedown"),
        ("priceup", "pricedown"),
        ("hadpriceup", "hadpricedown"),
    ):
        if a in sel and b in sel:
            dec = frac_to_decimal(sel[a], sel[b])
            if dec is not None:
                return dec
    for k in ("decimalOdds", "price", "currentprice", "odds"):
        if sel.get(k) is not None:
            try:
                v = float(sel[k])
                if 1.01 <= v <= 1000:
                    return round(v, 2)
            except (TypeError, ValueError):
                pass
    return None


def market_name(m: dict) -> str:
    for k in ("name", "marketname", "marketName", "typename", "type"):
        if m.get(k):
            return str(m[k])
    return str(m.get("idfomarkettype") or m.get("idfomarket") or "market")


def outcome_name(s: dict) -> str:
    for k in ("name", "selectionname", "selectionName", "hadvalue", "type"):
        if s.get(k):
            return str(s[k])
    return str(s.get("idfoselection") or "?")


def extract_markets(payload: dict) -> list[dict]:
    data = payload.get("data") or payload
    # various shapes
    events = []
    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        if data.get("foevents") or data.get("events"):
            events = data.get("foevents") or data.get("events")
        else:
            events = [data]
    markets_out = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        name = ev.get("name") or ev.get("eventname") or ev.get("eventName") or ""
        markets = (
            ev.get("markets")
            or ev.get("fomarkets")
            or ev.get("balancedMarkets")
            or []
        )
        # nested market groups
        for mg in ev.get("marketgroups") or ev.get("marketGroups") or []:
            markets = list(markets) + list(mg.get("markets") or mg.get("fomarkets") or [])
        for m in markets:
            mname = market_name(m)
            sels = m.get("selections") or m.get("foselections") or m.get("outcomes") or []
            outs = []
            for s in sels:
                o = selection_odds(s)
                if o is None:
                    continue
                outs.append({"outcome": outcome_name(s), "odds": o})
            if outs:
                markets_out.append({"event": name, "market": mname, "outcomes": outs})
    return markets_out


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = []
    all_markets = []

    # Try known event id + event variants
    for ctype, cid in [
        ("event", EVENT_ID),
        ("event", EVENT_ID.replace(".1", "")),
        ("foEvent", EVENT_ID),
        ("eventWithBalancedMarkets", EVENT_ID),
        ("eventWithBalancedMarkets", "8528637"),
    ]:
        try:
            payload = call_api(ctype, cid)
            (RAW / f"{ctype}_{cid}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2)[:500000],
                encoding="utf-8",
            )
            err = payload.get("errorType") or payload.get("error")
            print(f"{ctype}/{cid}: error={err} keys={list(payload.keys())[:8]}")
            mk = extract_markets(payload)
            print(f"  markets extracted: {len(mk)}")
            all_markets.extend(mk)
        except Exception as e:
            print(f"{ctype}/{cid}: FAIL {e}")

    # Search nav for live / in-play Spain Argentina
    try:
        nav = call_api("boNavigationTree", REGION)
        (RAW / "nav_tree.json").write_text(
            json.dumps(nav, ensure_ascii=False)[:200000], encoding="utf-8"
        )
        # dump text search
        blob = json.dumps(nav, ensure_ascii=False)
        for term in ("Spania", "Argentina", "ekstra", "live", "Live"):
            print(f"nav has {term}:", term in blob)
    except Exception as e:
        print("nav fail", e)

    # Print interesting markets
    KEY = (
        "ekstra",
        "straffe",
        "vinner",
        "mål",
        "over",
        "under",
        "begge",
        "hub",
        "fulltid",
        "sammenlagt",
        "score",
        "next",
        "neste",
        "total",
    )
    lines.append("Sport: Football")
    lines.append("Spania vs Argentina")
    lines.append("Kick-off: 2026-07-19 21:00")
    lines.append("LIVE EXTRA TIME — scraped")
    lines.append("")

    seen = set()
    for m in all_markets:
        key = (m["market"], tuple((o["outcome"], o["odds"]) for o in m["outcomes"]))
        if key in seen:
            continue
        seen.add(key)
        nl = m["market"].lower()
        if any(k in nl for k in KEY) or True:
            lines.append(m["market"])
            for o in m["outcomes"]:
                lines.append(o["outcome"])
                lines.append(str(o["odds"]))
            lines.append("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT, "n_unique_markets", len(seen))
    # also print compact
    for m in list(seen)[:5]:
        pass
    for m in all_markets[:40]:
        outs = ", ".join(f"{o['outcome']}:{o['odds']}" for o in m["outcomes"][:6])
        print(f"  {m['market']}: {outs}")


if __name__ == "__main__":
    main()
