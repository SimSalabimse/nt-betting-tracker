from __future__ import annotations

import re
from typing import Any


SPORT_ALIASES: dict[str, str] = {
    "fotball": "football",
    "soccer": "football",
    "soccer_football": "football",
    "eliteserien": "football",
    "ishockey": "hockey",
    "ice_hockey": "hockey",
    "ice-hockey": "hockey",
    "nba": "basketball",
    "wnba": "basketball",
    "basket": "basketball",
    "atp": "tennis",
    "wta": "tennis",
    "handball": "handball",
    "volleyball": "volleyball",
    "darts": "darts",
    "snooker": "snooker",
    "esports": "esports",
    "cs": "esports",
    "cs2": "esports",
    "csgo": "esports",
}


def normalize_sport(sport: str | None, ev: dict[str, Any] | None = None) -> str:
    s = (sport or "").strip().lower()
    if not s and ev:
        s = str(ev.get("sport") or "").strip().lower()
    s = SPORT_ALIASES.get(s, s)
    if s in (
        "football",
        "tennis",
        "basketball",
        "hockey",
        "handball",
        "volleyball",
        "darts",
        "snooker",
        "esports",
        "baseball",
    ):
        return s
    return s or "default"


def selection_family(selection: str, sport: str = "default") -> str:
    """
    Coarse market family for script conflicts.
    Shared across sports; profiles decide which are avail_sensitive.
    """
    s = (selection or "").strip().lower()
    if not s:
        return "other"

    # BTTS / both teams score
    if "btts" in s or "begge lag scorer" in s:
        if re.search(r"\bnei\b|\bno\b", s) and not re.search(r"\bja\b|\byes\b", s):
            return "btts_no"
        if re.search(r"\bja\b|\byes\b", s):
            return "btts_yes"
        return "other"

    # Side after colon (NT Over/Under labels)
    side = s.rsplit(":", 1)[-1].strip() if ":" in s else s

    if re.search(r"\bunder\b", side) and re.search(r"\d+\.?\d*", side):
        return "totals_under"
    if re.search(r"\bover\b", side) and re.search(r"\d+\.?\d*", side):
        return "totals_over"
    if re.search(r"\bunder\b", s) and re.search(r"\d+\.?\d*", s) and "over/under" not in s:
        return "totals_under"
    if re.search(r"\bover\b", s) and re.search(r"\d+\.?\d*", s) and "over/under" not in s:
        return "totals_over"

    # Player props (points, rebounds, 180s, aces, etc.)
    if any(
        k in s
        for k in (
            "spiller",
            "player",
            "points",
            "poeng",
            "rebounds",
            "assists",
            "180",
            "aces",
            "scorer",
            "målscorer",
            "anytime",
            "totalt antall 180",
            "checkout",
        )
    ):
        if "under" in side or re.search(r"\bunder\b", s):
            return "prop_under"
        if "over" in side or re.search(r"\bover\b", s):
            return "prop_over"
        return "prop"

    if "to win" in s or s in ("uavgjort", "draw") or re.search(r"\bhub\b", s) or "vinner" in s:
        return "ml"
    if "handikap" in s or "handicap" in s or "spread" in s:
        return "handicap"
    return "other"


# Competition / context markers → high context_risk
_HIGH_CONTEXT_MARKERS: tuple[str, ...] = (
    "world cup",
    "vm ",
    " vm",
    "wc ",
    "fifa",
    "euro ",
    "em ",
    "nations league",
    "international",
    "internasjonal",
    "friendly",
    "vennekamp",
    "bronze",
    "3rd place",
    "third place",
    "play-off",
    "playoff",
    "cup final",
    "cupfinale",
    "semi-final",
    "semifinal",
    "quarter-final",
    "kvartfinale",
    "back-to-back",
    "back to back",
    "b2b",
    "load management",
    "summer league",
    "g-league",
    "dead rubber",
    "stand-in",
    "standin",
    "retirement",
    "walkover",
)

