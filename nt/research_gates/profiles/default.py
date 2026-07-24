from __future__ import annotations

"""Generic profile for hockey, handball, esports, baseball, etc.

Darts/snooker have dedicated profiles (profiles/darts.py, profiles/snooker.py).
"""

from nt.research_gates.types import GateContext, GateResult
from nt.research_gates.universal import (
    apply_script_family_conflicts,
    apply_universal_availability,
    apply_universal_script_and_base_rate,
)

HIGH_SCRIPTS = frozenset(
    {"high_scoring", "high_pace", "open", "shootout", "attacking", "long_match"}
)
LOW_SCRIPTS = frozenset(
    {"low_scoring", "low_pace", "cagey", "defensive", "short_match", "blowout"}
)
HIGH_BLOCKS = frozenset({"totals_under", "btts_no", "prop_under"})
LOW_BLOCKS = frozenset({"totals_over", "btts_yes", "prop_over"})

SENSITIVE = frozenset(
    {
        "totals_under",
        "totals_over",
        "btts_no",
        "btts_yes",
        "prop_under",
        "prop_over",
        "prop",
    }
)


def is_avail_sensitive(family: str, cfg_gates: dict) -> bool:
    if bool(cfg_gates.get("gate_all_markets")):
        return True
    # Darts/snooker: totals/props only; ML less availability-gated
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
    if ctx.avail_sensitive:
        apply_universal_availability(ctx, result)
