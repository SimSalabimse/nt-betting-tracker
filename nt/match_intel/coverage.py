"""
Pure MIC coverage score + grade matrix (design §1.5).

No I/O. Sport-critical/optional key sets and form partial credit are SSOT here.
"""
from __future__ import annotations

from typing import Any

# Weights (sum of max contributions = 1.0)
W_CRITICAL = 0.70
W_OPTIONAL = 0.30

CRITICAL: dict[str, list[str]] = {
    "football": ["form_home", "form_away", "competition", "standings_or_rank"],
    "tennis": ["form_or_rank_home", "form_or_rank_away", "competition"],
    "esports": ["form_home", "form_away", "competition"],
    "default": ["form_home", "form_away", "competition"],
}

OPTIONAL: dict[str, list[str]] = {
    "football": [
        "h2h",
        "injuries",
        "home_away_split",
        "referee",
        "motivation",
        "rest_days",
    ],
    "tennis": ["h2h", "rest_days", "surface", "injuries"],
    "esports": ["h2h", "ranking_or_rating", "roster_notes"],
    "default": ["h2h", "standings_or_rank", "injuries", "motivation"],
}


def form_credit(n: int) -> float:
    """Partial credit for recent form sample size."""
    try:
        ni = int(n)
    except (TypeError, ValueError):
        return 0.0
    if ni >= 5:
        return 1.0
    if ni == 4:
        return 0.85
    if ni == 3:
        return 0.70
    return 0.0


def _side(card: dict[str, Any], which: str) -> dict[str, Any]:
    sides = card.get("sides") or {}
    if not isinstance(sides, dict):
        return {}
    s = sides.get(which) or {}
    return s if isinstance(s, dict) else {}


def _form_n_and_results(side: dict[str, Any]) -> tuple[int, list[Any]]:
    rf = side.get("recent_form") or {}
    if not isinstance(rf, dict):
        return 0, []
    results = rf.get("results") or []
    if not isinstance(results, list):
        results = []
    n = rf.get("n")
    try:
        ni = int(n) if n is not None else len(results)
    except (TypeError, ValueError):
        ni = len(results)
    return ni, results


def _has_rank_or_rating(side: dict[str, Any]) -> bool:
    st = side.get("standings") or {}
    if isinstance(st, dict) and st.get("rank") is not None:
        return True
    if side.get("rating") is not None:
        return True
    return False


def _injuries_present(card: dict[str, Any], side_key: str) -> bool:
    """
    Injuries present when list was fetched (incl. empty after fetch).

    Null / missing key = absent. extraction notes may mark injuries page fetched
    even if both lists empty.
    """
    side = _side(card, side_key)
    inj = side.get("injuries_suspensions")
    if isinstance(inj, list):
        return True
    extraction = card.get("extraction") or {}
    if isinstance(extraction, dict):
        fields = extraction.get("fields_fetched") or []
        if "injuries" in fields:
            return True
        notes = str(extraction.get("notes") or "").lower()
        if "injuries" in notes and "fetched" in notes:
            return True
    # sources may list injuries contribution
    for src in card.get("sources") or []:
        if not isinstance(src, dict):
            continue
        contrib = src.get("fields_contributed") or []
        if "injuries" in contrib:
            return True
    return False


