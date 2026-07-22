from __future__ import annotations

"""
Pack odds-snapshot integrity (HV Research Regime v3 §2).

Shared helpers for attach_evidence + build_portfolio:

- pack_odds_snapshot: SSOT reader (odds_at_research preferred, else decimal_odds_ref)
- odds_drift_rel: relative |board − snapshot| / snapshot
- placeable_odds_snapshot: fail-closed place eligibility (missing / inferred / drift)
- pack_recency_ts: researched_at or file mtime for soft-key newest-wins

Never invent p_model. Never stamp board odds into odds_at_research for place
eligibility in the same step (board_odds_at_attach is diagnostics only).
"""

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


def pack_odds_snapshot(ev: dict[str, Any] | None) -> float | None:
    """
    SSOT odds snapshot from a research pack.

    Prefer odds_at_research; fall back to decimal_odds_ref (aliases).
    """
    if not ev or not isinstance(ev, dict):
        return None
    for k in ("odds_at_research", "decimal_odds_ref"):
        v = ev.get(k)
        if v is None or v == "":
            continue
        try:
            o = float(v)
        except (TypeError, ValueError):
            continue
        if o >= 1.01:
            return o
    return None


def odds_drift_rel(
    snapshot: float | None,
    board_odds: float | None,
) -> float | None:
    """Relative drift |board − snapshot| / snapshot. None if inputs invalid."""
    try:
        s = float(snapshot) if snapshot is not None else None
        b = float(board_odds) if board_odds is not None else None
    except (TypeError, ValueError):
        return None
    if s is None or b is None or s <= 0 or b <= 0:
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
    2. odds_snapshot_inferred truthy → odds_snapshot_inferred
    3. Relative drift ≥ threshold → stale_odds_drift
    """
    pi = pack_integrity_cfg(cfg)
    if not bool(pi.get("require_odds_at_research_for_place", True)):
        return True, ""

    snap = pack_odds_snapshot(ev)
    if snap is None:
        return False, "missing_odds_snapshot"

    if ev and ev.get("odds_snapshot_inferred"):
        return False, "odds_snapshot_inferred"

    thr = float(pi.get("stale_odds_rel_threshold", 0.03))
    drift = odds_drift_rel(snap, board_odds)
    if drift is None:
        return False, "missing_odds_snapshot"
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
) -> None:
    """
    Dual-write decimal_odds_ref + odds_at_research when odds provided.
    Optionally stamp researched_at (UTC ISO). Clears odds_snapshot_inferred.
    """
    if odds is not None:
        try:
            o = float(odds)
        except (TypeError, ValueError):
            o = None
        if o is not None and o >= 1.01:
            pack["decimal_odds_ref"] = o
            pack["odds_at_research"] = o
            # Real dual-write supersedes any prior inferred stamp
            if "odds_snapshot_inferred" in pack:
                pack["odds_snapshot_inferred"] = False
    if researched_at is not None:
        pack["researched_at"] = researched_at
    elif stamp_researched_at:
        pack["researched_at"] = utc_now_iso()


def annotate_attach_diagnostics(
    ev: dict[str, Any],
    board_odds: float,
) -> dict[str, Any]:
    """
    Non-place metadata only. Never stamps board odds into odds_at_research /
    decimal_odds_ref. Returns a shallow copy so shared pack dicts stay clean.
    """
    out = dict(ev)
    try:
        out["board_odds_at_attach"] = float(board_odds)
    except (TypeError, ValueError):
        out["board_odds_at_attach"] = board_odds
    if pack_odds_snapshot(out) is None:
        out["odds_snapshot_missing"] = True
    return out
