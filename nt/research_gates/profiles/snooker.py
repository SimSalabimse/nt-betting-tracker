from __future__ import annotations

"""Snooker research-gates profile.

Aligned with evidence/sport_cards/snooker.yaml primary factors:
  frame_form, h2h_matchup, ranking_strength (+ recent_form, format_stage).

Compose only — FEH remains place owner (anti-soft / checklist / SAEF).
Gates hard → grade F; never place.
"""

from nt.research_gates.types import GateContext, GateResult
from nt.research_gates.universal import (
    apply_script_family_conflicts,
    apply_universal_availability,
    apply_universal_script_and_base_rate,
)

# Open frames / long BO / century-fest ↔ frame overs
HIGH_SCRIPTS = frozenset(
    {
        "high_scoring",
        "century_fest",
        "long_format",
        "long_match",
        "competitive",
        "open",
        "attacking",
    }
)
# Grind / short BO / dominant fav ↔ frame unders path; blocks overs
LOW_SCRIPTS = frozenset(
    {
        "low_scoring",
        "grind",
        "cagey",
        "defensive",
        "short_format",
        "short_match",
        "dominant_favorite",
        "blowout",
        "one_sided",
    }
)
HIGH_BLOCKS = frozenset({"totals_under", "prop_under"})
LOW_BLOCKS = frozenset({"totals_over", "prop_over"})

# Frame totals / props sensitive; ML & frame HC less so (FEH owns soft-UD HC).
SENSITIVE = frozenset(
    {
        "totals_under",
        "totals_over",
        "prop_under",
        "prop_over",
        "prop",
    }
)


def is_avail_sensitive(family: str, cfg_gates: dict) -> bool:
    if bool(cfg_gates.get("gate_all_markets")):
        return True
    return family in SENSITIVE


def apply(ctx: GateContext, result: GateResult) -> None:
    apply_universal_script_and_base_rate(ctx, result)
    apply_script_family_conflicts(
        ctx,
        result,
        high_scripts=HIGH_SCRIPTS,
        low_scripts=LOW_SCRIPTS,
        high_blocks=HIGH_BLOCKS,
        low_blocks=LOW_BLOCKS,
    )
    if bool(ctx.cfg_gates.get("reject_script_conflict", True)):
        if ctx.script_lean in ("grind", "cagey", "defensive") and ctx.family in (
            "totals_over",
            "prop_over",
            "prop",
        ):
            result.hard.append(
                f"script_lean={ctx.script_lean} conflicts with {ctx.family} — "
                "grind/cagey snooker path kills frame overs and high-break props"
            )
        if ctx.script_lean in ("blowout", "dominant_favorite", "one_sided") and ctx.family in (
            "totals_over",
            "prop_over",
        ):
            result.hard.append(
                f"script_lean={ctx.script_lean} conflicts with {ctx.family} — "
                "short/one-sided frame path kills frame overs"
            )
    if ctx.avail_sensitive:
        apply_universal_availability(ctx, result)
        if ctx.context_risk == "high" and ctx.tier in ("T3", "T4"):
            blob = (
                ctx.availability_notes
                + " "
                + str(ctx.ev.get("summary") or "")
                + " "
                + " ".join(str(s.get("takeaway") or "") for s in ctx.sources)
            ).lower()
            if not any(
                k in blob
                for k in (
                    "frame",
                    "century",
                    "form",
                    "h2h",
                    "ranking",
                    "wd",
                    "withdraw",
                    "fitness",
                    "cuetracker",
                )
            ):
                result.soft.append(
                    "snooker high context — document frame form/H2H or WD status "
                    "(primary: frame_form, h2h_matchup)"
                )
