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

    want_a = n_sources >= int(sel["min_research_sources"]["grade_A"]) or odds >= thr
    if want_a:
        # P1: Grade A requires uncertainty (SD / CI) or multi-model signal
        require_unc = bool(sel.get("grade_a_require_uncertainty", True))
        if require_unc and not _has_grade_a_uncertainty(ev, sources):
            soft = list(soft) + [
                "grade_A requires p_model_sd, edge CI, or multi-model — demoted to B"
            ]
            return "B", soft
        return "A", soft
    return "B", soft


def _has_grade_a_uncertainty(
    ev: dict[str, Any],
    sources: list[dict[str, Any]],
) -> bool:
    """True if pack has p_model_sd, edge CI, or multi-model probabilities."""
    # 1) Explicit SD
    sd = ev.get("p_model_sd")
    if sd is None and isinstance(ev.get("uncertainty"), dict):
        sd = (ev.get("uncertainty") or {}).get("p_model_sd")
    try:
        if sd is not None:
            sdv = float(sd)
            if 0.005 <= sdv <= 0.25:
                return True
    except (TypeError, ValueError):
        pass

    # 2) Edge / p CI
    lo = ev.get("p_model_ci_low")
    hi = ev.get("p_model_ci_high")
    if lo is None and isinstance(ev.get("uncertainty"), dict):
        u = ev["uncertainty"]
        lo = u.get("ci_low") or u.get("p_model_ci_low")
        hi = u.get("ci_high") or u.get("p_model_ci_high")
    try:
        if lo is not None and hi is not None:
            lo_f, hi_f = float(lo), float(hi)
            p = float(ev.get("p_model"))
            if lo_f < p < hi_f and (hi_f - lo_f) >= 0.02:
                return True
    except (TypeError, ValueError):
        pass

    # 3) Multi-model: list of p_models or ≥2 sources with p/prob
    pms = ev.get("p_models")
    if isinstance(pms, list) and len(pms) >= 2:
        return True
    n_src_p = 0
    for s in sources:
        for k in ("p_model", "prob", "probability", "p"):
            if s.get(k) is not None:
                try:
                    float(s[k])
                    n_src_p += 1
                    break
                except (TypeError, ValueError):
                    pass
    return n_src_p >= 2


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


def core_reason_text(evidence: dict[str, Any] | None) -> str:
    """Best available written core reason from a research pack."""
    if not evidence or not isinstance(evidence, dict):
        return ""
    for key in ("summary", "reason", "core_reason", "thesis"):
        t = str(evidence.get(key) or "").strip()
        if len(t) >= 20:
            return t
    takes = evidence.get("takeaways") or evidence.get("key_takeaways") or []
    if isinstance(takes, list):
        for t in takes:
            s = str(t or "").strip()
            if len(s) >= 20:
                return s
    return ""


def has_core_reason(evidence: dict[str, Any] | None) -> bool:
    """High-Volume v2: Grade C placeability requires a transparent written reason."""
    return bool(core_reason_text(evidence))


def is_strong_confidence(
    evidence: dict[str, Any] | None,
    grade: str,
    *,
    min_sources: int = 8,
) -> bool:
    """
    Strong multi-source / high-confidence → may use strong_min_ev (1.5%).
    Grade B+ and (≥min_sources or uncertainty or pack high_confidence flag).
    """
    g = (grade or "").strip().upper()
    if g not in ("A", "B"):
        return False
    if not evidence or not isinstance(evidence, dict):
        return False
    if evidence.get("high_confidence") is True:
        return True
    sources = normalize_sources(evidence.get("sources"))
    if len(sources) >= int(min_sources):
        return True
    # reuse grade-A uncertainty signal as high-confidence
    try:
        if _has_grade_a_uncertainty(evidence):
            return True
    except Exception:
        pass
    return False
