"""
Settlement predictability / variance taxonomy + learning_weight.

Applied to every settled bet (not only process_error). Pure helpers —
no I/O. Used by PostSettlementPacket, settlement_review, learning, CS.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

PREDICTABILITY = frozenset(
    {
        "highly_predictable",
        "moderately_predictable",
        "weakly_predictable",
        "unpredictable_from_available_info",
    }
)

VARIANCE_CLASS = frozenset(
    {
        "systematic_script_form",
        "research_process_miss",
        "model_error",
        "one_off_injury_late",
        "one_off_referee",
        "true_randomness",
        "unknown",
    }
)

# Legacy settlement_review / notes labels → new variance_class
_LEGACY_VARIANCE_MAP: dict[str, str] = {
    "process_error": "research_process_miss",
    "research_miss": "research_process_miss",
    "miss": "research_process_miss",
    "research_process_miss": "research_process_miss",
    "skill": "systematic_script_form",
    "edge": "systematic_script_form",
    "expected": "systematic_script_form",
    "process": "systematic_script_form",
    "systematic_script_form": "systematic_script_form",
    "variance": "true_randomness",
    "luck": "true_randomness",
    "noise": "true_randomness",
    "random": "true_randomness",
    "true_randomness": "true_randomness",
    "model": "model_error",
    "model_error": "model_error",
    "mixed": "unknown",
    "neutral": "unknown",
    "unknown": "unknown",
    "one_off_injury_late": "one_off_injury_late",
    "one_off_referee": "one_off_referee",
    "one_off": "one_off_injury_late",
}

_VARIANCE_BASE: dict[str, float] = {
    "systematic_script_form": 1.0,
    "research_process_miss": 0.95,
    "model_error": 0.65,
    "one_off_injury_late": 0.10,
    "one_off_referee": 0.10,
    "true_randomness": 0.05,
    "unknown": 0.40,
}

_PRED_MULT: dict[str, float] = {
    "highly_predictable": 1.0,
    "moderately_predictable": 0.75,
    "weakly_predictable": 0.45,
    "unpredictable_from_available_info": 0.20,
}

# Process-error class (gates / phase health / closed-loop)
PROCESS_ERROR_CLASSES = frozenset(
    {
        "process_error",  # legacy stored value
        "research_process_miss",
    }
)

_INJURY_LATE_RE = re.compile(
    r"\b("
    r"late\s+injury|injury\s+late|late\s+scratch|late\s+withdraw|"
    r"game[-\s]?time\s+decision|late\s+out|ruled\s+out\s+late|"
    r"warm[-\s]?up\s+injury|last[-\s]?minute\s+injury|"
    r"red\s+card\s+late|late\s+red|sent\s+off\s+early|"
    r"sudden\s+injury|unexpected\s+absence"
    r")\b",
    re.I,
)
_REFEREE_RE = re.compile(
    r"\b("
    r"referee|ref\s+decision|bad\s+call|controversial\s+penalty|"
    r"officiating|var\s+howler|soft\s+penalty\s+gift|"
    r"referee\s+error|ref\s+error"
    r")\b",
    re.I,
)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def normalize_predictability(val: Any) -> str | None:
    s = str(val or "").strip().lower()
    if not s:
        return None
    aliases = {
        "high": "highly_predictable",
        "highly": "highly_predictable",
        "moderate": "moderately_predictable",
        "medium": "moderately_predictable",
        "weak": "weakly_predictable",
        "low": "weakly_predictable",
        "unpredictable": "unpredictable_from_available_info",
        "unknown_info": "unpredictable_from_available_info",
    }
    s = aliases.get(s, s)
    return s if s in PREDICTABILITY else None


def normalize_variance_class(val: Any) -> str | None:
    s = str(val or "").strip().lower()
    if not s:
        return None
    mapped = _LEGACY_VARIANCE_MAP.get(s, s)
    return mapped if mapped in VARIANCE_CLASS else None


def is_process_error_class(variance_class: Any) -> bool:
    s = str(variance_class or "").strip().lower()
    if s in PROCESS_ERROR_CLASSES:
        return True
    mapped = _LEGACY_VARIANCE_MAP.get(s)
    return mapped in PROCESS_ERROR_CLASSES or mapped == "research_process_miss"


def compute_learning_weight(
    predictability: str | None,
    variance_class: str | None,
) -> float:
    """
    weight = clamp(base[variance_class] * pred_mult[predictability], 0, 1)

    Missing / invalid inputs fall back to unknown × weakly_predictable (~0.18).
    """
    vc = normalize_variance_class(variance_class) or "unknown"
    pred = normalize_predictability(predictability) or "weakly_predictable"
    base = float(_VARIANCE_BASE.get(vc, _VARIANCE_BASE["unknown"]))
    mult = float(_PRED_MULT.get(pred, _PRED_MULT["weakly_predictable"]))
    return round(_clamp01(base * mult), 4)


def map_legacy_labels(
    *,
    variance_tag: str | None = None,
    variance_class: str | None = None,
    research_quality_retro: str | None = None,
    label: str | None = None,
) -> dict[str, str]:
    """
    Map legacy feel/variance_tag / old variance_class labels into new taxonomy.
    Does not invent notes — only normalizes known enums.
    """
    raw = (
        variance_class
        or label
        or variance_tag
        or ""
    )
    vc = normalize_variance_class(raw)
    retro = str(research_quality_retro or "").strip().lower()

    if vc is None:
        if retro in ("poor", "wrong", "miss"):
            vc = "research_process_miss"
        else:
            vc = "unknown"

    # Predictability defaults from class + retro
    if vc == "research_process_miss":
        if retro in ("poor", "wrong", "miss"):
            pred = "moderately_predictable"
        else:
            pred = "highly_predictable"
    elif vc == "systematic_script_form":
        if retro in ("good", "solid", "correct", "ok"):
            pred = "highly_predictable"
        else:
            pred = "moderately_predictable"
    elif vc in ("one_off_injury_late", "one_off_referee", "true_randomness"):
        pred = "unpredictable_from_available_info"
    elif vc == "model_error":
        pred = "moderately_predictable"
    else:
        pred = "weakly_predictable"

    return {"variance_class": vc, "predictability": pred}


def auto_classify_taxonomy(
    item: dict[str, Any] | None = None,
    *,
    notes: str | None = None,
    variance_tag: str | None = None,
    research_quality_retro: str | None = None,
    variance_class: str | None = None,
    predictability: str | None = None,
    classified_by: str = "auto",
) -> dict[str, Any]:
    """
    Best-effort taxonomy for settle / backfill.

    Heuristics:
    - notes mention late injury / red → one_off_injury_late (or referee)
    - research_quality_retro poor + process_error tag → research_process_miss
      + moderately/highly predictable
    - else unknown + weakly_predictable (weight ~0.18)
    Explicit item fields always win when valid.
    """
    item = item or {}
    blob_parts = [
        str(notes or ""),
        str(item.get("notes") or ""),
        str(item.get("settlement_notes") or ""),
        str(item.get("key_events") or ""),
        str(item.get("classification_notes") or ""),
        str(item.get("variance_detail") or ""),
    ]
    blob = " ".join(blob_parts)

    tag = str(
        variance_tag
        or item.get("variance_tag")
        or item.get("feel")
        or ""
    ).strip().lower()
    retro = str(
        research_quality_retro
        or item.get("research_quality_retro")
        or item.get("research_retro")
        or ""
    ).strip().lower()
    explicit_vc = normalize_variance_class(
        variance_class or item.get("variance_class")
    )
    explicit_pred = normalize_predictability(
        predictability or item.get("predictability")
    )

    notes_out = str(item.get("classification_notes") or "").strip()
    reason_bits: list[str] = []

    if explicit_vc:
        vc = explicit_vc
        reason_bits.append(f"explicit variance_class={vc}")
    elif _INJURY_LATE_RE.search(blob):
        vc = "one_off_injury_late"
        reason_bits.append("notes: late injury / red / scratch")
    elif _REFEREE_RE.search(blob) and any(
        k in blob.lower() for k in ("bad", "error", "howler", "controversial", "soft")
    ):
        vc = "one_off_referee"
        reason_bits.append("notes: referee one-off")
    elif tag in ("process_error", "research_miss", "miss") or retro in (
        "poor",
        "wrong",
        "miss",
    ):
        vc = "research_process_miss"
        reason_bits.append(f"process tag/retro tag={tag or '-'} retro={retro or '-'}")
    elif tag in ("variance", "luck", "noise", "random"):
        vc = "true_randomness"
        reason_bits.append(f"variance tag={tag}")
    elif tag in ("skill", "edge", "expected", "process"):
        vc = "systematic_script_form"
        reason_bits.append(f"skill/expected tag={tag}")
    elif tag in ("model", "model_error"):
        vc = "model_error"
        reason_bits.append("model tag")
    else:
        # Fall back via legacy map if any residual label present
        mapped = map_legacy_labels(
            variance_tag=tag or None,
            research_quality_retro=retro or None,
            variance_class=str(item.get("variance_class") or "") or None,
        )
        vc = mapped["variance_class"]
        if vc == "unknown":
            reason_bits.append("default unknown")
        else:
            reason_bits.append(f"legacy map → {vc}")

    if explicit_pred:
        pred = explicit_pred
        reason_bits.append(f"explicit predictability={pred}")
    elif vc == "research_process_miss":
        # poor retro + process → moderately; bare process tag → highly (script was knowable)
        if retro in ("poor", "wrong", "miss"):
            pred = "moderately_predictable"
        else:
            pred = "highly_predictable"
    elif vc == "systematic_script_form":
        if retro in ("good", "solid", "correct"):
            pred = "highly_predictable"
        elif retro in ("ok",):
            pred = "moderately_predictable"
        else:
            pred = "moderately_predictable"
    elif vc in ("one_off_injury_late", "one_off_referee", "true_randomness"):
        pred = "unpredictable_from_available_info"
    elif vc == "model_error":
        pred = "moderately_predictable"
    else:
        # Default backfill: unknown + weakly → ~0.18
        pred = "weakly_predictable"

    weight = compute_learning_weight(pred, vc)
    if not notes_out:
        notes_out = "; ".join(reason_bits)[:240]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "predictability": pred,
        "variance_class": vc,
        "learning_weight": weight,
        "classification_notes": notes_out,
        "classified_by": str(classified_by or "auto"),
        "classified_at": str(item.get("classified_at") or now),
    }


def taxonomy_from_item(
    item: dict[str, Any],
    *,
    classified_by: str = "auto",
) -> dict[str, Any]:
    """Resolve taxonomy for a settle item / packet dict."""
    # If learning_weight already set with full fields, still recompute weight
    # from classes when both present (authoritative formula).
    tax = auto_classify_taxonomy(item, classified_by=classified_by)
    if item.get("learning_weight") is not None and item.get("variance_class") and item.get(
        "predictability"
    ):
        # Respect explicit classes; recompute weight from formula only
        pred = normalize_predictability(item.get("predictability")) or tax["predictability"]
        vc = normalize_variance_class(item.get("variance_class")) or tax["variance_class"]
        tax = {
            "predictability": pred,
            "variance_class": vc,
            "learning_weight": compute_learning_weight(pred, vc),
            "classification_notes": str(
                item.get("classification_notes") or tax["classification_notes"]
            )[:240],
            "classified_by": str(item.get("classified_by") or classified_by),
            "classified_at": str(item.get("classified_at") or tax["classified_at"]),
        }
    return tax


def merge_taxonomy_into(target: dict[str, Any], tax: dict[str, Any]) -> dict[str, Any]:
    """Copy taxonomy keys onto target dict (mutates and returns target)."""
    for k in (
        "predictability",
        "variance_class",
        "learning_weight",
        "classification_notes",
        "classified_by",
        "classified_at",
    ):
        if k in tax and tax[k] is not None:
            target[k] = tax[k]
    return target
