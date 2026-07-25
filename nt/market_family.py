"""
Normative coarse market_family keys for diversify hard caps.

Line numbers are NEVER part of the family key — all tennis game totals
(O/U 21.5–23.5 and beyond) share ``tennis_totals``.

Order (aligned with ``infer_market`` where practical):
  correct score → player props (incl. period scorers) → period/map →
  sport totals → BTTS → HC → ML → fallback.

Coarse by design: corners O/U and goal O/U both map to ``football_totals``.
"""
from __future__ import annotations

import re
from typing import Any

from nt.sport_taxonomy import normalize_sport


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:40]


def _is_correct_score_blob(blob: str, mk: str) -> bool:
    if "correct score" in mk or "correct_score" in mk:
        return True
    return bool(
        re.search(
            r"riktig resultat|korrekt resultat|correct score|korrekt score",
            blob,
        )
    )


def _is_totals_blob(blob: str, mk: str) -> bool:
    """Match totals / O-U markets (sport-agnostic blob)."""
    # Explicit ML / vinner structure wins over bare name "Over" in selection
    # (infer_market can tag Totals from player name "Over, Jeff").
    if "vinner" in blob or "to win" in blob or mk in (
        "match result",
        "match_result",
        "winner",
        "ml",
    ):
        if not (
            "totalt" in blob
            or "over/under" in blob
            or "over under" in blob
            or " o/u" in blob
            or re.search(r"(?<![/\w])over\s*[\d,.]", blob)
            or re.search(r"(?<![/\w])under\s*[\d,.]", blob)
        ):
            return False

    has_total_token = (
        "totalt" in blob
        or "over/under" in blob
        or "over under" in blob
        or " o/u" in blob
        or (
            "total" in blob
            and any(x in blob for x in ("mål", "goal", "game", "point", "corner", "run"))
        )
        or (re.search(r"(?<![/\w])over\b", blob) is not None and re.search(r"\d", blob))
        or (re.search(r"(?<![/\w])under\b", blob) is not None and re.search(r"\d", blob))
    )
    # Trust mk Totals* only when blob also looks total-ish (or mk is period/map totals)
    if mk.startswith("totals") or "period totals" in mk or "map totals" in mk:
        return has_total_token or "period totals" in mk or "map totals" in mk
    return has_total_token


def _is_handicap_blob(blob: str, mk: str) -> bool:
    if "correct score" in mk or _is_correct_score_blob(blob, mk):
        return False
    if "handicap" in mk or "handikap" in mk or mk in ("hc", "set handicap", "map handicap"):
        return True
    if "handikap" in blob or "handicap" in blob or "asian" in blob:
        return True
    # Signed line with unit (sets/maps/games) — not score fragments like 2-1
    if re.search(r"[+-]\s?\d+(?:[.,]\d+)?\s*(?:sets?|maps?|games?)\b", blob):
        return True
    # Explicit signed spread not part of a score pair digit-digit (avoid 2-1)
    if re.search(r"(?<!\d)[+-]\s?\d+(?:[.,]\d+)?\b", blob) and not re.search(
        r"\b\d+\s*[-–]\s*\d+\b", blob
    ):
        return True
    return False


def _is_ml_blob(blob: str, mk: str) -> bool:
    if mk in (
        "ml",
        "match_result",
        "match result",
        "winner",
        "period result",
        "dnb",
    ):
        return True
    if "vinner" in blob or "to win" in blob or "uavgjort" in blob:
        return True
    if re.search(r"\bhub\b", blob) and "omgang" not in blob:
        return True
    return False


def _is_player_prop(blob: str, mk: str) -> bool:
    # BTTS NO string "Begge lag scorer" must not classify as player prop
    if "begge lag" in blob or "btts" in blob or "both teams" in blob:
        return False
    if "player" in mk or "props" in mk:
        return True
    if any(
        x in blob
        for x in (
            "anytime",
            "målscorer",
            "to score",
            "checkout",
            "180",
            "player prop",
        )
    ):
        return True
    # Bare "scorer" (not BTTS) — player goals (incl. "scorer i 1. omgang")
    if "scorer" in blob and "begge" not in blob:
        return True
    return False


