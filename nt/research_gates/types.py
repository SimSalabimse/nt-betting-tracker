from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GateResult:
    hard: list[str] = field(default_factory=list)
    soft: list[str] = field(default_factory=list)
    tier: str = "T0"
    context_risk: str = "unknown"
    family: str = "other"
    sport: str = "default"
    avail_sensitive: bool = False

    def as_tuple(self) -> tuple[list[str], list[str]]:
        return self.hard, self.soft


@dataclass
class GateContext:
    """Normalized inputs for profile evaluation."""

    sport: str
    selection: str
    family: str
    odds: float
    context_risk: str
    tier: str
    availability_status: str
    availability_notes: str
    script_lean: str
    selection_vs_script: str
    base_rate_conflict: bool
    sources: list[dict[str, Any]]
    ev: dict[str, Any]
    cfg_gates: dict[str, Any]
    avail_sensitive: bool
