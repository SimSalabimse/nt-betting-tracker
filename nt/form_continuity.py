"""
Form continuity + anti-flip library (ESR).

Pure helpers for heavy-fav anchors, opposite-side detection, fail-closed AND
series window, ranking-gap HC tagging, and soft continuity penalties.

PR1: library + config defaults only (form_continuity.enabled: false).
No portfolio recommend wire-up — true EV is never rewritten here.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

# ---------------------------------------------------------------------------
# HC sign helpers (KD12)
# Prefer named imports from anti_soft_underdog when present; never import
# side-decision or hard-reject APIs from that package.
# Local copies match anti_soft_underdog regexes for standalone PR1.
# ---------------------------------------------------------------------------
try:
    from nt.evidence_hierarchy.anti_soft_underdog import (  # type: ignore[attr-defined]
        is_minus_handicap,
        is_plus_handicap,
    )
except ImportError:  # pragma: no cover — FEH package may not be on branch yet

    def is_plus_handicap(selection: str) -> bool:
        """True when selection is a +HC line (underdog handicap)."""
        s = selection or ""
        if re.search(r"\+\s*\d", s):
            return True
        if re.search(r"\+\d+(?:\.\d+)?", s):
            return True
        return False

    def is_minus_handicap(selection: str) -> bool:
        s = selection or ""
        if re.search(r"handikap|handicap", s, re.I) and re.search(r"-\s*\d", s):
            return True
        if re.search(r"-\d+(?:\.\d+)?", s) and not is_plus_handicap(s):
            return True
        return False


# Live-ledger filter — prefer shared helper when diversify PR is merged.
try:
    from nt.live_ledger import filter_live_rows  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover

    def filter_live_rows(
        rows: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        out: list[dict[str, Any]] = []
        for r in rows:
            if not isinstance(r, Mapping):
                continue
            src = str(r.get("source") or "").strip().lower()
            if src == "era_archive":
                continue
            out.append(dict(r))
        return out


_TERMINAL_WIN = frozenset({"Win"})
_PENDING_OK = frozenset({"Pending", "ConfirmedPlaced"})
_TERMINAL_ANY = frozenset({"Win", "Loss", "Refunded"})

_DEFAULT_HEAVY_LINE: dict[str, float] = {
    "baseball": 1.5,
    "basketball": 5.5,
    "football": 1.5,
    "ice_hockey": 1.5,
    "tennis": 2.5,
    "darts": 2.5,
    "esports": 1.5,
    "default": 1.5,
}

# Weak phrase blocklist (EN + NO) — missing phrases alone never grant escape.
_DEFAULT_WEAK_PHRASES: tuple[str, ...] = (
    # English
    "easier line",
    "+2.5 is easier",
    "softer number",
    "public on favourite",
    "public on favorite",
    "public on fav",
    "public chalk",
    "sharp lean",
    "sharp other way",
    "steam other side",
    "fade the favourite",
    "fade the favorite",
    "bounce back",
    # Norwegian
    "enklere linje",
    "mykere linje",
    "publikum på favoritt",
    "publikum pa favoritt",
    "publikum favoritt",
    "sharp motsatt",
    "propp motsatt side",
    "fade favoritt",
    "tilbakefall",
)

_CONVINCING_WIN_TOKENS: tuple[str, ...] = (
    "multi-run",
    "multirun",
    "blowout",
    "convincing",
    "rout",
    "dominant win",
    "covered easily",
)

# S1 vs S4 must be disjoint so one phrase cannot double-count into strong_flip.
# S1 = availability / injury / lineup break (material news).
_S1_NOTES_TOKENS: tuple[str, ...] = (
    "injury",
    "scratched",
    "out for",
    "lineup change",
    "lineup delta",
)
# S4 = structural matchup terms (pitcher/rest/travel/rotation) — not S1 tokens.
_STRUCTURAL_FLIP_TOKENS: tuple[str, ...] = (
    "pitcher change",
    "starting pitcher",
    "rotation change",
    "confirmed lineup",
    "rest advantage",
    "travel",
    "back-to-back",
    "b2b",
)

# Multi-word / longer idioms: plain substring OK.
# Short tokens use word-boundary match in is_ranking_gap_hc (avoid "frank"→"rank").
_RANK_IDIOMS_PHRASE: tuple[str, ...] = (
    "table position",
    "worst era",
    "best record",
    "elite vs bottom",
    "bottom of",
    "ranking gap",
    "strength gap",
    "standings",
)
_RANK_IDIOMS_WORD: tuple[str, ...] = (
    "rank",
    "elo",
    "seed",
)
# Backward-compatible combined view for tests/docs
_RANK_IDIOMS: tuple[str, ...] = _RANK_IDIOMS_PHRASE + _RANK_IDIOMS_WORD


def _fc_section(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    """Resolve form_continuity config from full cfg or bare section."""
    if not cfg:
        return {}
    # Already the form_continuity section
    if "heavy_fav_max_odds" in cfg or "max_hours" in cfg or "base_penalty" in cfg or "win_penalty" in cfg:
        if "enabled" in cfg or "max_hours" in cfg or "heavy_line_by_sport" in cfg:
            # Heuristic: bare section vs full config both may have "enabled"
            if "learning" not in cfg and "diversification" not in cfg:
                return dict(cfg)
    learning = cfg.get("learning") if isinstance(cfg.get("learning"), Mapping) else {}
    div = learning.get("diversification") if isinstance(learning, Mapping) else {}
    if not isinstance(div, Mapping):
        div = cfg.get("diversification") if isinstance(cfg.get("diversification"), Mapping) else cfg
    fc = (div or {}).get("form_continuity") if isinstance(div, Mapping) else None
    if isinstance(fc, Mapping):
        return dict(fc)
    # Bare form_continuity-like mapping
    return dict(cfg) if isinstance(cfg, Mapping) else {}


def default_form_continuity_cfg() -> dict[str, Any]:
    """PR1 defaults (enabled false until portfolio wire-up)."""
    return {
        "enabled": False,
        "live_ledger_only": True,
        "anchor_scan_limit": 30,
        "max_hours": 48,
        "max_games": 2,
        "heavy_fav_max_odds": 2.10,
        "heavy_line_by_sport": dict(_DEFAULT_HEAVY_LINE),
        "include_pending_anchors": True,
        "base_penalty": 0.035,
        "win_penalty": 0.035,
        "pending_penalty": 0.015,
        "weak_extra_penalty": 0.025,
        "convincing_win_mult": 1.25,
        "weak_flip_action": "soft_reject",
        "strong_flip_min_ev": 0.06,
        "weak_phrase_blocklist": [],
    }


def default_ranking_gap_cfg() -> dict[str, Any]:
    return {
        "enabled": False,
        "max_per_slip": 1,
        "ev_slack": 0.015,
        "soft_skip_reason": "ranking_gap_hc: soft cap 1 per slip",
    }


def selection_side_sign(selection: str) -> str:
    """Return 'plus' | 'minus' | 'unknown'. Plus wins when both signs appear."""
    if is_plus_handicap(selection):
        return "plus"
    if is_minus_handicap(selection):
        return "minus"
    return "unknown"


def parse_match_teams(match: str) -> tuple[str, str] | None:
    """
    Team pair from match string.

    Reuses combos._teams_from_match separator pattern: `` vs ``, `` v ``, `` - ``.
    """
    m = (match or "").strip()
    if not m:
        return None
    low = m.lower()
    for sep in (" vs ", " v ", " - "):
        if sep in low:
            # split on first occurrence using original case via index
            idx = low.index(sep)
            a = m[:idx].strip()
            b = m[idx + len(sep) :].strip()
            if a and b:
                return (a.lower(), b.lower())
    return None


def selection_team(selection: str, teams: tuple[str, str]) -> str | None:
    """Best-effort team token from selection via substring overlap with match teams."""
    sel = (selection or "").lower()
    if not sel or not teams:
        return None
    # Prefer longer team name first to avoid partial collisions
    ordered = sorted((t for t in teams if t), key=len, reverse=True)
    for t in ordered:
        if t and t in sel:
            return t
    # Token overlap: any significant token (≥3 chars) of team in selection
    for t in ordered:
        tokens = [tok for tok in re.split(r"\s+", t) if len(tok) >= 3]
        if tokens and all(tok in sel for tok in tokens):
            return t
    return None


def parse_hc_line(selection: str = "", market_type: str = "") -> float | None:
    """Absolute handicap line magnitude from selection / market_type."""
    text = f"{selection or ''} {market_type or ''}".replace(",", ".")
    if not text.strip():
        return None
    # Prefer signed number nearest to team / trailing (Rockies +2.5, Brewers -1.5)
    signed = re.findall(r"(?<!\d)([+-])\s*(\d+(?:\.\d+)?)", text)
    if signed:
        # Last signed number is usually the selection side line
        _sign, num = signed[-1]
        try:
            return abs(float(num))
        except ValueError:
            pass
    # Fallback: handikap … N.N
    m = re.search(r"(?:handikap|handicap)[^\d+-]*([+-]?\d+(?:\.\d+)?)", text, re.I)
    if m:
        try:
            return abs(float(m.group(1)))
        except ValueError:
            return None
    return None


def anchor_timestamp(row: Mapping[str, Any]) -> str:
    """
    Ledger-native SSOT for hours_since_anchor.

    Primary: updated_at → created_at (live BET_HEADER).
    Optional after: settled_at → placed_at (synthetic/test rows only).
    """
    for k in ("updated_at", "created_at", "settled_at", "placed_at"):
        v = str(row.get(k) or "").strip()
        if v:
            return v
    return ""


def _parse_ts(raw: str) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    # Normalize Zulu
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # date-only
        try:
            dt = datetime.fromisoformat(s[:10])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _row_calendar_date(row: Mapping[str, Any]) -> str:
    """YYYY-MM-DD for game-count (date field, else timestamp date)."""
    d = str(row.get("date") or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", d):
        return d[:10]
    kick = str(row.get("kickoff") or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", kick):
        return kick[:10]
    ts = anchor_timestamp(row)
    if ts:
        return ts[:10]
    return ""


def _same_team_pair(a: Mapping[str, Any] | str, b: Mapping[str, Any] | str) -> bool:
    ma = a if isinstance(a, str) else str(a.get("match") or "")
    mb = b if isinstance(b, str) else str(b.get("match") or "")
    ta = parse_match_teams(ma)
    tb = parse_match_teams(mb)
    if ta and tb:
        return set(ta) == set(tb)
    # Fallback exact normalized match
    return ma.strip().lower() == mb.strip().lower() and bool(ma.strip())


def _is_handicap_context(
    selection: str = "",
    market_type: str = "",
    market_family_key: str = "",
) -> bool:
    fam = (market_family_key or "").lower()
    if "handicap" in fam or fam.endswith("_hc"):
        return True
    blob = f"{selection or ''} {market_type or ''}".lower()
    if "handikap" in blob or "handicap" in blob:
        return True
    return selection_side_sign(selection) in ("plus", "minus")


def _heavy_line_threshold(sport: str, fc: Mapping[str, Any]) -> float:
    by = fc.get("heavy_line_by_sport") if isinstance(fc.get("heavy_line_by_sport"), Mapping) else {}
    by = dict(_DEFAULT_HEAVY_LINE, **{str(k).lower(): float(v) for k, v in (by or {}).items()})
    sp = (sport or "").strip().lower().replace(" ", "_")
    try:
        from nt.sport_taxonomy import normalize_sport

        sp = normalize_sport(sp, default=sp or "unknown")
    except Exception:
        pass
    if sp in by:
        return float(by[sp])
    return float(by.get("default", 1.5))


def _odds_of(row: Mapping[str, Any] | None = None, decimal_odds: float | None = None) -> float | None:
    if decimal_odds is not None:
        try:
            return float(decimal_odds)
        except (TypeError, ValueError):
            return None
    if not row:
        return None
    for k in ("decimal_odds", "odds"):
        v = row.get(k)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def is_heavy_favourite_hc(
    row: Mapping[str, Any] | None = None,
    cfg: Mapping[str, Any] | None = None,
    *,
    selection: str = "",
    market_type: str = "",
    sport: str = "",
    decimal_odds: float | None = None,
    market_family_key: str = "",
    result: str | None = None,
    require_result: bool = False,
) -> bool:
    """
    True when a seat is a heavy favourite handicap.

    Conditions (all):
      - handicap family / HC selection
      - minus side (plus preferred out → side sign minus)
      - abs(line) ≥ sport heavy threshold
      - odds ≤ heavy_fav_max_odds (default 2.10)
      - optional result filter when require_result or row result is checked by caller
    """
    fc = {**default_form_continuity_cfg(), **_fc_section(cfg)}
    if row is not None:
        selection = selection or str(row.get("selection") or "")
        market_type = market_type or str(row.get("market_type") or "")
        sport = sport or str(row.get("sport") or "")
        market_family_key = market_family_key or str(
            row.get("market_family") or row.get("market_family_key") or ""
        )
        if result is None:
            result = str(row.get("result") or "")
        if decimal_odds is None:
            decimal_odds = _odds_of(row)

    if not _is_handicap_context(selection, market_type, market_family_key):
        return False
    if selection_side_sign(selection) != "minus":
        return False
    line = parse_hc_line(selection, market_type)
    if line is None:
        return False
    thr = _heavy_line_threshold(sport, fc)
    if line + 1e-12 < thr:
        return False
    odds = _odds_of(None, decimal_odds)
    max_odds = float(fc.get("heavy_fav_max_odds", 2.10))
    if odds is None or odds > max_odds + 1e-12:
        return False

    if require_result:
        res = str(result or "").strip()
        include_pending = bool(fc.get("include_pending_anchors", True))
        if res in _TERMINAL_WIN:
            return True
        if include_pending and res in _PENDING_OK:
            return True
        return False
    return True


def is_opposite_side_hc(
    prior: Mapping[str, Any] | str,
    candidate: Mapping[str, Any] | str,
    *,
    prior_selection: str = "",
    candidate_selection: str = "",
    prior_match: str = "",
    candidate_match: str = "",
) -> bool:
    """True when same team-pair and opposite HC signs."""
    if isinstance(prior, Mapping):
        prior_selection = prior_selection or str(prior.get("selection") or "")
        prior_match = prior_match or str(prior.get("match") or "")
    else:
        prior_selection = prior_selection or str(prior)
    if isinstance(candidate, Mapping):
        candidate_selection = candidate_selection or str(candidate.get("selection") or "")
        candidate_match = candidate_match or str(candidate.get("match") or "")
    else:
        candidate_selection = candidate_selection or str(candidate)

    if prior_match or candidate_match:
        if not _same_team_pair(prior_match or prior, candidate_match or candidate):
            return False
    elif isinstance(prior, Mapping) and isinstance(candidate, Mapping):
        if not _same_team_pair(prior, candidate):
            return False

    a = selection_side_sign(prior_selection)
    b = selection_side_sign(candidate_selection)
    if a not in ("plus", "minus") or b not in ("plus", "minus"):
        return False
    return a != b


def _anchor_sort_key(r: Mapping[str, Any]) -> str:
    """Desc sort: updated_at → created_at → date (+ optional settled/placed after live keys)."""
    for k in ("updated_at", "created_at", "date", "settled_at", "placed_at"):
        v = str(r.get(k) or "").strip()
        if v:
            return v
    return ""


def _is_potential_continuity_anchor(row: Mapping[str, Any]) -> bool:
    """
    True when a row could seed an anti-flip heavy-fav anchor.

    Used to prefer HC minus / Win-Pending seats in the scan window so
    high-volume Loss/Refunded terminals do not dilute past anchor_scan_limit.
    """
    res = str(row.get("result") or "").strip()
    if res not in _TERMINAL_WIN and res not in _PENDING_OK:
        return False
    sel = str(row.get("selection") or "")
    mt = str(row.get("market_type") or "")
    fam = str(row.get("market_family") or row.get("market_family_key") or "")
    if selection_side_sign(sel) == "minus":
        return True
    if _is_handicap_context(sel, mt, fam) and selection_side_sign(sel) != "plus":
        return True
    return False


def live_continuity_anchor_window(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    limit: int = 30,
    include_pending: bool = True,
    live_ledger_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Last `limit` live terminal (+ optional pending) rows, newest first.

    NOT clamped to similar_recent's 10–15 band.
    Sort key (desc, ledger-native): updated_at → created_at → date.
    Always filter_live_rows when live_ledger_only. Excludes Abandoned.

    Prefer-filter (anti-dilution): potential continuity anchors
    (Win/Pending + minus-HC / handicap context) are taken first up to
    ``limit``, then remaining slots fill with other terminals. Prevents
    high-volume non-fav seats from pushing true heavy-fav Wins past the scan.
    """
    lim = max(1, int(limit) if limit else 30)
    if live_ledger_only:
        live = filter_live_rows(rows)
    else:
        live = [dict(r) for r in (rows or []) if isinstance(r, Mapping)]
    preferred: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    for r in live:
        res = str(r.get("result") or "").strip()
        if res == "Abandoned":
            continue
        row = dict(r)
        is_terminal = res in _TERMINAL_ANY or res in _TERMINAL_WIN
        is_pending = include_pending and res in _PENDING_OK
        if not is_terminal and not is_pending:
            continue
        if _is_potential_continuity_anchor(row):
            preferred.append(row)
        else:
            other.append(row)
    preferred.sort(key=_anchor_sort_key, reverse=True)
    other.sort(key=_anchor_sort_key, reverse=True)
    out = preferred[:lim]
    if len(out) < lim:
        out.extend(other[: lim - len(out)])
    return out


