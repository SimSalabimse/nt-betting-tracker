"""
Capital segments persistence (Phase 2.1 foundation).

File: data/state/capital_segments.json (default)
Not consulted by live risk/sizing until capital_v2.enabled (Phase 2.2+).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nt.capital_v2 import RULE_BUNDLE_VERSION, empty_segments, oslo_today
from nt.config import path_from_config
from nt.bets_io import utc_now


def segments_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("capital_segments"):
        return path_from_config(cfg, "capital_segments")
    state = path_from_config(cfg, "state_dir")
    return state / "capital_segments.json"


def load_segments(cfg: dict[str, Any], *, baseline_nok: float | None = None) -> dict[str, Any]:
    """Load segments file or return empty structure. Never raises on missing file."""
    path = segments_path(cfg)
    base = float(
        baseline_nok
        if baseline_nok is not None
        else (cfg.get("bankroll") or {}).get("baseline_nok") or 500.0
    )
    if not path.is_file():
        return empty_segments(baseline_nok=base)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_segments(baseline_nok=base)
    if not isinstance(data, dict):
        return empty_segments(baseline_nok=base)
    # ensure required keys
    empty = empty_segments(baseline_nok=base)
    for k, v in empty.items():
        if k not in data:
            data[k] = v
    if "freeze" in empty and isinstance(empty["freeze"], dict):
        fr = dict(empty["freeze"])
        fr.update(data.get("freeze") or {})
        data["freeze"] = fr
    data.setdefault("schema_version", 1)
    data.setdefault("rule_bundle_version", RULE_BUNDLE_VERSION)
    data.setdefault("secure_nok", 0.0)
    data.setdefault("secure_transfers", [])
    data.setdefault("unit_hwm_reset_equity_nok", base)
    return data


def save_segments(cfg: dict[str, Any], segments: dict[str, Any]) -> Path:
    """Write segments JSON (creates state dir)."""
    path = segments_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(segments)
    payload["updated_at"] = utc_now()
    payload["rule_bundle_version"] = payload.get("rule_bundle_version") or RULE_BUNDLE_VERSION
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def ensure_segments_file(cfg: dict[str, Any], *, baseline_nok: float | None = None) -> dict[str, Any]:
    """Load or create segments file on disk (foundation bootstrap)."""
    path = segments_path(cfg)
    if path.is_file():
        return load_segments(cfg, baseline_nok=baseline_nok)
    segs = empty_segments(
        baseline_nok=float(
            baseline_nok
            if baseline_nok is not None
            else (cfg.get("bankroll") or {}).get("baseline_nok") or 500.0
        ),
        oslo_date=oslo_today(),
    )
    save_segments(cfg, segs)
    return segs


def is_frozen(segments: dict[str, Any]) -> bool:
    fr = segments.get("freeze") or {}
    return bool(fr.get("active"))


def set_freeze(
    segments: dict[str, Any],
    *,
    active: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    """Return updated segments dict (pure mutate copy)."""
    out = dict(segments)
    fr = dict(out.get("freeze") or {})
    fr["active"] = bool(active)
    fr["reason"] = reason
    fr["activated_at"] = utc_now() if active else fr.get("activated_at")
    if not active:
        fr["reason"] = None
        fr["activated_at"] = None
    fr["unfreeze_requires"] = "manual"
    out["freeze"] = fr
    return out
