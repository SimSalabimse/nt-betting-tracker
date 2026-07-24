"""Single research sport key used by cards, sources, scaffold, SAEF."""
from __future__ import annotations

from nt.sport_taxonomy import normalize_sport

# Research SSOT keys (sport cards live under these names)
RESEARCH_SPORTS = frozenset(
    {
        "football",
        "tennis",
        "darts",
        "snooker",
        "baseball",
        "basketball",
        "esports",
        "ice_hockey",
        "handball",
        "default",
    }
)

# Canonical taxonomy → research card key
_RESEARCH_ALIAS: dict[str, str] = {
    "football": "football",
    "tennis": "tennis",
    "darts": "darts",
    "snooker": "snooker",
    "baseball": "baseball",
    "basketball": "basketball",
    "esports": "esports",
    "ice_hockey": "ice_hockey",
    "hockey": "ice_hockey",
    "handball": "handball",
    "esports_cs": "esports",
    "cs": "esports",
    "cs2": "esports",
    "csgo": "esports",
    "dota": "esports",
    "lol": "esports",
}


def normalize_sport_for_research(sport: str | None, *, default: str = "default") -> str:
    """
    Canonical research key for cards / list_sources / SAEF.
    Never invents football for unknown sports.
    Unmapped names keep a sanitized key so auto-onboard can write a quarantine card.
    """
    raw = (sport or "").strip().lower().replace(" ", "_")
    if not raw:
        return default
    if raw in _RESEARCH_ALIAS:
        return _RESEARCH_ALIAS[raw]
    can = normalize_sport(raw, default="unknown")
    if can in _RESEARCH_ALIAS:
        return _RESEARCH_ALIAS[can]
    if can in RESEARCH_SPORTS:
        return can
    if can != "unknown" and can:
        # Mapped sports without a full card yet (motorsport, golf, …)
        return can
    # Truly unknown label — keep slug for auto-onboard card path
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in raw).strip("_")
    return safe[:40] if safe else default
