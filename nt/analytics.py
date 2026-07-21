from __future__ import annotations

"""Pure analytics over the era ledger. Does not change bankroll/phase/risk math."""

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from nt.bets_io import band_roi_stats, fnum, odds_band as classify_odds_band


SETTLED = frozenset({"Win", "Loss", "Refunded"})
BAND_ORDER = ["<1.5", "1.5-1.8", "1.8-2.2", "2.2-2.5", "2.5-3.0", ">=3.0"]
WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

DATE_RANGE_PRESETS: list[tuple[str, str, int | None]] = [
    ("1d", "1 day", 1),
    ("3d", "3 days", 3),
    ("1w", "1 week", 7),
    ("2w", "2 weeks", 14),
    ("1m", "1 month", 30),
    ("3m", "3 months", 90),
    ("all", "All time", None),
]


def date_range_bounds(
    key: str,
    *,
    today: date | None = None,
    era_start: str | None = None,
) -> tuple[str | None, str | None, str]:
    """Return (date_from, date_to, label) as ISO dates inclusive."""
    today = today or date.today()
    label = "All time"
    days: int | None = None
    for k, lab, d in DATE_RANGE_PRESETS:
        if k == key:
            label = lab
            days = d
            break
    else:
        label = "All time"
        days = None

    date_to = today.isoformat()
    if days is None:
        return era_start, date_to, label
    date_from = (today - timedelta(days=days - 1)).isoformat()
    if era_start and date_from < era_start:
        date_from = era_start
    return date_from, date_to, label


