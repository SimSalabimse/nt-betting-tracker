from __future__ import annotations

"""
Calibration tracking: predicted p_model vs realized outcomes.

Sources of p_model (in order of preference per bet):
1. data/state/bet_decisions.jsonl
2. evidence recovered fields / notes meta
3. optional data/state/calibration.jsonl historical rows

On settle, append a calibration row when p_model is known.
Reports: Brier score, log loss, reliability bins, by band/market/phase.

This never changes stakes — pure learning signal.
"""

import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from nt.analytics import infer_market
from nt.bets_io import fnum, load_bets, odds_band, utc_now
from nt.config import path_from_config
from nt.decisions import load_decisions, parse_notes_meta
from nt.defaults import simulation_cfg


def calibration_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("calibration_jsonl"):
        return path_from_config(cfg, "calibration_jsonl")
    return path_from_config(cfg, "state_dir") / "calibration.jsonl"


def append_calibration(cfg: dict[str, Any], record: dict[str, Any]) -> Path:
    path = calibration_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(record)
    rec.setdefault("ts", utc_now())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def load_calibration_quality(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Lightweight Brier + n for Kelly gating.
    Prefers data/state/calibration_summary.json if present; else analyzes calibration.jsonl.
    """
    paths = cfg.get("paths") or {}
    if paths.get("calibration_summary_json"):
        sp = path_from_config(cfg, "calibration_summary_json")
    else:
        sp = path_from_config(cfg, "state_dir") / "calibration_summary.json"
    if sp.is_file():
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("n") is not None:
                return {
                    "n": int(data.get("n") or 0),
                    "brier": float(data["brier"]) if data.get("brier") is not None else None,
                    "source": "summary",
                }
        except Exception:
            pass
    try:
        rows = load_calibration(cfg)
        rep = analyze_calibration(rows, cfg)
        return {
            "n": int(rep.get("n") or 0),
            "brier": float(rep["brier"]) if rep.get("brier") is not None else None,
            "source": "jsonl",
        }
    except Exception:
        return {"n": 0, "brier": None, "source": "none"}


def load_calibration(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = calibration_path(cfg)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _outcome_binary(result: str) -> float | None:
    r = (result or "").strip()
    if r == "Win":
        return 1.0
    if r == "Loss":
        return 0.0
    # Refunded / void excluded from calibration
    return None


def record_from_settled_bet(
    bet: dict[str, str],
    decision: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build one calibration record if p_model and Win/Loss available."""
    y = _outcome_binary(bet.get("result") or "")
    if y is None:
        return None

    p = None
    if decision and decision.get("p_model") is not None:
        try:
            p = float(decision["p_model"])
        except (TypeError, ValueError):
            p = None
    if p is None:
        meta = parse_notes_meta(bet.get("notes"))
        p = meta.get("p_model")
    if p is None:
        return None
    try:
        p = float(p)
    except (TypeError, ValueError):
        return None
    if not (0.01 <= p <= 0.99):
        return None

    odds = fnum(bet.get("decimal_odds"))
    return {
        "ts": utc_now(),
        "bet_id": bet.get("bet_id"),
        "date": bet.get("date"),
        "match": bet.get("match"),
        "selection": bet.get("selection"),
        "sport": bet.get("sport"),
        "market": infer_market(bet.get("selection") or "", bet.get("market_type") or ""),
        "odds": odds,
        "odds_band": bet.get("odds_band") or (odds_band(odds) if odds else ""),
        "phase": bet.get("phase"),
        "grade": bet.get("research_grade"),
        "p_model": round(p, 4),
        "y": y,
        "result": bet.get("result"),
        "p_l_nok": fnum(bet.get("p_l_nok")),
        "source": "settle" if decision else "rebuild",
        "brier": round((p - y) ** 2, 6),
        "log_loss": round(_log_loss(p, y), 6),
    }


def _log_loss(p: float, y: float) -> float:
    p = min(1.0 - 1e-9, max(1e-9, p))
    return float(-(y * math.log(p) + (1.0 - y) * math.log(1.0 - p)))


def append_for_settled(
    cfg: dict[str, Any],
    bet: dict[str, str],
    decisions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Called from settle for each newly settled bet."""
    sc = simulation_cfg(cfg)
    if not sc.get("calibration_enabled", True):
        return None
    decisions = decisions if decisions is not None else load_decisions(cfg)
    bid = bet.get("bet_id") or ""
    rec = record_from_settled_bet(bet, decisions.get(bid))
    if not rec:
        return None
    # de-dupe: skip if last line for same bet_id already present (cheap tail scan)
    existing = load_calibration(cfg)
    for row in reversed(existing[-50:]):
        if row.get("bet_id") == bid and row.get("result") == bet.get("result"):
            return None
    append_calibration(cfg, rec)
    return rec


def rebuild_calibration(cfg: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    """Rebuild calibration.jsonl from ledger + decisions (idempotent rewrite)."""
    rows = load_bets(path_from_config(cfg, "bets"))
    decisions = load_decisions(cfg)
    records: list[dict[str, Any]] = []
    for bet in rows:
        if bet.get("result") not in ("Win", "Loss"):
            continue
        rec = record_from_settled_bet(bet, decisions.get(bet.get("bet_id") or ""))
        if rec:
            rec["source"] = "rebuild"
            records.append(rec)

    if write:
        path = calibration_path(cfg)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    report = analyze_calibration(records)
    report["n_written"] = len(records)
    report["path"] = str(calibration_path(cfg)) if write else None
    return report


def analyze_calibration(rows: list[dict[str, Any]] | None = None, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    if rows is None:
        if cfg is None:
            raise ValueError("cfg required if rows is None")
        rows = load_calibration(cfg)

    usable = [r for r in rows if r.get("y") in (0, 0.0, 1, 1.0) and r.get("p_model") is not None]
    n = len(usable)
    if n == 0:
        return {
            "n": 0,
            "brier": None,
            "log_loss": None,
            "mean_p": None,
            "base_rate": None,
            "message": "No calibration rows with p_model + Win/Loss. Settle researched bets or run calibrate rebuild.",
        }

    brier = sum(float(r.get("brier") or (float(r["p_model"]) - float(r["y"])) ** 2) for r in usable) / n
    ll = sum(float(r.get("log_loss") or _log_loss(float(r["p_model"]), float(r["y"]))) for r in usable) / n
    mean_p = sum(float(r["p_model"]) for r in usable) / n
    base = sum(float(r["y"]) for r in usable) / n

    bins = _reliability_bins(usable, n_bins=10)
    by_band = _group_metrics(usable, "odds_band")
    by_market = _group_metrics(usable, "market")
    by_phase = _group_metrics(usable, "phase")
    by_grade = _group_metrics(usable, "grade")

    # Overconfidence: average (p - y) — positive means predicted too high
    bias = sum(float(r["p_model"]) - float(r["y"]) for r in usable) / n

    return {
        "n": n,
        "brier": round(brier, 5),
        "log_loss": round(ll, 5),
        "mean_p_model": round(mean_p, 4),
        "base_rate_wins": round(base, 4),
        "bias_p_minus_y": round(bias, 4),
        "interpretation": _interpret(bias, brier, n),
        "reliability_bins": bins,
        "by_odds_band": by_band,
        "by_market": by_market,
        "by_phase": by_phase,
        "by_grade": by_grade,
    }


def _reliability_bins(rows: list[dict[str, Any]], n_bins: int = 10) -> list[dict[str, Any]]:
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        p = float(r["p_model"])
        # bins [0,0.1), …, [0.9,1.0]
        idx = min(n_bins - 1, max(0, int(p * n_bins)))
        buckets[idx].append(r)
    out: list[dict[str, Any]] = []
    for i in range(n_bins):
        items = buckets.get(i, [])
        lo = i / n_bins
        hi = (i + 1) / n_bins
        if not items:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": 0, "mean_p": None, "emp_rate": None})
            continue
        mean_p = sum(float(x["p_model"]) for x in items) / len(items)
        emp = sum(float(x["y"]) for x in items) / len(items)
        out.append(
            {
                "bin": f"{lo:.1f}-{hi:.1f}",
                "n": len(items),
                "mean_p": round(mean_p, 4),
                "emp_rate": round(emp, 4),
                "gap": round(mean_p - emp, 4),
            }
        )
    return out


def _group_metrics(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        g = str(r.get(key) or "(empty)")
        groups[g].append(r)
    out: dict[str, dict[str, Any]] = {}
    for g, items in groups.items():
        n = len(items)
        brier = sum((float(x["p_model"]) - float(x["y"])) ** 2 for x in items) / n
        bias = sum(float(x["p_model"]) - float(x["y"]) for x in items) / n
        out[g] = {
            "n": n,
            "brier": round(brier, 5),
            "bias": round(bias, 4),
            "mean_p": round(sum(float(x["p_model"]) for x in items) / n, 4),
            "winrate": round(sum(float(x["y"]) for x in items) / n, 4),
        }
    return out


def _interpret(bias: float, brier: float, n: int) -> str:
    if n < 20:
        return f"Thin sample (n={n}). Do not change process hard until n≥30–50."
    parts = []
    if bias > 0.05:
        parts.append("Overconfident: mean p_model > win rate — haircut/discipline working; don't raise p.")
    elif bias < -0.05:
        parts.append("Underconfident: wins more than p implies — may be leaving EV on table (or variance).")
    else:
        parts.append("Bias near zero — rough calibration OK.")
    if brier > 0.28:
        parts.append(f"Brier {brier:.3f} is weak (random coin ~0.25 at 50%).")
    elif brier < 0.20:
        parts.append(f"Brier {brier:.3f} is solid for sports if n large.")
    return " ".join(parts)


def render_calibration_md(report: dict[str, Any]) -> str:
    lines = [
        f"# Calibration report — {date.today().isoformat()}",
        "",
        f"**n** = {report.get('n')}",
    ]
    if report.get("n", 0) == 0:
        lines.append(report.get("message") or "No data.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"**Brier** = {report.get('brier')} (lower better; 0 = perfect)",
            f"**Log loss** = {report.get('log_loss')}",
            f"**Mean p_model** = {report.get('mean_p_model')} · **Win rate** = {report.get('base_rate_wins')}",
            f"**Bias (p−y)** = {report.get('bias_p_minus_y')}",
            "",
            f"_Interpretation:_ {report.get('interpretation')}",
            "",
            "## Reliability bins",
            "",
            "| Bin | n | mean p | empirical | gap (p−emp) |",
            "|-----|---|--------|-----------|-------------|",
        ]
    )
    for b in report.get("reliability_bins") or []:
        if b.get("n", 0) == 0:
            lines.append(f"| {b['bin']} | 0 | — | — | — |")
        else:
            lines.append(
                f"| {b['bin']} | {b['n']} | {b['mean_p']} | {b['emp_rate']} | {b.get('gap')} |"
            )

    for title, key in (
        ("By odds band", "by_odds_band"),
        ("By market", "by_market"),
        ("By phase", "by_phase"),
        ("By grade", "by_grade"),
    ):
        block = report.get(key) or {}
        if not block:
            continue
        lines.extend(["", f"## {title}", "", "| Group | n | Brier | Bias | mean p | WR |", "|-------|---|-------|------|--------|----|"])
        for g, st in sorted(block.items(), key=lambda kv: -kv[1].get("n", 0)):
            lines.append(
                f"| {g} | {st['n']} | {st['brier']} | {st['bias']} | {st['mean_p']} | {st['winrate']} |"
            )

    lines.extend(
        [
            "",
            "## How to use",
            "",
            "- Positive bias → you set p_model too high; keep haircut; don't sim-inflate.",
            "- Bad band Brier → raise EV bar or cut volume in that band (already partially automated).",
            "- Rebuild anytime: `python run_nt.py calibrate rebuild`",
            "",
            "_Calibration does not auto-change stakes. Code is law remains in portfolio/risk._",
            "",
        ]
    )
    return "\n".join(lines)


def run_calibration_report(cfg: dict[str, Any], *, write_outbox: bool = True) -> dict[str, Any]:
    rows = load_calibration(cfg)
    if not rows:
        # auto-rebuild once if empty
        report = rebuild_calibration(cfg, write=True)
    else:
        report = analyze_calibration(rows, cfg)
        report["path"] = str(calibration_path(cfg))
    md = render_calibration_md(report)
    report["markdown"] = md
    if write_outbox:
        outbox = path_from_config(cfg, "outbox")
        outbox.mkdir(parents=True, exist_ok=True)
        path = outbox / f"CALIBRATION_{date.today().isoformat()}.md"
        path.write_text(md, encoding="utf-8")
        (outbox / "CALIBRATION.md").write_text(md, encoding="utf-8")
        report["report_path"] = str(path)
    return report
