"""
P0: PostSettlementPacket — structured settlement forensics.

Fail-closed when variance_tag=process_error or research_quality_retro=poor:
critical fields required before settle writes the ledger.

Every settled bet also carries predictability / variance_class / learning_weight
taxonomy (soft-required; auto-filled from retro/tag heuristics when absent).
"""
from __future__ import annotations

from typing import Any

from nt.settlement_taxonomy import (
    PREDICTABILITY,
    VARIANCE_CLASS,
    compute_learning_weight,
    merge_taxonomy_into,
    normalize_predictability,
    normalize_variance_class,
    taxonomy_from_item,
)

SCHEMA_VERSION = 1

LINEUP_STATUS = frozenset({"confirmed", "predicted", "unknown", "n/a", "na"})
SCRIPT_REALIZED = frozenset({"agreed", "conflict", "unclear", "n/a", "na"})
ROOT_CAUSES = frozenset(
    {"lineup", "script", "price", "model", "info", "availability", "other"}
)

_STRICT_VARIANCE = frozenset({"process_error", "research_miss", "miss"})
_STRICT_RETRO = frozenset({"poor", "wrong", "miss"})


def is_strict_packet_required(item: dict[str, Any]) -> bool:
    tag = str(item.get("variance_tag") or item.get("feel") or "").strip().lower()
    retro = str(
        item.get("research_quality_retro") or item.get("research_retro") or ""
    ).strip().lower()
    return tag in _STRICT_VARIANCE or retro in _STRICT_RETRO


def _norm_enum(val: Any, allowed: frozenset[str]) -> str:
    s = str(val or "").strip().lower()
    if s in ("na", "n.a.", "none"):
        s = "n/a"
    return s


def build_packet_from_item(item: dict[str, Any]) -> dict[str, Any]:
    """Build packet from settle item / UI payload (includes taxonomy)."""
    score = item.get("actual_score") or item.get("score") or item.get("actual_score")
    if score is None:
        score = ""
    root = str(item.get("process_root_cause") or "").strip()
    root_l = root.lower()
    if root_l.startswith("other"):
        root_norm = root  # preserve free text after other:
    else:
        root_norm = root_l

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "bet_id": str(item.get("bet_id") or ""),
        "actual_score": str(score).strip(),
        "actual_lineup_status": _norm_enum(
            item.get("actual_lineup_status"), LINEUP_STATUS
        ),
        "predicted_vs_actual_xi_delta": str(
            item.get("predicted_vs_actual_xi_delta") or ""
        ).strip(),
        "script_realized": _norm_enum(item.get("script_realized"), SCRIPT_REALIZED),
        "process_root_cause": root_norm,
        "variance_tag": str(item.get("variance_tag") or item.get("feel") or "").strip(),
        "research_quality_retro": str(
            item.get("research_quality_retro") or item.get("research_retro") or ""
        ).strip(),
        "key_events": str(item.get("key_events") or "").strip(),
        "notes": str(item.get("notes") or item.get("settlement_notes") or "").strip(),
    }

    # Soft-require taxonomy: agent values if valid, else auto from retro/tag/notes
    classified_by = str(item.get("classified_by") or "auto")
    tax = taxonomy_from_item(item, classified_by=classified_by)
    # Prefer explicit valid enums from item when present
    pred = normalize_predictability(item.get("predictability"))
    vc = normalize_variance_class(item.get("variance_class"))
    if pred:
        tax["predictability"] = pred
    if vc:
        tax["variance_class"] = vc
    if pred or vc:
        tax["learning_weight"] = compute_learning_weight(
            tax["predictability"], tax["variance_class"]
        )
        if item.get("classified_by"):
            tax["classified_by"] = str(item.get("classified_by"))
        if item.get("classification_notes"):
            tax["classification_notes"] = str(item.get("classification_notes"))[:240]
        if item.get("classified_at"):
            tax["classified_at"] = str(item.get("classified_at"))
    merge_taxonomy_into(packet, tax)
    return packet


def validate_packet(
    packet: dict[str, Any],
    *,
    strict: bool,
) -> tuple[bool, list[str]]:
    """
    Validate packet. When strict=True, critical forensic fields required.
    Taxonomy is soft: invalid enums are normalized upstream; missing values
    should already be auto-filled by build_packet_from_item.
    """
    errors: list[str] = []
    # Soft taxonomy sanity (never fail closed alone — auto defaults handle settle)
    pred = str(packet.get("predictability") or "").strip().lower()
    if pred and pred not in PREDICTABILITY:
        errors.append(
            "predictability must be highly_predictable|moderately_predictable|"
            "weakly_predictable|unpredictable_from_available_info"
        )
    vc = str(packet.get("variance_class") or "").strip().lower()
    if vc and vc not in VARIANCE_CLASS:
        errors.append(
            "variance_class must be systematic_script_form|research_process_miss|"
            "model_error|one_off_injury_late|one_off_referee|true_randomness|unknown"
        )

    if not strict:
        # Soft taxonomy only: strip taxonomy errors for non-strict so settle never
        # blocks on missing taxonomy (auto-fill is law).
        errors = []
        return True, errors

    score = str(packet.get("actual_score") or "").strip()
    if not score:
        errors.append("actual_score required for process_error/poor retro")

    lineup = _norm_enum(packet.get("actual_lineup_status"), LINEUP_STATUS)
    if lineup not in LINEUP_STATUS or not lineup:
        errors.append(
            "actual_lineup_status required (confirmed|predicted|unknown|n/a)"
        )

    xi = str(packet.get("predicted_vs_actual_xi_delta") or "").strip()
    if not xi:
        errors.append(
            "predicted_vs_actual_xi_delta required (use n/a if non-XI sport)"
        )

    script = _norm_enum(packet.get("script_realized"), SCRIPT_REALIZED)
    if script not in SCRIPT_REALIZED or not script:
        errors.append("script_realized required (agreed|conflict|unclear|n/a)")

    root = str(packet.get("process_root_cause") or "").strip()
    root_l = root.lower()
    if not root:
        errors.append(
            "process_root_cause required (lineup|script|price|model|info|other)"
        )
    elif not (
        root_l in ROOT_CAUSES
        or root_l.startswith("other:")
        or root_l.startswith("other ")
    ):
        errors.append(
            "process_root_cause must be lineup|script|price|model|info|availability|other"
        )

    return (len(errors) == 0, errors)


def packet_to_notes_blob(packet: dict[str, Any]) -> str:
    """Compact portable blob for bets.csv notes."""
    parts = [
        f"score:{packet.get('actual_score') or ''}",
        f"xi:{packet.get('actual_lineup_status') or ''}",
        f"xi_delta:{(packet.get('predicted_vs_actual_xi_delta') or '')[:80]}",
        f"script:{packet.get('script_realized') or ''}",
        f"root:{(packet.get('process_root_cause') or '')[:60]}",
    ]
    pred = packet.get("predictability")
    vc = packet.get("variance_class")
    lw = packet.get("learning_weight")
    if pred or vc or lw is not None:
        parts.append(f"pred:{pred or ''}")
        parts.append(f"vclass:{vc or ''}")
        parts.append(f"lw:{lw if lw is not None else ''}")
    return "psp{" + "; ".join(parts) + "}"


def validate_settle_item(item: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Full check for one settle item. Returns (ok, errors, packet).
    Non-strict: always ok structurally; taxonomy auto-filled.
    """
    packet = build_packet_from_item(item)
    strict = is_strict_packet_required(item)
    ok, errors = validate_packet(packet, strict=strict)
    return ok, errors, packet
