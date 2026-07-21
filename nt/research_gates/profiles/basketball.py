from __future__ import annotations

from nt.research_gates.types import GateContext, GateResult
from nt.research_gates.universal import (
    apply_script_family_conflicts,
    apply_universal_availability,
    apply_universal_script_and_base_rate,
)

HIGH_SCRIPTS = frozenset({"high_pace", "competitive", "track_meet"})
LOW_SCRIPTS = frozenset({"low_pace", "grind", "blowout", "star_rest"})
HIGH_BLOCKS = frozenset({"totals_under", "prop_under"})
LOW_BLOCKS = frozenset({"totals_over", "prop_over"})

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
        if ctx.script_lean == "star_rest" and ctx.family in ("prop_over", "prop", "totals_over"):
            result.hard.append(
                "script_lean=star_rest conflicts with overs/props — "
                "star DNP/load management kills player overs and often team total"
            )
        if ctx.script_lean == "blowout" and ctx.family in ("prop_over",):
            result.soft.append(
                "blowout script — player props volatile (starters sit late); prefer confirmed minutes"
            )
    if ctx.avail_sensitive:
        apply_universal_availability(ctx, result)
