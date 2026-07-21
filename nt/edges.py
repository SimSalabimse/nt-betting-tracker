from __future__ import annotations

"""
Query and summarize data/edges.jsonl (append-only lesson log).

Backward compatible: accepts legacy keys (odds, p_l, note) and richer future keys.
"""

import json
from pathlib import Path
from typing import Any

from nt.config import path_from_config


def edges_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("edges_jsonl"):
        return path_from_config(cfg, "edges_jsonl")
    return path_from_config(cfg, "state_dir") / ".." / "edges.jsonl"


def load_edges(cfg: dict[str, Any], *, limit: int | None = None) -> list[dict[str, Any]]:
    path = edges_path(cfg)
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
    if limit is not None and limit > 0:
        return rows[-limit:]
    return rows


def append_edge(cfg: dict[str, Any], record: dict[str, Any]) -> Path:
    """Append one edge/lesson record. Does not modify existing lines."""
    from nt.bets_io import utc_now

    path = edges_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(record)
    rec.setdefault("ts", utc_now())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def query_edges(
    cfg: dict[str, Any],
    *,
    last: int = 50,
    result: str | None = None,
    phase: str | None = None,
    grade: str | None = None,
    q: str | None = None,
    sport: str | None = None,
) -> list[dict[str, Any]]:
    rows = load_edges(cfg)
    out: list[dict[str, Any]] = []
    for r in rows:
        if result and str(r.get("result") or "").lower() != result.lower():
            continue
        if phase and str(r.get("phase") or "") != phase:
            continue
        if grade and str(r.get("grade") or "").upper() != grade.upper():
            continue
        if sport and str(r.get("sport") or "").lower() != sport.lower():
            continue
        if q:
            blob = " ".join(
                str(r.get(k) or "")
                for k in ("match", "selection", "note", "notes", "lesson", "sport")
            ).lower()
            if q.lower() not in blob:
                continue
        out.append(r)
    if last and last > 0:
        out = out[-last:]
    return out


def summarize_edges(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "wins": 0, "losses": 0, "pl_sum": 0.0, "by_phase": {}, "by_grade": {}}
    wins = sum(1 for r in rows if str(r.get("result") or "") == "Win")
    losses = sum(1 for r in rows if str(r.get("result") or "") == "Loss")
    pl_sum = 0.0
    for r in rows:
        v = r.get("p_l") if r.get("p_l") is not None else r.get("p_l_nok")
        try:
            pl_sum += float(v or 0)
        except (TypeError, ValueError):
            pass
    by_phase: dict[str, int] = {}
    by_grade: dict[str, int] = {}
    for r in rows:
        p = str(r.get("phase") or "(none)")
        g = str(r.get("grade") or "(none)")
        by_phase[p] = by_phase.get(p, 0) + 1
        by_grade[g] = by_grade.get(g, 0) + 1
    return {
        "n": len(rows),
        "wins": wins,
        "losses": losses,
        "pl_sum": round(pl_sum, 2),
        "by_phase": by_phase,
        "by_grade": by_grade,
    }


def render_edges_md(rows: list[dict[str, Any]], title: str = "Edges") -> str:
    summary = summarize_edges(rows)
    lines = [
        f"# {title}",
        "",
        f"n={summary['n']} W={summary['wins']} L={summary['losses']} P/L sum={summary['pl_sum']:+.2f}",
        "",
        "| ts | match | selection | result | p_l | grade | phase |",
        "|----|-------|-----------|--------|-----|-------|-------|",
    ]
    for r in rows[-100:]:
        pl = r.get("p_l") if r.get("p_l") is not None else r.get("p_l_nok")
        lines.append(
            f"| {r.get('ts','')} | {r.get('match','')[:40]} | {r.get('selection','')[:30]} | "
            f"{r.get('result','')} | {pl} | {r.get('grade','')} | {r.get('phase','')} |"
        )
    lines.append("")
    return "\n".join(lines)