def hours_since_anchor(
    anchor: Mapping[str, Any],
    *,
    now_utc: datetime | None = None,
) -> float | None:
    ts = _parse_ts(anchor_timestamp(anchor))
    if ts is None:
        return None
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max(0.0, (now - ts).total_seconds() / 3600.0)


def games_in_pair_since_anchor(
    anchor: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    now_utc: datetime | None = None,
) -> int:
    """
    Distinct match calendar dates for same team-pair with timestamp ≥ anchor
    and ≤ now (inclusive of anchor game date). Doubleheaders same date = 1.
    """
    anchor_ts = _parse_ts(anchor_timestamp(anchor))
    anchor_date = _row_calendar_date(anchor)
    if not anchor_date and anchor_ts is None:
        return 0
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    dates: set[str] = set()
    if anchor_date:
        dates.add(anchor_date)
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        if not _same_team_pair(anchor, r):
            continue
        d = _row_calendar_date(r)
        if not d:
            continue
        # timestamp ≥ anchor
        r_ts = _parse_ts(anchor_timestamp(r))
        if anchor_ts is not None and r_ts is not None:
            if r_ts < anchor_ts:
                continue
            if r_ts > now:
                continue
        elif anchor_date and d < anchor_date:
            continue
        dates.add(d)
    return len(dates)


