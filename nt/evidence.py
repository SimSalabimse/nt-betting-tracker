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


def normalize_sources(sources: Any) -> list[dict[str, Any]]:
    """Accept list of dicts or bare URL strings (legacy-friendly)."""
    if not isinstance(sources, list):
        return []
    out: list[dict[str, Any]] = []
    for s in sources:
        if isinstance(s, dict):
            out.append(s)
        elif isinstance(s, str) and s.strip():
            out.append({"url": s.strip(), "takeaway": ""})
    return out


def source_quality_notes(sources: list[dict[str, Any]]) -> list[str]:
    """Non-fatal notes for research quality (do not alone fail grade)."""
    notes: list[str] = []
    empty_take = sum(1 for s in sources if not str(s.get("takeaway") or "").strip())
    if empty_take:
        notes.append(f"{empty_take}/{len(sources)} sources missing takeaway text")
    kinds = {str(s.get("kind") or "").lower() for s in sources if s.get("kind")}
    if kinds and "injury" not in kinds and "lineup" not in kinds:
        notes.append("no source tagged kind=injury or lineup (optional v5 field)")
    return notes


def evaluate_research_gates(
    ev: dict[str, Any],
    cfg: dict[str, Any],
    *,
    selection: str = "",
    sport: str = "",
    odds: float = 1.0,
) -> tuple[list[str], list[str]]:
    """
    Multi-sport research gates (delegates to nt.research_gates).

    Hard issues → cannot place. Soft notes → informational.
    """
    from nt.research_gates import evaluate_research_gates as _eval

    return _eval(ev, cfg, selection=selection, sport=sport, odds=odds)


def football_selection_family(selection: str) -> str:
    """Back-compat re-export."""
    from nt.research_gates import football_selection_family as _fam

    return _fam(selection)


def grade_evidence(
    ev: dict[str, Any] | None,
    cfg: dict[str, Any],
    odds: float,
    *,
    selection: str | None = None,
    sport: str | None = None,
) -> tuple[str, list[str]]:
    """
    Return (grade, issues). Grades: A, B, C, F.
    High odds (> threshold) require grade A to be placeable.

    Multi-sport research gates can force F (availability, script, base rate).
    """
    if not ev:
        return "F", ["missing evidence pack"]

    issues: list[str] = []
    sources = normalize_sources(ev.get("sources"))
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

    soft = source_quality_notes(sources)

    sel_text = selection if selection is not None else str(ev.get("selection") or "")
    sport_text = sport if sport is not None else str(ev.get("sport") or "")
    hard_gates, gate_soft = evaluate_research_gates(
        ev, cfg, selection=sel_text, sport=sport_text, odds=odds
    )
    soft.extend(gate_soft)

    # Hard research gates → F always (cannot place)
    if hard_gates:
        return "F", hard_gates + issues + soft

    if issues:
        if n_sources >= need and p is not None and not any("p_model" in i for i in issues):
            return "C", issues + soft
        if n_sources >= max(3, need // 2):
            return "C", issues + soft
        return "F", issues + soft

    if n_sources >= int(sel["min_research_sources"]["grade_A"]) or odds >= thr:
        return "A", soft
    return "B", soft


def validate_evidence_schema(ev: dict[str, Any]) -> list[str]:
    """Return human-readable schema warnings (non-blocking)."""
    warnings: list[str] = []
    if not isinstance(ev, dict):
        return ["evidence must be a JSON object"]
    for key in ("match", "selection", "p_model", "summary", "failure_modes", "sources"):
        if key not in ev:
            warnings.append(f"missing recommended key: {key}")
    sources = normalize_sources(ev.get("sources"))
    for i, s in enumerate(sources):
        if not s.get("url") and not s.get("name"):
            warnings.append(f"source[{i}] lacks url/name")
    return warnings


def ev_after_haircut(p_model: float, odds: float, haircut: float) -> float:
    p = max(0.01, min(0.99, p_model - haircut))
    return p * odds - 1.0
