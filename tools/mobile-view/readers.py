"""
Build schema_version 1 desk snapshot from on-disk state files.

No nt.* imports — pure file reads so the mobile surface cannot mutate engines.
Charts are derived from data/bets.csv + bankroll baseline (same formulas as Book).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
PLACE_EXCERPT_CHARS = 4000
STATUS_EXCERPT_CHARS = 2500


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: Path, limit: int | None = None) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if limit is not None and len(text) > limit:
        return text[:limit] + "\n…(truncated)"
    return text


def _fnum(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _load_bets_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def _pending_bets(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    open_results = {"Pending", "ConfirmedPlaced"}
    out: list[dict[str, Any]] = []
    for r in rows:
        if (r.get("result") or "").strip() not in open_results:
            continue
        out.append(
            {
                "bet_id": (r.get("bet_id") or "").strip() or None,
                "date": (r.get("date") or "").strip() or None,
                "match": (r.get("match") or "").strip() or None,
                "selection": (r.get("selection") or "").strip() or None,
                "decimal_odds": _fnum(r.get("decimal_odds")),
                "stake_nok": _fnum(r.get("stake_nok")),
                "result": (r.get("result") or "").strip() or None,
                "sport": (r.get("sport") or "").strip() or None,
                "updated_at": (r.get("updated_at") or "").strip() or None,
            }
        )
    # Newest first for desk scan
    out.sort(key=lambda x: x.get("updated_at") or x.get("date") or "", reverse=True)
    return out


def _place_these(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "exists": False,
            "mtime": None,
            "title": None,
            "summary_line": None,
            "text_excerpt": None,
            "rows_preview": [],
        }
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        mtime_s = mtime.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except OSError:
        mtime_s = None
    text = _read_text(path, PLACE_EXCERPT_CHARS) or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0].lstrip("# ").strip() if lines else path.name
    summary = next((ln for ln in lines[1:] if ln and not ln.startswith("#")), None)
    return {
        "exists": True,
        "mtime": mtime_s,
        "title": title,
        "summary_line": summary,
        "text_excerpt": text,
        "rows_preview": [],  # v1: Slip uses text_excerpt only
    }


def _equity_curve(rows: list[dict[str, str]], baseline: float) -> list[dict[str, Any]]:
    settled = [r for r in rows if (r.get("result") or "") not in ("Pending", "ConfirmedPlaced", "Abandoned")]
    # Treat any non-pending with date as settled for curve (Win/Loss/Refunded)
    settled = [r for r in rows if (r.get("result") or "").strip() in ("Win", "Loss", "Refunded")]
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or r.get("created_at") or ""))
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in settled:
        by_date[r.get("date") or ""].append(r)
    out: list[dict[str, Any]] = []
    running_pl = 0.0
    for d in sorted(k for k in by_date if k):
        day_rows = by_date[d]
        day_pl = sum(_fnum(r.get("p_l_nok")) or 0.0 for r in day_rows)
        running_pl = round(running_pl + day_pl, 2)
        out.append(
            {
                "date": d,
                "equity": round(baseline + running_pl, 2),
                "day_pl": round(day_pl, 2),
                "cum_pl": running_pl,
            }
        )
    return out


def _drawdown_series(curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    peak: float | None = None
    out: list[dict[str, Any]] = []
    for p in curve:
        eq = float(p["equity"])
        if peak is None or eq > peak:
            peak = eq
        dd = round((peak or eq) - eq, 2)
        dd_pct = (dd / peak) if peak else 0.0
        out.append(
            {
                "date": p["date"],
                "equity": eq,
                "drawdown": dd,
                "drawdown_pct": round(dd_pct, 4),
                "peak": peak,
            }
        )
    return out


def _sport_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if (r.get("result") or "").strip() not in ("Win", "Loss", "Refunded"):
            continue
        g = (r.get("sport") or "").strip() or "(empty)"
        buckets[g].append(r)
    out: dict[str, dict[str, float]] = {}
    for g, items in buckets.items():
        stake = sum(_fnum(r.get("stake_nok")) or 0.0 for r in items)
        pl = sum(_fnum(r.get("p_l_nok")) or 0.0 for r in items)
        wins = sum(1 for r in items if r.get("result") == "Win")
        losses = sum(1 for r in items if r.get("result") == "Loss")
        decided = wins + losses
        out[g] = {
            "n": float(len(items)),
            "wins": float(wins),
            "losses": float(losses),
            "stake": round(stake, 2),
            "pl": round(pl, 2),
            "roi": (pl / stake) if stake else 0.0,
            "winrate": (wins / decided) if decided else 0.0,
        }
    return out


def _overall_stats(rows: list[dict[str, str]]) -> dict[str, float]:
    settled = [r for r in rows if (r.get("result") or "").strip() in ("Win", "Loss", "Refunded")]
    pending = [r for r in rows if (r.get("result") or "").strip() in ("Pending", "ConfirmedPlaced")]
    stake = sum(_fnum(r.get("stake_nok")) or 0.0 for r in settled)
    pl = sum(_fnum(r.get("p_l_nok")) or 0.0 for r in settled)
    wins = sum(1 for r in settled if r.get("result") == "Win")
    losses = sum(1 for r in settled if r.get("result") == "Loss")
    decided = wins + losses
    return {
        "n_settled": float(len(settled)),
        "n_pending": float(len(pending)),
        "wins": float(wins),
        "losses": float(losses),
        "stake": round(stake, 2),
        "pl": round(pl, 2),
        "roi": (pl / stake) if stake else 0.0,
        "winrate": (wins / decided) if decided else 0.0,
    }


def build_charts(root: Path, bankroll: dict[str, Any] | None) -> dict[str, Any]:
    """Simple Book-aligned chart series for mobile (most important stats only)."""
    rows = _load_bets_csv(root / "data" / "bets.csv")
    baseline = float((bankroll or {}).get("baseline_nok") or 0.0)
    curve = _equity_curve(rows, baseline)
    dd = _drawdown_series(curve)
    max_dd = max((p["drawdown"] for p in dd), default=0.0)
    daily = [
        {"date": p["date"], "pl": p["day_pl"], "equity": p["equity"]}
        for p in curve
    ]
    return {
        "range_label": "All time (era)",
        "overall": _overall_stats(rows),
        "equity_curve": curve,
        "daily": daily,
        "drawdown": dd,
        "max_drawdown": max_dd,
        "by_sport": _sport_stats(rows),
    }


def build_desk_snapshot(root: Path) -> dict[str, Any]:
    """
    Schema v1 desk JSON. Optional `charts` key is additive (unknown keys safe for old clients).
    """
    root = Path(root)
    warnings: list[str] = []
    bankroll = _read_json(root / "data" / "state" / "bankroll.json")
    risk = _read_json(root / "data" / "state" / "risk.json")
    phase = _read_json(root / "data" / "state" / "phase.json")
    if bankroll is None:
        warnings.append("missing_bankroll")
    if risk is None:
        warnings.append("missing_risk")
    if phase is None:
        warnings.append("missing_phase")

    rows = _load_bets_csv(root / "data" / "bets.csv")
    if not rows and not (root / "data" / "bets.csv").is_file():
        warnings.append("missing_bets_csv")

    status_path = root / "data" / "state" / "status.md"
    status_text = _read_text(status_path, STATUS_EXCERPT_CHARS)
    place = _place_these(root / "outbox" / "PLACE_THESE.md")

    equity = _fnum((bankroll or {}).get("equity_nok"))
    liquid = _fnum((bankroll or {}).get("liquid_nok"))
    pending_risk = _fnum((bankroll or {}).get("pending_at_risk_nok"))
    if pending_risk is None:
        pending_risk = _fnum((risk or {}).get("open_pending_risk_nok"))

    can_bet = (risk or {}).get("can_bet")
    size_mode = (risk or {}).get("size_mode")
    stopped = bool((risk or {}).get("stopped") or (risk or {}).get("daily_hard_stopped") or (risk or {}).get("weekly_hard_stopped"))
    freeze = bool((risk or {}).get("freeze_manual") or (risk or {}).get("dd_frozen"))
    remaining = _fnum((risk or {}).get("remaining_risk_nok"))
    reasons = (risk or {}).get("reasons") if isinstance((risk or {}).get("reasons"), list) else []

    # Server-side stale: bankroll clock missing / very old is operator concern only
    stale = bool(warnings)

    charts = build_charts(root, bankroll)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "project_root": str(root),
        "view_only": True,
        "stale": stale,
        "warnings": warnings,
        "equity_nok": equity,
        "liquid_nok": liquid,
        "pending_at_risk_nok": pending_risk,
        "realized_pl_nok": _fnum((bankroll or {}).get("realized_pl_nok")),
        "baseline_nok": _fnum((bankroll or {}).get("baseline_nok")),
        "settled_count": (bankroll or {}).get("settled_count"),
        "pending_count": (bankroll or {}).get("pending_count"),
        "bankroll_updated_at": (bankroll or {}).get("updated_at"),
        "phase_id": (phase or {}).get("phase_id"),
        "phase_label": (phase or {}).get("label"),
        "can_bet": can_bet,
        "size_mode": size_mode,
        "stopped": stopped,
        "freeze": freeze,
        "remaining_risk_nok": remaining,
        "daily_risk_cap_nok": _fnum((risk or {}).get("daily_risk_cap_nok")),
        "open_pending_risk_nok": _fnum((risk or {}).get("open_pending_risk_nok")),
        "today_realized_pl_nok": _fnum((risk or {}).get("today_realized_pl_nok")),
        "unit_size_nok": _fnum((risk or {}).get("unit_size_nok")),
        "risk_reasons": reasons,
        "pending_bets": _pending_bets(rows),
        "place_these": place,
        "status_excerpt": status_text,
        "charts": charts,
    }