def in_series_window(
    anchor: Mapping[str, Any],
    candidate_match: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    max_hours: float = 48.0,
    max_games: int = 2,
    now_utc: datetime | None = None,
) -> tuple[bool, float | None, int]:
    """
    Fail-closed AND:
      same_team_pair AND hours_since ≤ max_hours AND games_since ≤ max_games
    """
    if not _same_team_pair(str(anchor.get("match") or ""), candidate_match):
        return False, None, 0
    hours = hours_since_anchor(anchor, now_utc=now_utc)
    games = games_in_pair_since_anchor(anchor, rows, now_utc=now_utc)
    if hours is None:
        return False, None, games
    ok = hours <= float(max_hours) + 1e-9 and games <= int(max_games)
    return ok, hours, games


def _blob_has_weak_phrase(text: str, extra: Sequence[str] | None = None) -> bool:
    blob = (text or "").lower()
    phrases = list(_DEFAULT_WEAK_PHRASES)
    if extra:
        phrases.extend(str(p).lower() for p in extra if p)
    return any(p in blob for p in phrases if p)


def _convincing_win(row: Mapping[str, Any]) -> bool:
    notes = str(row.get("notes") or "").lower()
    return any(t in notes for t in _CONVINCING_WIN_TOKENS)


def _count_strong_flip_signals(
    *,
    base_ev: float | None,
    grade: str,
    evidence_snapshot: Mapping[str, Any] | None,
    notes: str,
    strong_flip_min_ev: float,
) -> tuple[int, list[str]]:
    """
    Return (count, signal ids). Escape requires ≥2 positive signals.

    S1 and S4 token sets are disjoint: a single phrase (e.g. ``pitcher change``)
    can credit at most one of S1/S4.
    """
    snap = evidence_snapshot or {}
    hits: list[str] = []
    notes_l = (notes or "").lower()
    why = str(snap.get("why_flip") or "")
    summary_l = str(snap.get("summary") or "").lower()
    # S1 material news / injury-lineup break (disjoint from S4 structural set)
    if snap.get("injury_or_lineup_break"):
        hits.append("S1_injury_lineup")
    elif any(t in notes_l for t in _S1_NOTES_TOKENS):
        hits.append("S1_injury_lineup")
    # S2 explicit why_flip ≥40 chars, not weak-only
    why_ok = len(why.strip()) >= 40 and not _blob_has_weak_phrase(why)
    notes_why = ""
    m = re.search(r"why_flip\s*[:=]\s*(.+)", notes or "", re.I)
    if m:
        notes_why = m.group(1).strip()
    if not why_ok and len(notes_why) >= 40 and not _blob_has_weak_phrase(notes_why):
        why_ok = True
    if why_ok:
        hits.append("S2_why_flip")
    # S3 base_ev ≥ min AND grade ≥ B
    g = (grade or "").strip().upper()
    grade_ok = g in ("A", "B") or g.startswith("A") or g.startswith("B")
    try:
        bev = float(base_ev) if base_ev is not None else None
    except (TypeError, ValueError):
        bev = None
    if bev is not None and bev + 1e-12 >= float(strong_flip_min_ev) and grade_ok:
        hits.append("S3_base_ev_grade")
    # S4 structural matchup terms (disjoint from S1 — no injury/lineup tokens here)
    struct_blob = f"{notes_l} {summary_l} {why.lower()}"
    if any(t in struct_blob for t in _STRUCTURAL_FLIP_TOKENS):
        hits.append("S4_structural")
    return len(hits), hits