def key_credit(card: dict[str, Any], key: str) -> float:
    """
    0.0 absent; (0,1] partial/full per presence predicate.

    Partial form uses form_credit(n) when n∈[3,4] and non-empty results.
    """
    if not isinstance(card, dict):
        return 0.0

    if key == "form_home":
        n, results = _form_n_and_results(_side(card, "home"))
        if n < 3 or not results:
            return 0.0
        return form_credit(n)

    if key == "form_away":
        n, results = _form_n_and_results(_side(card, "away"))
        if n < 3 or not results:
            return 0.0
        return form_credit(n)

    if key == "form_or_rank_home":
        home = _side(card, "home")
        n, results = _form_n_and_results(home)
        if n >= 3 and results:
            return form_credit(n)
        return 1.0 if _has_rank_or_rating(home) else 0.0

    if key == "form_or_rank_away":
        away = _side(card, "away")
        n, results = _form_n_and_results(away)
        if n >= 3 and results:
            return form_credit(n)
        return 1.0 if _has_rank_or_rating(away) else 0.0

    if key == "competition":
        comp = card.get("competition") or {}
        if isinstance(comp, dict) and str(comp.get("name") or "").strip():
            return 1.0
        return 0.0

    if key == "standings_or_rank":
        if _has_rank_or_rating(_side(card, "home")) or _has_rank_or_rating(_side(card, "away")):
            return 1.0
        return 0.0

    if key == "h2h":
        h2h = card.get("h2h") or {}
        if not isinstance(h2h, dict):
            return 0.0
        try:
            n = int(h2h.get("n") or 0)
        except (TypeError, ValueError):
            n = 0
        if n >= 1:
            return 1.0
        summary = str(h2h.get("summary") or "").strip()
        polarity = h2h.get("polarity")
        if summary and polarity:
            return 1.0
        return 0.0

    if key == "injuries":
        if _injuries_present(card, "home") or _injuries_present(card, "away"):
            return 1.0
        return 0.0

    if key == "home_away_split":
        for sk in ("home", "away"):
            split = _side(card, sk).get("home_away_split") or {}
            if isinstance(split, dict) and any(
                split.get(k) for k in ("home_wdl", "away_wdl", "notes")
            ):
                return 1.0
        return 0.0

    if key == "referee":
        ref = card.get("referee") or {}
        if isinstance(ref, dict) and ref.get("name"):
            return 1.0
        return 0.0

    if key == "motivation":
        mot = card.get("motivation_situational") or {}
        if not isinstance(mot, dict):
            return 0.0
        tags = mot.get("tags") or []
        if tags or mot.get("notes") or mot.get("final") or mot.get("relegation_battle") or mot.get(
            "title_race"
        ):
            return 1.0
        return 0.0

    if key == "rest_days":
        for sk in ("home", "away"):
            rd = _side(card, sk).get("rest_days")
            if rd is not None:
                return 1.0
        return 0.0

    if key == "surface":
        # tennis surface may live under competition.format or other_high_signal
        comp = card.get("competition") or {}
        if isinstance(comp, dict) and str(comp.get("format") or "").strip().lower() in (
            "hard",
            "clay",
            "grass",
            "carpet",
            "indoor_hard",
        ):
            return 1.0
        for item in card.get("other_high_signal") or []:
            if isinstance(item, dict) and "surface" in str(item.get("fact") or "").lower():
                return 1.0
        return 0.0

    if key == "ranking_or_rating":
        return 1.0 if _has_rank_or_rating(_side(card, "home")) or _has_rank_or_rating(
            _side(card, "away")
        ) else 0.0

    if key == "roster_notes":
        for item in card.get("other_high_signal") or []:
            if isinstance(item, dict) and "roster" in str(item.get("fact") or "").lower():
                return 1.0
        return 0.0

    return 0.0


def _sport_key(card: dict[str, Any]) -> str:
    sport = str(card.get("sport") or "default").strip().lower()
    if sport in CRITICAL:
        return sport
    return "default"


def coverage_score(card: dict[str, Any]) -> float:
    """Weighted sum of critical (0.70) + optional (0.30); rounded to 4 dp, capped 1.0."""
    if not isinstance(card, dict):
        return 0.0
    sk = _sport_key(card)
    crit = CRITICAL[sk]
    opt = OPTIONAL[sk]
    c_w = W_CRITICAL / max(len(crit), 1)
    o_w = W_OPTIONAL / max(len(opt), 1)
    s = sum(c_w * key_credit(card, k) for k in crit)
    s += sum(o_w * key_credit(card, k) for k in opt)
    return round(min(1.0, s), 4)


