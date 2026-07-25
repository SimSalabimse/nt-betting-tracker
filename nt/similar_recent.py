"""
Similar-recent soft demotion for portfolio sort_ev (ESR FIX 3).

Live ledger only (filter_live_rows / data/bets.csv). Soft penalties only —
true EV is never rewritten. hard_reject_if_count defaults to null (off).
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from nt.live_ledger import filter_live_rows
from nt.market_family import market_family
from nt.sport_taxonomy import normalize_sport

_TERMINAL_OK = frozenset({"Win", "Loss", "Refunded"})
_PENDING_OK = frozenset({"Pending", "ConfirmedPlaced"})


def parse_line(selection: str = "", market_type: str = "") -> float | None:
    """
    Extract a betting line (e.g. 22.5, 2.5) from selection / market_type.

    Prefers *.0 / *.5 numbers; falls back to last float. Comma decimals OK.
    """
    text = f"{selection or ''} {market_type or ''}".replace(",", ".")
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if not nums:
        return None
    half = [float(x) for x in nums if "." in x and x.endswith(("0", "5"))]
    if half:
        return half[-1]
    try:
        return float(nums[-1])
    except ValueError:
        return None


def bet_type_macro(
    *,
    market_family_key: str = "",
    selection: str = "",
    market_type: str = "",
    sport: str = "",
) -> str:
    """Coarse macro for prefer_bet_type_spread: ml | handicap | total | prop | other."""
    fam = (market_family_key or "").strip().lower()
    if not fam:
        fam = market_family(
            sport=sport,
            selection=selection,
            market_type=market_type,
        ).lower()
    if fam in ("player_props", "darts_180s") or fam.endswith("_props"):
        return "prop"
    if "totals" in fam or fam.endswith("_total"):
        return "total"
    if "handicap" in fam or fam.endswith("_hc"):
        return "handicap"
    if (
        fam.endswith("_ml")
        or fam.endswith("_1x2")
        or fam in ("ml_unknown", "football_1x2")
        or fam.endswith("_dnb")
    ):
        return "ml"
    if "btts" in fam:
        return "other"
    return "other"


def _row_sort_key(r: Mapping[str, Any]) -> str:
    """Descending sort key: prefer updated_at, then date, then placed_at."""
    for k in ("updated_at", "settled_at", "date", "placed_at", "created_at"):
        v = str(r.get(k) or "").strip()
        if v:
            return v
    return ""


def live_recent_window(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    window: int = 12,
    include_pending: bool = True,
) -> list[dict[str, Any]]:
    """
    Last N live settled (+ optional pending) rows, newest first.

    Excludes Abandoned and era_archive. Clamps window to 10–15 when outside.
    """
    w = int(window) if window else 12
    if w < 10:
        w = 10
    if w > 15:
        w = 15
    live = filter_live_rows(rows)
    eligible: list[dict[str, Any]] = []
    for r in live:
        res = str(r.get("result") or "").strip()
        if res == "Abandoned":
            continue
        if res in _TERMINAL_OK:
            eligible.append(dict(r))
        elif include_pending and res in _PENDING_OK:
            eligible.append(dict(r))
    eligible.sort(key=_row_sort_key, reverse=True)
    return eligible[:w]


def similar_recent_hits(
    *,
    sport: str,
    selection: str,
    market_type: str = "",
    market_key: str = "",
    market_family_key: str = "",
    match: str = "",
    recent_rows: Sequence[Mapping[str, Any]],
    line_tolerance: float = 1.0,
    include_ml: bool = False,
) -> list[dict[str, Any]]:
    """
    Rows in recent window similar to candidate.

    Default include_ml=False: both sides need parseable lines; same sport +
    market_family + |line_c - line_r| <= tolerance.
    """
    sp = normalize_sport(sport or "", default="unknown")
    fam = (market_family_key or "").strip() or market_family(
        sport=sp,
        selection=selection or "",
        market_type=market_type or "",
        market_key=market_key or "",
    )
    cand_line = parse_line(selection or "", market_type or "")

    # include_ml false → skip ML / no-line candidates entirely
    if cand_line is None and not include_ml:
        return []

    hits: list[dict[str, Any]] = []
    tol = float(line_tolerance)
    match_n = (match or "").strip().lower()

    for r in recent_rows:
        r_sp = normalize_sport(
            str(r.get("sport") or ""),
            default="unknown",
        )
        r_sel = str(r.get("selection") or "")
        r_mt = str(r.get("market_type") or "")
        r_mk = str(r.get("market_key") or "")
        r_fam = market_family(
            sport=r_sp if r_sp != "unknown" else str(r.get("sport") or ""),
            selection=r_sel,
            market_type=r_mt,
            market_key=r_mk,
        )
        if r_sp == "unknown" and fam.startswith("tennis"):
            r_sp = "tennis"
        if r_sp == "unknown" and fam.startswith("football"):
            r_sp = "football"

        if sp != "unknown" and r_sp != "unknown" and sp != r_sp:
            continue
        if r_fam != fam:
            continue

        r_line = parse_line(r_sel, r_mt)

        if cand_line is not None and r_line is not None:
            if abs(cand_line - r_line) <= tol + 1e-9:
                hits.append(dict(r))
            continue

        # One or both missing line
        if not include_ml:
            continue
        # ML / no-line: require same match
        r_match = str(r.get("match") or "").strip().lower()
        if match_n and r_match and match_n == r_match:
            hits.append(dict(r))

    return hits


def similar_recent_penalty(
    *,
    sport: str,
    selection: str,
    market_type: str = "",
    market_key: str = "",
    market_family_key: str = "",
    match: str = "",
    recent_rows: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any] | None = None,
) -> tuple[float, str, list[dict[str, Any]]]:
    """
    Soft penalty + visible reason for composite sort_ev.

    Returns (penalty, reason_string, hits). True EV must not use this penalty.
    """
    sr = dict(cfg or {})
    if not bool(sr.get("enabled", True)):
        return 0.0, "", []

    window = int(sr.get("window", 12) or 12)
    include_ml = bool(sr.get("include_ml", False))
    line_tol = float(sr.get("line_tolerance", 1.0) or 1.0)
    soft_pen = float(sr.get("soft_ev_penalty", 0.012) or 0.0)
    loss_extra = float(sr.get("loss_pattern_extra_penalty", 0.010) or 0.0)

    fam = (market_family_key or "").strip() or market_family(
        sport=sport,
        selection=selection or "",
        market_type=market_type or "",
        market_key=market_key or "",
    )

    hits = similar_recent_hits(
        sport=sport,
        selection=selection,
        market_type=market_type,
        market_key=market_key,
        market_family_key=fam,
        match=match,
        recent_rows=recent_rows,
        line_tolerance=line_tol,
        include_ml=include_ml,
    )
    if not hits:
        return 0.0, "", []

    n = len(hits)
    n_loss = sum(1 for h in hits if str(h.get("result") or "") == "Loss")
    pen = soft_pen if n >= 1 else 0.0
    if n_loss > 0:
        pen += loss_extra

    # Human-visible: similar_recent: similar to recent tennis_totals – demoted (…)
    loss_bit = f"; {n_loss} Loss" if n_loss else ""
    reason = (
        f"similar_recent: similar to recent {fam} – demoted "
        f"({n} in last {window}{loss_bit})"
    )
    return round(pen, 6), reason, hits


def similar_recent_hard_reject_count(cfg: Mapping[str, Any] | None) -> int | None:
    """Return hard_reject_if_count or None (never hard-reject when null/missing)."""
    if not cfg:
        return None
    raw = cfg.get("hard_reject_if_count", None)
    if raw is None or raw == "" or str(raw).lower() in ("null", "none", "false"):
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return n