def market_family(
    sport: str = "",
    selection: str = "",
    market_type: str = "",
    market_key: str = "",
    evidence: dict[str, Any] | None = None,
) -> str:
    """
    Coarse sport-scoped market family for hard diversify caps.

    Order: correct score → player props → period/map → sport totals →
    BTTS → HC → ML → fallback. Line is never part of the key.
    """
    del evidence  # reserved for future pack-aware refinements
    sp = normalize_sport(sport or "", default="unknown")
    sel = (selection or "").strip()
    if not sel and not (market_type or "").strip() and not (market_key or "").strip():
        return "other"

    sel_l = sel.lower().replace(",", ".")
    mt_l = (market_type or "").lower()
    blob = f"{sel_l} {mt_l}".strip()

    from nt.analytics import infer_market

    mk_raw = market_key or infer_market(selection, market_type) or ""
    mk = mk_raw.lower()

    # --- Step -1: correct score before handicap (score hyphens are not spreads) ---
    if _is_correct_score_blob(blob, mk):
        if sp == "football" or sp == "unknown":
            return "football_correct_score"
        return f"{sp}_correct_score"

    # --- Step 0a: player props BEFORE period (HT scorers stay player_props) ---
    # Matches infer_market SSOT: props before period classification.
    if _is_player_prop(blob, mk):
        if "180" in blob:
            return "darts_180s"
        return "player_props"

    # --- Step 0b: period / map / special totals BEFORE generic totals ---
    if re.search(
        r"1\.\s*omgang|2\.\s*omgang|1st half|2nd half|first half|second half",
        blob,
    ):
        if _is_totals_blob(blob, mk) or "period totals" in mk:
            return f"{sp}_period_totals" if sp != "unknown" else "period_totals"
        return f"{sp}_period" if sp != "unknown" else "period"

    if "kart" in blob or re.search(r"\bmaps?\b", blob):
        if _is_totals_blob(blob, mk) or "map totals" in mk:
            return "esports_map_totals"
        return "esports_map_handicap"

    # --- Step 2: totals / O-U (sport-scoped); line band is NOT a filter ---
    if _is_totals_blob(blob, mk):
        if sp == "tennis":
            return "tennis_totals"
        if sp == "football":
            return "football_totals"
        if sp == "basketball":
            return "basketball_totals"
        if sp == "baseball":
            return "baseball_run_totals"
        if sp == "darts":
            return "darts_totals"
        if sp == "esports":
            return "esports_map_totals"
        if sp == "unknown":
            if re.search(r"\bgames?\b|antall games|set ", blob):
                return "tennis_totals"
            if re.search(r"mål|goal", blob):
                return "football_totals"
            return "totals_unknown"
        return f"{sp}_totals"

    # --- Step 3: BTTS ---
    if "btts" in blob or "begge lag" in blob or "both teams" in blob or mk == "btts":
        return "football_btts" if sp in ("football", "unknown") else f"{sp}_btts"

    # --- Step 4: handicap / spreads ---
    if _is_handicap_blob(blob, mk):
        if sp == "tennis":
            return "tennis_handicap"
        if sp == "football":
            return "football_handicap"
        if sp == "darts":
            return "darts_handicap"
        if sp == "unknown":
            return "handicap_unknown"
        return f"{sp}_handicap"

    # --- Step 5: ML / 1X2 / vinner ---
    if _is_ml_blob(blob, mk):
        if sp == "tennis":
            return "tennis_ml"
        if sp == "football":
            return "football_1x2"
        if sp == "unknown":
            return "ml_unknown"
        return f"{sp}_ml"

    # --- Step 6: fallback ---
    if sp != "unknown" and mk:
        return f"{sp}_{_slug(mk)}"[:48]
    return "other"
