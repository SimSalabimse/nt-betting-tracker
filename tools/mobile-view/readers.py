"""
Build schema_version 1 desk snapshot from on-disk state files.

No nt.* imports — pure file reads so the mobile surface cannot mutate engines.
Charts are derived from data/bets.csv + bankroll baseline (same formulas as Book).

Versions:
  schema_version — wire shape (docs/api/DESK_SCHEMA_V1.md)
  api_version    — this package (VERSION file / version_info.API_VERSION)
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow `from version_info import …` when loaded via importlib in tests.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from version_info import API_VERSION, SCHEMA_VERSION  # noqa: E402

PLACE_EXCERPT_CHARS = 4000
STATUS_EXCERPT_CHARS = 2500

# Package-local identity cache (never under data/state/). Overridable in tests.
_IDENTITY_PATH: Path | None = None

# Core ledger inputs for full-snapshot memory short-circuit (per-file path/mtime_ns/size).
_CORE_INPUT_REL = (
    ("data", "state", "bankroll.json"),
    ("data", "state", "risk.json"),
    ("data", "state", "phase.json"),
    ("data", "state", "capital_segments.json"),
    ("data", "state", "status.md"),
    ("data", "bets.csv"),
    ("outbox", "PLACE_THESE.md"),
)

_ODDS_SUFFIXES = {".txt", ".md", ".csv", ".log", ".odds"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json_bytes(obj: dict) -> bytes:
    """Canonical JSON for content fingerprint (sorted keys, compact, UTF-8)."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def fingerprint_desk(body: dict) -> str:
    """Hash desk content identity. Input must not include generated_at or content_hash."""
    payload = {k: v for k, v in body.items() if k not in ("generated_at", "content_hash")}
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return digest[:16]


def _identity_file_path() -> Path:
    if _IDENTITY_PATH is not None:
        return _IDENTITY_PATH
    return _HERE / ".cache" / "desk_identity.json"


def _load_identity() -> tuple[str | None, str | None]:
    data = _read_json(_identity_file_path())
    if not data:
        return None, None
    h = data.get("content_hash")
    g = data.get("generated_at")
    if isinstance(h, str) and isinstance(g, str) and h and g:
        return h, g
    return None, None


def _persist_identity(content_hash: str, generated_at: str) -> None:
    """Atomic write of package-local desk identity (temp + os.replace)."""
    path = _identity_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"content_hash": content_hash, "generated_at": generated_at},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        tmp = path.parent / f".desk_identity.{os.getpid()}.tmp"
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp = path.parent / f".desk_identity.{os.getpid()}.tmp"
            if tmp.is_file():
                tmp.unlink()
        except OSError:
            pass


def _file_stat_tuple(path: Path) -> tuple[str, int, int]:
    """(path_posix, mtime_ns, size); missing/unreadable → mtime/size = -1."""
    try:
        st = path.stat()
        return (path.as_posix(), int(st.st_mtime_ns), int(st.st_size))
    except OSError:
        return (path.as_posix(), -1, -1)


def _odds_candidate_paths(root: Path) -> list[Path]:
    """Same selection rules as odds kickoff scan (top 60 per folder, allowed suffixes)."""
    out: list[Path] = []
    for folder in (root / "inbox", root / "outbox"):
        if not folder.is_dir():
            continue
        try:
            files = [p for p in folder.iterdir() if p.is_file()]
        except OSError:
            continue
        files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        for p in files[:60]:
            suf = p.suffix.lower()
            if suf and suf not in _ODDS_SUFFIXES:
                continue
            out.append(p)
    return out


def _input_fingerprint(root: Path) -> tuple[Any, ...]:
    """Explicit per-file (path, mtime_ns, size) for core inputs + odds candidates."""
    root = Path(root)
    try:
        root_key = str(root.resolve())
    except OSError:
        root_key = str(root)
    core = tuple(_file_stat_tuple(root.joinpath(*parts)) for parts in _CORE_INPUT_REL)
    odds = tuple(_file_stat_tuple(p) for p in _odds_candidate_paths(root))
    return (root_key, core, odds)


