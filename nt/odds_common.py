"""
Shared odds / evidence key helpers (Phase 4–5).

Used by attach_evidence, research write-pack, and collectors where useful.
Keeps selection/match soft-matching consistent across the pipeline.
"""
from __future__ import annotations

import re


def normalize_match_key(match: str | None) -> str:
    """Soft identity for match names (vs / hyphen, case, whitespace)."""
    m = (match or "").strip().lower()
    m = m.replace(" – ", " vs ").replace(" — ", " vs ").replace(" - ", " vs ")
    m = re.sub(r"\s+", " ", m)
    return m


def normalize_selection_key(selection: str | None) -> str:
    """
    Soft identity for selections so packs attach across spelling variants.

    Examples:
      ``Vinner: Merida, Daniel`` ↔ ``Merida, Daniel to Win``
      ``BTTS Ja`` ↔ ``Begge lag scorer: Ja`` (partial; still exact on core tokens)
    """
    s = (selection or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    # Common moneyline prefixes/suffixes
    for prefix in (
        "vinner (inkludert overtid/straffer):",
        "vinner (inkludert ekstra innings):",
        "vinner:",
        "vinner ",
        "winner:",
        "winner ",
        "moneyline:",
    ):
        if s.startswith(prefix):
            s = s[len(prefix) :].strip()
            break
    for suffix in (" to win", " to win.", " vinner"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    # Normalize punctuation lightly
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"\s*:\s*", ": ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def evidence_pair_key(match: str | None, selection: str | None) -> tuple[str, str]:
    return normalize_match_key(match), normalize_selection_key(selection)


def fnum(x: object) -> float | None:
    """Parse odds/number from str/float (comma decimal OK)."""
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None
