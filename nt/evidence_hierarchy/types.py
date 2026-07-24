"""SAEF types — signal slots and required groups."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Reserved for PR2 FEH orchestrator reject codes (declared early for shared imports).
FEHRejectCode = Literal[
    "FEH_ANTI_SOFT_UNDERDOG",
    "FEH_SIDE_CONFLICT",
    "FEH_SIDE_UNCLEAR_UD",
    "FEH_PRICE_LED_SIDE",
    "FEH_CHECKLIST_INCOMPLETE",
    "FEH_NATURAL_MARKET_UNEVALUATED",
]


@dataclass(frozen=True)
class SignalSlot:
    id: str
    tier: int  # 1 | 2 | 3
    weight: float
    markets: frozenset[str]
    require_when: frozenset[str]
    public_sources: tuple[str, ...] = ()
    min_takeaway_chars: int = 24
    allows_negative_strength: bool = False
    individual_h2h: bool = False  # never-ignore for individual sports


@dataclass(frozen=True)
class RequiredGroup:
    id: str
    slot_ids: tuple[str, ...]
    min_filled: int = 1
    apply_when: frozenset[str] = frozenset({"*"})


@dataclass
class SlotFill:
    slot_id: str
    f_i: float
    weight: float
    applicable: bool
    required: bool
    note: str = ""


@dataclass
class EvidenceScorecard:
    sport: str
    card_id: str
    onboarded: bool
    E: float
    r: float
    quality_source_count: int
    distinct_quality_domains: int
    grade_suggestion: str
    hard_rejects: list[str] = field(default_factory=list)
    soft_notes: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    filled_slots: list[str] = field(default_factory=list)
    strongest_positive: str = ""
    strongest_negative: str = ""
    factors: list[dict[str, Any]] = field(default_factory=list)
    primary_weights: dict[str, float] = field(default_factory=dict)
    confidence: str = "Low"  # High | Medium | Low
    p_reliability: float = 0.0

    def to_audit(self) -> dict[str, Any]:
        return {
            "sport": self.sport,
            "card_id": self.card_id,
            "onboarded": self.onboarded,
            "E": round(self.E, 4),
            "r": round(self.r, 4),
            "quality_source_count": self.quality_source_count,
            "distinct_quality_domains": self.distinct_quality_domains,
            "grade_suggestion": self.grade_suggestion,
            "hard_rejects": list(self.hard_rejects),
            "soft_notes": list(self.soft_notes)[:8],
            "missing_required": list(self.missing_required),
            "filled_slots": list(self.filled_slots),
            "strongest_positive": self.strongest_positive,
            "strongest_negative": self.strongest_negative,
            "factors": list(self.factors)[:12],
            "primary_weights": dict(self.primary_weights),
            "confidence": self.confidence,
            "p_reliability": round(self.p_reliability, 4),
        }