def build_evidence_snapshot(
    ev: Mapping[str, Any] | None,
    grade: str,
) -> dict[str, Any]:
    """Lightweight snapshot for annotate (no pack reload)."""
    ev = dict(ev or {})
    cl = ev.get("feh_checklist") if isinstance(ev.get("feh_checklist"), dict) else None
    if cl is None:
        cl = ev.get("checklist") if isinstance(ev.get("checklist"), dict) else {}
    signals = ev.get("signals") if isinstance(ev.get("signals"), dict) else {}
    rank_sig = signals.get("ranking_seed") or signals.get("ranking_strength") or {}
    signals_rank_primary = bool(
        isinstance(rank_sig, dict)
        and rank_sig.get("filled")
        and str(rank_sig.get("strength") or "").lower()
        in ("positive", "strong", "medium", "high")
    )
    injury_or_lineup_break = bool(
        str(ev.get("availability_status") or "").lower() in ("doubtful", "out", "changed")
        or str(ev.get("lineup_status") or "").lower() in ("changed", "uncertain")
        or "injury" in str(ev.get("availability_notes") or "").lower()
        or "injury" in str(ev.get("lineup_notes") or "").lower()
    )
    return {
        "summary": str(ev.get("summary") or "")[:400],
        "why_flip": (
            str((ev.get("form_continuity") or {}).get("why_flip") or "")
            or str((ev.get("opposite_side_check") or {}).get("one_liner") or "")
            or str(cl.get("why_this_side_not_opposite") or "")
        )[:300],
        "injury_or_lineup_break": injury_or_lineup_break,
        "higher_ranked_side": str(cl.get("higher_ranked_side") or "unknown"),
        "ranking_confidence": float(cl.get("ranking_confidence") or 0.0),
        "signals_rank_primary": signals_rank_primary,
        "opposite_side_check": ev.get("opposite_side_check"),
        "grade": grade,
    }


