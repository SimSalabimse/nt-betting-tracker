from __future__ import annotations

"""
Pack odds-snapshot integrity (HV Research Regime v3 §2).

Shared helpers for attach_evidence + build_portfolio:

- pack_odds_snapshot: SSOT reader (odds_at_research preferred, else decimal_odds_ref)
- odds_drift_rel: relative |board − snapshot| / snapshot (None if non-finite/invalid)
- placeable_odds_snapshot: fail-closed place eligibility
- pack_recency_ts: researched_at or file mtime for soft-key newest-wins

Never invent p_model. Never stamp board odds into odds_at_research for place
eligibility in the same step (board_odds_at_attach is diagnostics only).

Scaffold dual-write of board odds marks odds_snapshot_inferred=True so place
is blocked until write_research_pack / real research dual-write clears it.
"""

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pack_integrity_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Return research.pack_integrity with safe defaults."""
    defaults = {
        "stale_odds_rel_threshold": 0.03,
        "require_odds_at_research_for_place": True,
    }
    if not cfg:
        return dict(defaults)
    try:
        from nt.defaults import research_cfg

        rcfg = research_cfg(cfg)
    except Exception:
        rcfg = dict(cfg.get("research") or {})
    raw = dict(rcfg.get("pack_integrity") or {})
    return {**defaults, **raw}


def is_true_flag(value: Any) -> bool:
    """
    Explicit truthy gate for pack flags (odds_snapshot_inferred, etc.).

    True for: True, 1, "true"/"yes"/"1" (case-insensitive).
    False for: False, 0, None, "", "false"/"no"/"0", and other values.
    """
    if value is True or value is False:
        return bool(value)
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            return False
        return float(value) != 0.0
    s = str(value).strip().lower()
    if s in ("true", "yes", "1", "y", "on"):
        return True
    if s in ("false", "no", "0", "n", "off", ""):
        return False
    # Unknown non-empty strings: fail-closed (treat as inferred/true for safety)
    return bool(s)


def _finite_odds(value: Any) -> float | None:
    """Parse a finite odds float ≥ 1.01, else None."""
    if value is None or value == "":
        return None
    try:
        o = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(o) or o < 1.01:
        return None
    return o


def pack_odds_snapshot(ev: dict[str, Any] | None) -> float | None:
    """
    SSOT odds snapshot from a research pack.

    Prefer odds_at_research; fall back to decimal_odds_ref (aliases).
    Non-finite / &lt;1.01 values are ignored.
    """
    if not ev or not isinstance(ev, dict):
        return None
    for k in ("odds_at_research", "decimal_odds_ref"):
        o = _finite_odds(ev.get(k))
        if o is not None:
            return o
    return None


def snapshot_alias_disagreement(
    ev: dict[str, Any] | None,
    *,
    rel_threshold: float = 0.03,
) -> float | None:
    """
    Relative |odds_at_research − decimal_odds_ref| / min when both present and finite.
    Returns None if not both usable. Warn-only diagnostic (does not invent odds).
    """
    if not ev or not isinstance(ev, dict):
        return None
    a = _finite_odds(ev.get("odds_at_research"))
    b = _finite_odds(ev.get("decimal_odds_ref"))
    if a is None or b is None:
        return None
    base = min(a, b)
    if base <= 0:
        return None
    rel = abs(a - b) / base
    return rel if rel >= float(rel_threshold) else None


def odds_drift_rel(
    snapshot: float | None,
    board_odds: float | None,
) -> float | None:
    """
    Relative drift |board − snapshot| / snapshot.

    Returns None if either input is missing, non-finite, or ≤ 0.
    """
    try:
        s = float(snapshot) if snapshot is not None else None
        b = float(board_odds) if board_odds is not None else None
    except (TypeError, ValueError):
        return None
    if s is None or b is None:
        return None
    if not math.isfinite(s) or not math.isfinite(b):
        return None
    if s <= 0 or b <= 0:
        return None
    return abs(b - s) / s


def placeable_odds_snapshot(
    ev: dict[str, Any] | None,
    board_odds: float,
    cfg: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """
    Fail-closed place law (v3.0).

    Returns (placeable, reason). reason is empty when placeable.

    1. Missing snapshot → missing_odds_snapshot
    2. odds_snapshot_inferred (is_true_flag) → odds_snapshot_inferred
    3. Invalid / non-finite board odds → invalid_board_odds
    4. Relative drift ≥ threshold → stale_odds_drift
    5. Drift uncomputable despite valid snap → odds_drift_unavailable
    """
    pi = pack_integrity_cfg(cfg)
    if not bool(pi.get("require_odds_at_research_for_place", True)):
        return True, ""

    snap = pack_odds_snapshot(ev)
    if snap is None:
        return False, "missing_odds_snapshot"

    if ev and is_true_flag(ev.get("odds_snapshot_inferred")):
        return False, "odds_snapshot_inferred"

    # Board odds must be finite and ≥ 1.01 for place
    board = _finite_odds(board_odds)
    if board is None:
        return False, "invalid_board_odds"

    thr = float(pi.get("stale_odds_rel_threshold", 0.03))
    drift = odds_drift_rel(snap, board)
    if drift is None:
        return False, "odds_drift_unavailable"
    if drift >= thr:
        return False, "stale_odds_drift"
    return True, ""


def pack_recency_ts(ev: dict[str, Any] | None, path: Path | None = None) -> float:
    """
    Recency score for soft-key collision: prefer researched_at, else path mtime.
    Higher = newer.
    """
    if ev and isinstance(ev, dict):
        raw = ev.get("researched_at")
        if raw:
            try:
                s = str(raw).strip().replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except (TypeError, ValueError, OSError):
                pass
    if path is not None:
        try:
            if path.is_file():
                return float(path.stat().st_mtime)
        except OSError:
            pass
    return 0.0


def apply_odds_snapshot_fields(
    pack: dict[str, Any],
    odds: float | None,
    *,
    researched_at: str | None = None,
    stamp_researched_at: bool = False,
    inferred: bool | None = None,
) -> None:
    """
    Dual-write decimal_odds_ref + odds_at_research when odds provided.

    inferred:
      - True  → mark board/template provenance (scaffold); place rejects
      - False → real research dual-write; always write odds_snapshot_inferred=False
      - None  → leave flag untouched if present; still dual-write odds
    """
    if odds is not None:
        o = _finite_odds(odds)
        if o is not None:
            pack["decimal_odds_ref"] = o
            pack["odds_at_research"] = o
            if inferred is True:
                pack["odds_snapshot_inferred"] = True
            elif inferred is False:
                # Stable schema: always clear on successful real dual-write
                pack["odds_snapshot_inferred"] = False
    if researched_at is not None:
        pack["researched_at"] = researched_at
    elif stamp_researched_at:
        pack["researched_at"] = utc_now_iso()


def annotate_attach_diagnostics(
    ev: dict[str, Any],
    board_odds: float,
    *,
    rel_threshold: float = 0.03,
) -> dict[str, Any]:
    """
    Non-place metadata only. Never stamps board odds into odds_at_research /
    decimal_odds_ref. Returns a shallow copy so shared pack dicts stay clean.
    """
    out = dict(ev)
    try:
        b = float(board_odds)
        out["board_odds_at_attach"] = b if math.isfinite(b) else board_odds
    except (TypeError, ValueError):
        out["board_odds_at_attach"] = board_odds
    if pack_odds_snapshot(out) is None:
        out["odds_snapshot_missing"] = True
    # Warn-only when dual aliases disagree (SSOT still prefers odds_at_research)
    disagree = snapshot_alias_disagreement(out, rel_threshold=rel_threshold)
    if disagree is not None:
        out["odds_snapshot_alias_disagreement_rel"] = round(float(disagree), 6)
    return out