@dataclass
class _DeskMemoryCache:
    input_fingerprint: tuple[Any, ...]
    content_hash: str
    generated_at: str
    body: dict[str, Any]


_desk_memory: _DeskMemoryCache | None = None


def clear_desk_cache() -> None:
    """Drop in-process full-snapshot cache (tests / process restart simulation)."""
    global _desk_memory
    _desk_memory = None


def _debug_log(msg: str) -> None:
    if os.environ.get("MOBILE_VIEW_DEBUG", "").strip() in ("1", "true", "yes"):
        print(f"[mobile-view] {msg}", file=sys.stderr)


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


_KO_NOTE_RE = re.compile(
    r"kickoff\s*=\s*(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})",
    re.IGNORECASE,
)
_KO_LINE_RE = re.compile(
    r"(?i)kick[- ]?off\s*:\s*(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?",
)


def _extract_kickoff(notes: str | None) -> str | None:
    """Pull wall-clock kickoff from ledger notes (`kickoff=YYYY-MM-DD HH:MM`).

    Operator times are Europe/Oslo wall clock (same as recommend notes). Returns
    normalized ``YYYY-MM-DD HH:MM`` or None.
    """
    text = notes or ""
    m = _KO_NOTE_RE.search(text)
    if not m:
        return None
    return f"{m.group(1)} {m.group(2)}"


def _norm_match_key(match: str | None) -> str:
    s = re.sub(r"\s+", " ", (match or "").strip().lower())
    # Collapse common separators so "A vs B" / "A – B" still match.
    s = s.replace(" vs. ", " vs ").replace(" – ", " vs ").replace(" — ", " vs ")
    return s


def _match_sides(match: str | None) -> list[str]:
    """Split 'Home vs Away' into side tokens for fuzzy odds-dump lookup."""
    key = _norm_match_key(match)
    if " vs " not in key:
        return [key] if key else []
    return [p.strip() for p in key.split(" vs ", 1) if p.strip()]


def _kickoff_index_from_ledger(rows: list[dict[str, str]]) -> dict[str, str]:
    """match_key → kickoff from any ledger row notes (settled peers help open ones)."""
    index: dict[str, str] = {}
    for r in rows:
        ko = _extract_kickoff(r.get("notes"))
        if not ko:
            continue
        mk = _norm_match_key(r.get("match"))
        if mk and mk not in index:
            index[mk] = ko
        # Also key by match + calendar date for disambiguation.
        d = (r.get("date") or "").strip()[:10]
        if mk and d:
            index.setdefault(f"{mk}|{d}", ko)
    return index


def _index_odds_text(text: str, index: dict[str, str]) -> None:
    """Index Kick-off lines against nearby match titles / side names in odds dumps."""
    # Blocks: blank-line separated (same idea as nt.odds_parse without importing it).
    parts = re.split(r"(?:\r?\n[ \t]*){2,}", text.strip())
    for part in parts:
        lines = [ln.strip() for ln in part.splitlines() if ln.strip()]
        if not lines:
            continue
        ko: str | None = None
        for ln in lines:
            m = _KO_LINE_RE.search(ln)
            if m and m.group(2):
                ko = f"{m.group(1)} {m.group(2)}"
                break
            # Also accept bare kickoff= in paste notes.
            m2 = _KO_NOTE_RE.search(ln)
            if m2:
                ko = f"{m2.group(1)} {m2.group(2)}"
                break
        if not ko:
            continue
        # Prefer explicit "A vs B" line; else HUB/Vinner two-way sides.
        match_name = ""
        for ln in lines:
            low = ln.lower()
            if " vs " in low or " vs. " in low:
                match_name = ln
                break
        if not match_name and len(lines) >= 4:
            # Vinner / HUB style: sideA, odds, sideB, odds — take non-odds name lines.
            names: list[str] = []
            for ln in lines[1:6]:
                if re.fullmatch(r"\d+(?:[.,]\d+)?", ln.replace(",", ".")):
                    continue
                if ln.lower().startswith(("sport:", "kick-off", "kickoff", "hub", "vinner", "event:")):
                    continue
                if ln.lower() in ("uavgjort", "draw", "x", "live"):
                    continue
                names.append(ln)
                if len(names) >= 2:
                    break
            if len(names) >= 2:
                match_name = f"{names[0]} vs {names[1]}"
        if match_name:
            mk = _norm_match_key(match_name)
            if mk:
                index.setdefault(mk, ko)
            for side in _match_sides(match_name):
                if len(side) >= 4:
                    index.setdefault(f"side:{side}", ko)