_MEDIUM_CONTEXT_MARKERS: tuple[str, ...] = (
    "cup",
    "cupen",
    "copa",
    "fa cup",
    "after champions",
    "midweek",
    "3-in-4",
    "three in four",
    "travel",
    "altitude",
)


def infer_context_risk(ev: dict[str, Any], sport: str = "default") -> str:
    """high | medium | low | unknown from explicit fields or text markers."""
    gates = ev.get("research_gates") if isinstance(ev.get("research_gates"), dict) else {}
    for key in ("context_risk", "rotation_risk"):
        raw = ev.get(key) or gates.get(key) or ""
        s = str(raw).strip().lower()
        if s in ("high", "medium", "low"):
            return s

    blob = " ".join(
        [
            str(ev.get("league") or ""),
            str(ev.get("competition") or ""),
            str(ev.get("match") or ""),
            str(ev.get("summary") or ""),
            str(ev.get("availability_notes") or ""),
            str(ev.get("lineup_notes") or ""),
            str(gates.get("base_rate_note") or ""),
            str(gates.get("availability_notes") or ""),
        ]
    ).lower()

    if any(m in blob for m in _HIGH_CONTEXT_MARKERS):
        return "high"
    if any(m in blob for m in _MEDIUM_CONTEXT_MARKERS):
        return "medium"
    # Sport-specific heuristics
    if sport == "basketball" and ("b2b" in blob or "back-to-back" in blob):
        return "high"
    if sport == "tennis" and any(k in blob for k in ("retir", "injury", "walkover", "fatigue")):
        return "high"
    return "unknown"


def tier_for_context(context_risk: str, cfg_gates: dict[str, Any]) -> str:
    if bool(cfg_gates.get("strict_confirmed_only")):
        return "T4"
    if context_risk == "high":
        if bool(cfg_gates.get("high_context_require_confirmed")):
            return "T4"
        return "T3"
    if context_risk == "medium":
        return "T2"
    if context_risk == "low":
        return "T0"
    return "T1"  # unknown → treat as late-data practical tier


def availability_status(ev: dict[str, Any]) -> str:
    gates = ev.get("research_gates") if isinstance(ev.get("research_gates"), dict) else {}
    raw = (
        ev.get("availability_status")
        or ev.get("lineup_status")
        or ev.get("fitness_status")
        or gates.get("availability_status")
        or gates.get("lineup_status")
        or gates.get("fitness_status")
        or ""
    )
    return str(raw).strip().lower().replace(" ", "_")


def availability_notes(ev: dict[str, Any]) -> str:
    gates = ev.get("research_gates") if isinstance(ev.get("research_gates"), dict) else {}
    return str(
        ev.get("availability_notes")
        or ev.get("lineup_notes")
        or gates.get("availability_notes")
        or gates.get("lineup_notes")
        or ""
    ).strip()


def script_lean(ev: dict[str, Any]) -> str:
    gates = ev.get("research_gates") if isinstance(ev.get("research_gates"), dict) else {}
    raw = ev.get("script_lean") or gates.get("script_lean") or gates.get("match_script") or ""
    return str(raw).strip().lower().replace(" ", "_").replace("-", "_")


def selection_vs_script(ev: dict[str, Any]) -> str:
    gates = ev.get("research_gates") if isinstance(ev.get("research_gates"), dict) else {}
    raw = (
        ev.get("selection_vs_script")
        or gates.get("selection_vs_script")
        or gates.get("agrees_with_script")
        or ""
    )
    s = str(raw).strip().lower()
    if s in ("true", "yes", "1", "agree", "agrees"):
        return "agree"
    if s in ("false", "no", "0", "conflict", "conflicts", "disagree"):
        return "conflict"
    return s or "unknown"


def base_rate_conflict(ev: dict[str, Any]) -> bool:
    gates = ev.get("research_gates") if isinstance(ev.get("research_gates"), dict) else {}
    raw = ev.get("base_rate_conflict")
    if raw is None:
        raw = gates.get("base_rate_conflict")
    return raw in (True, "true", "yes", 1, "1")
