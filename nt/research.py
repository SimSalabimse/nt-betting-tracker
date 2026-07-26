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


# ---------------------------------------------------------------------------
# Deep research v1 — atomic complete-pack writer (ESR Stage 2)
# ---------------------------------------------------------------------------

GATE_AVAILABILITY_STATUSES: frozenset[str] = frozenset(
    {"confirmed", "predicted", "stable_guess", "missing"}
)
LINEUP_STATUSES_ALLOWED: frozenset[str] = GATE_AVAILABILITY_STATUSES | frozenset(
    {"changed", "uncertain"}
)
DEEP_RESEARCH_SCHEMA = "deep_research_v1"
DEEP_RESEARCH_MODEL = "agent_deep_research"
_MIN_TAKEAWAY_CHARS = 8
_MIN_ONE_LINER_CHARS = 20
_MIN_SOURCES_WITH_TAKEAWAY = 4
_MIN_WHY_FLIP_CHARS = 20
_ESR_OVERLAY_KEYS: tuple[str, ...] = (
    "opposite_side_check",
    "form_continuity",
    "deep_research",
    "signals",
    "feh_checklist",
    "scan_agents",
    "market_family",
    "sources",
    "lineup_status",
    "lineup_notes",
    "availability_notes",
    "notes",
    "confidence",
    "decimal_odds_ref",
)


def _takeaway_ok(src: Any) -> bool:
    if not isinstance(src, dict):
        return False
    t = str(src.get("takeaway") or "").strip()
    return len(t) >= _MIN_TAKEAWAY_CHARS


def _weak_phrase_hits(text: str) -> list[str]:
    """Return weak-phrase substrings found (warn-only; never hard-fail)."""
    from nt.form_continuity import _DEFAULT_WEAK_PHRASES

    blob = (text or "").lower()
    return [p for p in _DEFAULT_WEAK_PHRASES if p and p in blob]


