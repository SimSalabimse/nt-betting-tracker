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

# Window config is clamped to this band (design: 10–15).
_WINDOW_MIN = 10
_WINDOW_MAX = 15

# Soft penalty scale caps (Issue 3): mild growth with pattern severity, still soft-only.
_PEN_COUNT_CAP = 3


def clamp_window(window: int | None) -> int:
    """Clamp similar-recent window to the design band [10, 15]."""
    w = int(window) if window else 12
    if w < _WINDOW_MIN:
        return _WINDOW_MIN
    if w > _WINDOW_MAX:
        return _WINDOW_MAX
    return w


def is_ml_family(fam: str) -> bool:
    """True for ML / 1X2 / DNB / bare-result families (no real line market)."""
    f = (fam or "").strip().lower()
    if not f:
        return False
    if f.endswith("_ml") or f.endswith("_1x2") or f.endswith("_dnb"):
        return True
    if f in ("ml_unknown", "football_1x2", "ml"):
        return True
    return False


def _is_line_market_context(text: str) -> bool:
    """True when blob looks like O/U / totals / handicap (not bare 1X2 / ML)."""
    t = (text or "").lower()
    if re.search(r"1\s*[x×]\s*2|1x2", t):
        # 1X2 labels often sit next to other tokens — still not a line market
        if not any(
            x in t
            for x in (
                "totalt",
                "over/under",
                "over under",
                " o/u",
                "handikap",
                "handicap",
                "over ",
                "under ",
            )
        ):
            return False
    return bool(
        re.search(
            r"totalt|over/under|over under|\bo/u\b|handikap|handicap|"
            r"(?<![/\w])over\b|(?<![/\w])under\b|"
            r"[+-]\s?\d+(?:[.,]\d+)?|"
            r"antall\s+(?:games?|m[åa]l|points?|kart|maps?)",
            t,
        )
    )


def parse_line(selection: str = "", market_type: str = "") -> float | None:
    """
    Extract a betting line (e.g. 22.5, 2.5) from selection / market_type.

    Only accepts lines in O/U / totals / handicap context. Never treats bare
    ``1`` / ``2`` / ``X`` or digits inside ``1X2`` as a line.
    """
    sel = (selection or "").strip()
    mt = (market_type or "").strip()
    text = f"{sel} {mt}".replace(",", ".")
    if not text.strip():
        return None

    # Strip 1X2 tokens so their embedded digits never become a phantom line
    cleaned = re.sub(r"1\s*[x×]\s*2", " ", text, flags=re.I)
    cleaned = re.sub(r"\b1x2\b", " ", cleaned, flags=re.I)

    if not _is_line_market_context(cleaned):
        return None

    # Prefer number adjacent to Over/Under / signed HC; else half-lines (*.0/*.5)
    adj = re.findall(
        r"(?:over|under|handikap|handicap|[+-])\s*(\d+(?:\.\d+)?)",
        cleaned,
        flags=re.I,
    )
    if adj:
        try:
            return float(adj[-1])
        except ValueError:
            pass

    nums = re.findall(r"\d+(?:\.\d+)?", cleaned)
    if not nums:
        return None
    # Prefer *.0 / *.5 style lines; reject bare integers 1/2 that are ML outcomes
    half = [float(x) for x in nums if "." in x and x.endswith(("0", "5"))]
    if half:
        return half[-1]
    # Integer lines only when clearly a total/HC context with larger numbers
    # (e.g. Over 3 games) — skip 1 and 2 alone (ML / 1X2 residue)
    ints = [float(x) for x in nums if "." not in x]
    ints = [v for v in ints if v >= 3.0 or v == 0.0]
    if ints:
        return ints[-1]
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
    if is_ml_family(fam):
        return "ml"
    if "btts" in fam:
        return "other"
    return "other"


def _sport_from_family(fam: str) -> str:
    """Best-effort sport from family prefix (tennis_totals → tennis)."""
    f = (fam or "").strip().lower()
    if not f or f in ("other", "player_props", "ml_unknown", "totals_unknown", "handicap_unknown"):
        return "unknown"
    # Cross-sport families
    if f.startswith("esports_"):
        return "esports"
    if f.startswith("darts_"):
        return "darts"
    prefix = f.split("_", 1)[0]
    if prefix in (
        "tennis",
        "football",
        "basketball",
        "baseball",
        "darts",
        "esports",
        "ice",
        "unknown",
    ):
        if prefix == "ice":
            return "ice_hockey"
        return prefix
    return "unknown"


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
    live_ledger_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Last N live settled (+ optional pending) rows, newest first.

    Excludes Abandoned. When live_ledger_only (default), drops era_archive via
    filter_live_rows. Clamps window to 10–15.
    """
    w = clamp_window(window)
    if live_ledger_only:
        live = filter_live_rows(rows)
    else:
        live = [dict(r) for r in (rows or []) if isinstance(r, Mapping)]
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

    Default include_ml=False: skip ML/1X2 families entirely (family-based, not
    parse_line-only). Line markets need same sport + market_family + line within
    tolerance. When include_ml=True, no-line pairs require same match.
    """
    sp = normalize_sport(sport or "", default="unknown")
    fam = (market_family_key or "").strip() or market_family(
        sport=sp,
        selection=selection or "",
        market_type=market_type or "",
        market_key=market_key or "",
    )

    # include_ml false → skip ML / 1X2 / DNB families (do not rely on parse_line alone)
    if not include_ml and is_ml_family(fam):
        return []

    cand_line = parse_line(selection or "", market_type or "")

    # No parseable line and not opting into ML path → skip (bare no-line non-ML)
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
        if not include_ml and is_ml_family(r_fam):
            continue

        if r_sp == "unknown":
            r_sp = _sport_from_family(r_fam)

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
    Reason window uses the same clamped value as the search window.
    """
    sr = dict(cfg or {})
    if not bool(sr.get("enabled", True)):
        return 0.0, "", []

    # Same clamp as live_recent_window (Issue 2)
    window = clamp_window(int(sr.get("window", 12) or 12))
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
    # Mild scale with count/loss severity, capped (Issue 3) — still soft-only
    n_scale = min(n, _PEN_COUNT_CAP)
    loss_scale = min(n_loss, _PEN_COUNT_CAP) if n_loss > 0 else 0
    pen = soft_pen * n_scale
    if loss_scale > 0:
        pen += loss_extra * loss_scale

    # Human-visible: similar_recent: similar to recent tennis_totals – demoted (…)
    loss_bit = f"; {n_loss} Loss" if n_loss else ""
    reason = (
        f"similar_recent: similar to recent {fam} – demoted "
        f"({n} in last {window}{loss_bit})"
    )
    return round(pen, 6), reason, hits


def similar_recent_hard_reject_count(cfg: Mapping[str, Any] | None) -> int | None:
    """
    Return hard_reject_if_count or None.

    ESR product default is null (never hard-reject from similar). A positive
    value is an opt-in escape hatch only — prefer soft demotion.
    """
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
