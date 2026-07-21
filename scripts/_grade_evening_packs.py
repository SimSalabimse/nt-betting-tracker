import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nt_bootstrap  # noqa: F401
from nt.config import load_config
from nt.evidence import grade_evidence, load_evidence

cfg = load_config()
EV = Path("evidence")
for pattern in ("*Clayton*", "*Gerwen*", "*Falkenberg*", "*Fenerbahce*", "*Sturm*", "*Einfach*"):
    for p in sorted(EV.glob(pattern)):
        ev = load_evidence(p)
        if not ev:
            continue
        odds = 1.8
        sel = str(ev.get("selection") or "")
        if "1.50" in p.name or "van Gerwen" in str(ev.get("match")) and "Vinner" in sel:
            odds = 1.5
        g, iss = grade_evidence(
            ev, cfg, odds, selection=ev.get("selection"), sport=ev.get("sport")
        )
        print(f"{g:1} p={ev.get('p_model')} {p.name[:70]}")
        if iss:
            print("   ", iss[:6])