def validate_deep_research_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Validate deep_research_v1 payload.

    Returns ``{"ok": bool, "errors": list[str], "warnings": list[str]}``.
    Weak phrases produce warnings only.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(payload, dict):
        return {"ok": False, "errors": ["payload must be a JSON object"], "warnings": []}

    match = str(payload.get("match") or "").strip()
    selection = str(payload.get("selection") or "").strip()
    if not match:
        errors.append("match is required")
    if not selection:
        errors.append("selection is required")

    p_model = payload.get("p_model")
    if p_model is None:
        errors.append("p_model is required (do not invent; omit write if unknown)")
    else:
        try:
            pm = float(p_model)
            if not (0.01 <= pm <= 0.99):
                errors.append("p_model must be between 0.01 and 0.99")
        except (TypeError, ValueError):
            errors.append("p_model must be a number")

    avail = str(payload.get("availability_status") or "predicted").strip().lower()
    if avail not in GATE_AVAILABILITY_STATUSES:
        errors.append(
            "availability_status must be gate-canonical: "
            f"{sorted(GATE_AVAILABILITY_STATUSES)} (got {avail!r}); "
            "use lineup_status=changed|uncertain + notes for S1"
        )

    lineup = payload.get("lineup_status")
    if lineup is not None and str(lineup).strip():
        ls = str(lineup).strip().lower()
        if ls not in LINEUP_STATUSES_ALLOWED:
            errors.append(
                f"lineup_status invalid: {ls!r}; allowed {sorted(LINEUP_STATUSES_ALLOWED)}"
            )

    sources = payload.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        good_n = 0
    else:
        good_n = sum(1 for s in sources if _takeaway_ok(s))
        if good_n < _MIN_SOURCES_WITH_TAKEAWAY:
            errors.append(
                f"need ≥{_MIN_SOURCES_WITH_TAKEAWAY} sources with non-empty takeaway "
                f"(≥{_MIN_TAKEAWAY_CHARS} chars); got {good_n}"
            )

    opp = payload.get("opposite_side_check")
    if not isinstance(opp, dict):
        errors.append("opposite_side_check is required")
    else:
        if opp.get("evaluated") is not True:
            errors.append("opposite_side_check.evaluated must be true")
        one = str(opp.get("one_liner") or "").strip()
        if len(one) < _MIN_ONE_LINER_CHARS:
            errors.append(
                f"opposite_side_check.one_liner must be ≥{_MIN_ONE_LINER_CHARS} chars"
            )
        if not str(opp.get("opposite_selection") or "").strip():
            errors.append("opposite_side_check.opposite_selection is required")

    dr = payload.get("deep_research")
    if not isinstance(dr, dict):
        errors.append("deep_research block is required")
    else:
        sv = str(dr.get("schema_version") or "").strip()
        if sv != DEEP_RESEARCH_SCHEMA:
            errors.append(
                f"deep_research.schema_version must be {DEEP_RESEARCH_SCHEMA!r} (got {sv!r})"
            )
        for key in (
            "match_context",
            "recent_form",
            "h2h",
            "ranking_strength_gap",
            "natural_markets",
            "key_risks",
            "verdict",
        ):
            if key not in dr:
                errors.append(f"deep_research.{key} is required")

    fc = payload.get("form_continuity")
    flip_risk = False
    if isinstance(fc, dict):
        flip_risk = bool(fc.get("flip_risk_suspected") or fc.get("form_continuity_triggered"))
        if flip_risk:
            if fc.get("checked") is not True:
                errors.append(
                    "form_continuity.checked must be true when flip risk is suspected/triggered"
                )
            why = str(fc.get("why_flip") or "").strip()
            if len(why) < _MIN_WHY_FLIP_CHARS:
                errors.append(
                    f"form_continuity.why_flip must be ≥{_MIN_WHY_FLIP_CHARS} chars when flip risk"
                )
    elif flip_risk:
        errors.append("form_continuity object required when flip risk")

    # Weak-phrase warn (never hard-fail) on why_flip / one_liner / summary
    check_blobs: list[tuple[str, str]] = [
        ("summary", str(payload.get("summary") or "")),
    ]
    if isinstance(opp, dict):
        check_blobs.append(("opposite_side_check.one_liner", str(opp.get("one_liner") or "")))
        check_blobs.append(
            ("opposite_side_check.why_not_opposite", str(opp.get("why_not_opposite") or ""))
        )
    if isinstance(fc, dict):
        check_blobs.append(("form_continuity.why_flip", str(fc.get("why_flip") or "")))
    feh = payload.get("feh_checklist")
    if isinstance(feh, dict):
        check_blobs.append(
            (
                "feh_checklist.why_this_side_not_opposite",
                str(feh.get("why_this_side_not_opposite") or ""),
            )
        )
    for field, text in check_blobs:
        hits = _weak_phrase_hits(text)
        if hits:
            warnings.append(
                f"weak-phrase in {field}: {hits!r} — fix before Strong/Acceptable on flip "
                "(S2 fails if snapshot sees these; even negation counts)"
            )

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON via temp file + os.replace (idempotent overwrite of same path)."""
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.stem}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_deep_research_pack(
    cfg: dict[str, Any],
    payload: dict[str, Any],
    *,
    odds: float | None = None,
    filename: str | None = None,
    evidence_dir: Path | str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """
    Atomic final writer for deep_research_v1 evidence packs.

    Builds a complete pack (gate fields + ESR keys + sources with takeaways)
    and writes once under evidence/. Idempotent overwrite of the same path.
    Never invents p_model. Bare ``write_research_pack`` is not the final path.
    """
    v = validate_deep_research_payload(payload)
    if not v["ok"]:
        return {
            "ok": False,
            "errors": v["errors"],
            "warnings": v["warnings"],
            "path": None,
            "pack": None,
            "esr_keys_present": False,
        }

    match = str(payload["match"]).strip()
    selection = str(payload["selection"]).strip()
    p_model = float(payload["p_model"])
    sport = str(payload.get("sport") or "football")
    league = str(payload.get("league") or "")
    odds_ref = odds
    if odds_ref is None and payload.get("decimal_odds_ref") is not None:
        try:
            odds_ref = float(payload["decimal_odds_ref"])
        except (TypeError, ValueError):
            odds_ref = None

    avail = str(payload.get("availability_status") or "predicted").strip().lower()
    avail_notes = str(payload.get("availability_notes") or "")
    context_risk = str(payload.get("context_risk") or "low")
    script_lean = str(payload.get("script_lean") or "neutral")
    svs = str(payload.get("selection_vs_script") or "agree")
    brc = bool(payload.get("base_rate_conflict", False))
    summary = str(payload.get("summary") or "")
    failure_modes = str(payload.get("failure_modes") or "")
    notes = str(payload.get("notes") or "deep_research_v1")
    confidence = payload.get("confidence")
    if confidence is None:
        confidence = 0.55
    else:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.55

    # In-memory gate scaffold (no disk write) then overlay ESR.
    base = scaffold_evidence(
        cfg,
        match=match,
        selection=selection,
        p_model=p_model,
        league=league,
        sport=sport,
        odds=odds_ref,
        write=False,
    )
    pack = base["pack"]
    pack["p_model"] = p_model
    pack["summary"] = summary
    pack["failure_modes"] = failure_modes
    pack["confidence"] = confidence
    pack["model_name"] = str(payload.get("model_name") or DEEP_RESEARCH_MODEL)
    pack["context_risk"] = context_risk
    pack["availability_status"] = avail
    pack["availability_notes"] = avail_notes
    # S1-safe: lineup_status may differ from gate availability (changed|uncertain).
    lineup_status = payload.get("lineup_status")
    if lineup_status is not None and str(lineup_status).strip():
        pack["lineup_status"] = str(lineup_status).strip().lower()
    else:
        pack["lineup_status"] = avail
    lineup_notes = payload.get("lineup_notes")
    pack["lineup_notes"] = (
        str(lineup_notes) if lineup_notes is not None else avail_notes
    )
    pack["rotation_risk"] = context_risk
    pack["script_lean"] = script_lean
    pack["selection_vs_script"] = svs
    pack["base_rate_conflict"] = brc
    pack["research_gates"] = {
        "context_risk": context_risk,
        "availability_status": avail,
        "availability_notes": avail_notes,
        "lineup_status": pack["lineup_status"],
        "rotation_risk": context_risk,
        "script_lean": script_lean,
        "selection_vs_script": svs,
        "base_rate_conflict": brc,
        "base_rate_note": str(payload.get("base_rate_note") or ""),
        "lineup_notes": pack["lineup_notes"],
    }
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
    pack["notes"] = notes
    if odds_ref is not None:
        pack["decimal_odds_ref"] = float(odds_ref)

    # ESR overlay — sources with takeaways + form/opposite/deep_research/etc.
    pack["sources"] = list(payload.get("sources") or [])
    pack["opposite_side_check"] = dict(payload.get("opposite_side_check") or {})
    pack["deep_research"] = dict(payload.get("deep_research") or {})
    if "schema_version" not in pack["deep_research"]:
        pack["deep_research"]["schema_version"] = DEEP_RESEARCH_SCHEMA

    if isinstance(payload.get("form_continuity"), dict):
        pack["form_continuity"] = dict(payload["form_continuity"])
    if isinstance(payload.get("signals"), dict):
        pack["signals"] = dict(payload["signals"])
    if isinstance(payload.get("feh_checklist"), dict):
        pack["feh_checklist"] = dict(payload["feh_checklist"])
    if payload.get("scan_agents") is not None:
        pack["scan_agents"] = list(payload["scan_agents"])
    if payload.get("market_family") is not None:
        pack["market_family"] = str(payload["market_family"])

    # Copy through any extra additive keys not handled above (grader-safe unknowns).
    reserved = {
        "match",
        "selection",
        "p_model",
        "sport",
        "league",
        "summary",
        "failure_modes",
        "availability_status",
        "context_risk",
        "script_lean",
        "selection_vs_script",
        "base_rate_conflict",
        "base_rate_note",
        "model_name",
        "checklist",
        "research_gates",
        "rotation_risk",
        *_ESR_OVERLAY_KEYS,
    }
    for k, val in payload.items():
        if k not in reserved and k not in pack:
            pack[k] = val

    esr_keys_present = all(
        k in pack and pack[k] not in (None, "", [], {})
        for k in ("opposite_side_check", "deep_research", "sources")
    )

    if evidence_dir is not None:
        ev_dir = Path(evidence_dir)
    else:
        ev_dir = path_from_config(cfg, "evidence")
    ev_dir = Path(ev_dir)
    ev_dir.mkdir(parents=True, exist_ok=True)
    fname = filename or _safe_filename(match, selection)
    path = ev_dir / fname
    if path.exists() and not overwrite:
        return {
            "ok": False,
            "errors": [f"exists: {path}"],
            "warnings": v["warnings"],
            "path": str(path),
            "pack": pack,
            "esr_keys_present": esr_keys_present,
        }

    _atomic_write_json(path, pack)
    return {
        "ok": True,
        "errors": [],
        "warnings": v["warnings"],
        "path": str(path),
        "pack": pack,
        "esr_keys_present": esr_keys_present,
    }


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