def critical_missing_count(card: dict[str, Any]) -> int:
    """Count critical keys with key_credit == 0 (partial form n≥3 counts present)."""
    if not isinstance(card, dict):
        return len(CRITICAL["default"])
    sk = _sport_key(card)
    return sum(1 for k in CRITICAL[sk] if key_credit(card, k) == 0.0)


def _is_unusable(card: dict[str, Any] | None) -> bool:
    if card is None or not isinstance(card, dict):
        return True
    if not card.get("match_key") and not card.get("match"):
        return True
    # Explicit skeleton with no usable fields
    extraction = card.get("extraction") or {}
    if not isinstance(extraction, dict):
        extraction = {}
    errors = extraction.get("errors") or []
    score = 0.0
    try:
        # quick check: any critical credit?
        sk = _sport_key(card)
        score = sum(key_credit(card, k) for k in CRITICAL[sk])
    except Exception:  # noqa: BLE001
        score = 0.0
    if score == 0.0 and (
        extraction.get("primary_method") in ("failed", "none", "skeleton")
        or "no_source" in errors
        or "unreadable" in errors
        or "match_key_mismatch" in errors
    ):
        return True
    # needs_review with zero critical credit
    if extraction.get("needs_review") and score == 0.0 and not any(
        key_credit(card, k) > 0 for k in CRITICAL.get(_sport_key(card), CRITICAL["default"])
    ):
        # still allow C/D if we have some fields — only F when truly empty
        if all(key_credit(card, k) == 0.0 for k in CRITICAL[_sport_key(card)]):
            # if competition also empty etc — F
            return coverage_score(card) == 0.0
    return False


def grade_card(card: dict[str, Any] | None) -> dict[str, Any]:
    """
    Compute full coverage block: score, grade, present/missing lists.

    Grade precedence (design §1.5.3): critical-count overrides raw score.
    B requires n_miss == 0.
    """
    if card is None or not isinstance(card, dict) or _is_unusable(card):
        return {
            "score": 0.0,
            "max_score": 1.0,
            "grade": "F",
            "critical_present": [],
            "critical_missing": list(CRITICAL.get(
                str((card or {}).get("sport") or "default").lower()
                if isinstance(card, dict)
                else "default",
                CRITICAL["default"],
            )),
            "optional_present": [],
            "optional_missing": [],
            "notes": "missing / unreadable / unusable MIC",
        }

    sk = _sport_key(card)
    crit = CRITICAL[sk]
    opt = OPTIONAL[sk]
    score = coverage_score(card)
    n_miss = critical_missing_count(card)

    crit_present = [k for k in crit if key_credit(card, k) > 0.0]
    crit_missing = [k for k in crit if key_credit(card, k) == 0.0]
    opt_present = [k for k in opt if key_credit(card, k) > 0.0]
    opt_missing = [k for k in opt if key_credit(card, k) == 0.0]

    # Grade matrix
    if n_miss >= 2 or score < 0.40:
        grade = "D"
    elif n_miss == 1:
        grade = "C"
    elif n_miss == 0 and score >= 0.80:
        grade = "A"
    elif n_miss == 0 and score >= 0.60:
        grade = "B"
    elif n_miss == 0 and score >= 0.40:
        grade = "C"
    else:
        grade = "D"

    # Absolute empty card → F (overrides D when completely blank)
    if score == 0.0 and n_miss == len(crit) and not opt_present:
        extraction = card.get("extraction") or {}
        if isinstance(extraction, dict) and (
            extraction.get("primary_method") in ("failed", "none", "skeleton", "stub")
            or extraction.get("errors")
        ):
            grade = "F"

    notes_parts: list[str] = []
    if crit_missing:
        notes_parts.append("missing critical: " + ", ".join(crit_missing))
    if grade == "B" and n_miss != 0:
        # should be unreachable — belt-and-suspenders
        grade = "C"
        notes_parts.append("B requires n_miss==0")

    return {
        "score": score,
        "max_score": 1.0,
        "grade": grade,
        "critical_present": crit_present,
        "critical_missing": crit_missing,
        "optional_present": opt_present,
        "optional_missing": opt_missing,
        "notes": "; ".join(notes_parts),
    }