def _kickoff_index_from_odds_files(root: Path) -> dict[str, str]:
    """Scan inbox / outbox odds dumps (desktop odds list source) for Kick-off times."""
    index: dict[str, str] = {}
    for p in _odds_candidate_paths(root):
        try:
            # Cap read — odds pastes are usually well under this.
            raw = p.read_bytes()[:1_500_000]
            text = raw.decode("utf-8", errors="replace")
        except OSError:
            continue
        if "kick" not in text.lower() and "kickoff" not in text.lower():
            continue
        _index_odds_text(text, index)
    return index


def _resolve_kickoff(
    *,
    notes: str | None,
    match: str | None,
    date: str | None,
    ledger_idx: dict[str, str],
    odds_idx: dict[str, str],
) -> str | None:
    """Resolve kickoff: notes → ledger peers → odds dumps (match / sides)."""
    ko = _extract_kickoff(notes)
    if ko:
        return ko
    mk = _norm_match_key(match)
    d = (date or "").strip()[:10]
    if mk and d and f"{mk}|{d}" in ledger_idx:
        return ledger_idx[f"{mk}|{d}"]
    if mk and mk in ledger_idx:
        return ledger_idx[mk]
    if mk and mk in odds_idx:
        return odds_idx[mk]
    # Side-based: both sides must agree on the same kickoff when possible.
    sides = _match_sides(match)
    if len(sides) == 2:
        a = odds_idx.get(f"side:{sides[0]}")
        b = odds_idx.get(f"side:{sides[1]}")
        if a and a == b:
            return a
        if a and not b:
            return a
        if b and not a:
            return b
    elif len(sides) == 1 and f"side:{sides[0]}" in odds_idx:
        return odds_idx[f"side:{sides[0]}"]
    return None


def _pending_bets(rows: list[dict[str, str]], root: Path | None = None) -> list[dict[str, Any]]:
    open_results = {"Pending", "ConfirmedPlaced"}
    ledger_idx = _kickoff_index_from_ledger(rows)
    odds_idx = _kickoff_index_from_odds_files(root) if root is not None else {}
    out: list[dict[str, Any]] = []
    for r in rows:
        if (r.get("result") or "").strip() not in open_results:
            continue
        match = (r.get("match") or "").strip() or None
        date = (r.get("date") or "").strip() or None
        kickoff = _resolve_kickoff(
            notes=r.get("notes"),
            match=match,
            date=date,
            ledger_idx=ledger_idx,
            odds_idx=odds_idx,
        )
        out.append(
            {
                "bet_id": (r.get("bet_id") or "").strip() or None,
                "date": date,
                "kickoff": kickoff,
                "match": match,
                "selection": (r.get("selection") or "").strip() or None,
                "decimal_odds": _fnum(r.get("decimal_odds")),
                "stake_nok": _fnum(r.get("stake_nok")),
                "result": (r.get("result") or "").strip() or None,
                "sport": (r.get("sport") or "").strip() or None,
                "updated_at": (r.get("updated_at") or "").strip() or None,
            }
        )
    # Soonest kickoff first when known; else newest updated.
    def _sort_key(x: dict[str, Any]) -> tuple:
        ko = x.get("kickoff") or "9999-99-99 99:99"
        return (ko, x.get("updated_at") or "", x.get("date") or "")

    out.sort(key=_sort_key)
    return out


def _split_table_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _normalize_cell(raw: str) -> str:
    s = (raw or "").strip()
    if len(s) >= 4:
        if s.startswith("**") and s.endswith("**"):
            s = s[2:-2]
        elif s.startswith("__") and s.endswith("__"):
            s = s[2:-2]
    if len(s) >= 2:
        if s.startswith("*") and s.endswith("*") and not s.startswith("**"):
            s = s[1:-1]
        elif s.startswith("_") and s.endswith("_") and not s.startswith("__"):
            s = s[1:-1]
    return s.strip()