def slice_rows_by_date(
    rows: list[dict[str, str]],
    date_from: str | None,
    date_to: str | None,
    *,
    include_pending: bool = False,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in rows:
        if r.get("result") == "Pending":
            if include_pending:
                out.append(r)
            continue
        d = r.get("date") or ""
        if date_from and d < date_from:
            continue
        if date_to and d > date_to:
            continue
        out.append(r)
    return out


def settled_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [r for r in rows if r.get("result") != "Pending"]


def _totals_side(selection: str) -> str | None:
    """Detect Over vs Under from selection text. None if ambiguous."""
    sel = (selection or "").lower()
    # Prefer number-bound tokens: "Over 2.5", "Under 2,5", "over 2.5 mål"
    if re.search(r"(?<![/\w])under\s*[\d,.]", sel) or re.search(
        r"(?<![/\w])under\s+(?:\d|mål|goals?|games?|points?|corners?)", sel
    ):
        return "Under"
    if re.search(r"(?<![/\w])over\s*[\d,.]", sel) or re.search(
        r"(?<![/\w])over\s+(?:\d|mål|goals?|games?|points?|corners?)", sel
    ):
        return "Over"
    # Trailing direction after line: "...: Under 2.5"
    if re.search(r":\s*under\b", sel):
        return "Under"
    if re.search(r":\s*over\b", sel):
        return "Over"
    # Lone side without colliding with market name "over/under"
    has_under = bool(re.search(r"(?<![/\w])under\b", sel))
    has_over = bool(re.search(r"(?<![/\w])over\b", sel))
    if has_under and not has_over:
        return "Under"
    if has_over and not has_under:
        return "Over"
    return None


def infer_market(selection: str, market_type: str = "") -> str:
    """
    Canonical market family for learning + charts.

    Always prefer selection text (and normalized market_type) so we never
    keep raw NT dump strings like "Totalt antall mål - over/under 2.5" as
    separate buckets, and so empty market_type still classifies.

    Totals are split into "Totals Over" / "Totals Under" when the side is
    clear so learning can compare which side actually performs.
    """
    sel = (selection or "").strip()
    sel_l = sel.lower()
    s = f"{sel_l} {(market_type or '').lower()}".strip()

    if "begge lag" in s or "btts" in s or "both teams" in s:
        return "BTTS"
    if "holder nullen" in s or "clean sheet" in s or "clean-sheet" in s:
        return "Clean sheet"
    if "correct score" in s or "riktig resultat" in s or "korrekt resultat" in s:
        return "Correct score"
    if "tilbakebetales" in s or "dnb" in s or "draw no bet" in s:
        return "DNB"

    # Esports maps (totals vs handicap) before generic handicap
    if "kart" in s or re.search(r"\bmaps?\b", s):
        if "total" in s or "over" in s or "under" in s or "totalt" in s:
            side = _totals_side(sel)
            if side == "Over":
                return "Map totals Over"
            if side == "Under":
                return "Map totals Under"
            return "Map totals"
        return "Map handicap"

    # Set handicap (tennis)
    if re.search(r"[+-]\s?\d+(?:[.,]\d+)?\s*sets?\b", sel_l) or (
        "sets" in sel_l and re.search(r"[+-]\s?\d", sel_l)
    ):
        return "Set handicap"

    # Spreads / Asian / run lines / goal lines without the word "handicap"
    if (
        "handikap" in s
        or "handicap" in s
        or "asian" in s
        or re.search(r"[+-]\s?\d+(?:[.,]\d+)?(?:\s*(?:sets?|maps?|games?))?\s*$", sel_l)
        or re.search(r"\s[+-]\s?\d+(?:[.,]\d+)?\s*(?:\(|$)", sel_l)
        or re.search(r"^[a-zæøå0-9 .'/-]+\s+[+-]\s?\d+(?:[.,]\d+)?$", sel_l)
    ):
        return "Handicap"

    if "scorer" in s or "to score" in s or "målscorer" in s or "anytime" in s:
        return "Player props"
    # Period / half totals & 1H result (after player props so "scorer i 1. omgang" stays props)
    if re.search(r"1\.\s*omgang|2\.\s*omgang|1st half|2nd half|first half|second half", s):
        if "hub" in s or "vinner" in s or "uavgjort" in s:
            return "Period result"
        if "over" in s or "under" in s or "totalt" in s:
            return "Period totals"
        return "Period"

    # Place / top-N / outrights (cycling stages, athletics, etc.)
    if (
        re.search(r"\btopp?\s*\d", s)
        or "topp " in s
        or re.search(r"\btop\s*\d", s)
        or "outright" in s
        or "rytter" in s
        or "best leadout" in s
    ):
        return "Place / outright"

    # Motorsport specials
    if (
        "safety car" in s
        or "raskeste runde" in s
        or "fastest lap" in s
        or "formel 1" in s
        or "f1 " in s
    ):
        return "Motorsport"

    # Totals / O-U — split Over vs Under when possible
    is_totals = (
        "totalt" in s
        or "over/under" in s
        or "over under" in s
        or " o/u" in s
        or re.search(r"(?<![/\w])over\b", s) is not None
        or re.search(r"(?<![/\w])under\b", s) is not None
        or (
            "total" in s
            and ("mål" in s or "goal" in s or "game" in s or "point" in s or "corner" in s)
        )
    )
    if is_totals:
        side = _totals_side(sel)
        if side == "Over":
            return "Totals Over"
        if side == "Under":
            return "Totals Under"
        return "Totals"

    # 1X2 / moneyline
    if (
        "to win" in s
        or "vinner" in s
        or "seier" in s
        or "winner" in s
        or sel_l in ("uavgjort", "draw", "x", "1", "2", "1x2")
        or sel_l.startswith("hub")
        or ("uavgjort" in s and "tilbakebetales" not in s)
    ):
        return "Match result"
    if "win" in s:
        return "Match result"

    # Bare team / player name lines (common NT ML dumps without "to Win")
    if sel and not re.search(r"\d", sel_l):
        if "," in sel:  # "Last, First" athlete → outright-ish
            return "Place / outright"
        # short non-keyword string → treat as moneyline
        words = sel_l.split()
        if 1 <= len(words) <= 5 and " vs " not in sel_l and " - " not in f" {sel_l} ":
            return "Match result"

    mt = (market_type or "").strip()
    known = {
        "BTTS",
        "Totals",
        "Totals Over",
        "Totals Under",
        "Match result",
        "DNB",
        "Handicap",
        "Map totals",
        "Map totals Over",
        "Map totals Under",
        "Map handicap",
        "Set handicap",
        "Player props",
        "Clean sheet",
        "Correct score",
        "Place / outright",
        "Motorsport",
        "HUB",
    }
    if mt in known:
        return "Match result" if mt == "HUB" else mt
    if mt == "Combo":
        return "Combo"
    return "Other"


def with_derived(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return shallow copies with market_inferred and high_odds flags."""
    out = []
    for r in rows:
        d = dict(r)
        d["market_inferred"] = infer_market(r.get("selection") or "", r.get("market_type") or "")
        odds = fnum(r.get("decimal_odds"))
        d["high_odds"] = "yes" if odds is not None and odds > 2.5 else "no"
        if not (d.get("odds_band") or "").strip() and odds is not None:
            d["odds_band"] = classify_odds_band(odds)
        src = (r.get("source") or "").strip()
        d["source_group"] = "era_archive" if src == "era_archive" else "live"
        out.append(d)
    return out


def equity_series(rows: list[dict[str, str]], baseline: float) -> list[dict[str, Any]]:
    """Daily end-of-day equity = baseline + cumulative settled P/L."""
    settled = [r for r in rows if r.get("result") != "Pending"]
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or r.get("created_at") or ""))

    out: list[dict[str, Any]] = []
    running_pl = 0.0
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in settled:
        by_date[r.get("date") or ""].append(r)

    for d in sorted(by_date.keys()):
        day_rows = by_date[d]
        day_pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in day_rows)
        day_stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in day_rows)
        wins = sum(1 for r in day_rows if r.get("result") == "Win")
        losses = sum(1 for r in day_rows if r.get("result") == "Loss")
        running_pl = round(running_pl + day_pl, 2)
        out.append(
            {
                "date": d,
                "equity": round(baseline + running_pl, 2),
                "day_pl": round(day_pl, 2),
                "day_stake": round(day_stake, 2),
                "day_n": len(day_rows),
                "day_wins": wins,
                "day_losses": losses,
                "cum_pl": running_pl,
            }
        )
    return out


def daily_pl(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    buckets: dict[str, float] = defaultdict(float)
    n: dict[str, int] = defaultdict(int)
    stake: dict[str, float] = defaultdict(float)
    wins: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.get("result") == "Pending":
            continue
        d = r.get("date") or ""
        buckets[d] += fnum(r.get("p_l_nok")) or 0.0
        n[d] += 1
        stake[d] += fnum(r.get("stake_nok")) or 0.0
        if r.get("result") == "Win":
            wins[d] += 1
    return [
        {
            "date": d,
            "pl": round(buckets[d], 2),
            "n": n[d],
            "stake": round(stake[d], 2),
            "wins": wins[d],
            "roi": (buckets[d] / stake[d]) if stake[d] else 0.0,
        }
        for d in sorted(buckets.keys())
    ]


def daily_volume(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Bets and stake per calendar day (includes pending stakes for that date)."""
    n: dict[str, int] = defaultdict(int)
    stake: dict[str, float] = defaultdict(float)
    for r in rows:
        d = r.get("date") or ""
        n[d] += 1
        stake[d] += fnum(r.get("stake_nok")) or 0.0
    return [{"date": d, "n": n[d], "stake": round(stake[d], 2)} for d in sorted(n.keys())]


def _bucket_stats(items: list[dict[str, str]]) -> dict[str, float]:
    stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in items)
    pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in items)
    wins = sum(1 for r in items if r.get("result") == "Win")
    losses = sum(1 for r in items if r.get("result") == "Loss")
    refunds = sum(1 for r in items if r.get("result") == "Refunded")
    decided = wins + losses
    odds_vals = [fnum(r.get("decimal_odds")) for r in items if fnum(r.get("decimal_odds"))]
    return {
        "n": float(len(items)),
        "wins": float(wins),
        "losses": float(losses),
        "refunds": float(refunds),
        "stake": round(stake, 2),
        "pl": round(pl, 2),
        "roi": (pl / stake) if stake else 0.0,
        "winrate": (wins / decided) if decided else 0.0,
        "avg_odds": (sum(odds_vals) / len(odds_vals)) if odds_vals else 0.0,
        "avg_stake": (stake / len(items)) if items else 0.0,
        "avg_pl": (pl / len(items)) if items else 0.0,
    }


