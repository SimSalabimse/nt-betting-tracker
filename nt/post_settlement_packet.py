"""
P0: PostSettlementPacket — structured settlement forensics.

Fail-closed when variance_tag=process_error or research_quality_retro=poor:
critical fields required before settle writes the ledger.
"""
from __future__ import annotations

from typing import Any

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
    """Build packet from settle item / UI payload."""
    score = item.get("actual_score") or item.get("score") or item.get("actual_score")
    if score is None:
        score = ""
    root = str(item.get("process_root_cause") or "").strip()
    root_l = root.lower()
    if root_l.startswith("other"):
        root_norm = root  # preserve free text after other:
    else:
        root_norm = root_l

    return {
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


def validate_packet(
    packet: dict[str, Any],
    *,
    strict: bool,
) -> tuple[bool, list[str]]:
    """
    Validate packet. When strict=True, critical fields are required (fail-closed).
    """
    errors: list[str] = []
    # bet_id is preferred but settle may match by match/selection first —
    # never fail non-strict on missing id alone.

    if not strict:
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
    return "psp{" + "; ".join(parts) + "}"


def validate_settle_item(item: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Full check for one settle item. Returns (ok, errors, packet).
    Non-strict: always ok structurally (empty packet fields allowed).
    """
    packet = build_packet_from_item(item)
    strict = is_strict_packet_required(item)
    ok, errors = validate_packet(packet, strict=strict)
    return ok, errors, packet
