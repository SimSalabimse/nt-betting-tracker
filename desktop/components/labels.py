from __future__ import annotations

"""UI display labels — keep raw data in engines, map Norwegian NT names for the desk."""

_MARKET_EXACT = {
    "HUB": "Match 1X2",
    "hub": "Match 1X2",
    "BTTS": "BTTS",
    "Begge lag scorer": "BTTS",
    "Match result": "Match result",
    "Player props": "Player props",
    "Handicap": "Handicap",
    "DNB": "DNB",
    "Map totals": "Map totals",
    "Totals": "Totals",
    "Other": "Other",
}


def market_label(name: str | None) -> str:
    """Short English-ish label for market family / NT market_type strings."""
    if not name:
        return "—"
    n = str(name).strip()
    if n in _MARKET_EXACT:
        return _MARKET_EXACT[n]
    low = n.lower()
    if low == "hub" or low.startswith("hub ") or "1. omgang - hub" in low:
        return "Match 1X2"
    if "begge lag" in low or low in ("btts", "btts ja", "btts nei"):
        return "BTTS"
    if "over/under 2.5" in low or "over/under 2,5" in low:
        return "Totals 2.5"
    if "over/under 3.5" in low or "over/under 3,5" in low:
        return "Totals 3.5"
    if "over/under 1.5" in low or "over/under 1,5" in low:
        return "Totals 1.5"
    if "over/under 0.5" in low:
        return "Totals 0.5"
    if "over/under 4.5" in low:
        return "Totals 4.5"
    if "totalt antall" in low or "total" in low:
        return "Totals"
    if "handikap" in low or "handicap" in low:
        return "Handicap"
    if "korrekt resultat" in low:
        return "Correct score"
    if "pause/fulltid" in low or "halvtid" in low:
        return "HT/FT"
    if "dnb" in low or "uavgjort tilbakebetales" in low:
        return "DNB"
    if "scorer" in low or "målscorer" in low:
        return "Player props"
    if "kart" in low or "map" in low:
        return "Map totals"
    # Truncate very long raw NT strings
    if len(n) > 28:
        return n[:27] + "…"
    return n


def humanize_phase_reason(raw: str) -> str | None:
    """Turn engine phase reason strings into desk copy. Returns None to hide noise."""
    if not raw:
        return None
    s = str(raw).strip()
    low = s.lower()
    if low.startswith("equity_phase="):
        # equity_phase=1A (equity 570.18)
        t = s.replace("equity_phase=", "Equity ladder ").replace(" (equity ", " · bankroll ")
        return t.rstrip(")")
    if low.startswith("count_phase="):
        t = s.replace("count_phase=", "Count ladder ").replace(" (settled ", " · settled ")
        return t.rstrip(")")
    if low.startswith("peak_equity="):
        return s.replace("peak_equity=", "Peak equity ")
    if "count unlock capped" in low:
        return "Count unlock held to equity+1 (anti-skip)"
    if "demote" in low:
        return s
    if "rolling" in low:
        return s
    # skip pure key=value noise we already show elsewhere
    if "=" in s and " " not in s.split("=")[0]:
        return None
    return s
