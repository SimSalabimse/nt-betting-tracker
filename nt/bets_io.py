from __future__ import annotations

import csv
import hashlib
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BET_HEADER = [
    "bet_id",
    "date",
    "match",
    "selection",
    "decimal_odds",
    "stake_nok",
    "result",
    "p_l_nok",
    "payout_nok",
    "sport",
    "market_type",
    "odds_band",
    "research_grade",
    "phase",
    "notes",
    "source",
    "created_at",
    "updated_at",
]

# Ledger result states (real-money control plane)
# - Pending: recommend intent — NOT confirmed on NT (counts as open risk)
# - ConfirmedPlaced: user/agent confirmed ticket is live on NT (open risk)
# - Win / Loss / Refunded: terminal settled outcomes
# - Abandoned: never placed / abandoned intent — P/L 0, NOT open risk, NOT phase sample
VALID_RESULTS = {
    "Pending",
    "ConfirmedPlaced",
    "Win",
    "Loss",
    "Refunded",
    "Abandoned",
}
OPEN_RISK_RESULTS = frozenset({"Pending", "ConfirmedPlaced"})
PERFORMANCE_SETTLED_RESULTS = frozenset({"Win", "Loss", "Refunded"})
TERMINAL_RESULTS = frozenset({"Win", "Loss", "Refunded", "Abandoned"})


def is_open_risk(result: str | None) -> bool:
    """True if stake still counts against daily risk / pending exposure."""
    return (result or "") in OPEN_RISK_RESULTS


def is_performance_settled(result: str | None) -> bool:
    """True for outcomes that count as settled sample (phase unlock / ROI)."""
    return (result or "") in PERFORMANCE_SETTLED_RESULTS


def is_terminal(result: str | None) -> bool:
    return (result or "") in TERMINAL_RESULTS


def settlement_calendar_day(
    row: dict[str, str],
    *,
    tz_name: str = "Europe/Oslo",
) -> str:
    """
    Calendar day when the bet was settled/abandoned (Europe/Oslo).

    Prefer ``updated_at`` (UTC ISO) converted to local calendar day — NOT match
    kickoff ``date``. Fallback to match ``date`` only if updated_at missing.
    """
    ua = (row.get("updated_at") or "").strip()
    if ua:
        try:
            raw = ua.replace("Z", "+00:00") if ua.endswith("Z") else ua
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            try:
                from zoneinfo import ZoneInfo

                local = dt.astimezone(ZoneInfo(tz_name))
            except Exception:
                # Windows without tzdata: approximate CEST as UTC+2 for July audit era
                from datetime import timedelta

                local = dt.astimezone(timezone(timedelta(hours=2)))
            return local.date().isoformat()
        except ValueError:
            if len(ua) >= 10 and ua[4] == "-" and ua[7] == "-":
                return ua[:10]
    return (row.get("date") or "")[:10]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fnum(x: Any) -> float | None:
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    return float(s.replace(",", "."))


def fmt_num(x: float | None, nd: int = 2) -> str:
    if x is None:
        return ""
    s = f"{x:.{nd}f}".rstrip("0").rstrip(".")
    return s


def odds_band(odds: float | None) -> str:
    if odds is None:
        return ""
    if odds < 1.5:
        return "<1.5"
    if odds < 1.8:
        return "1.5-1.8"
    if odds < 2.2:
        return "1.8-2.2"
    if odds < 2.5:
        return "2.2-2.5"
    if odds < 3.0:
        return "2.5-3.0"
    return ">=3.0"


