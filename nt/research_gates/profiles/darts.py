from __future__ import annotations

"""Darts research-gates profile.

Aligned with evidence/sport_cards/darts.yaml primary factors:
  checkout_scoring, h2h_matchup, recent_form (+ format_stage, ranking_seed).

Compose only — FEH remains place owner (anti-soft / checklist / SAEF).
Gates hard → grade F; never place.
"""

from nt.research_gates.types import GateContext, GateResult
from nt.research_gates.universal import (
    apply_script_family_conflicts,
    apply_universal_availability,
    apply_universal_script_and_base_rate,
)

# High averages / long BO / dual 180s ↔ leg overs & 180 props
HIGH_SCRIPTS = frozenset(
    {
        "high_scoring",
        "dual_high_180",
        "high_checkout",
        "long_format",
        "long_match",
        "competitive",
        "open",
    }
)
# Short BO / one-sided / dominant fav ↔ leg unders path; blocks overs
LOW_SCRIPTS = frozenset(
    {
        "low_scoring",
        "short_format",
        "short_match",
        "dominant_favorite",
        "blowout",
        "one_sided",
    }
)
HIGH_BLOCKS = frozenset({"totals_under", "prop_under"})
LOW_BLOCKS = frozenset({"totals_over", "prop_over"})

# Totals (legs) and 180/checkout props are availability-sensitive.
# ML / handicap are not — individual sport; WD rare; FEH owns soft-UD HC.
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
        # prop (no side) not in LOW_BLOCKS — still block on one-sided scripts
        if ctx.script_lean in ("blowout", "dominant_favorite", "one_sided") and ctx.family == "prop":
            result.hard.append(
                f"script_lean={ctx.script_lean} conflicts with prop markets — "
                "short/one-sided darts path kills 180/checkout props"
            )
    if ctx.avail_sensitive:
        apply_universal_availability(ctx, result)
        # High context (TV stage / major) without form/checkout note → soft nudge
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
                    "checkout",
                    "average",
                    "avg",
                    "180",
                    "form",
                    "h2h",
                    "wd",
                    "withdraw",
                    "fitness",
                )
            ):
                result.soft.append(
                    "darts high context — document checkout/averages/form or WD status "
                    "(primary: checkout_scoring, recent_form)"
                )
