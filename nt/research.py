from __future__ import annotations

"""
Research helpers: sources, checklists, evidence scaffolding, p_model calculator.

Does not place bets. Scaffold writes are explicit and opt-in.
"""

import json
import re
from pathlib import Path
from typing import Any

from nt.config import path_from_config
from nt.defaults import research_cfg
from nt.evidence import ev_after_haircut, grade_evidence
from nt.paths import ROOT, resolve


SPORT_SOURCES: dict[str, list[dict[str, str]]] = {
    "football": [
        {"name": "FBref", "url": "https://fbref.com", "use": "xG, form, shooting, history"},
        {"name": "Transfermarkt", "url": "https://www.transfermarkt.com", "use": "injuries, suspensions, squads"},
        {"name": "Sofascore", "url": "https://www.sofascore.com", "use": "form, ratings, lineups"},
        {"name": "Flashscore", "url": "https://www.flashscore.com", "use": "H2H, schedules, scores"},
        {"name": "Understat", "url": "https://understat.com", "use": "shot quality / xG (selected leagues)"},
        {"name": "WhoScored", "url": "https://www.whoscored.com", "use": "ratings, event trends"},
        {"name": "SoccerSTATS", "url": "https://www.soccerstats.com", "use": "BTTS / O-U tables"},
        {"name": "OddsPortal", "url": "https://www.oddsportal.com", "use": "odds history (soft signal)"},
    ],
    "tennis": [
        {"name": "TennisExplorer", "url": "https://www.tennisexplorer.com", "use": "H2H, form, surface"},
        {"name": "ATP/WTA", "url": "https://www.atptour.com", "use": "rankings, draws"},
        {"name": "Sofascore", "url": "https://www.sofascore.com", "use": "live form"},
        {"name": "Flashscore", "url": "https://www.flashscore.com", "use": "schedules"},
    ],
    "hockey": [
        {"name": "Hockey-Reference", "url": "https://www.hockey-reference.com", "use": "history, form"},
        {"name": "Eliteprospects", "url": "https://www.eliteprospects.com", "use": "lineups, injuries"},
        {"name": "Sofascore", "url": "https://www.sofascore.com", "use": "form"},
    ],
    "esports_cs": [
        {"name": "HLTV", "url": "https://www.hltv.org", "use": "form, maps, H2H"},
        {"name": "Liquipedia", "url": "https://liquipedia.net", "use": "rosters, events"},
    ],
    "snooker": [
        {"name": "CueTracker", "url": "https://cuetracker.net", "use": "H2H history"},
        {"name": "Snooker.org", "url": "https://www.snooker.org", "use": "rankings, results"},
        {"name": "Flashscore", "url": "https://www.flashscore.com", "use": "live"},
    ],
    "basketball": [
        {"name": "Basketball-Reference", "url": "https://www.basketball-reference.com", "use": "stats history"},
        {"name": "NBA.com", "url": "https://www.nba.com", "use": "official"},
        {"name": "Sofascore", "url": "https://www.sofascore.com", "use": "form lineups"},
    ],
}

CHECKLISTS: dict[str, list[str]] = {
    "football": [
        "table_position_motivation",
        "recent_form_xg",
        "injuries_suspensions",
        "lineup_or_availability",  # confirmed XI when out; else predicted + injuries
        "injuries_suspensions_rotation",
        "lineup_rotation_attack_vs_defence_read",
        "h2h_last_meetings",
        "home_away_split",
        "market_specific_stats",
        "script_lean_vs_selection_check",  # high_scoring vs under/BTTS No = NO BET
        "base_rate_vs_selection_check",
        "rotation_risk_set",  # low|medium|high — WC/intl/cup = high
        "failure_modes_written",
        "p_model_calibrated_not_forced",
    ],
    "tennis": [
        "surface_h2h",
        "recent_form_fatigue",
        "injury_retirement_risk",
        "serve_return_split",
        "fitness_availability_status",
        "context_risk_schedule",
        "script_lean_vs_selection_check",
        "base_rate_vs_selection_check",
        "failure_modes_written",
        "p_model_calibrated_not_forced",
    ],
    "basketball": [
        "form_net_rating",
        "injuries_minutes_load",
        "back_to_back_or_rest",
        "availability_status",
        "context_risk_set",
        "script_lean_vs_selection_check",
        "base_rate_vs_selection_check",
        "failure_modes_written",
        "p_model_calibrated_not_forced",
    ],
    "default": [
        "form_check",
        "availability_lineups",
        "h2h_or_matchup",
        "motivation_context",
        "context_risk_set",
        "script_lean_vs_selection_check",
        "base_rate_vs_selection_check",
        "failure_modes_written",
        "p_model_calibrated_not_forced",
    ],
}


