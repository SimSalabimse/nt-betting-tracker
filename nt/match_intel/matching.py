"""Alias + fuzzy name match helpers for free-source page resolution."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from nt.fetchers.names import name_match_score, norm_name, pair_match_score, split_match
from nt.odds_common import normalize_match_key

# Cap fuzzy distance / require high Jaccard — design §1.6
FUZZY_JACCARD_MIN = 0.85
# Max Levenshtein-style edit distance as fraction of longer string (cap)
MAX_EDIT_FRACTION = 0.15


def fuzzy_token_jaccard(a: str, b: str) -> float:
    """Token Jaccard on normalized name tokens (stopwords stripped lightly)."""
    stop = {"fc", "fk", "if", "bk", "sc", "ac", "cf", "the", "club", "team"}
    ta = set(norm_name(a).split()) - stop
    tb = set(norm_name(b).split()) - stop
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Cap length to avoid pathological blow-ups
    if len(a) > 80 or len(b) > 80:
        a, b = a[:80], b[:80]
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def edit_distance_ok(a: str, b: str, *, max_fraction: float = MAX_EDIT_FRACTION) -> bool:
    """True if edit distance ≤ max_fraction of longer string length."""
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb:
        return False
    dist = _levenshtein(na, nb)
    longer = max(len(na), len(nb))
    if longer == 0:
        return False
    return (dist / longer) <= max_fraction


def load_aliases(path: Path | str | None) -> list[dict[str, Any]]:
    """Load operator-maintained match_aliases.json; empty list if missing."""
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    aliases = data.get("aliases") if isinstance(data, dict) else None
    if isinstance(aliases, list):
        return [x for x in aliases if isinstance(x, dict)]
    return []


def match_confidence(
    odds_match: str,
    page_title_or_teams: str,
    *,
    aliases: list[dict[str, Any]] | None = None,
    sport: str | None = None,
) -> tuple[str, float]:
    """
    Return (confidence_label, score).

    Labels: exact | alias | fuzzy | none
    """
    a = normalize_match_key(odds_match)
    b = normalize_match_key(page_title_or_teams)
    if a and b and a == b:
        return "exact", 1.0

    # Side-aware exact via token pair
    oh, oa = split_match(odds_match)
    ph, pa = split_match(page_title_or_teams)
    if oh and oa and ph and pa:
        pair = pair_match_score(oh, oa, ph, pa)
        if pair >= 0.99:
            return "exact", pair

    for row in aliases or []:
        if sport and row.get("sport") and str(row["sport"]).lower() != str(sport).lower():
            continue
        odds_alias = str(row.get("odds_match") or row.get("match") or "")
        if odds_alias and normalize_match_key(odds_alias) == a:
            return "alias", 0.95
        slug = str(row.get("flashscore_slug") or row.get("slug") or "")
        if slug and slug.replace("-", " ") in norm_name(page_title_or_teams):
            if odds_alias and normalize_match_key(odds_alias) == a:
                return "alias", 0.95

    # Fuzzy: token Jaccard on full string + per-side
    j = fuzzy_token_jaccard(odds_match, page_title_or_teams)
    if oh and oa and ph and pa:
        j_sides = (
            fuzzy_token_jaccard(oh, ph) + fuzzy_token_jaccard(oa, pa)
        ) / 2.0
        j_swap = (
            fuzzy_token_jaccard(oh, pa) + fuzzy_token_jaccard(oa, ph)
        ) / 2.0
        j = max(j, j_sides, j_swap * 0.95)
    if j >= FUZZY_JACCARD_MIN:
        # Cap: also require edit distance not wild on joined names
        if edit_distance_ok(odds_match, page_title_or_teams, max_fraction=0.35) or j >= 0.92:
            return "fuzzy", round(j, 4)
    # name_match_score average as last resort
    if oh and oa and ph and pa:
        score = pair_match_score(oh, oa, ph, pa)
        if score >= FUZZY_JACCARD_MIN:
            return "fuzzy", round(score, 4)

    return "none", round(j, 4)


def resolve_match(
    odds_match: str,
    candidates: list[str],
    *,
    aliases: list[dict[str, Any]] | None = None,
    sport: str | None = None,
) -> dict[str, Any]:
    """
    Pick best candidate page title / team pair.

    Returns dict: matched, confidence, score, candidate
    """
    best: dict[str, Any] = {
        "matched": False,
        "confidence": "none",
        "score": 0.0,
        "candidate": None,
    }
    order = {"exact": 3, "alias": 2, "fuzzy": 1, "none": 0}
    for cand in candidates:
        conf, score = match_confidence(
            odds_match, cand, aliases=aliases, sport=sport
        )
        if order.get(conf, 0) > order.get(best["confidence"], 0) or (
            conf == best["confidence"] and score > float(best["score"])
        ):
            best = {
                "matched": conf != "none",
                "confidence": conf,
                "score": score,
                "candidate": cand,
            }
    return best


def team_tokens(name: str) -> list[str]:
    """Normalized token list for debugging / tests."""
    return [t for t in re.split(r"\s+", norm_name(name)) if t]
