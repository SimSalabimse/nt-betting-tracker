from __future__ import annotations

from nt.research_gates.types import GateContext, GateResult
from nt.research_gates.universal import (
    apply_script_family_conflicts,
    apply_universal_availability,
    apply_universal_script_and_base_rate,
)

# long match / high games ↔ overs; retirement / short ↔ unders of games careful
HIGH_SCRIPTS = frozenset({"long_match", "competitive", "three_setter", "five_setter"})
LOW_SCRIPTS = frozenset({"short_match", "dominant_favorite", "retirement_risk", "bagel_path"})
# high script blocks unders of games/sets; low/retirement blocks overs
HIGH_BLOCKS = frozenset({"totals_under", "prop_under"})
LOW_BLOCKS = frozenset({"totals_over", "prop_over"})

SENSITIVE = frozenset(
    {
        "totals_under",
        "totals_over",
        "prop_under",
        "prop_over",
        "prop",
        "handicap",
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
    # Extra: retirement_risk always blocks game/set overs
    if bool(ctx.cfg_gates.get("reject_script_conflict", True)):
        if ctx.script_lean == "retirement_risk" and ctx.family in (
            "totals_over",
            "prop_over",
            "prop",
        ):
            result.hard.append(
                "script_lean=retirement_risk conflicts with overs/props — "
                "do not back long-match or high game totals"
            )
    if ctx.avail_sensitive:
        apply_universal_availability(ctx, result)
        # High context tennis without fatigue note in summary/notes
        if ctx.context_risk == "high" and ctx.tier in ("T3", "T4"):
            blob = (ctx.availability_notes + str(ctx.ev.get("summary") or "")).lower()
            if not any(k in blob for k in ("fatig", "rest", "injury", "fitness", "retir", "schedule")):
                if "fatig" not in " ".join(
                    str(s.get("takeaway") or "").lower() for s in ctx.sources
                ):
                    result.soft.append(
                        "tennis high context — document fatigue/schedule/injury explicitly"
                    )