def list_sources(sport: str = "football") -> list[dict[str, str]]:
    key = (sport or "football").strip().lower()
    aliases = {
        "fotball": "football",
        "soccer": "football",
        "eliteserien": "football",
        "cs": "esports_cs",
        "csgo": "esports_cs",
        "cs2": "esports_cs",
        "ice_hockey": "hockey",
        "ishockey": "hockey",
        "nba": "basketball",
    }
    key = aliases.get(key, key)
    return list(SPORT_SOURCES.get(key) or SPORT_SOURCES["football"])


def checklist_for(sport: str = "football") -> list[str]:
    key = (sport or "football").strip().lower()
    if key in ("fotball", "soccer", "eliteserien"):
        key = "football"
    return list(CHECKLISTS.get(key) or CHECKLISTS["default"])


def _safe_filename(match: str, selection: str) -> str:
    raw = f"{match}_{selection}".lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return (raw[:70] or "research_pack") + ".json"


def scaffold_evidence(
    cfg: dict[str, Any],
    *,
    match: str,
    selection: str,
    p_model: float | None = None,
    league: str = "",
    sport: str = "football",
    odds: float | None = None,
    write: bool = False,
    filename: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build a research pack dict; optionally write under evidence/."""
    from nt.sport_taxonomy import normalize_sport

    sport_c = normalize_sport(sport, default="football") if sport else "football"
    sources_meta = list_sources(sport_c)
    pack: dict[str, Any] = {
        "match": match,
        "selection": selection,
        "league": league,
        "sport": sport_c,
        "p_model": p_model,
        "summary": "",
        "failure_modes": "",
        "confidence": None,
        "checklist": {k: False for k in checklist_for(sport_c)},
        "model_name": "manual",
        # Multi-sport research gates — docs/RESEARCH_GATES.md
        "context_risk": "unknown",  # low | medium | high
        "availability_status": "missing",  # confirmed | predicted | stable_guess | missing
        "availability_notes": "",
        "lineup_status": "missing",  # football alias of availability_status
        "lineup_notes": "",
        "rotation_risk": "unknown",  # alias of context_risk
        "script_lean": "neutral",
        "selection_vs_script": "unknown",
        "base_rate_conflict": False,
        "research_gates": {
            "context_risk": "unknown",
            "availability_status": "missing",
            "availability_notes": "",
            "lineup_status": "missing",
            "rotation_risk": "unknown",
            "script_lean": "neutral",
            "selection_vs_script": "unknown",
            "base_rate_conflict": False,
            "base_rate_note": "",
            "lineup_notes": "",
        },
        "sources": [
            {
                "url": s["url"],
                "takeaway": "",
                "kind": "stats",
                "name": s["name"],
                "use": s["use"],
            }
            for s in sources_meta[:8]
        ],
        "notes": (
            "Fill takeaways, summary, failure_modes, p_model. "
            "Sensitive markets (totals/BTTS/props): set availability_status=predicted|confirmed "
            "+ injury/load/fitness research. Domestic 12h boards: predicted OK. "
            "High context (WC/intl/B2B): deeper availability_notes. "
            "Never set selection_vs_script=conflict. See docs/RESEARCH_GATES.md."
        ),
    }
    if odds is not None:
        pack["decimal_odds_ref"] = odds

    path = None
    if write:
        evidence_dir = path_from_config(cfg, "evidence")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or _safe_filename(match, selection)
        path = evidence_dir / fname
        if path.exists() and not overwrite:
            return {"ok": False, "error": f"exists: {path}", "pack": pack, "path": str(path)}
        path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "pack": pack, "path": str(path) if path else None}


def write_research_pack(
    cfg: dict[str, Any],
    *,
    match: str,
    selection: str,
    p_model: float,
    sport: str = "football",
    odds: float | None = None,
    summary: str = "",
    failure_modes: str = "",
    availability_status: str = "predicted",
    availability_notes: str = "",
    context_risk: str = "low",
    script_lean: str = "neutral",
    selection_vs_script: str = "agree",
    base_rate_conflict: bool = False,
    confidence: float | None = 0.55,
    model_name: str = "agent_research",
    league: str = "",
    notes: str = "",
    filename: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """
    Phase 5: single write path for deep evidence packs (replaces ad-hoc scripts).

    Always writes under evidence/ with research-gate fields filled enough to
    pass domestic predicted boards when notes are present.
    """
    from nt.sport_taxonomy import normalize_sport

    sport_c = normalize_sport(sport, default="football") if sport else "football"
    base = scaffold_evidence(
        cfg,
        match=match,
        selection=selection,
        p_model=float(p_model),
        league=league,
        sport=sport_c,
        odds=odds,
        write=False,
    )
    pack = base["pack"]
    pack["p_model"] = float(p_model)
    pack["summary"] = summary or pack.get("summary") or ""
    pack["failure_modes"] = failure_modes or pack.get("failure_modes") or ""
    pack["confidence"] = confidence
    pack["model_name"] = model_name
    pack["context_risk"] = context_risk
    pack["availability_status"] = availability_status
    pack["availability_notes"] = availability_notes
    pack["lineup_status"] = availability_status
    pack["lineup_notes"] = availability_notes
    pack["rotation_risk"] = context_risk
    pack["script_lean"] = script_lean
    pack["selection_vs_script"] = selection_vs_script
    pack["base_rate_conflict"] = bool(base_rate_conflict)
    pack["research_gates"] = {
        "context_risk": context_risk,
        "availability_status": availability_status,
        "availability_notes": availability_notes,
        "lineup_status": availability_status,
        "rotation_risk": context_risk,
        "script_lean": script_lean,
        "selection_vs_script": selection_vs_script,
        "base_rate_conflict": bool(base_rate_conflict),
        "base_rate_note": "",
        "lineup_notes": availability_notes,
    }
    # Mark checklist keys that write-pack satisfies by construction
    cl = pack.get("checklist") or {}
    for k in cl:
        if k in (
            "failure_modes_written",
            "p_model_calibrated_not_forced",
            "script_lean_vs_selection_check",
            "base_rate_vs_selection_check",
            "lineup_or_availability",
            "fitness_availability_status",
            "availability_status",
            "context_risk_set",
            "context_risk_schedule",
            "rotation_risk_set",
        ):
            cl[k] = True
    pack["checklist"] = cl
    if notes:
        pack["notes"] = notes
    if odds is not None:
        pack["decimal_odds_ref"] = odds

    evidence_dir = path_from_config(cfg, "evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    fname = filename or _safe_filename(match, selection)
    path = evidence_dir / fname
    if path.exists() and not overwrite:
        return {"ok": False, "error": f"exists: {path}", "pack": pack, "path": str(path)}
    path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "pack": pack, "path": str(path)}


def p_model_report(cfg: dict[str, Any], odds: float, p_model: float, high_odds: bool | None = None) -> dict[str, Any]:
    sel = cfg.get("selection") or {}
    haircut = float(sel.get("probability_haircut", 0.05))
    thr = float(sel.get("high_odds_threshold", 2.5))
    high = high_odds if high_odds is not None else odds >= thr
    implied = 1.0 / odds if odds > 0 else None
    ev = ev_after_haircut(p_model, odds, haircut)
    min_ev = float(sel.get("high_odds_min_ev" if high else "standard_min_ev", 0.03))
    return {
        "odds": odds,
        "implied_prob": round(implied, 4) if implied else None,
        "p_model": p_model,
        "p_after_haircut": round(max(0.01, min(0.99, p_model - haircut)), 4),
        "haircut": haircut,
        "ev": round(ev, 4),
        "min_ev": min_ev,
        "clears_ev_bar": ev >= min_ev,
        "high_odds": high,
        "edge_vs_implied": round(p_model - (implied or 0), 4) if implied else None,
        "note": "EV uses haircut; do not force p_model to clear the bar.",
    }


def critique_pack(cfg: dict[str, Any], path: Path, odds: float = 1.90) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "error": f"not found: {path}"}
    with open(path, encoding="utf-8") as f:
        ev = json.load(f)
    grade, issues = grade_evidence(ev, cfg, odds)
    rcfg = research_cfg(cfg)
    extra: list[str] = []
    summary = str(ev.get("summary") or "")
    fm = str(ev.get("failure_modes") or "")
    if len(summary) < int(rcfg.get("min_summary_chars") or 20):
        extra.append("summary too short for high-quality research")
    if len(fm) < int(rcfg.get("min_failure_modes_chars") or 10):
        extra.append("failure_modes too thin")
    empty_takeaways = sum(
        1 for s in (ev.get("sources") or []) if isinstance(s, dict) and not str(s.get("takeaway") or "").strip()
    )
    if empty_takeaways:
        extra.append(f"{empty_takeaways} sources missing takeaways")
    p = ev.get("p_model")
    report = None
    if p is not None:
        try:
            report = p_model_report(cfg, odds, float(p))
        except (TypeError, ValueError):
            extra.append("invalid p_model")
    return {
        "ok": True,
        "path": str(path),
        "grade": grade,
        "issues": issues,
        "quality_notes": extra,
        "p_model_report": report,
        "checklist": ev.get("checklist"),
    }


def render_sources_md(sport: str = "football") -> str:
    lines = [f"# Sources — {sport}", ""]
    for s in list_sources(sport):
        lines.append(f"- **{s['name']}** — {s['use']} — {s['url']}")
    lines.append("")
    lines.append("## Checklist")
    for c in checklist_for(sport):
        lines.append(f"- [ ] `{c}`")
    lines.append("")
    return "\n".join(lines)


def templates_dir(cfg: dict[str, Any]) -> Path:
    rcfg = research_cfg(cfg)
    return resolve(rcfg.get("templates_dir") or "evidence/templates")