def _parse_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    t = _normalize_cell(raw)
    if not t or t in ("—", "–", "-", "−"):
        return None
    if "," in t and "." not in t:
        t = t.replace(",", ".")
    else:
        t = t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def _parse_index(raw: str) -> int | None:
    t = (raw or "").strip()
    if not t or t in ("—", "–", "-", "−"):
        return None
    try:
        return int(t)
    except ValueError:
        return None


def _is_separator_row(line: str) -> bool:
    """Markdown table separator like |---|-------|."""
    s = line.strip()
    if not s or "|" not in s:
        return False
    # Only dashes, colons, pipes, spaces
    core = s.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")
    return core == "" and ("-" in s or ":" in s)


def _parse_rows_preview(text: str) -> list[dict[str, Any]]:
    """
    Parse placeable bet rows from PLACE_THESE Markdown into object dicts.

    Shape matches iOS PlaceTheseRowPreview / design § API:
      index, match, selection, decimal_odds, stake_nok, ev, grade, band

    Returns [] when no parseable placeable rows (missing table, NO BETS, garbage).
    schema_version stays 1 — element type is object (iOS tolerant decode required first).
    """
    if not text:
        return []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    header_idx: int | None = None
    col: dict[str, int] = {}
    for i, line in enumerate(lines):
        if "|" not in line.strip():
            continue
        cells = [_normalize_cell(c) for c in _split_table_cells(line)]
        match_i = next((j for j, h in enumerate(cells) if h.lower() == "match"), None)
        sel_i = next((j for j, h in enumerate(cells) if h.lower() == "selection"), None)
        if match_i is None or sel_i is None:
            continue
        col = {"match": match_i, "selection": sel_i}
        for j, h in enumerate(cells):
            lower = h.lower()
            if lower in ("#", "index", "no", "no."):
                col["index"] = j
            elif "odds" in lower:
                col["odds"] = j
            elif "stake" in lower:
                col["stake"] = j
            elif lower == "ev":
                col["ev"] = j
            elif "grade" in lower:
                col["grade"] = j
            elif "band" in lower:
                col["band"] = j
        if "#" in cells:
            col["index"] = cells.index("#")
        header_idx = i
        break

    if header_idx is None:
        return []

    def cell_at(cells: list[str], key: str) -> str:
        j = col.get(key)
        if j is None or j < 0 or j >= len(cells):
            return ""
        return cells[j]

    required = max(col["match"], col["selection"]) + 1
    out: list[dict[str, Any]] = []
    i = header_idx + 1
    while i < len(lines) and _is_separator_row(lines[i]):
        i += 1

    while i < len(lines):
        raw = lines[i]
        trimmed = raw.strip()
        if not trimmed:
            i += 1
            if i < len(lines) and lines[i].strip().startswith("##"):
                break
            continue
        if trimmed.startswith("##"):
            break
        if _is_separator_row(raw):
            i += 1
            continue
        if "|" not in trimmed:
            break

        cells = _split_table_cells(raw)
        if len(cells) < required:
            i += 1
            continue

        match_cell = _normalize_cell(cell_at(cells, "match"))
        selection_cell = _normalize_cell(cell_at(cells, "selection"))

        # Empty slip marker — not a placeable row
        if "no bets" in match_cell.lower():
            i += 1
            continue

        if not match_cell or not selection_cell:
            i += 1
            continue

        index_raw = _normalize_cell(cell_at(cells, "index")) if "index" in col else ""
        grade_raw = _normalize_cell(cell_at(cells, "grade")) if "grade" in col else ""
        band_raw = _normalize_cell(cell_at(cells, "band")) if "band" in col else ""

        row: dict[str, Any] = {
            "index": _parse_index(index_raw),
            "match": match_cell,
            "selection": selection_cell,
            "decimal_odds": _parse_number(cell_at(cells, "odds")) if "odds" in col else None,
            "stake_nok": _parse_number(cell_at(cells, "stake")) if "stake" in col else None,
            "ev": _parse_number(cell_at(cells, "ev")) if "ev" in col else None,
            "grade": grade_raw or None,
            "band": band_raw or None,
        }
        out.append(row)
        i += 1

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
    # Full file for table parse (excerpt may truncate mid-table); excerpt still capped for payload.
    full_text = _read_text(path) or ""
    text = full_text
    if len(text) > PLACE_EXCERPT_CHARS:
        text = text[:PLACE_EXCERPT_CHARS] + "\n…(truncated)"
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0].lstrip("# ").strip() if lines else path.name
    summary = next((ln for ln in lines[1:] if ln and not ln.startswith("#")), None)
    # Prefer full file so late table rows are not lost to excerpt cap.
    rows_preview = _parse_rows_preview(full_text)
    return {
        "exists": True,
        "mtime": mtime_s,
        "title": title,
        "summary_line": summary,
        "text_excerpt": text,
        "rows_preview": rows_preview,
    }


