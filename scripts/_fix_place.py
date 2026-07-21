from pathlib import Path
from datetime import date
import sys
sys.path.insert(0, ".")
import nt_bootstrap
from nt.bets_io import load_bets
from nt.config import load_config
from nt.recommend import refresh_state

cfg = load_config()
b, ph, risk = refresh_state(cfg)
rows = load_bets(Path("data/bets.csv"))
pend = [r for r in rows if r.get("result") == "Pending"]
ts = date.today().isoformat()
lines = [
    f"# Bets to place — {ts}",
    "",
    f"Phase **{ph['phase_id']}** | Equity **{b['equity_nok']:.2f}** | Open **{b['pending_at_risk_nok']:.0f}** | Remaining **{risk['remaining_risk_nok']:.2f}**",
    "",
    "Multi-sport slip: football + tennis + esports (exploration where book ROI supports).",
    "",
    "| # | Sport | Match | Selection | Odds | Stake |",
    "|---|-------|-------|-----------|------|-------|",
]
for i, r in enumerate(pend, 1):
    lines.append(
        f"| {i} | {r.get('sport') or ''} | {(r.get('match') or '')[:42]} | {(r.get('selection') or '')[:40]} | {r.get('decimal_odds')} | {r.get('stake_nok')} |"
    )
lines.extend(
    [
        "",
        "## Notes",
        "",
        "- Inter Turku BTTS Ja — UECL 2nd leg after 1-1",
        "- De Jong ML — Bastad clay; tennis book ROI ~+33% n=10 (explore)",
        "- Pain Gaming ML — CS2 form/H2H vs 3DMAX; esports book ROI ~+17% n=10 (explore)",
        "- Oliynykova / Merida researched; band diversify limited further 1.5-1.8 this round",
        "",
    ]
)
md = "\n".join(lines) + "\n"
Path("outbox/PLACE_THESE.md").write_text(md, encoding="utf-8")
Path(f"outbox/PLACE_THESE_{ts}.md").write_text(md, encoding="utf-8")
print(md)
print("pending_n", len(pend), "equity", b["equity_nok"], "open", b["pending_at_risk_nok"])
