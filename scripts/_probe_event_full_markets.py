"""Probe eventFullMarkets + subscription hosts for live NT odds."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "api_raw" / "live_probe"
OUT.mkdir(parents=True, exist_ok=True)

HOSTS = [
    "https://www-opr1.sport2.norsk-tipping.no",
    "https://www-opr2.sport2.norsk-tipping.no",
    "https://cdn1-opr1.sport2.norsk-tipping.no",
]
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "poseidon": "oddsen",
    "Origin": "https://www.norsk-tipping.no",
    "Referer": "https://www.norsk-tipping.no/sport/oddsen/sportsbook/",
}


def post(url: str, body: dict) -> tuple[int, dict | str]:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=H, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw[:500]
    except Exception as e:
        return -1, str(e)


def get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=H, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()[:300].decode(errors="replace")
    except Exception as e:
        return -1, str(e)


# Discover config / hosts if any public endpoint
for host in HOSTS:
    for path in [
        "/services/configuration",
        "/configuration",
        "/services/content/hosts",
        "/sportsbook/config",
    ]:
        st, body = get(host + path)
        if st > 0:
            print("GET", host + path, st, body[:120])

ctypes = [
    "eventFullMarkets",
    "eventfullmarkets",
    "EventFullMarkets",
    "inPlayEvent",
    "inPlayEvents",
    "liveEvent",
    "foInPlayEvent",
    "event",
    "foEvent",
    "eventWithBalancedMarkets",
]
ids = [
    "8528632.1",  # inplay mapping
    "8528637.1",  # prematch
    "8528632",
    "8528637",
]

for host in HOSTS[:1]:
    url = host + "/services/content/get"
    for ctype in ctypes:
        for cid in ids:
            st, data = post(
                url,
                {
                    "contentId": {"type": ctype, "id": cid},
                    "clientContext": {"language": "NO", "ipAddress": "0.0.0.0"},
                },
            )
            if isinstance(data, dict):
                et = data.get("errorType")
                d = data.get("data")
                n_m = 0
                blob = ""
                if isinstance(d, dict):
                    n_m = len(d.get("markets") or [])
                    blob = json.dumps(d, ensure_ascii=False)
                elif isinstance(d, list):
                    blob = json.dumps(d, ensure_ascii=False)
                interesting = n_m > 0 or (
                    isinstance(d, dict) and len(blob) > 800 and "markets" in blob
                )
                if et == "CONTENT_TYPE_NOT_FOUND":
                    print(f"{ctype}: TYPE_BAD")
                    break
                if et and not interesting:
                    continue
                print(
                    f"{ctype}/{cid}: st={st} et={et} n_m={n_m} "
                    f"blob={len(blob)} spania={'Spania' in blob}"
                )
                if interesting or (isinstance(d, dict) and n_m >= 0 and len(blob) > 1000):
                    fp = OUT / f"{ctype}_{cid}.json"
                    fp.write_text(
                        json.dumps(data, ensure_ascii=False)[:800000], encoding="utf-8"
                    )
                    print("  saved", fp.name)
            else:
                if "NOT_FOUND" not in str(data) and st > 0:
                    print(ctype, cid, st, str(data)[:100])

# Try subscribe endpoint (may need subscriber id from WS first)
print("\n=== subscribe attempts ===")
for host in HOSTS[:1]:
    for path in [
        "/services/content/subscribe",
        "/services/subscription/content/subscribe",
        "/subscription/content/subscribe",
    ]:
        st, data = post(
            host + path,
            {
                "contentId": {"type": "eventFullMarkets", "id": "8528637.1"},
                "clientContext": {"language": "NO", "ipAddress": "0.0.0.0"},
                "subscriberId": "test",
            },
        )
        print(path, st, str(data)[:200] if not isinstance(data, dict) else json.dumps(data)[:200])
