from __future__ import annotations

"""
Performance attribution, streak deep-dive, and edge-tracking reports.

Read-only over the ledger. Writes optional markdown to outbox/ only when requested.
"""

from datetime import date
from typing import Any

from nt.analytics import (
    deep_dive,
    group_stats,
    market_stats,
    overall_stats,
    streak_stats,
    top_bottom_groups,
)
from nt.bankroll import compute_bankroll
from nt.bets_io import fnum, load_bets
from nt.config import path_from_config
from nt.edges import load_edges, summarize_edges
from nt.phase import evaluate_phase, load_phase_state
from nt.risk import evaluate_risk


def _loss_streak_grade_gate(cfg: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    streaks = streak_stats(rows)
    cur = streaks.get("current") or {}
    lim = int((cfg.get("risk") or {}).get("loss_streak_grade_a_only", 3))
    active = cur.get("type") == "Loss" and int(cur.get("length") or 0) >= lim
    return {
        "loss_streak_length": int(cur.get("length") or 0) if cur.get("type") == "Loss" else 0,
        "grade_a_only_active": active,
        "threshold": lim,
        "current_streak": cur,
    }


def attribution(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Multi-axis P/L and ROI attribution for settled bets."""
    settled = [r for r in rows if r.get("result") != "Pending"]
    return {
        "overall": overall_stats(rows),
        "by_sport": group_stats(settled, "sport"),
        "by_band": group_stats(settled, "odds_band"),
        "by_phase": group_stats(settled, "phase"),
        "by_grade": group_stats(settled, "research_grade"),
        "by_market": market_stats(settled),
        "by_source": group_stats(settled, "source"),
        "top_sports": top_bottom_groups(group_stats(settled, "sport"), min_n=5, top=5),
        "top_markets": top_bottom_groups(market_stats(settled), min_n=5, top=5),
        "top_bands": top_bottom_groups(group_stats(settled, "odds_band"), min_n=5, top=6),
    }


def calibration_hints(rows: list[dict[str, str]], decisions: dict[str, dict[str, Any]] | None = None) -> list[str]:
    """Heuristic process lessons (not statistical guarantees)."""
    hints: list[str] = []
    settled = [r for r in rows if r.get("result") in ("Win", "Loss")]
    if len(settled) < 20:
        hints.append("Thin sample (<20 decided) — avoid hard process changes.")
        return hints

    by_band = group_stats(settled, "odds_band")
    for band, st in sorted(by_band.items(), key=lambda kv: kv[1].get("roi", 0)):
        if st.get("n", 0) >= 15 and st.get("roi", 0) < -0.10:
            hints.append(f"Band {band}: n={int(st['n'])} ROI={st['roi']*100:.1f}% — raise EV bar or cut volume.")

    by_sport = group_stats(settled, "sport")
    for sport, st in by_sport.items():
        if st.get("n", 0) >= 15 and st.get("roi", 0) < -0.15:
            hints.append(f"Sport '{sport}' deep red (ROI {st['roi']*100:.1f}%) — soft-block may engage via learning.")

    high = [r for r in settled if (fnum(r.get("decimal_odds")) or 0) >= 2.5]
    if len(high) >= 10:
        hs = sum(fnum(r.get("stake_nok")) or 0 for r in high)
        hp = sum(fnum(r.get("p_l_nok")) or 0 for r in high)
        roi = (hp / hs) if hs else 0
        if roi < -0.10:
            hints.append(f"High odds (≥2.5) ROI {roi*100:.1f}% on n={len(high)} — enforce grade A strictly.")

    if decisions:
        with_model = [r for r in settled if decisions.get(r.get("bet_id") or "", {}).get("p_model") is not None]
        if len(with_model) >= 15:
            # crude: average (result win?) vs p_model not computed fully; note coverage
            hints.append(f"Decision log coverage: {len(with_model)}/{len(settled)} settled have p_model meta.")
    return hints


def run_analyze(cfg: dict[str, Any], *, write_outbox: bool = False) -> dict[str, Any]:
    rows = load_bets(path_from_config(cfg, "bets"))
    bankroll = compute_bankroll(cfg)
    prev = load_phase_state(cfg)
    phase = evaluate_phase(
        cfg,
        bankroll["equity_nok"],
        bankroll["settled_count"],
        rows,
        current_phase=prev["phase_id"] if prev else None,
    )
    risk = evaluate_risk(cfg, bankroll["equity_nok"], phase, rows)
    baseline = float(cfg["bankroll"]["baseline_nok"])
    dive = deep_dive(rows, baseline, cfg, phase, range_key="all", range_label="All time")
    attr = attribution(rows)
    from nt.decisions import load_decisions

    decisions = load_decisions(cfg)
    hints = calibration_hints(rows, decisions)
    streak_gate = _loss_streak_grade_gate(cfg, rows)
    edges = load_edges(cfg, limit=50)
    edge_sum = summarize_edges(edges)

    roll20 = dive.get("rolling_20") or []
    last_roll = roll20[-1] if roll20 else {}

    report = {
        "generated": date.today().isoformat(),
        "bankroll": {
            "equity_nok": bankroll["equity_nok"],
            "realized_pl_nok": bankroll["realized_pl_nok"],
            "pending_at_risk_nok": bankroll["pending_at_risk_nok"],
            "settled_count": bankroll["settled_count"],
        },
        "phase": {
            "phase_id": phase["phase_id"],
            "label": phase.get("label"),
            "rolling_roi": phase.get("rolling_roi"),
            "peak_equity_nok": phase.get("peak_equity_nok"),
            "drawdown_from_peak_pct": phase.get("drawdown_from_peak_pct"),
            "equity_phase": phase.get("equity_phase"),
            "count_phase": phase.get("count_phase"),
        },
        "risk": {
            "daily_risk_cap_nok": risk["daily_risk_cap_nok"],
            "remaining_risk_nok": risk["remaining_risk_nok"],
            "can_bet": risk["can_bet"],
            "stopped": risk.get("stopped"),
        },
        "overall": dive["overall"],
        "max_drawdown": dive["max_drawdown"],
        "streaks": dive["streaks"],
        "streak_gate": streak_gate,
        "rolling_20_last": last_roll,
        "attribution": {
            "top_sports": attr["top_sports"],
            "top_markets": attr["top_markets"],
            "top_bands": attr["top_bands"],
            "by_grade": attr["by_grade"],
            "by_phase": attr["by_phase"],
        },
        "hints": hints,
        "edges_recent": edge_sum,
        "concentration": dive.get("concentration"),
    }

    md = render_analyze_md(report)
    report["markdown"] = md
    if write_outbox:
        outbox = path_from_config(cfg, "outbox")
        outbox.mkdir(parents=True, exist_ok=True)
        path = outbox / f"ANALYSIS_REPORT_{date.today().isoformat()}.md"
        path.write_text(md, encoding="utf-8")
        report["path"] = str(path)
    return report


def render_analyze_md(report: dict[str, Any]) -> str:
    b = report["bankroll"]
    p = report["phase"]
    o = report["overall"]
    roll = p.get("rolling_roi")
    roll_s = f"{roll * 100:.1f}%" if roll is not None else "n/a"
    lines = [
        f"# NT Analyze Report — {report.get('generated')}",
        "",
        "## Snapshot",
        f"- Equity: **{b['equity_nok']:.2f} NOK** (P/L {b['realized_pl_nok']:+.2f})",
        f"- Phase: **{p['phase_id']}** ({p.get('label')}) | equity_phase={p.get('equity_phase')} count_phase={p.get('count_phase')}",
        f"- Rolling ROI (phase window): {roll_s}",
        f"- Peak equity: {p.get('peak_equity_nok')} | DD from peak: {float(p.get('drawdown_from_peak_pct') or 0)*100:.1f}%",
        f"- Max DD (curve): {report.get('max_drawdown')}",
        f"- Settled: {int(o.get('n_settled', 0))} | ROI {float(o.get('roi') or 0)*100:.1f}% | WR {float(o.get('winrate') or 0)*100:.1f}%",
        "",
        "## Streaks & gates",
        f"- {report.get('streaks')}",
        f"- Grade-A-only gate: {report.get('streak_gate')}",
        "",
        "## Process hints",
    ]
    for h in report.get("hints") or ["(none)"]:
        lines.append(f"- {h}")
    lines.extend(["", "## Attribution (top groups)", ""])
    for label, key in (("Sports", "top_sports"), ("Markets", "top_markets"), ("Bands", "top_bands")):
        block = (report.get("attribution") or {}).get(key) or {}
        lines.append(f"### {label}")
        for side in ("best", "worst"):
            items = block.get(side) or []
            if not items:
                continue
            lines.append(f"**{side}**")
            for name, st in items[:5]:
                lines.append(f"- {name}: n={int(st.get('n',0))} ROI={st.get('roi',0)*100:.1f}% P/L={st.get('pl',0):+.1f}")
        lines.append("")
    lines.extend(
        [
            "## Recent edges summary",
            f"- {report.get('edges_recent')}",
            "",
            "_Generated by `nt analyze`. Does not modify the ledger._",
            "",
        ]
    )
    return "\n".join(lines)
