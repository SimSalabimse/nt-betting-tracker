import json
from collections import Counter
from pathlib import Path

paths = [
    Path("outbox/REJECTS_2026-07-21.jsonl"),
    Path("outbox/REJECTS_LATEST.jsonl"),
]
for path in paths:
    if not path.is_file():
        print("missing", path)
        continue
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
    print("===", path.name, "n=", len(rows))
    for name in [
        "Clayton",
        "van Gerwen",
        "Falkenberg",
        "Fenerbahce",
        "Sturm",
        "Einfach",
        "Faria",
        "Jacquemot",
    ]:
        sub = [r for r in rows if name in str(r.get("match", ""))]
        if not sub:
            continue
        reasons = Counter(r.get("reason", "?") for r in sub)
        print(name, len(sub), reasons.most_common(6))
        for r in sub:
            if r.get("p_model") is not None or "EV" in str(r.get("reason", "")):
                print(
                    " ",
                    r.get("reason"),
                    "|",
                    str(r.get("selection", ""))[:48],
                    "| p=",
                    r.get("p_model"),
                    "g=",
                    r.get("grade"),
                    "iss=",
                    r.get("issues"),
                )
