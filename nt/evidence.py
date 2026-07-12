from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def evidence_path(evidence_dir: Path, bet_key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in bet_key)[:80]
    return evidence_dir / f"{safe}.json"


def load_evidence(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def grade_evidence(ev: dict[str, Any] | None, cfg: dict[str, Any], odds: float) -> tuple[str, list[str]]:
    """
    Return (grade, issues). Grades: A, B, C, F.
    High odds (> threshold) require grade A to be placeable.
    """
    if not ev:
        return "F", ["missing evidence pack"]

    issues: list[str] = []
    sources = ev.get("sources") or []
    if not isinstance(sources, list):
        sources = []
    n_sources = len(sources)
    sel = cfg["selection"]
    thr = float(sel["high_odds_threshold"])
    need = int(sel["min_research_sources"]["default"])
    if odds >= thr:
        need = int(sel["min_research_sources"]["high_odds"])
    elif (ev.get("requested_grade") or "").upper() == "A":
        need = int(sel["min_research_sources"]["grade_A"])

    if n_sources < need:
        issues.append(f"sources {n_sources} < required {need}")

    p = ev.get("p_model")
    if p is None:
        issues.append("missing p_model")
    else:
        try:
            p = float(p)
            if not (0.01 <= p <= 0.99):
                issues.append("p_model out of range")
        except (TypeError, ValueError):
            issues.append("invalid p_model")
            p = None

    for field in ("summary", "failure_modes"):
        if not ev.get(field):
            issues.append(f"missing {field}")

    if issues:
        # Partial credit
        if n_sources >= need and p is not None and not any("p_model" in i for i in issues):
            return "C", issues
        if n_sources >= max(3, need // 2):
            return "C", issues
        return "F", issues

    # Full requirements met
    if n_sources >= int(sel["min_research_sources"]["grade_A"]) or odds >= thr:
        return "A", []
    return "B", []


def ev_after_haircut(p_model: float, odds: float, haircut: float) -> float:
    p = max(0.01, min(0.99, p_model - haircut))
    return p * odds - 1.0