# Open risk never moves equity (same as bankroll.settled_pl_sum / is_open_risk).
_OPEN_RISK = frozenset({"Pending", "ConfirmedPlaced"})
# Terminal outcomes that belong on the equity curve.
_EQUITY_RESULTS = frozenset({"Win", "Loss", "Refunded", "Abandoned"})


def _resolve_baseline(bankroll: dict[str, Any] | None) -> float:
    """Baseline for equity curve — must match Lumina / bankroll.json.

    Prefer ``baseline_nok``. If missing/zero but realized+equity present, back out
    baseline so a refund-only first day still shows **500** not a garbage level.
    """
    b = bankroll or {}
    raw = _fnum(b.get("baseline_nok"))
    if raw is not None and raw > 0:
        return float(raw)
    equity = _fnum(b.get("equity_nok"))
    realized = _fnum(b.get("realized_pl_nok"))
    if equity is not None and realized is not None:
        back = round(float(equity) - float(realized), 2)
        if back > 0:
            return back
    # Clean-restart default used in this project
    return 500.0


def _equity_curve(rows: list[dict[str, str]], baseline: float) -> list[dict[str, Any]]:
    """End-of-day equity by **match date** — aligned with bankroll + Lumina Book.

    - Bucket by ledger ``date`` (match / kickoff calendar day), like ``equity_series``.
    - Only **terminal** rows: Win / Loss / Refunded / Abandoned (never Pending /
      ConfirmedPlaced — open tickets must not move equity).
    - Refunded / Abandoned with empty p_l count as **0** (day stays at baseline).
    - Equity[day] = baseline + cumulative day P/L through that match date.

    Example: one Refunded on 2026-07-25 → ``{date: 25, equity: 500, day_pl: 0}``;
    settled bets on 26th accumulate from there.
    """
    by_date: dict[str, float] = defaultdict(float)
    for r in rows:
        res = (r.get("result") or "").strip()
        if not res or res in _OPEN_RISK:
            continue
        if res not in _EQUITY_RESULTS:
            # Unknown status: only count if a numeric p_l is present (fail-safe).
            pl_unknown = _fnum(r.get("p_l_nok"))
            if pl_unknown is None:
                continue
            pl = pl_unknown
        else:
            pl = _fnum(r.get("p_l_nok"))
            if pl is None:
                # Refunded/Abandoned should be 0; skip Win/Loss with missing p_l.
                if res in ("Refunded", "Abandoned"):
                    pl = 0.0
                else:
                    continue
        d = (r.get("date") or "").strip()[:10]
        if len(d) < 10:
            continue
        by_date[d] += float(pl)

    out: list[dict[str, Any]] = []
    running_pl = 0.0
    for d in sorted(by_date.keys()):
        day_pl = round(by_date[d], 2)
        running_pl = round(running_pl + day_pl, 2)
        out.append(
            {
                "date": d,
                "equity": round(baseline + running_pl, 2),
                "day_pl": day_pl,
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
    """Simple Book-aligned chart series for mobile (most important stats only).

    Full era series always returned; clients may filter by date for range chips.
    Equity levels use bankroll baseline so a refund-only day stays at baseline.
    """
    rows = _load_bets_csv(root / "data" / "bets.csv")
    baseline = _resolve_baseline(bankroll)
    curve = _equity_curve(rows, baseline)
    # Reconcile last point to bankroll equity when state is present (tiny float drift only).
    bank_eq = _fnum((bankroll or {}).get("equity_nok"))
    if curve and bank_eq is not None and abs(curve[-1]["equity"] - float(bank_eq)) <= 0.02:
        curve[-1]["equity"] = round(float(bank_eq), 2)
    dd = _drawdown_series(curve)
    max_dd = max((p["drawdown"] for p in dd), default=0.0)
    daily = [
        {"date": p["date"], "pl": p["day_pl"], "equity": p["equity"]}
        for p in curve
    ]
    return {
        "range_label": "All time (era)",
        "range_key": "all",
        "baseline_nok": baseline,
        "overall": _overall_stats(rows),
        "equity_curve": curve,
        "daily": daily,
        "drawdown": dd,
        "max_drawdown": max_dd,
        "by_sport": _sport_stats(rows),
    }


def _build_desk_body(root: Path) -> dict[str, Any]:
    """
    Build desk dict **without** generated_at / content_hash (fingerprint input).
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

    # Secure Variant A partition (capital_v2): locked secure vs riskable working equity.
    secure_nok = _fnum((risk or {}).get("secure_nok"))
    working_equity = _fnum((risk or {}).get("working_equity_nok"))
    if working_equity is None and equity is not None and secure_nok is not None:
        working_equity = round(float(equity) - float(secure_nok), 2)
    riskable_liquid = _fnum((risk or {}).get("riskable_liquid_nok"))
    segs = _read_json(root / "data" / "state" / "capital_segments.json") or {}
    secure_ref_hwm = _fnum(segs.get("ref_hwm_nok") or segs.get("secure_ref_hwm_nok"))

    # Server-side stale: bankroll clock missing / very old is operator concern only
    stale = bool(warnings)

    charts = build_charts(root, bankroll)

    return {
        "schema_version": SCHEMA_VERSION,
        "api_version": API_VERSION,
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
        # Secure Variant A (additive)
        "secure_nok": secure_nok,
        "working_equity_nok": working_equity,
        "riskable_liquid_nok": riskable_liquid,
        "secure_variant": "A",
        "secure_ref_hwm_nok": secure_ref_hwm,
        "risk_reasons": reasons,
        "pending_bets": _pending_bets(rows, root),
        "place_these": place,
        "status_excerpt": status_text,
        "charts": charts,
    }


def build_desk_snapshot(root: Path) -> dict[str, Any]:
    """
    Schema v1 desk JSON. Optional `charts` key is additive (unknown keys safe for old clients).

    Content identity (api_version ≥ 1.2.0):
      - ``content_hash`` — first 16 hex of SHA-256 over canonical JSON excluding
        ``generated_at`` and ``content_hash``
      - ``generated_at`` — last **content** change time (durable across restarts via
        package-local ``.cache/desk_identity.json``), not HTTP response time
      - In-process memory cache keyed on explicit per-file input fingerprints
    """
    global _desk_memory
    root = Path(root)
    fp = _input_fingerprint(root)
    if _desk_memory is not None and _desk_memory.input_fingerprint == fp:
        _debug_log("cache_hit")
        # Shallow copy so callers cannot mutate the cached body.
        return dict(_desk_memory.body)

    _debug_log("rebuild")
    body = _build_desk_body(root)
    content_hash = fingerprint_desk(body)
    stored_h, stored_g = _load_identity()
    if stored_h == content_hash and stored_g:
        generated_at = stored_g
        _debug_log("identity_reuse")
    else:
        generated_at = _now_iso()
        _persist_identity(content_hash, generated_at)

    # Assignment order: hash first, then generated_at (never hash a body that already
    # has content_hash set — fingerprint_desk already strips both).
    body["content_hash"] = content_hash
    body["generated_at"] = generated_at

    _desk_memory = _DeskMemoryCache(
        input_fingerprint=fp,
        content_hash=content_hash,
        generated_at=generated_at,
        body=body,
    )
    return dict(body)
