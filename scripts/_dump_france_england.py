"""Dump all Frankrike/England related odds from current dump."""
from pathlib import Path
import re
import json

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "inbox" / "current_odds_01.txt").read_text(encoding="utf-8", errors="replace")
# Also props file
text2 = (ROOT / "inbox" / "current_odds_02.txt").read_text(encoding="utf-8", errors="replace")

for label, t in [("01", text), ("02", text2)]:
    print(f"===== FILE {label} len={len(t)} =====")
    # Find blocks: split by double newlines roughly, keep those mentioning both or HUB France
    # Simpler: find "Event: Frankrike" or "Frankrike - England" or "HUB\nFrankrike"
    patterns = [
        r"Event: Frankrike[^\n]*",
        r"Event: England[^\n]*",
        r"Frankrike - England[^\n]*",
        r"Kick-off:.*\nEvent: Frankrike",
    ]
    for m in re.finditer(r"(?is)(?:HUB\s*\nFrankrike|Frankrike - England|Event: Frankrike[^\n]*|Event: England[^\n]*).{0,50}", t):
        start = max(0, m.start() - 120)
        # extend to next double blank or 2500 chars
        chunk = t[start : start + 3500]
        # cut at next clear event if any
        print("--- chunk ---")
        print(chunk[:3000])
        print()

# structured
st = json.loads((ROOT / "artifacts" / "odds_structured.json").read_text(encoding="utf-8"))
print("===== STRUCTURED =====")
for e in st:
    blob = json.dumps(e, ensure_ascii=False)
    if "Frankrike" in blob or "England" in blob or "France" in blob:
        print("EVENT", e.get("event"), e.get("kickoff_iso"), e.get("competition"), e.get("sport"))
        print("id", e.get("idfoevent"), "markets", len(e.get("markets") or []))
        for mk in e.get("markets") or []:
            outs = [(o.get("outcome"), o.get("odds")) for o in (mk.get("outcomes") or [])]
            print(f"  [{mk.get('market')}] {outs}")
