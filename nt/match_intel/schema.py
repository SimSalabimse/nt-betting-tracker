"""MIC dict schema helpers + filesystem match_key slug."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from nt.odds_common import normalize_match_key


SCHEMA_VERSION = 1


def mic_match_key(match: str) -> str:
    """Filesystem-safe key for outbox/match_intel/{key}.json."""
    s = normalize_match_key(match)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:120] or "unknown_match"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def side_dict(
    name: str = "",
    *,
    recent_form: dict[str, Any] | None = None,
    standings: dict[str, Any] | None = None,
    rating: float | int | None = None,
    home_away_split: dict[str, Any] | None = None,
    injuries_suspensions: list[dict[str, Any]] | None = None,
    rest_days: int | None = None,
) -> dict[str, Any]:
    """Build one side (home/away) object with stable keys."""
    return {
        "name": name or "",
        "recent_form": recent_form
        if recent_form is not None
        else {"n": 0, "results": [], "scores": [], "summary": ""},
        "standings": standings if standings is not None else {},
        "rating": rating,
        "home_away_split": home_away_split if home_away_split is not None else {},
        "injuries_suspensions": (
            list(injuries_suspensions) if injuries_suspensions is not None else None
        ),
        "rest_days": rest_days,
    }


def empty_mic_skeleton(
    match: str,
    *,
    sport: str = "football",
    odds_file: str | None = None,
    errors: list[str] | None = None,
    primary_method: str = "failed",
    match_confidence: str = "none",
    needs_review: bool = True,
) -> dict[str, Any]:
    """
    Grade-F-ready skeleton when no free page is resolved.

    Never invent form/injuries — leave fields empty/null and let coverage grade F/D.
    """
    now = _utc_now_iso()
    home, away = _split_sides(match)
    return {
        "schema_version": SCHEMA_VERSION,
        "match_key": mic_match_key(match),
        "match": match,
        "sport": (sport or "football").strip().lower() or "football",
        "competition": {
            "name": "",
            "country": None,
            "tier": None,
            "format": None,
            "importance": None,
            "series_context": None,
        },
        "kickoff_utc": None,
        "kickoff_local": None,
        "sides": {
            "home": side_dict(home),
            "away": side_dict(away),
        },
        "h2h": {"n": 0, "summary": "", "recent": [], "polarity": None},
        "referee": {"name": None, "cards_tendency": None, "notes": None},
        "motivation_situational": {
            "tags": [],
            "notes": None,
            "final": False,
            "relegation_battle": False,
            "title_race": False,
        },
        "other_high_signal": [],
        "sources": [],
        "coverage": {
            "score": 0.0,
            "max_score": 1.0,
            "grade": "F",
            "critical_present": [],
            "critical_missing": [],
            "optional_present": [],
            "optional_missing": [],
            "notes": "skeleton — no free facts extracted",
        },
        "extraction": {
            "primary_method": primary_method,
            "fallbacks_used": [],
            "exa_used": False,
            "match_confidence": match_confidence,
            "needs_review": needs_review,
            "duration_ms": 0,
            "errors": list(errors or ["no_source"]),
        },
        "created_at": now,
        "updated_at": now,
        "odds_file": odds_file,
    }


def _split_sides(match: str) -> tuple[str, str]:
    m = (match or "").strip()
    for sep in (" vs ", " v ", " - ", " – ", " — "):
        if sep in m:
            a, b = m.split(sep, 1)
            return a.strip(), b.strip()
    return m, ""


def validate_mic_shape(card: dict[str, Any]) -> list[str]:
    """Return list of structural issues (empty = OK)."""
    issues: list[str] = []
    if not isinstance(card, dict):
        return ["not_a_dict"]
    for key in ("schema_version", "match_key", "match", "sport", "sides", "coverage", "extraction"):
        if key not in card:
            issues.append(f"missing:{key}")
    sides = card.get("sides")
    if isinstance(sides, dict):
        for side in ("home", "away"):
            if side not in sides:
                issues.append(f"missing:sides.{side}")
    else:
        issues.append("missing:sides")
    return issues


def finalize_coverage(card: dict[str, Any]) -> dict[str, Any]:
    """
    Mutate card['coverage'] from pure coverage helpers and return card.

    Caps grade at C when match_confidence is fuzzy / manual_pending or needs_review
    with low-confidence extraction (design §1.6).
    """
    from nt.match_intel.coverage import grade_card

    cov = grade_card(card)
    extraction = card.get("extraction") or {}
    conf = str(extraction.get("match_confidence") or "").lower()
    needs_review = bool(extraction.get("needs_review"))
    # Low-confidence rule: cannot raise grade above C
    if conf in ("fuzzy", "manual_pending") or (
        needs_review and conf not in ("exact", "alias") and cov.get("grade") in ("A", "B")
    ):
        if cov.get("grade") in ("A", "B"):
            cov = dict(cov)
            cov["grade"] = "C"
            notes = cov.get("notes") or ""
            extra = "grade capped at C (low match confidence / needs_review)"
            cov["notes"] = f"{notes}; {extra}".strip("; ") if notes else extra
    card["coverage"] = cov
    return card
