"""Shared qualitative/numeric H2H + strength normalization (FEH PR1)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

H2HPolarity = Literal["positive", "negative", "mixed", "unknown", "unchecked"]

_POSITIVE = frozenset(
    {
        "positive",
        "pos",
        "strong",
        "leads",
        "dominates",
        "advantage",
        "favours",
        "favors",
        "edge_pos",
        "plus",
    }
)
_NEGATIVE = frozenset(
    {
        "negative",
        "neg",
        "weak",
        "never beaten",
        "winless",
        "disadvantage",
        "against",
        "edge_neg",
        "minus",
    }
)
_MIXED = frozenset(
    {
        "mixed",
        "mixed_competitive",
        "competitive",
        "even",
        "neutral",
        "close",
        "balanced",
        "toss_up",
        "tossup",
        "coin_flip",
    }
)


@dataclass(frozen=True)
class H2HNorm:
    """Normalized H2H / edge polarity (attribute access for tests)."""

    checked: bool
    polarity: H2HPolarity
    edge_numeric: float | None
    positive: bool
    negative: bool
    mixed: bool
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "polarity": self.polarity,
            "edge_numeric": self.edge_numeric,
            "edge": self.edge_numeric,
            "positive": self.positive,
            "negative": self.negative,
            "mixed": self.mixed,
            "summary": self.summary,
        }


def _polarity_from_string(raw: str) -> H2HPolarity:
    s = raw.strip().lower().replace("-", "_").replace(" ", "_")
    s_space = raw.strip().lower()
    if not s:
        return "unknown"
    if s in _POSITIVE or s_space in _POSITIVE:
        return "positive"
    if s in _NEGATIVE or s_space in _NEGATIVE:
        return "negative"
    if s in _MIXED or s_space in _MIXED:
        return "mixed"
    # partial contains (mixed_competitive etc.)
    if "mixed" in s or "competitive" in s or s in ("even", "neutral", "close"):
        return "mixed"
    if any(p in s_space for p in ("never beaten", "winless", "0-")):
        return "negative"
    if any(p in s for p in ("positive", "dominat", "leads")):
        return "positive"
    if any(p in s for p in ("negative", "weak")):
        return "negative"
    return "unknown"


def normalize_strength(raw: Any) -> tuple[float | None, H2HPolarity]:
    """
    Map signal strength / edge to (numeric_or_None, polarity).

    Rules (normative):
      numeric > 0  → positive (float clamped to abs≤1 for signals)
      numeric < 0  → negative
      numeric == 0 → mixed
      str positive synonyms → positive
      str negative synonyms → negative
      str mixed* / competitive / even / neutral → mixed  # NOT positive
      empty/missing → unknown
    """
    if raw is None:
        return None, "unknown"
    if isinstance(raw, bool):
        return (0.7 if raw else -0.7), ("positive" if raw else "negative")
    if isinstance(raw, (int, float)):
        v = float(raw)
        if v > 0:
            return min(1.0, v), "positive"
        if v < 0:
            return max(-1.0, v), "negative"
        return 0.0, "mixed"
    s = str(raw).strip()
    if not s:
        return None, "unknown"
    # numeric string?
    try:
        v = float(s)
        if v > 0:
            return min(1.0, v), "positive"
        if v < 0:
            return max(-1.0, v), "negative"
        return 0.0, "mixed"
    except (TypeError, ValueError):
        pass
    pol = _polarity_from_string(s)
    if pol == "positive":
        return 0.7, "positive"
    if pol == "negative":
        return -0.7, "negative"
    if pol == "mixed":
        return 0.0, "mixed"
    return None, "unknown"


def _from_edge_and_meta(
    *,
    edge: Any,
    checked: bool,
    summary: str,
) -> H2HNorm:
    num, pol = normalize_strength(edge)
    if edge is None and not summary and not checked:
        return H2HNorm(
            checked=False,
            polarity="unchecked",
            edge_numeric=None,
            positive=False,
            negative=False,
            mixed=False,
            summary="",
        )
    if pol == "unknown" and (checked or summary or edge is not None):
        # checked without parseable edge → unknown (not positive)
        polarity: H2HPolarity = "unknown"
    elif edge is None and not checked and not summary:
        polarity = "unchecked"
    else:
        polarity = pol if pol != "unknown" else "unknown"

    positive = polarity == "positive"
    negative = polarity == "negative"
    mixed = polarity == "mixed"
    is_checked = bool(checked or summary or edge is not None or polarity not in ("unchecked",))
    return H2HNorm(
        checked=is_checked,
        polarity=polarity if is_checked or polarity != "unknown" else "unchecked",
        edge_numeric=num,
        positive=positive,
        negative=negative,
        mixed=mixed,
        summary=summary or "",
    )


def normalize_h2h(ev: Any) -> H2HNorm:
    """
    Normalize H2H edge from:
      - bare string/number edge (e.g. \"mixed_competitive\")
      - h2h dict {checked, edge, summary}
      - full evidence pack with nested h2h

    Smith pack edge \"mixed_competitive\" → polarity=mixed, positive=False, negative=False.
    """
    if ev is None:
        return H2HNorm(
            checked=False,
            polarity="unchecked",
            edge_numeric=None,
            positive=False,
            negative=False,
            mixed=False,
            summary="",
        )

    # Bare edge string / number
    if not isinstance(ev, dict):
        return _from_edge_and_meta(edge=ev, checked=True, summary="")

    # Full pack or h2h dict
    if "h2h" in ev and isinstance(ev.get("h2h"), (dict, str, int, float)):
        h = ev.get("h2h")
    else:
        h = ev

    if not isinstance(h, dict):
        return _from_edge_and_meta(edge=h, checked=True, summary="")

    checked = bool(h.get("checked") or h.get("summary") or h.get("edge") is not None)
    summary = str(h.get("summary") or "")
    edge = h.get("edge")
    result = _from_edge_and_meta(edge=edge, checked=checked, summary=summary)

    # Blob text fallbacks (never-beaten etc.) only when edge empty
    if result.polarity in ("unknown", "unchecked") and not result.positive and not result.negative:
        blob = " ".join(
            [
                summary,
                str(h.get("record") or ""),
                str(ev.get("summary") or "") if isinstance(ev, dict) else "",
            ]
        ).lower()
        if blob.strip():
            if any(
                tok in blob
                for tok in (
                    "never beaten",
                    "negative h2h",
                    "winless vs",
                    "lost all",
                    "0-5",
                    "0-4",
                    "0-3",
                )
            ):
                return H2HNorm(
                    checked=True,
                    polarity="negative",
                    edge_numeric=-0.7,
                    positive=False,
                    negative=True,
                    mixed=False,
                    summary=summary,
                )
            if any(
                tok in blob
                for tok in (
                    "positive h2h",
                    "leads h2h",
                    "dominates",
                    "h2h edge",
                )
            ):
                return H2HNorm(
                    checked=True,
                    polarity="positive",
                    edge_numeric=0.7,
                    positive=True,
                    negative=False,
                    mixed=False,
                    summary=summary,
                )
            if any(tok in blob for tok in ("competitive", "mixed", "even ", "close contest")):
                return H2HNorm(
                    checked=True,
                    polarity="mixed",
                    edge_numeric=0.0,
                    positive=False,
                    negative=False,
                    mixed=True,
                    summary=summary,
                )
            # Any h2h prose → checked unknown
            if "h2h" in blob or "head to head" in blob or "head-to-head" in blob or "matchup" in blob:
                return H2HNorm(
                    checked=True,
                    polarity="unknown",
                    edge_numeric=None,
                    positive=False,
                    negative=False,
                    mixed=False,
                    summary=summary,
                )
    return result