def make_bet_id(date: str, match: str, selection: str, odds: float, stake: float, salt: str = "") -> str:
    raw = f"{date}|{match}|{selection}|{odds}|{stake}|{salt}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def load_bets(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != BET_HEADER:
            # tolerate subset / re-order if all required present
            required = {"bet_id", "date", "match", "selection", "decimal_odds", "stake_nok", "result"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError(f"Invalid bets header in {path}: {reader.fieldnames}")
        return list(reader)


def write_bets(path: Path, rows: list[dict[str, str]], backup: bool = True) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if backup and path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(path.suffix + f".backup_{ts}")
        shutil.copy2(path, backup_path)

    # normalize rows to header
    out_rows = []
    for r in rows:
        out_rows.append({k: r.get(k, "") for k in BET_HEADER})

    fd, tmp = tempfile.mkstemp(prefix="bets_", suffix=".csv", dir=str(path.parent))
    try:
        import os

        os.close(fd)
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=BET_HEADER, lineterminator="\n")
            w.writeheader()
            w.writerows(out_rows)
        Path(tmp).replace(path)
    finally:
        if Path(tmp).exists():
            Path(tmp).unlink(missing_ok=True)
    return backup_path


def validate_bets(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for i, r in enumerate(rows, start=1):
        if r.get("bet_id") in ids:
            errors.append(f"Row {i}: duplicate bet_id {r.get('bet_id')}")
        ids.add(r.get("bet_id") or "")
        res = r.get("result") or ""
        if res not in VALID_RESULTS:
            errors.append(f"Row {i}: invalid result {res!r}")
        odds = fnum(r.get("decimal_odds"))
        stake = fnum(r.get("stake_nok"))
        if odds is None or odds < 1.01:
            errors.append(f"Row {i}: bad odds")
        if stake is None or stake < 0:
            errors.append(f"Row {i}: bad stake")
        if is_open_risk(res):
            if r.get("p_l_nok") not in ("", None):
                errors.append(f"Row {i}: {res} must have empty p_l_nok")
        elif res == "Abandoned":
            pl = fnum(r.get("p_l_nok"))
            if pl is None:
                errors.append(f"Row {i}: Abandoned missing p_l_nok (expect 0)")
            elif abs(pl) > 1e-9:
                errors.append(f"Row {i}: Abandoned must have p_l_nok 0 (got {pl})")
        else:
            pl = fnum(r.get("p_l_nok"))
            if pl is None:
                errors.append(f"Row {i}: settled bet missing p_l_nok")
        if stake is not None and stake < 10 and not is_open_risk(res):
            # historical may have been ok; only warn via soft — min stake for NEW is enforced elsewhere
            pass
    return errors


def pending_stake_total(rows: list[dict[str, str]]) -> float:
    """Open risk: Pending + ConfirmedPlaced stakes only (Abandoned excluded)."""
    total = 0.0
    for r in rows:
        if is_open_risk(r.get("result")):
            s = fnum(r.get("stake_nok")) or 0.0
            total += s
    return round(total, 2)


def settled_pl_sum(rows: list[dict[str, str]]) -> float:
    """Equity P/L: all terminal rows with p_l (Abandoned contributes 0)."""
    total = 0.0
    for r in rows:
        if is_open_risk(r.get("result")):
            continue
        pl = fnum(r.get("p_l_nok"))
        if pl is not None:
            total += pl
    return round(total, 2)


def settled_count(rows: list[dict[str, str]]) -> int:
    """Phase unlock sample: Win/Loss/Refunded only (not Abandoned / open)."""
    return sum(1 for r in rows if is_performance_settled(r.get("result")))


def band_roi_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Return per odds_band: n, stake, pl, roi."""
    buckets: dict[str, list[tuple[float, float]]] = {}
    for r in rows:
        if not is_performance_settled(r.get("result")):
            continue
        band = r.get("odds_band") or odds_band(fnum(r.get("decimal_odds")))
        stake = fnum(r.get("stake_nok")) or 0.0
        pl = fnum(r.get("p_l_nok")) or 0.0
        buckets.setdefault(band, []).append((stake, pl))
    out: dict[str, dict[str, float]] = {}
    for band, items in buckets.items():
        stake = sum(s for s, _ in items)
        pl = sum(p for _, p in items)
        out[band] = {
            "n": float(len(items)),
            "stake": stake,
            "pl": pl,
            "roi": (pl / stake) if stake else 0.0,
        }
    return out
