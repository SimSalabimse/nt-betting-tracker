from pathlib import Path
import re
import json
import urllib.request

text = Path("artifacts/js/app.js").read_text(encoding="utf-8", errors="ignore")
for pat in [
    "callMidtierFetch",
    "DATA_EVENTS",
    "fullMarkets",
    "services/",
    "midtier",
    "inplay",
    "InPlay",
    "sport2",
]:
    print("===", pat, text.lower().count(pat.lower()) if pat.islower() else text.count(pat))
    for m in re.finditer(re.escape(pat), text, flags=re.I):
        print(repr(text[max(0, m.start() - 60) : m.start() + 120]))
        break

urls = set(re.findall(r"https://[a-zA-Z0-9._/-]+", text))
print("urls sample", sorted(urls)[:40])

# try common live odds endpoints
API_HOSTS = [
    "https://www-opr1.sport2.norsk-tipping.no",
    "https://www.norsk-tipping.no",
]
H = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "poseidon": "oddsen",
    "Origin": "https://www.norsk-tipping.no",
    "Referer": "https://www.norsk-tipping.no/sport/oddsen/sportsbook/",
}

paths = [
    "/services/content/get",
    "/services/inplay/events",
    "/services/sportsbook/inplay",
    "/services/push/inplay",
]

for host in API_HOSTS[:1]:
    for path in paths[1:]:
        url = host + path
        try:
            req = urllib.request.Request(url, headers=H, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()[:200]
                print("GET", url, resp.status, body[:100])
        except Exception as e:
            print("GET", url, type(e).__name__, str(e)[:80])
