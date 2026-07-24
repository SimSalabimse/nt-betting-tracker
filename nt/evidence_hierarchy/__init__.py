"""Sport-Aware Evidence Framework (SAEF) + Sport Research Cards."""
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
    score_evidence,
)

__all__ = [
    "SportCard",
    "EvidenceScorecard",
    "score_evidence",
    "load_sport_card",
    "ensure_sport_card",
    "list_onboarded_sports",
    "sport_card_path",
    "normalize_sport_for_research",
    "normalize_h2h",
    "normalize_strength",
]
