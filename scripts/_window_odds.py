"""List events in next N hours from odds_structured.json."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CEST = timezone(timedelta(hours=2))
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
path = ROOT / "artifacts" / "odds_structured.json"
if not path.is_file():
    path = ROOT / "data" / "odds" / "latest.json"

now = datetime.now(CEST)
end = now + timedelta(hours=hours)
print(f"NOW {now.isoformat()}  WINDOW +{hours}h → {end.isoformat()}")
print(f"SOURCE {path} mtime={datetime.fromtimestamp(path.stat().st_mtime, CEST)}")

events = json.loads(path.read_text(encoding="utf-8"))
in_window = []
for e in events:
    iso = e.get("kickoff_iso") or ""
    if not iso:
        continue
    s = iso.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CEST)
        dt = dt.astimezone(CEST)
    except Exception:
        continue
    if now - timedelta(minutes=20) <= dt <= end:
        in_window.append((dt, e))

in_window.sort(key=lambda x: x[0])
print(f"events_in_window {len(in_window)}")
by_sport: dict[str, int] = {}
for dt, e in in_window:
    sp = e.get("sport") or "?"
    by_sport[sp] = by_sport.get(sp, 0) + 1
    ev = (e.get("event") or "")[:52]
    comp = (e.get("competition") or "")[:36]
    nmk = len(e.get("markets") or [])
    print(f"{dt.strftime('%H:%M')} | {sp:14} | {ev:52} | mk={nmk} | {comp}")
print("by_sport", by_sport)

# Write shortlist json for research
out = []
for dt, e in in_window:
    for mk in e.get("markets") or []:
        for o in mk.get("outcomes") or []:
            odds = o.get("odds")
            if not odds or float(odds) < 1.45 or float(odds) > 3.2:
                continue
            out.append(
                {
                    "kickoff": dt.isoformat(),
                    "sport": e.get("sport"),
                    "league": e.get("competition"),
                    "match": (e.get("event") or "").replace(" - ", " vs "),
                    "market": mk.get("market"),
                    "selection": o.get("outcome"),
                    "odds": float(odds),
                }
            )
(ROOT / "outbox" / "WINDOW_3H_LINES.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"candidate_lines {len(out)} → outbox/WINDOW_3H_LINES.json")
