"""
Canonical sport labels for the NT betting system.

Phase 3: one taxonomy for parse → diversify → learning → forensic soft-match.
Collector may emit display names (``Darts``, ``LoL``, ``Basketball``); we map
them to stable lowercase keys.
"""
from __future__ import annotations

import re

# Preferred set used in ledger, diversify, and learning
CANONICAL_SPORTS = frozenset(
    {
        "football",
        "tennis",
        "darts",
        "snooker",
        "basketball",
        "baseball",
        "ice_hockey",
        "handball",
        "esports",
        "motorsport",
        "cycling",
        "golf",
        "unknown",
    }
)

# Map aliases / legacy / collector labels → canonical
_ALIAS: dict[str, str] = {
    # football
    "football": "football",
    "fotball": "football",
    "soccer": "football",
    # tennis
    "tennis": "tennis",
    # darts
    "darts": "darts",
    # snooker
    "snooker": "snooker",
    # basketball (collapse NBA/WNBA into one diversify bucket)
    "basketball": "basketball",
    "nba": "basketball",
    "wnba": "basketball",
    # baseball
    "baseball": "baseball",
    "mlb": "baseball",
    # hockey
    "ice_hockey": "ice_hockey",
    "ice hockey": "ice_hockey",
    "ishockey": "ice_hockey",
    "hockey": "ice_hockey",
    # handball
    "handball": "handball",
    "håndball": "handball",
    "haandball": "handball",
    # esports
    "esports": "esports",
    "e-sports": "esports",
    "counter-strike": "esports",
    "counter strike": "esports",
    "cs": "esports",
    "cs2": "esports",
    "csgo": "esports",
    "dota": "esports",
    "dota 2": "esports",
    "lol": "esports",
    "league of legends": "esports",
    "valorant": "esports",
    # motorsport
    "motorsport": "motorsport",
    "formula 1": "motorsport",
    "formel 1": "motorsport",
    "f1": "motorsport",
    # cycling / golf
    "cycling": "cycling",
    "sykkel": "cycling",
    "golf": "golf",
    # unknown
    "unknown": "unknown",
    "": "unknown",
}

# WNBA franchise tokens (for subtype detection / basketball confirmation)
WNBA_TEAM_TOKENS = frozenset(
    {
        "tempo",
        "mystics",
        "fever",
        "liberty",
        "sparks",
        "mercury",
        "sky",
        "dream",
        "aces",
        "sun",
        "lynx",
        "storm",
        "wings",
        "valkyries",
    }
)


def normalize_sport(raw: str | None, *, default: str = "unknown") -> str:
    """
    Map any sport label to a canonical diversify/learning key.

    Examples:
      ``"Darts"`` → ``darts``
      ``"nba"`` / ``"WNBA"`` → ``basketball``
      ``"LoL"`` / ``"Counter-Strike"`` → ``esports``
    """
    if raw is None:
        return default if default in CANONICAL_SPORTS else "unknown"
    s = str(raw).strip().lower()
    s = re.sub(r"\s+", " ", s)
    # strip rating suffixes like "football rating 8"
    s = re.sub(r"\s+rating\s+\d+$", "", s).strip()
    if s in _ALIAS:
        return _ALIAS[s]
    # hyphen/underscore variants
    s2 = s.replace("_", " ").replace("-", " ")
    s2 = re.sub(r"\s+", " ", s2).strip()
    if s2 in _ALIAS:
        return _ALIAS[s2]
    # slug form
    slug = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if slug in _ALIAS:
        return _ALIAS[slug]
    if slug in CANONICAL_SPORTS:
        return slug
    # partial contains for collector display names
    for key, canon in (
        ("counter", "esports"),
        ("dota", "esports"),
        ("league of legends", "esports"),
        ("basket", "basketball"),
        ("baseball", "baseball"),
        ("snooker", "snooker"),
        ("dart", "darts"),
        ("tennis", "tennis"),
        ("fotball", "football"),
        ("football", "football"),
        ("hockey", "ice_hockey"),
        ("handball", "handball"),
        ("formel", "motorsport"),
        ("formula", "motorsport"),
    ):
        if key in s2:
            return canon
    return default if default in CANONICAL_SPORTS else "unknown"


def basketball_subtype(home: str, away: str, blob: str = "") -> str:
    """
    Optional subtype for notes/UI only — diversify still uses ``basketball``.

    Returns ``wnba`` | ``nba`` | ``basketball``.
    """
    homes = f"{home} {away}".lower()
    if any(t in homes for t in WNBA_TEAM_TOKENS):
        return "wnba"
    if "wnba" in (blob or "").lower():
        return "wnba"
    if "nba" in (blob or "").lower() or "inkludert overtid" in (blob or "").lower():
        return "nba"
    return "basketball"