def group_stats(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, float]]:
    """Per-group stats (excludes pending)."""
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if r.get("result") == "Pending":
            continue
        g = (r.get(key) or "").strip() or "(empty)"
        buckets[g].append(r)
    return {g: _bucket_stats(items) for g, items in buckets.items()}


DEFAULT_BET_IDS_CAP = 500


def group_stats_with_ids(
    rows: list[dict[str, str]],
    key: str,
    *,
    id_cap: int = DEFAULT_BET_IDS_CAP,
    include_pending: bool = False,
    key_fn: Any | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Per-group stats plus forensic return path: bet_ids (capped).

    Aggregations are pure query-time over the filtered row list. Storage never
    pre-bundles buckets. Callers drill back via filter_rows(bet_ids=...).

    key_fn: optional (row) -> group key; when set, overrides field `key`.
    """
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if not include_pending and r.get("result") == "Pending":
            continue
        if key_fn is not None:
            g = str(key_fn(r) or "").strip() or "(empty)"
        else:
            g = (r.get(key) or "").strip() or "(empty)"
        buckets[g].append(r)

    out: dict[str, dict[str, Any]] = {}
    cap = max(1, int(id_cap))
    for g, items in buckets.items():
        st = dict(_bucket_stats(items))
        ids = [str(r.get("bet_id") or "") for r in items if r.get("bet_id")]
        truncated = len(ids) > cap
        st["bet_ids"] = ids[:cap]
        st["bet_ids_truncated"] = truncated
        st["bet_ids_cap"] = cap
        st["n_ids"] = float(len(ids))
        out[g] = st
    return out


def group_stats_derived(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, float]]:
    """Like group_stats but runs on with_derived copies."""
    return group_stats(with_derived(rows), key)


def overall_stats(rows: list[dict[str, str]]) -> dict[str, float]:
    settled = [r for r in rows if r.get("result") != "Pending"]
    pending = [r for r in rows if r.get("result") == "Pending"]
    stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in settled)
    pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in settled)
    wins = sum(1 for r in settled if r.get("result") == "Win")
    losses = sum(1 for r in settled if r.get("result") == "Loss")
    refunds = sum(1 for r in settled if r.get("result") == "Refunded")
    decided = wins + losses
    odds_vals = [fnum(r.get("decimal_odds")) for r in settled if fnum(r.get("decimal_odds"))]
    stake_vals = [fnum(r.get("stake_nok")) or 0.0 for r in settled]
    gross_win = sum(fnum(r.get("p_l_nok")) or 0.0 for r in settled if (fnum(r.get("p_l_nok")) or 0) > 0)
    gross_loss = abs(sum(fnum(r.get("p_l_nok")) or 0.0 for r in settled if (fnum(r.get("p_l_nok")) or 0) < 0))
    high = [r for r in settled if (fnum(r.get("decimal_odds")) or 0) > 2.5]
    high_pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in high)
    high_stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in high)
    dates = sorted({r.get("date") for r in settled if r.get("date")})
    days = len(dates)
    return {
        "n_settled": float(len(settled)),
        "n_pending": float(len(pending)),
        "wins": float(wins),
        "losses": float(losses),
        "refunds": float(refunds),
        "stake": round(stake, 2),
        "pl": round(pl, 2),
        "roi": (pl / stake) if stake else 0.0,
        "winrate": (wins / decided) if decided else 0.0,
        "avg_odds": (sum(odds_vals) / len(odds_vals)) if odds_vals else 0.0,
        "avg_stake": (sum(stake_vals) / len(stake_vals)) if stake_vals else 0.0,
        "median_odds": _median(odds_vals) if odds_vals else 0.0,
        "min_odds": min(odds_vals) if odds_vals else 0.0,
        "max_odds": max(odds_vals) if odds_vals else 0.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss else (999.0 if gross_win else 0.0),
        "gross_win": round(gross_win, 2),
        "gross_loss": round(gross_loss, 2),
        "high_odds_n": float(len(high)),
        "high_odds_pl": round(high_pl, 2),
        "high_odds_roi": (high_pl / high_stake) if high_stake else 0.0,
        "active_days": float(days),
        "bets_per_day": (len(settled) / days) if days else 0.0,
        "stake_per_day": (stake / days) if days else 0.0,
        "pl_per_day": (pl / days) if days else 0.0,
        "expectancy": (pl / len(settled)) if settled else 0.0,
        "yield_per_bet": (pl / len(settled)) if settled else 0.0,
    }


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def drawdown_series(equity_pts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    peak = None
    out: list[dict[str, Any]] = []
    for p in equity_pts:
        eq = float(p["equity"])
        if peak is None or eq > peak:
            peak = eq
        dd = round(peak - eq, 2) if peak is not None else 0.0
        dd_pct = (dd / peak) if peak else 0.0
        out.append({"date": p["date"], "equity": eq, "drawdown": dd, "drawdown_pct": dd_pct, "peak": peak})
    return out


def max_drawdown(equity_pts: list[dict[str, Any]]) -> float:
    series = drawdown_series(equity_pts)
    if not series:
        return 0.0
    return max(s["drawdown"] for s in series)


def current_streak(rows: list[dict[str, str]]) -> dict[str, Any]:
    settled = [r for r in rows if r.get("result") in ("Win", "Loss")]
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or ""))
    if not settled:
        return {"type": None, "length": 0}
    last = settled[-1].get("result")
    n = 0
    for r in reversed(settled):
        if r.get("result") == last:
            n += 1
        else:
            break
    return {"type": last, "length": n}


def streak_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    settled = [r for r in rows if r.get("result") in ("Win", "Loss")]
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or ""))
    max_w = max_l = cur_w = cur_l = 0
    for r in settled:
        if r.get("result") == "Win":
            cur_w += 1
            cur_l = 0
            max_w = max(max_w, cur_w)
        else:
            cur_l += 1
            cur_w = 0
            max_l = max(max_l, cur_l)
    return {
        "max_win_streak": max_w,
        "max_loss_streak": max_l,
        "current": current_streak(rows),
    }


def recent_settlements(rows: list[dict[str, str]], n: int = 10) -> list[dict[str, str]]:
    settled = [r for r in rows if r.get("result") != "Pending"]
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or ""), reverse=True)
    return settled[:n]


def band_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    return band_roi_stats(rows)


def weekday_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if r.get("result") == "Pending":
            continue
        d = r.get("date") or ""
        try:
            wd = datetime.strptime(d, "%Y-%m-%d").strftime("%a")
        except ValueError:
            wd = "?"
        buckets[wd].append(r)
    return {k: _bucket_stats(v) for k, v in buckets.items()}


def stake_bucket_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    def bucket(stake: float) -> str:
        if stake < 12:
            return "10–11"
        if stake < 15:
            return "12–14"
        if stake < 20:
            return "15–19"
        return "20+"

    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if r.get("result") == "Pending":
            continue
        s = fnum(r.get("stake_nok")) or 0.0
        buckets[bucket(s)].append(r)
    return {k: _bucket_stats(v) for k, v in buckets.items()}


def odds_histogram(rows: list[dict[str, str]], bins: list[float] | None = None) -> list[dict[str, Any]]:
    """Count settled bets per odds interval."""
    edges = bins or [1.0, 1.3, 1.5, 1.7, 1.9, 2.1, 2.5, 3.0, 4.0, 10.0]
    settled = [r for r in rows if r.get("result") != "Pending"]
    counts = [0] * (len(edges) - 1)
    pl_sum = [0.0] * (len(edges) - 1)
    for r in settled:
        o = fnum(r.get("decimal_odds"))
        if o is None:
            continue
        for i in range(len(edges) - 1):
            if edges[i] <= o < edges[i + 1] or (i == len(edges) - 2 and o >= edges[i]):
                counts[i] += 1
                pl_sum[i] += fnum(r.get("p_l_nok")) or 0.0
                break
    out = []
    for i in range(len(edges) - 1):
        label = f"{edges[i]:g}–{edges[i+1]:g}"
        out.append({"label": label, "n": counts[i], "pl": round(pl_sum[i], 2)})
    return out


def rolling_metrics(rows: list[dict[str, str]], window: int = 20) -> list[dict[str, Any]]:
    """Per settled bet: rolling ROI and winrate over last `window` settled bets."""
    settled = [r for r in rows if r.get("result") != "Pending"]
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or ""))
    out: list[dict[str, Any]] = []
    for i in range(len(settled)):
        start = max(0, i - window + 1)
        window_rows = settled[start : i + 1]
        stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in window_rows)
        pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in window_rows)
        wins = sum(1 for r in window_rows if r.get("result") == "Win")
        losses = sum(1 for r in window_rows if r.get("result") == "Loss")
        decided = wins + losses
        out.append(
            {
                "i": i,
                "date": settled[i].get("date"),
                "rolling_roi": (pl / stake) if stake else 0.0,
                "rolling_wr": (wins / decided) if decided else 0.0,
                "rolling_pl": round(pl, 2),
                "window_n": len(window_rows),
            }
        )
    return out


def best_worst_bets(rows: list[dict[str, str]], n: int = 8) -> dict[str, list[dict[str, str]]]:
    settled = [r for r in rows if r.get("result") != "Pending"]
    by_pl = sorted(settled, key=lambda r: fnum(r.get("p_l_nok")) or 0.0)
    return {
        "worst": by_pl[:n],
        "best": list(reversed(by_pl[-n:])),
    }


def top_bottom_groups(
    stats: dict[str, dict[str, float]],
    *,
    min_n: int = 3,
    top: int = 5,
) -> dict[str, list[tuple[str, dict[str, float]]]]:
    items = [(k, v) for k, v in stats.items() if v.get("n", 0) >= min_n]
    by_pl = sorted(items, key=lambda kv: kv[1].get("pl", 0.0), reverse=True)
    return {"best": by_pl[:top], "worst": list(reversed(by_pl[-top:]))}


def calendar_cells(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """One cell per day for heatmap-style views."""
    return daily_pl(rows)


def archive_vs_live(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    return group_stats_derived(rows, "source_group")


def market_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    return group_stats_derived(rows, "market_inferred")


def high_odds_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    return group_stats_derived(rows, "high_odds")


def concentration(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Share of volume in top sport / top band."""
    settled = [r for r in rows if r.get("result") != "Pending"]
    if not settled:
        return {"top_sport": None, "top_sport_pct": 0.0, "football_pct": 0.0}
    by_sport = group_stats(settled, "sport")
    top = max(by_sport.items(), key=lambda kv: kv[1]["n"])
    foot = by_sport.get("football", {}).get("n", 0)
    return {
        "top_sport": top[0],
        "top_sport_n": top[1]["n"],
        "top_sport_pct": top[1]["n"] / len(settled),
        "football_pct": foot / len(settled),
        "n_sports": float(len(by_sport)),
    }


def phase_progress(cfg: dict[str, Any], equity: float, settled_count: int, phase: dict[str, Any]) -> dict[str, Any]:
    """Distance to next phase unlocks from config ladder (desk-friendly absolute %)."""
    phases = cfg.get("phases") or {}
    order = list(phases.keys())
    current = phase.get("phase_id")
    nxt = phase.get("next")
    if not nxt or nxt not in phases:
        return {
            "current": current,
            "next": None,
            "next_label": None,
            "equity_needed": 0.0,
            "settled_needed": 0,
            "equity_progress": 1.0,
            "count_progress": 1.0,
            "equity_now": equity,
            "equity_target": equity,
            "settled_now": settled_count,
            "settled_target": settled_count,
            "equity_phase": phase.get("equity_phase"),
            "count_phase": phase.get("count_phase"),
        }
    target = phases[nxt]
    enter_eq = float(target.get("enter_equity") or 0)
    enter_n = int(target.get("enter_settled") or 0)
    # Absolute progress toward next enter thresholds (clearer than span-from-current)
    eq_prog = min(1.0, max(0.0, equity / enter_eq)) if enter_eq > 0 else 1.0
    n_prog = min(1.0, max(0.0, settled_count / enter_n)) if enter_n > 0 else 1.0
    return {
        "current": current,
        "next": nxt,
        "next_label": target.get("label"),
        "equity_now": equity,
        "equity_target": enter_eq,
        "equity_needed": max(0.0, enter_eq - equity),
        "settled_now": settled_count,
        "settled_target": enter_n,
        "settled_needed": max(0, enter_n - settled_count),
        "equity_progress": eq_prog,
        "count_progress": n_prog,
        "equity_phase": phase.get("equity_phase"),
        "count_phase": phase.get("count_phase"),
        "phase_order": order,
    }


def deep_dive(
    rows: list[dict[str, str]],
    baseline: float,
    cfg: dict[str, Any] | None = None,
    phase: dict[str, Any] | None = None,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    range_key: str = "all",
    range_label: str = "All time",
) -> dict[str, Any]:
    """
    Analytics payload. Optional date_from/date_to (ISO, inclusive) scopes settled stats.
    Equity curve is full-era then sliced so levels stay consistent with bankroll math.
    Phase progress always uses live full-era phase/equity (not period-filtered).
    """
    # Full curve for correct equity levels, then window
    full_curve = equity_series(rows, baseline)
    if date_from or date_to:
        curve = [
            p
            for p in full_curve
            if (not date_from or p["date"] >= date_from) and (not date_to or p["date"] <= date_to)
        ]
        scoped = slice_rows_by_date(rows, date_from, date_to, include_pending=False)
    else:
        curve = full_curve
        scoped = [r for r in rows if r.get("result") != "Pending"]
        # keep pending count in overall via full rows for n_pending
        scoped = rows

    # When filtering, overall should reflect only period settled + still show pending from full book
    if date_from or date_to:
        period_settled = slice_rows_by_date(rows, date_from, date_to, include_pending=False)
        pending = [r for r in rows if r.get("result") == "Pending"]
        scoped_for_stats = period_settled + pending
    else:
        scoped_for_stats = rows
        period_settled = [r for r in rows if r.get("result") != "Pending"]

    overall = overall_stats(scoped_for_stats)
    return {
        "overall": overall,
        "equity_curve": curve,
        "daily": daily_pl(period_settled),
        "volume": daily_volume(period_settled),
        "drawdown": drawdown_series(curve),
        "max_drawdown": max_drawdown(curve),
        "streaks": streak_stats(period_settled),
        "bands": band_stats(period_settled),
        "by_band": group_stats(period_settled, "odds_band"),
        "by_sport": group_stats(period_settled, "sport"),
        "by_phase": group_stats(period_settled, "phase"),
        "by_grade": group_stats(period_settled, "research_grade"),
        "by_market": market_stats(period_settled),
        "by_weekday": weekday_stats(period_settled),
        "by_stake_bucket": stake_bucket_stats(period_settled),
        "by_source": archive_vs_live(period_settled),
        "by_high_odds": high_odds_stats(period_settled),
        "odds_hist": odds_histogram(period_settled),
        "rolling_20": rolling_metrics(period_settled, 20),
        "rolling_40": rolling_metrics(period_settled, 40),
        "best_worst": best_worst_bets(period_settled, 8),
        "concentration": concentration(period_settled),
        "recent": recent_settlements(period_settled, 15),
        "notes_count": sum(1 for r in period_settled if (r.get("notes") or "").strip()),
        "date_from": date_from or (min((r.get("date") or "9999") for r in period_settled) if period_settled else None),
        "date_to": date_to or (max((r.get("date") or "") for r in period_settled) if period_settled else None),
        "range_key": range_key,
        "range_label": range_label,
        "period_n": len(period_settled),
        "phase_progress": phase_progress(
            cfg or {},
            float((phase or {}).get("equity_nok") or baseline + overall_stats(rows).get("pl", 0)),
            int((phase or {}).get("settled_count") or overall_stats(rows).get("n_settled") or 0),
            phase or {},
        )
        if cfg and phase
        else {},
    }


def _as_str_list(val: str | list[str] | None) -> list[str] | None:
    """Normalize filter values: None / empty list = no filter; str = single."""
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else None
    out = [str(x).strip() for x in val if str(x).strip()]
    return out or None


def filter_rows(
    rows: list[dict[str, str]],
    *,
    sport: str | list[str] | None = None,
    odds_band: str | list[str] | None = None,
    result: str | list[str] | None = None,
    phase: str | list[str] | None = None,
    grade: str | list[str] | None = None,
    source: str | list[str] | None = None,
    market: str | list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    query: str | None = None,
    bet_ids: str | list[str] | None = None,
) -> list[dict[str, str]]:
    """
    Filter ledger rows (query-time grain). Categorical dims accept str or list[str].

    bet_ids: exact forensic drill-down from aggregate buckets (chart → tickets).
    """
    out = rows

    ids = _as_str_list(bet_ids)
    if ids is not None:
        id_set = set(ids)
        out = [r for r in out if str(r.get("bet_id") or "") in id_set]

    sports = _as_str_list(sport)
    if sports is not None:
        out = [r for r in out if (r.get("sport") or "") in sports]

    bands = _as_str_list(odds_band)
    if bands is not None:
        out = [r for r in out if (r.get("odds_band") or "") in bands]

    results = _as_str_list(result)
    if results is not None:
        out = [r for r in out if (r.get("result") or "") in results]

    phases = _as_str_list(phase)
    if phases is not None:
        out = [r for r in out if (r.get("phase") or "") in phases]

    grades = _as_str_list(grade)
    if grades is not None:
        out = [r for r in out if (r.get("research_grade") or "") in grades]

    sources = _as_str_list(source)
    if sources is not None:
        # Preserve legacy live/era_archive shortcuts alongside multi raw sources
        def _src_ok(r: dict[str, str]) -> bool:
            raw = (r.get("source") or "").strip()
            for s in sources:
                if s == "era_archive" and raw == "era_archive":
                    return True
                if s == "live" and raw != "era_archive":
                    return True
                if s == raw:
                    return True
            return False

        out = [r for r in out if _src_ok(r)]

    markets = _as_str_list(market)
    if markets is not None:
        mset = set(markets)
        out = [
            r
            for r in out
            if infer_market(r.get("selection") or "", r.get("market_type") or "") in mset
        ]

    if date_from:
        out = [r for r in out if (r.get("date") or "") >= date_from]
    if date_to:
        out = [r for r in out if (r.get("date") or "") <= date_to]
    if query:
        q = query.lower().strip()
        # Support id: prefix for exact bet_id forensic search
        if q.startswith("id:"):
            want = q[3:].strip()
            out = [r for r in out if str(r.get("bet_id") or "").lower() == want]
        else:
            out = [
                r
                for r in out
                if q in (r.get("match") or "").lower()
                or q in (r.get("selection") or "").lower()
                or q in (r.get("notes") or "").lower()
                or q in str(r.get("bet_id") or "").lower()
            ]
    return out
