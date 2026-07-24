"""Pre-Filter Checklist schema v1 — fail-closed for place when incomplete."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SideLean = Literal[
    "favourite",
    "underdog",
    "even",
    "unknown",
    "n_a",
    "player_a",
    "player_b",
    "home",
    "away",
]
Verdict = Literal[
    "positive",
    "negative",
    "mixed",
    "unknown",
    "n_a",
    "even",
    "unchecked",
]

# Explicitly excluded from anti-soft condition A (documented for callers)
NON_MATCHUP_FACTOR_IDS = frozenset(
    {
        "recent_form",
        "form",
        "checkout_scoring",
        "avg_checkout",
        "format_stage",
        "ranking_seed",
        "ranking_strength",
        "ranking_form",
    }
)


@dataclass
class ChecklistAnswers:
    """Checklist schema_version = 1 (design §3)."""

    schema_version: int = 1
    higher_ranked_side: SideLean = "unknown"  # Q1
    ranking_confidence: float = 0.0
    better_form_side: SideLean = "unknown"  # Q2
    form_confidence: float = 0.0
    h2h_verdict: Verdict = "unknown"  # Q3
    h2h_summary: str = ""
    natural_market_hint: str = ""  # Q4
    natural_markets: list[str] = field(default_factory=list)
    underdog_supported_by_evidence: bool = False  # Q5 — NOT sufficient for anti-soft A
    underdog_support_reason: str = ""
    why_this_side_not_opposite: str = ""
    strongest_positive: str = ""
    strongest_negative: str = ""
    primary_factors_used: list[str] = field(default_factory=list)
    complete: bool = False
    incomplete_reasons: list[str] = field(default_factory=list)
    inferred: bool = False  # True if synthesized from pack signals

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "higher_ranked_side": self.higher_ranked_side,
            "ranking_confidence": self.ranking_confidence,
            "better_form_side": self.better_form_side,
            "form_confidence": self.form_confidence,
            "h2h_verdict": self.h2h_verdict,
            "h2h_summary": self.h2h_summary,
            "natural_market_hint": self.natural_market_hint,
            "natural_markets": list(self.natural_markets),
            "underdog_supported_by_evidence": self.underdog_supported_by_evidence,
            "underdog_support_reason": self.underdog_support_reason,
            "why_this_side_not_opposite": self.why_this_side_not_opposite,
            "strongest_positive": self.strongest_positive,
            "strongest_negative": self.strongest_negative,
            "primary_factors_used": list(self.primary_factors_used),
            "complete": self.complete,
            "incomplete_reasons": list(self.incomplete_reasons),
            "inferred": self.inferred,
        }


def _norm_lean(raw: Any) -> SideLean:
    if raw is None:
        return "unknown"
    s = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "fav": "favourite",
        "favorite": "favourite",
        "favoured": "favourite",
        "favored": "favourite",
        "dog": "underdog",
        "ud": "underdog",
        "under": "underdog",
        "na": "n_a",
        "n/a": "n_a",
        "none": "n_a",
        "tie": "even",
        "neutral": "even",
        "unclear": "unknown",
        "playera": "player_a",
        "playerb": "player_b",
    }
    s = aliases.get(s, s)
    allowed = {
        "favourite",
        "underdog",
        "even",
        "unknown",
        "n_a",
        "player_a",
        "player_b",
        "home",
        "away",
    }
    return s if s in allowed else "unknown"  # type: ignore[return-value]


def _norm_verdict(raw: Any) -> Verdict:
    if raw is None:
        return "unknown"
    s = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if s in ("pos", "positive", "strong", "leads", "dominates"):
        return "positive"
    if s in ("neg", "negative", "weak", "winless"):
        return "negative"
    if s in ("mixed", "mixed_competitive", "competitive", "even", "neutral", "close"):
        return "mixed"
    if s in ("n_a", "na", "n/a", "none"):
        return "n_a"
    if s in ("unchecked",):
        return "unchecked"
    if s in ("unknown", "unclear", ""):
        return "unknown"
    return "unknown"


def _strength_to_lean_for_dog(
    strength: Any,
    *,
    signal_id: str,
) -> tuple[SideLean, float]:
    """
    Map signal strength relative to the *selection* (typically the underdog pack).

    Positive strength on ranking_seed for a dog pack often means "supports selection"
    in pack convention — but ranking_seed note "Price higher ranked" uses strength
    negative for the dog. We treat:
      positive → underdog edge (supports selection side)
      negative → favourite edge
      mixed → even
    """
    from nt.evidence_hierarchy.h2h_normalize import normalize_strength

    _num, pol = normalize_strength(strength)
    conf = 0.7 if pol in ("positive", "negative") else (0.5 if pol == "mixed" else 0.0)
    if pol == "positive":
        # ranking negative for dog is more common; form/checkout positive = dog
        if signal_id in ("ranking_seed", "ranking_strength", "ranking_form"):
            return "underdog", conf  # positive rank for selection = dog higher? rare
        return "underdog", conf
    if pol == "negative":
        if signal_id in ("ranking_seed", "ranking_strength", "ranking_form"):
            return "favourite", conf  # negative rank on dog pack = fav higher ranked
        return "favourite", conf
    if pol == "mixed":
        return "even", 0.5
    return "unknown", 0.0


def checklist_completeness(cl: ChecklistAnswers) -> tuple[bool, list[str]]:
    """
    Completeness (fail-closed for place):
      Q1–Q3 not unknown (or N/A+reason);
      Q4 list or \"none\"+reason;
      Q5 present+reason≥24;
      why-side≥40; +/− ≥20; ≥1 valid primary factor id.
    """
    reasons: list[str] = []

    # Q1 ranking
    if cl.higher_ranked_side in ("unknown", ""):
        reasons.append("Q1 higher_ranked_side unknown")
    elif cl.higher_ranked_side == "n_a" and not (cl.strongest_negative or cl.h2h_summary):
        reasons.append("Q1 n_a without reason")

    # Q2 form
    if cl.better_form_side in ("unknown", ""):
        reasons.append("Q2 better_form_side unknown")
    elif cl.better_form_side == "n_a" and not cl.underdog_support_reason:
        reasons.append("Q2 n_a without reason")

    # Q3 H2H
    if cl.h2h_verdict in ("unknown", "unchecked", ""):
        reasons.append("Q3 h2h_verdict unknown")
    elif cl.h2h_verdict == "n_a" and len((cl.h2h_summary or "").strip()) < 10:
        reasons.append("Q3 n_a without summary")

    # Q4 natural markets
    nm = [str(x).strip() for x in (cl.natural_markets or []) if str(x).strip()]
    hint = (cl.natural_market_hint or "").strip().lower()
    if not nm and hint not in ("none", "n/a", "na", "n_a") and len(hint) < 4:
        reasons.append("Q4 natural_markets empty without none+reason")

    # Q5 underdog support claim + reason
    if len((cl.underdog_support_reason or "").strip()) < 24:
        reasons.append("Q5 underdog_support_reason < 24 chars")

    why = (cl.why_this_side_not_opposite or "").strip()
    if len(why) < 40:
        reasons.append("why_this_side_not_opposite < 40 chars")

    if len((cl.strongest_positive or "").strip()) < 20:
        reasons.append("strongest_positive < 20 chars")
    if len((cl.strongest_negative or "").strip()) < 20:
        reasons.append("strongest_negative < 20 chars")

    factors = [str(x).strip() for x in (cl.primary_factors_used or []) if str(x).strip()]
    if not factors:
        reasons.append("primary_factors_used empty")

    return (len(reasons) == 0, reasons)


def load_checklist_from_pack(
    ev: dict[str, Any] | None,
    *,
    h2h: dict[str, Any] | None = None,
    primary_factor_ids: list[str] | None = None,
) -> ChecklistAnswers:
    """
    Load FEH checklist from pack.feh_checklist / pack.checklist (schema v1),
    else infer structured leans from signals + h2h for side/anti-soft votes.

    Inferred checklists are almost never `complete` (honesty: free text missing).
    """
    ev = ev or {}
    raw = ev.get("feh_checklist")
    if not isinstance(raw, dict):
        raw = ev.get("checklist") if isinstance(ev.get("checklist"), dict) else {}

    # Detect FEH schema vs legacy boolean checklist keys
    is_feh_schema = any(
        k in raw
        for k in (
            "higher_ranked_side",
            "better_form_side",
            "h2h_verdict",
            "why_this_side_not_opposite",
            "schema_version",
            "underdog_supported_by_evidence",
        )
    )

    if is_feh_schema:
        cl = ChecklistAnswers(
            schema_version=int(raw.get("schema_version") or 1),
            higher_ranked_side=_norm_lean(raw.get("higher_ranked_side")),
            ranking_confidence=float(raw.get("ranking_confidence") or 0.0),
            better_form_side=_norm_lean(raw.get("better_form_side")),
            form_confidence=float(raw.get("form_confidence") or 0.0),
            h2h_verdict=_norm_verdict(raw.get("h2h_verdict")),
            h2h_summary=str(raw.get("h2h_summary") or ""),
            natural_market_hint=str(raw.get("natural_market_hint") or ""),
            natural_markets=[str(x) for x in (raw.get("natural_markets") or [])],
            underdog_supported_by_evidence=bool(
                raw.get("underdog_supported_by_evidence")
            ),
            underdog_support_reason=str(raw.get("underdog_support_reason") or ""),
            why_this_side_not_opposite=str(
                raw.get("why_this_side_not_opposite") or ""
            ),
            strongest_positive=str(raw.get("strongest_positive") or ""),
            strongest_negative=str(raw.get("strongest_negative") or ""),
            primary_factors_used=[
                str(x) for x in (raw.get("primary_factors_used") or [])
            ],
            inferred=False,
        )
        # Align h2h_verdict with normalize_h2h when present
        if h2h and h2h.get("checked"):
            if h2h.get("positive"):
                cl.h2h_verdict = "positive"
            elif h2h.get("negative"):
                cl.h2h_verdict = "negative"
            elif h2h.get("mixed"):
                cl.h2h_verdict = "mixed"
            if not cl.h2h_summary:
                cl.h2h_summary = str(h2h.get("summary") or "")
        ok, reasons = checklist_completeness(cl)
        cl.complete = ok
        cl.incomplete_reasons = reasons
        return cl

    # Infer from signals + h2h (legacy packs like Smith)
    return infer_checklist_from_pack(
        ev, h2h=h2h, primary_factor_ids=primary_factor_ids
    )


def infer_checklist_from_pack(
    ev: dict[str, Any] | None,
    *,
    h2h: dict[str, Any] | None = None,
    primary_factor_ids: list[str] | None = None,
) -> ChecklistAnswers:
    """Synthesize Q1–Q3 leans from structured signals; free-text fields stay empty."""
    from nt.evidence_hierarchy.h2h_normalize import normalize_h2h, normalize_strength

    ev = ev or {}
    if h2h is None:
        norm = normalize_h2h(ev)
        h2h = norm.to_dict()

    signals = ev.get("signals") if isinstance(ev.get("signals"), dict) else {}
    rank_lean: SideLean = "unknown"
    rank_conf = 0.0
    form_lean: SideLean = "unknown"
    form_conf = 0.0
    factors: list[str] = []
    strongest_pos = ""
    strongest_neg = ""

    for sid, sig in signals.items():
        if not isinstance(sig, dict) or not sig.get("filled"):
            continue
        factors.append(str(sid))
        note = str(sig.get("note") or "")
        _num, pol = normalize_strength(sig.get("strength"))
        if pol == "positive" and not strongest_pos:
            strongest_pos = note or sid
        if pol == "negative" and not strongest_neg:
            strongest_neg = note or sid

        if sid in ("ranking_seed", "ranking_strength", "ranking_form"):
            rank_lean, rank_conf = _strength_to_lean_for_dog(
                sig.get("strength"), signal_id=str(sid)
            )
            # Note-based override: "higher ranked" favourite language
            note_l = note.lower()
            if any(
                tok in note_l
                for tok in (
                    "higher ranked",
                    "price higher",
                    "favourite ranked",
                    "fav ranked",
                    "seed advantage",
                )
            ):
                rank_lean, rank_conf = "favourite", max(rank_conf, 0.7)
        elif sid in ("recent_form", "form", "xg_form", "frame_form"):
            form_lean, form_conf = _strength_to_lean_for_dog(
                sig.get("strength"), signal_id=str(sid)
            )

    # H2H verdict
    if h2h.get("positive"):
        h2h_v: Verdict = "positive"
    elif h2h.get("negative"):
        h2h_v = "negative"
    elif h2h.get("mixed"):
        h2h_v = "mixed"
    elif h2h.get("checked"):
        h2h_v = "unknown"
    else:
        h2h_v = "unchecked"

    if primary_factor_ids:
        # Prefer card primary ids that appear in pack
        pf = [f for f in factors if f in set(primary_factor_ids)] or factors[:3]
    else:
        pf = factors[:5]

    cl = ChecklistAnswers(
        higher_ranked_side=rank_lean,
        ranking_confidence=rank_conf,
        better_form_side=form_lean,
        form_confidence=form_conf,
        h2h_verdict=h2h_v,
        h2h_summary=str(h2h.get("summary") or ""),
        natural_market_hint="",
        natural_markets=[],
        underdog_supported_by_evidence=False,
        underdog_support_reason="",
        why_this_side_not_opposite="",
        strongest_positive=strongest_pos[:120],
        strongest_negative=strongest_neg[:120],
        primary_factors_used=pf,
        inferred=True,
    )
    ok, reasons = checklist_completeness(cl)
    cl.complete = ok
    cl.incomplete_reasons = reasons
    return cl
