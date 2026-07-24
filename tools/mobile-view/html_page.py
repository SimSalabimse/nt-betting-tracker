"""Minimal dark HTML desk for browser / Home Screen (not full LuminaNT)."""

from __future__ import annotations

import html
import json
from typing import Any


def _esc(v: Any) -> str:
    if v is None:
        return "—"
    return html.escape(str(v))


def _fmt_nok(v: Any) -> str:
    try:
        return f"{float(v):,.2f} NOK".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def render_html(snap: dict[str, Any]) -> str:
    charts = snap.get("charts") or {}
    overall = charts.get("overall") or {}
    equity_pts = charts.get("equity_curve") or []
    equity_js = json.dumps(
        [{"d": p.get("date"), "e": p.get("equity")} for p in equity_pts],
        separators=(",", ":"),
    )
    daily_js = json.dumps(
        [{"d": p.get("date"), "p": p.get("pl")} for p in (charts.get("daily") or [])],
        separators=(",", ":"),
    )
    sports = charts.get("by_sport") or {}
    sport_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{int(v.get('n', 0))}</td>"
        f"<td>{(v.get('roi') or 0)*100:.1f}%</td><td>{_fmt_nok(v.get('pl'))}</td></tr>"
        for k, v in sorted(sports.items(), key=lambda kv: -float(kv[1].get("pl") or 0))
    )
    pending = snap.get("pending_bets") or []
    pend_html = "".join(
        f"<li><strong>{_esc(b.get('match'))}</strong><br/>"
        f"{_esc(b.get('selection'))} @ {_esc(b.get('decimal_odds'))} · "
        f"{_fmt_nok(b.get('stake_nok'))}</li>"
        for b in pending
    ) or "<li class='muted'>No open pending</li>"

    freeze = bool(snap.get("freeze") or snap.get("stopped"))
    banner = ""
    if freeze:
        banner = (
            f"<div class='banner warn'>Freeze/stop — can_bet={_esc(snap.get('can_bet'))} "
            f"mode={_esc(snap.get('size_mode'))}</div>"
        )
    if snap.get("stale"):
        banner += f"<div class='banner muted'>Server warnings: {_esc(snap.get('warnings'))}</div>"

    place = snap.get("place_these") or {}
    place_block = _esc((place.get("text_excerpt") or "")[:1200]) if place.get("exists") else "No PLACE_THESE.md"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<title>NT Desk</title>
<style>
  :root {{ color-scheme: dark; --bg:#0f1115; --card:#1a1d24; --text:#e8eaed; --muted:#9aa0a6;
           --accent:#7cb7ff; --good:#3dd68c; --bad:#f07178; --border:#2a2f3a; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:15px/1.45 -apple-system,system-ui,sans-serif; background:var(--bg); color:var(--text); }}
  header {{ padding:16px 18px 8px; }}
  h1 {{ font-size:1.15rem; margin:0 0 4px; }}
  .meta {{ color:var(--muted); font-size:12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; padding:0 14px 14px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:12px; }}
  .card .k {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.04em; }}
  .card .v {{ font-size:1.25rem; font-weight:600; margin-top:4px; }}
  .banner {{ margin:8px 14px; padding:10px 12px; border-radius:10px; background:#3a2a12; border:1px solid #6a4a18; }}
  .banner.muted {{ background:#222; border-color:var(--border); color:var(--muted); }}
  section {{ padding:0 14px 18px; }}
  h2 {{ font-size:.95rem; margin:16px 0 8px; color:var(--accent); }}
  canvas {{ width:100%; height:160px; background:var(--card); border-radius:12px; border:1px solid var(--border); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  td,th {{ text-align:left; padding:6px 4px; border-bottom:1px solid var(--border); }}
  ul {{ padding-left:18px; margin:0; }}
  li {{ margin:8px 0; }}
  pre {{ white-space:pre-wrap; font-size:12px; background:var(--card); padding:12px; border-radius:12px; border:1px solid var(--border); }}
  .muted {{ color:var(--muted); }}
</style>
</head>
<body>
<header>
  <h1>NT Desk</h1>
  <div class="meta">generated {_esc(snap.get('generated_at'))} · phase {_esc(snap.get('phase_id'))} {_esc(snap.get('phase_label'))} · view-only</div>
</header>
{banner}
<div class="grid">
  <div class="card"><div class="k">Equity</div><div class="v">{_fmt_nok(snap.get('equity_nok'))}</div></div>
  <div class="card"><div class="k">Liquid</div><div class="v">{_fmt_nok(snap.get('liquid_nok'))}</div></div>
  <div class="card"><div class="k">Open risk</div><div class="v">{_fmt_nok(snap.get('pending_at_risk_nok'))}</div></div>
  <div class="card"><div class="k">Remaining</div><div class="v">{_fmt_nok(snap.get('remaining_risk_nok'))}</div></div>
  <div class="card"><div class="k">ROI</div><div class="v">{(overall.get('roi') or 0)*100:.1f}%</div></div>
  <div class="card"><div class="k">Win rate</div><div class="v">{(overall.get('winrate') or 0)*100:.1f}%</div></div>
</div>
<section>
  <h2>Equity</h2>
  <canvas id="eq" width="600" height="160"></canvas>
  <h2>Daily P/L</h2>
  <canvas id="pl" width="600" height="160"></canvas>
  <h2>By sport</h2>
  <table><tr><th>Sport</th><th>n</th><th>ROI</th><th>P/L</th></tr>{sport_rows or '<tr><td colspan=4 class=muted>No settled</td></tr>'}</table>
  <h2>Pending ({len(pending)})</h2>
  <ul>{pend_html}</ul>
  <h2>PLACE_THESE</h2>
  <pre>{place_block}</pre>
</section>
<script>
const EQ = {equity_js};
const PL = {daily_js};
function line(canvasId, pts, key, color) {{
  const c = document.getElementById(canvasId);
  if (!c || !pts.length) return;
  const ctx = c.getContext('2d');
  const w = c.width, h = c.height, pad = 12;
  const vals = pts.map(p => +p[key]);
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = (max - min) || 1;
  ctx.clearRect(0,0,w,h);
  ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
  pts.forEach((p,i) => {{
    const x = pad + (i/(pts.length-1||1))*(w-2*pad);
    const y = h - pad - ((+p[key]-min)/span)*(h-2*pad);
    if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  }});
  ctx.stroke();
}}
function bars(canvasId, pts, key) {{
  const c = document.getElementById(canvasId);
  if (!c || !pts.length) return;
  const ctx = c.getContext('2d');
  const w = c.width, h = c.height, pad = 12;
  const vals = pts.map(p => +p[key]);
  const maxAbs = Math.max(...vals.map(Math.abs), 1);
  const mid = h/2;
  const bw = Math.max(2, (w-2*pad)/pts.length - 2);
  pts.forEach((p,i) => {{
    const v = +p[key];
    const x = pad + i*((w-2*pad)/pts.length);
    const bh = (Math.abs(v)/maxAbs)*(h/2 - pad);
    ctx.fillStyle = v >= 0 ? '#3dd68c' : '#f07178';
    if (v >= 0) ctx.fillRect(x, mid - bh, bw, bh);
    else ctx.fillRect(x, mid, bw, bh);
  }});
  ctx.strokeStyle = '#2a2f3a'; ctx.beginPath(); ctx.moveTo(0,mid); ctx.lineTo(w,mid); ctx.stroke();
}}
line('eq', EQ, 'e', '#7cb7ff');
bars('pl', PL, 'p');
setTimeout(() => location.reload(), 20000);
</script>
</body>
</html>
"""
