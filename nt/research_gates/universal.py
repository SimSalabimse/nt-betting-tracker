from __future__ import annotations

from typing import Any

from nt.research_gates.types import GateContext, GateResult

CONFIRMED = frozenset({"confirmed", "official", "starting_xi", "confirmed_xi", "fit", "active"})
PREDICTED = frozenset(
    {
        "predicted",
        "expected",
        "probable",
        "leaked",
        "stable_guess",
        "projected",
        "likely",
        "doubt",  # tennis/basketball uncertain but researched
    }
)


def has_source_kind(sources: list[dict[str, Any]], kind: str) -> bool:
    k = kind.lower()
    return any(str(s.get("kind") or "").lower() == k for s in sources)


def has_availability_research(ctx: GateContext) -> bool:
    """True if pack shows injury/lineup/fitness/load research."""
    sources = ctx.sources
    if has_source_kind(sources, "injury"):
        return True
    if has_source_kind(sources, "lineup"):
        return True
    if has_source_kind(sources, "team_news"):
        return True
    if has_source_kind(sources, "fitness"):
        return True
    if has_source_kind(sources, "load"):
        return True
    notes = (ctx.availability_notes + " " + str(ctx.ev.get("summary") or "")).lower()
    keys = (
        "injur",
        "suspend",
        "out:",
        "doubt",
        "availab",
        "skade",
        "uteslutt",
        "rotation",
        "rested",
        "missing",
        "lineup",
        "starting",
        "minutes",
        "load",
        "fatigue",
        "retirement",
        "fitness",
        "goalie",
        "starter",
        "dnp",
        "questionable",
        "probable",
        "no absences",
        "full strength",
        "stand-in",
        "roster",
    )
    if any(k in notes for k in keys):
        return True
    for s in sources:
        take = str(s.get("takeaway") or "").lower()
        if any(k in take for k in keys):
            return True
    return False


def apply_universal_script_and_base_rate(ctx: GateContext, result: GateResult) -> None:
    g = ctx.cfg_gates
    if bool(g.get("reject_script_conflict", True)):
        if ctx.selection_vs_script == "conflict":
            result.hard.append(
                "selection_vs_script=conflict — cannot place a bet against your own match script"
            )
    if bool(g.get("reject_base_rate_conflict", True)) and ctx.base_rate_conflict:
        result.hard.append(
            "base_rate_conflict=true — historical base rate opposes this selection "
            "(e.g. bronze 3.8 GPG vs Under 3.5)"
        )


def apply_universal_availability(ctx: GateContext, result: GateResult) -> None:
    """Tiered availability gates for avail_sensitive markets."""
    if not ctx.avail_sensitive:
        return
    g = ctx.cfg_gates
    if not bool(g.get("require_availability_status", True)):
        return

    status = ctx.availability_status
    notes = ctx.availability_notes
    researched = has_availability_research(ctx)
    predicted_ok = bool(g.get("predicted_availability_ok", True))
    require_research = bool(g.get("require_availability_research_if_predicted", True))
    min_notes = int(g.get("high_context_min_notes_chars", 40))
    thr = float(g.get("high_odds_threshold", 2.5))

    if not status or status in ("missing", "unknown", "none"):
        if not researched:
            result.hard.append(
                "availability_status missing and no availability research — "
                "for sensitive markets set availability_status/lineup_status="
                "predicted|confirmed and document injuries/load/fitness"
            )
        else:
            result.hard.append(
                "availability_status must be set explicitly "
                "(predicted|confirmed|stable_guess) for sensitive markets — do not leave missing"
            )
            result.soft.append(
                "availability research present but status blank — set predicted or confirmed"
            )
        return

    if status in PREDICTED:
        if bool(g.get("strict_confirmed_only")) or (
            ctx.tier == "T4" and bool(g.get("high_context_require_confirmed"))
        ):
            result.hard.append(
                f"availability_status={status} blocked — confirmed required "
                f"(tier {ctx.tier} / strict mode)"
            )
            return
        if not predicted_ok:
            result.hard.append(
                f"availability_status={status} not allowed (predicted_availability_ok=false)"
            )
            return
        if require_research and not researched:
            result.hard.append(
                "predicted availability without injury/load/fitness research — "
                "document who is out, minutes, or fitness (kind=injury|lineup|fitness|load)"
            )
        if ctx.tier in ("T3", "T4") and bool(g.get("high_context_stricter_notes", True)):
            if len(notes) < min_notes:
                result.hard.append(
                    f"high context_risk (tier {ctx.tier}) with predicted availability — "
                    f"write availability_notes/lineup_notes (≥{min_notes} chars) covering "
                    "likely rotation, minutes, or fitness; or wait for confirmed"
                )
            else:
                result.soft.append(
                    f"tier {ctx.tier} + predicted availability — haircut p harder; "
                    "anti-script unders/props especially fragile"
                )
        if ctx.odds >= thr and bool(g.get("high_odds_prefer_confirmed", True)):
            result.soft.append(
                "high-odds sensitive market on predicted availability — "
                "OK for 12h boards; re-check when official status drops"
            )
        return

    if status in CONFIRMED:
        if not researched and not notes:
            result.soft.append(
                "availability_status=confirmed but no source/notes — add takeaway for audit trail"
            )
        return

    result.soft.append(
        f"unrecognized availability_status={status!r} — "
        "use confirmed|predicted|stable_guess|missing"
    )


def apply_script_family_conflicts(
    ctx: GateContext,
    result: GateResult,
    *,
    high_scripts: frozenset[str],
    low_scripts: frozenset[str],
    high_blocks: frozenset[str],
    low_blocks: frozenset[str],
) -> None:
    if not bool(ctx.cfg_gates.get("reject_script_conflict", True)):
        return
    script = ctx.script_lean
    if not script or script in ("neutral", "unknown", ""):
        return
    # Normalize aliases
    if script in ("shootout", "open", "attacking", "high_pace"):
        script_n = "high_scoring" if "high_scoring" in high_scripts else script
    else:
        script_n = script
    if script_n in high_scripts or script in high_scripts:
        if ctx.family in high_blocks:
            result.hard.append(
                f"script_lean={ctx.script_lean} conflicts with {ctx.family} "
                f"(high/open script → do not back {ctx.family})"
            )
    if script_n in low_scripts or script in low_scripts:
        if ctx.family in low_blocks:
            result.hard.append(
                f"script_lean={ctx.script_lean} conflicts with {ctx.family} "
                f"(low/cagey script → do not back {ctx.family})"
            )