def selection_agrees_with_rank(
    selection: str,
    snap: Mapping[str, Any],
    *,
    match: str = "",
) -> bool:
    """
    True when the selection is on the higher-ranked side.

    higher_ranked_side: favourite | home | player_a | underdog | away | player_b |
    even | unknown | n_a
    """
    hrs = str(snap.get("higher_ranked_side") or "unknown").strip().lower()
    if hrs in ("", "unknown", "n_a", "even"):
        return False
    sign = selection_side_sign(selection)
    if hrs in ("favourite", "favorite", "home", "player_a"):
        if sign == "minus":
            return True
        teams = parse_match_teams(match) if match else None
        if teams:
            sel_team = selection_team(selection, teams)
            return bool(sel_team and sel_team == teams[0])
        return False
    if hrs in ("underdog", "away", "player_b"):
        if sign == "plus":
            return True
        teams = parse_match_teams(match) if match else None
        if teams and len(teams) > 1:
            sel_team = selection_team(selection, teams)
            return bool(sel_team and sel_team == teams[1])
        return False
    return False


def is_ranking_gap_hc(
    *,
    market_family: str = "",
    selection: str = "",
    notes: str = "",
    match: str = "",
    evidence_snapshot: Mapping[str, Any] | None = None,
    market_type: str = "",
) -> bool:
    """Tag ranking-gap handicap seats (soft slip cap in PR4)."""
    fam = (market_family or "").lower()
    if "handicap" not in fam and not _is_handicap_context(selection, market_type, fam):
        return False
    # Require HC context even when family empty
    if "handicap" not in fam and selection_side_sign(selection) == "unknown":
        if "handikap" not in (selection or "").lower() and "handicap" not in (
            selection or ""
        ).lower():
            return False
    snap = evidence_snapshot or {}
    if snap.get("signals_rank_primary"):
        if selection_agrees_with_rank(selection, snap, match=match):
            return True
    hrs = str(snap.get("higher_ranked_side") or "")
    try:
        conf = float(snap.get("ranking_confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    if (
        hrs
        and hrs not in ("unknown", "n_a", "even", "")
        and conf >= 0.6
        and selection_agrees_with_rank(selection, snap, match=match)
    ):
        return True
    blob = f"{notes} {snap.get('summary') or ''}".lower()
    if any(t in blob for t in _RANK_IDIOMS_PHRASE):
        return True
    # Short tokens: word boundary so "frank" ≠ "rank", "seeded" can still match seed*
    for w in _RANK_IDIOMS_WORD:
        if re.search(rf"\b{re.escape(w)}\b", blob):
            return True
    return False


def _prior_signed_label(row: Mapping[str, Any]) -> str:
    sel = str(row.get("selection") or "")
    teams = parse_match_teams(str(row.get("match") or ""))
    team = selection_team(sel, teams) if teams else None
    line = parse_hc_line(sel, str(row.get("market_type") or ""))
    sign = selection_side_sign(sel)
    signed = ""
    if line is not None:
        signed = f"{'-' if sign == 'minus' else '+' if sign == 'plus' else ''}{line:g}"
    name = (team or "fav").title() if team else "fav"
    # Prefer original casing snippet from selection
    if team and teams:
        raw_match = str(row.get("match") or "")
        for part in re.split(r"\s+vs\s+|\s+v\s+|\s+-\s+", raw_match, flags=re.I):
            if part.strip().lower() == team:
                name = part.strip()
                break
    return f"{name} {signed}".strip()


def form_continuity_penalty(
    rec_or_row: Mapping[str, Any] | None = None,
    live_rows: Sequence[Mapping[str, Any]] | None = None,
    cfg: Mapping[str, Any] | None = None,
    *,
    match: str = "",
    selection: str = "",
    sport: str = "",
    market_type: str = "",
    market_family_key: str = "",
    decimal_odds: float | None = None,
    base_ev: float | None = None,
    grade: str | None = None,
    evidence_snapshot: Mapping[str, Any] | None = None,
    notes: str = "",
    recent_rows: Sequence[Mapping[str, Any]] | None = None,
    now_utc: datetime | None = None,
    force: bool = False,
) -> tuple[float, str, dict[str, Any]]:
    """
    Continuity / anti-flip soft penalty.

    Returns ``(penalty, reason, meta)``.
    Reason always starts with ``form_continuity:`` when non-empty.
    True EV / place EV must not use this penalty (sort_ev / soft-reject only).

    Accepts either a mapping candidate (rec_or_row) + live_rows, or explicit
    keyword fields + recent_rows (design API).
    """
    fc = {**default_form_continuity_cfg(), **_fc_section(cfg)}
    empty_meta: dict[str, Any] = {
        "enabled": bool(fc.get("enabled", False)),
        "soft_reject": False,
        "flip_detected": False,
        "strong_flip_evidence": False,
        "weak_evidence": False,
        "anchor_bet_id": None,
        "hours_since": None,
        "games_since": None,
    }
    if not force and not fc.get("enabled", False):
        return 0.0, "", {**empty_meta, "enabled": False}

    if rec_or_row is not None and isinstance(rec_or_row, Mapping):
        match = match or str(rec_or_row.get("match") or "")
        selection = selection or str(rec_or_row.get("selection") or "")
        sport = sport or str(rec_or_row.get("sport") or "")
        market_type = market_type or str(rec_or_row.get("market_type") or "")
        market_family_key = market_family_key or str(
            rec_or_row.get("market_family")
            or rec_or_row.get("market_family_key")
            or ""
        )
        if decimal_odds is None:
            decimal_odds = _odds_of(rec_or_row)
        if grade is None:
            grade = str(rec_or_row.get("grade") or "")
        if base_ev is None and rec_or_row.get("base_ev") is not None:
            try:
                base_ev = float(rec_or_row.get("base_ev"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                base_ev = None
        if not notes:
            notes = str(rec_or_row.get("notes") or "")
        if evidence_snapshot is None and isinstance(
            rec_or_row.get("evidence_snapshot"), Mapping
        ):
            evidence_snapshot = rec_or_row.get("evidence_snapshot")  # type: ignore[assignment]

    rows_src = recent_rows if recent_rows is not None else live_rows
    include_pending = bool(fc.get("include_pending_anchors", True))
    limit = int(fc.get("anchor_scan_limit", 30) or 30)
    live_only = bool(fc.get("live_ledger_only", True))
    window = live_continuity_anchor_window(
        rows_src,
        limit=limit,
        include_pending=include_pending,
        live_ledger_only=live_only,
    )
    # For game-count use full live set (not just window slice)
    if live_only:
        all_live = filter_live_rows(rows_src)
    else:
        all_live = [dict(r) for r in (rows_src or []) if isinstance(r, Mapping)]

    max_hours = float(fc.get("max_hours", 48))
    max_games = int(fc.get("max_games", 2))
    win_pen = float(fc.get("base_penalty", fc.get("win_penalty", 0.035)))
    pending_pen = float(fc.get("pending_penalty", 0.015))
    weak_extra = float(fc.get("weak_extra_penalty", 0.025))
    conv_mult = float(fc.get("convincing_win_mult", 1.25))
    strong_min = float(fc.get("strong_flip_min_ev", 0.06))
    weak_action = str(fc.get("weak_flip_action", "soft_reject") or "soft_reject").strip().lower()
    extra_weak = fc.get("weak_phrase_blocklist") or []

    best: dict[str, Any] | None = None
    best_pen = 0.0
    best_hours: float | None = None
    best_games = 0
    best_is_win = False

    for anchor in window:
        res = str(anchor.get("result") or "").strip()
        is_win = res in _TERMINAL_WIN
        is_pending = res in _PENDING_OK
        if not is_win and not (include_pending and is_pending):
            continue
        if not is_heavy_favourite_hc(anchor, fc, require_result=False):
            continue
        # Require minus-side heavy fav (is_heavy already checks)
        if not is_opposite_side_hc(anchor, {"match": match, "selection": selection}):
            continue
        ok, hours, games = in_series_window(
            anchor,
            match,
            all_live,
            max_hours=max_hours,
            max_games=max_games,
            now_utc=now_utc,
        )
        if not ok:
            continue
        pen = win_pen if is_win else pending_pen
        if is_win and _convincing_win(anchor):
            pen *= conv_mult
        # Prefer win anchors over pending; then higher penalty
        rank = (1 if is_win else 0, pen)
        if best is None or rank > (
            1 if best_is_win else 0,
            best_pen,
        ):
            best = anchor
            best_pen = pen
            best_hours = hours
            best_games = games
            best_is_win = is_win

    if best is None:
        return 0.0, "", {
            **empty_meta,
            "enabled": True,
            "flip_detected": False,
        }

    flip_detected = True
    n_strong, strong_ids = _count_strong_flip_signals(
        base_ev=base_ev,
        grade=str(grade or ""),
        evidence_snapshot=evidence_snapshot,
        notes=notes,
        strong_flip_min_ev=strong_min,
    )
    strong = n_strong >= 2
    # Weak phrases inform demote messaging but do NOT grant escape alone
    blob = f"{notes} {str((evidence_snapshot or {}).get('summary') or '')} {str((evidence_snapshot or {}).get('why_flip') or '')}"
    has_weak_phrase = _blob_has_weak_phrase(blob, list(extra_weak) if extra_weak else None)

    soft_reject = False
    weak_evidence = False
    reason_parts: list[str] = []
    label = _prior_signed_label(best)

    if best_is_win:
        reason_parts.append(
            f"Opposite side of recent successful {label} — strong continuity penalty applied"
        )
        if _convincing_win(best):
            reason_parts[-1] += " (convincing win)"
    else:
        reason_parts.append(
            f"Opposite side of open heavy fav {label} — caution"
        )

    # Pending-only anchors: demote only, never soft_reject
    if not best_is_win:
        weak_evidence = False
        soft_reject = False
    elif strong:
        weak_evidence = False
        soft_reject = False
    else:
        # Fail-closed WEAK (no ambiguous third state)
        weak_evidence = True
        if weak_action == "soft_reject":
            soft_reject = True
            reason_parts.append("weak flip justification — rejected")
        else:
            soft_reject = False
            best_pen = best_pen + weak_extra
            reason_parts.append("weak flip justification — demoted")

    if has_weak_phrase and weak_evidence:
        # already noted via weak justification
        pass

    reason = "form_continuity: " + "; ".join(reason_parts)
    meta = {
        "enabled": True,
        "soft_reject": soft_reject,
        "flip_detected": flip_detected,
        "strong_flip_evidence": strong,
        "strong_signals": strong_ids,
        "weak_evidence": weak_evidence,
        "has_weak_phrase": has_weak_phrase,
        "anchor_bet_id": best.get("bet_id") or best.get("id"),
        "anchor_selection": str(best.get("selection") or ""),
        "anchor_result": str(best.get("result") or ""),
        "hours_since": best_hours,
        "games_since": best_games,
        "penalty": round(float(best_pen), 6),
        "pending_anchor": not best_is_win,
    }
    return round(float(best_pen), 6), reason, meta
