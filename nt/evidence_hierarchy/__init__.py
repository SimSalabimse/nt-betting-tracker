"""Sport-Aware Evidence Framework (SAEF) + Forced Evidence Hierarchy (FEH)."""
from __future__ import annotations

from nt.evidence_hierarchy.cards import (
    SportCard,
    ensure_sport_card,
    list_onboarded_sports,
    load_sport_card,
    sport_card_path,
)
from nt.evidence_hierarchy.h2h_normalize import normalize_h2h, normalize_strength
from nt.evidence_hierarchy.normalize import normalize_sport_for_research
from nt.evidence_hierarchy.score import (
    EvidenceScorecard,
    place_uses_saef,
    score_evidence,
)

__all__ = [
    "SportCard",
    "EvidenceScorecard",
    "score_evidence",
    "place_uses_saef",
    "load_sport_card",
    "ensure_sport_card",
    "list_onboarded_sports",
    "sport_card_path",
    "normalize_sport_for_research",
    "normalize_h2h",
    "normalize_strength",
    "run_forced_evidence_hierarchy",
]


def __getattr__(name: str):
    # Lazy import FEH orchestrator to avoid circular imports at package load
    if name == "run_forced_evidence_hierarchy":
        from nt.evidence_hierarchy.feh import run_forced_evidence_hierarchy

        return run_forced_evidence_hierarchy
    if name == "FEHResult":
        from nt.evidence_hierarchy.feh import FEHResult

        return FEHResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
