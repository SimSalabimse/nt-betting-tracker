"""
Thin multi-agent scan merge helper (Stage 1b).

Parse agent JSONL/JSON (+ best-effort MD), validate against full odds dump,
dedupe by evidence_pair_key, soft family/sport diversity, light-fail drop,
emit MULTI_AGENT_SHORTLIST.md (+ optional JSON) with primary worklist hints.

No place / p_model / ledger writes. Engine deep_queue.json is never rewritten.
PR3 surface: agents A/B/C + conditional D (+ ENGINE top-up / fallback).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from nt.bets_io import is_open_risk
from nt.config import path_from_config
from nt.live_ledger import filter_live_rows
from nt.market_coverage import TIER_1, TIER_2, TIER_3, TIER_4, assign_family, assign_tier
from nt.market_family import market_family
from nt.odds_common import evidence_pair_key, fnum
from nt.odds_parse import parse_odds_file
from nt.sport_taxonomy import normalize_sport

ODDS_TOL_REL = 0.02
MAX_FAMILY_AFTER_MERGE = 2
MAX_PER_SPORT_SOFT = 3
SHORTLIST_MAX = 15
SHORTLIST_MIN = 8
PRIMARY_CAP = 15
AGENT_MAX = 5
AGENT_A_ODDS_LO = 1.40
AGENT_A_ODDS_HI = 1.90
FORCE_SCAN_TOKEN = "force_scan:"
OPEN_FULL_READD_MAX = 1
# Agent D spawn: strict product >40 ⇒ default min lines = 41 (n >= cfg only).
DEFAULT_AGENT_D_MIN_LINES = 41
COVERAGE_TAGS = (
    "coverage_floor:top_promo_scaffold",
    "coverage_floor:sport_rotation",
)
TOP_PROMO_SCAFFOLD_PCT = 0.2
_AGENT_ORDER = ("A", "B", "C", "D", "ENGINE")
_LONG_TAIL_FAMILIES = frozenset(
    {
        "goalscorer",
        "player_stat",
        "corners",
        "cards",
        "special",
        "specials",
        "prop",
        "props",
    }
)
_LONG_TAIL_BLOB_RE = re.compile(
    r"prop|card|corner|shot|målscorer|hjørne|kort|special|spesial|180|"
    r"anytime|player|booking|rødt|scorer",
    re.I,
)
# Explicit main-board markers checked before long-tail (HUB often fails tier rules).
_MAIN_BOARD_BLOB_RE = re.compile(
    r"(?:^|\b)hub(?:\b|:)|"
    r"^vinner(?:\s|\s*\(|:)|to win|"
    r"^uavgjort|\bdraw\b|"
    r"handikap|handicap|"
    r"totalt antall mål\s*-\s*over/under\s*2\.5|"
    r"over/under\s*2\.5|"
    r"\bou\s*2\.5\b|"
    r"dobbel sjanse|double chance|"
    r"\bbtts\b|begge lag scorer(?!\s+og)",
    re.I,
)

_MD_BLOCK_RE = re.compile(
    r"(?P<num>\d+)\.\s*\*\*Match:\*\*\s*(?P<match>.+?)\s*"
    r"(?:-\s*\*\*Selection\s*\+?\s*odds:\*\*\s*(?P<selodds>.+?)\s*)?"
    r"(?:-\s*\*\*Why promising:\*\*\s*(?P<why>.+?)\s*)?"
    r"(?:-\s*\*\*scan_agent:\*\*\s*(?P<agent>\S+)\s*)?",
    re.I | re.S,
)
_SEL_ODDS_RE = re.compile(
    r"^(?P<sel>.+?)\s*@\s*(?P<odds>[\d]+(?:[.,]\d+)?)\s*$"
)


def _normalize_agent_id(raw: object, default: str = "") -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return default
    m = re.search(r"\b([ABCD])\b", s)
    if m:
        return m.group(1)
    if s.startswith("AGENT_"):
        tail = s.split("_", 1)[-1]
        return _normalize_agent_id(tail, default=default)
    if s in _AGENT_ORDER:
        return s
    return default or s[:8]


def match_line_counts(odds_path: Path | str) -> dict[str, Any]:
    """
    Per-match Candidate counts from parse_odds_file (post parser de-dupe).

    lines_count(M) = |{ Candidate rows with match == M }|
    Never reuses market-scan high_volume bool.
    """
    path = Path(odds_path)
    raw = parse_odds_file(path)
    per_match: Counter[str] = Counter()
    for c in raw:
        m = str(getattr(c, "match", "") or "").strip()
        if m:
            per_match[m] += 1
    per = dict(per_match)
    max_n = max(per.values()) if per else 0
    return {
        "odds_file": str(path),
        "per_match": per,
        "max_lines_per_match": int(max_n),
        "total_lines": int(sum(per.values())),
        "match_n": len(per),
    }


def should_spawn_agent_d(
    counts: Mapping[str, Any],
    min_lines: int = DEFAULT_AGENT_D_MIN_LINES,
) -> bool:
    """
    SPAWN_D := exists M such that lines_count(M) >= min_lines.

    Implement as n >= cfg only — never reuse market-scan high_volume (n >= 40).
    Default min_lines=41 so n=40 → false, n=41 → true.
    """
    per = counts.get("per_match") if isinstance(counts, Mapping) else None
    if not isinstance(per, Mapping):
        return False
    thr = int(min_lines)
    return any(int(n) >= thr for n in per.values())


def agent_d_min_lines_from_cfg(cfg: Mapping[str, Any] | None) -> int:
    """Read research.adaptive_scan_agent_d_min_lines (default 41)."""
    if not cfg:
        return DEFAULT_AGENT_D_MIN_LINES
    research = cfg.get("research") if isinstance(cfg, Mapping) else None
    if not isinstance(research, Mapping):
        return DEFAULT_AGENT_D_MIN_LINES
    raw = research.get("adaptive_scan_agent_d_min_lines")
    if raw is None:
        return DEFAULT_AGENT_D_MIN_LINES
    try:
        return int(raw)
    except (TypeError, ValueError):
        return DEFAULT_AGENT_D_MIN_LINES


def _explicit_main_board(selection: str, market_type: str = "") -> bool:
    """HUB / Vinner ML / main HC / primary O2.5 / bare draw — pattern pass."""
    blob = f"{selection} {market_type}".strip()
    return bool(_MAIN_BOARD_BLOB_RE.search(blob))


def is_long_tail(
    selection: str,
    market_type: str = "",
    market_family: str = "",
) -> bool:
    """Long-tail: T2–T4 / prop-family / props|cards|corners|shots|specials spirit."""
    sel = str(selection or "")
    mt = str(market_type or "")
    fam = str(market_family or "").strip().lower()
    # Main-board markers are never long-tail (HUB can fail tier rules → T4_specials).
    if _explicit_main_board(sel, mt):
        return False
    if not fam:
        fam = str(assign_family(sel, mt) or "").lower()
    # Coarse diversify families that are clearly main.
    if any(x in fam for x in ("_ml", "1x2", "moneyline", "handicap")) and not any(
        x in fam for x in ("prop", "player", "corner", "card")
    ):
        return False
    tier = assign_tier(sel, mt)
    if tier in (TIER_2, TIER_3):
        return True
    if tier == TIER_4:
        # T4 is also the unmatched fallback — require prop/special spirit.
        if fam in _LONG_TAIL_FAMILIES or any(
            x in fam for x in ("prop", "corner", "card", "goalscorer", "player", "special", "shot")
        ):
            return True
        blob = f"{sel} {mt}".strip()
        return bool(_LONG_TAIL_BLOB_RE.search(blob))
    if fam in _LONG_TAIL_FAMILIES:
        return True
    if any(
        x in fam
        for x in ("prop", "corner", "card", "goalscorer", "player", "special", "shot")
    ):
        return True
    blob = f"{sel} {mt}".strip()
    return bool(_LONG_TAIL_BLOB_RE.search(blob))


def is_main_board(
    selection: str,
    market_type: str = "",
    market_family: str = "",
) -> bool:
    """
    Main board: HUB / Vinner ML / main HC / primary O2.5 / bare draw — T1_main style.
    Explicit main markers win; otherwise long-tail wins over weak T1 fallback.
    """
    sel = str(selection or "")
    mt = str(market_type or "")
    fam = str(market_family or "").strip().lower()
    if _explicit_main_board(sel, mt):
        return True
    if is_long_tail(sel, mt, fam):
        return False
    tier = assign_tier(sel, mt)
    if tier == TIER_1:
        return True
    if any(
        x in fam
        for x in (
            "_ml",
            "moneyline",
            "1x2",
            "handicap",
            "ou_25",
            "draw",
            "btts",
        )
    ):
        if "prop" in fam or "player" in fam:
            return False
        return True
    # football_totals O2.5 only (not corners/cards mis-tagged as totals)
    if "total" in fam and re.search(r"2\.5", f"{sel} {mt}"):
        if not _LONG_TAIL_BLOB_RE.search(f"{sel} {mt}"):
            return True
    return False


def run_scan_depth(
    cfg: Mapping[str, Any] | None,
    odds: Path | str,
    *,
    min_lines: int | None = None,
) -> dict[str, Any]:
    """
    Compute per-match line counts and Agent D spawn flag for Stage 1b.
    """
    thr = int(min_lines) if min_lines is not None else agent_d_min_lines_from_cfg(cfg)
    counts = match_line_counts(odds)
    spawn = should_spawn_agent_d(counts, min_lines=thr)
    over = sorted(
        m for m, n in (counts.get("per_match") or {}).items() if int(n) >= thr
    )
    return {
        **counts,
        "min_lines": thr,
        "spawn_agent_d": bool(spawn),
        "matches_over_threshold": over,
        "agent_d": (
            f"spawned (max_lines_per_match={counts.get('max_lines_per_match')}, "
            f"min_lines={thr})"
            if spawn
            else (
                f"skipped (max_lines_per_match={counts.get('max_lines_per_match')}, "
                f"min_lines={thr})"
            )
        ),
    }


def _agents_list(raw: object, default_agent: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(raw, (list, tuple)):
        for x in raw:
            a = _normalize_agent_id(x, default="")
            if a and a not in out:
                out.append(a)
    else:
        s = str(raw or "").strip()
        if s:
            parts = re.split(r"[+,/|\s]+", s)
            for p in parts:
                a = _normalize_agent_id(p, default="")
                if a and a not in out:
                    out.append(a)
    if not out and default_agent:
        a = _normalize_agent_id(default_agent, default="")
        if a:
            out.append(a)
    out.sort(key=lambda x: (_AGENT_ORDER.index(x) if x in _AGENT_ORDER else 99, x))
    return out


def _cand_from_dict(
    d: Mapping[str, Any], *, default_agent: str = ""
) -> dict[str, Any] | None:
    if not isinstance(d, Mapping):
        return None
    match = str(d.get("match") or "").strip()
    selection = str(d.get("selection") or "").strip()
    if not match or not selection:
        return None
    odds = fnum(d.get("decimal_odds") if d.get("decimal_odds") is not None else d.get("odds"))
    agents = _agents_list(
        d.get("scan_agents") if d.get("scan_agents") is not None else d.get("scan_agent"),
        default_agent=default_agent,
    )
    reason = str(
        d.get("scan_reason") or d.get("reason") or d.get("why") or ""
    ).strip()
    sport = str(d.get("sport") or "").strip()
    market_type = str(d.get("market_type") or "").strip()
    light = str(d.get("light_verdict") or d.get("light") or "").strip().lower()
    promo = fnum(d.get("promo_score") if d.get("promo_score") is not None else d.get("promotion_score"))
    fam = str(d.get("market_family") or "").strip()
    role = str(d.get("role") or "").strip()
    return {
        "match": match,
        "selection": selection,
        "decimal_odds": odds,
        "sport": sport,
        "market_type": market_type,
        "market_family": fam,
        "scan_agents": agents,
        "scan_reason": reason,
        "role": role,
        "light_verdict": light,
        "promo_score": float(promo or 0.0),
        "in_engine_deep_queue": bool(d.get("in_engine_deep_queue") or False),
        "notes": str(d.get("notes") or "").strip(),
    }


def _parse_json_payload(text: str, *, default_agent: str = "") -> list[dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        if isinstance(data.get("candidates"), list):
            rows = data["candidates"]
        elif data.get("match") and data.get("selection"):
            rows = [data]
        else:
            rows = []
    else:
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        c = _cand_from_dict(r, default_agent=default_agent)
        if c:
            out.append(c)
    return out


def _parse_jsonl(text: str, *, default_agent: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("//"):
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        c = _cand_from_dict(obj, default_agent=default_agent)
        if c:
            out.append(c)
    return out


def _parse_md_best_effort(text: str, *, default_agent: str = "") -> list[dict[str, Any]]:
    """Best-effort MD template parser (JSONL remains primary)."""
    out: list[dict[str, Any]] = []
    chunks = re.split(r"(?m)(?=^\d+\.\s)", text)
    for chunk in chunks:
        if not re.match(r"^\d+\.", chunk.strip()):
            continue
        m_match = re.search(r"\*\*Match:\*\*\s*(.+)", chunk, re.I)
        if not m_match:
            continue
        match = m_match.group(1).strip()
        sel = ""
        odds: float | None = None
        m_sel = re.search(r"\*\*Selection\s*\+?\s*odds:\*\*\s*(.+)", chunk, re.I)
        if m_sel:
            raw = m_sel.group(1).strip()
            mo = _SEL_ODDS_RE.match(raw)
            if mo:
                sel = mo.group("sel").strip()
                odds = fnum(mo.group("odds"))
            else:
                sel = raw
        reason = ""
        m_why = re.search(r"\*\*Why promising:\*\*\s*(.+)", chunk, re.I)
        if m_why:
            reason = m_why.group(1).strip().splitlines()[0].strip()
        agent_raw = default_agent
        m_ag = re.search(r"\*\*scan_agent:\*\*\s*(\S+)", chunk, re.I)
        if m_ag:
            agent_raw = m_ag.group(1)
        c = _cand_from_dict(
            {
                "match": match,
                "selection": sel,
                "decimal_odds": odds,
                "scan_reason": reason,
                "scan_agents": _agents_list(agent_raw, default_agent=default_agent),
            },
            default_agent=default_agent,
        )
        if c:
            out.append(c)
    return out


def parse_agent_file(
    path: Path | str | None, *, default_agent: str = ""
) -> list[dict[str, Any]]:
    """
    Parse one agent artifact.

    Primary: JSONL or JSON. Empty / missing file → []. MD best-effort secondary.
    """
    if path is None:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return []
    if not text.strip():
        return []
    suffix = p.suffix.lower()
    if suffix == ".json":
        return _parse_json_payload(text, default_agent=default_agent)
    if suffix in (".jsonl", ".ndjson"):
        return _parse_jsonl(text, default_agent=default_agent)
    # Auto-detect: whole-file JSON vs JSONL
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        rows = _parse_json_payload(text, default_agent=default_agent)
        if rows:
            return rows
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if lines and all(
        ln.strip().startswith("{") for ln in lines[: min(5, len(lines))]
    ):
        return _parse_jsonl(text, default_agent=default_agent)
    if suffix in (".md", ".markdown", ".txt") or "**Match:**" in text or "**match:**" in text:
        return _parse_md_best_effort(text, default_agent=default_agent)
    # fallback try jsonl then json
    rows = _parse_jsonl(text, default_agent=default_agent)
    if rows:
        return rows
    return _parse_json_payload(text, default_agent=default_agent)


def discover_agent_files(agents_dir: Path | str) -> dict[str, Path]:
    """Find scan_agent_a/b/c/d* files under a directory (prefer jsonl > json > md)."""
    d = Path(agents_dir)
    found: dict[str, Path] = {}
    if not d.is_dir():
        return found
    for letter in ("a", "b", "c", "d"):
        pats = [
            f"scan_agent_{letter}*.jsonl",
            f"scan_agent_{letter}*.json",
            f"scan_agent_{letter}*.md",
            f"scan_{letter}*.jsonl",
        ]
        hits: list[Path] = []
        for pat in pats:
            hits.extend(sorted(d.glob(pat)))
        if hits:
            # Prefer jsonl > json > md; stable by name
            def _rank(p: Path) -> tuple[int, str]:
                s = p.suffix.lower()
                pref = 0 if s == ".jsonl" else (1 if s == ".json" else 2)
                return (pref, p.name.upper())

            hits.sort(key=_rank)
            found[letter.upper()] = hits[0]
    return found


def build_odds_index(
    odds_path: Path | str,
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[Any]]:
    """
    Index full odds dump by evidence_pair_key.

    Returns (index, raw_candidates).
    """
    raw = parse_odds_file(Path(odds_path))
    idx: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for c in raw:
        match = getattr(c, "match", "") or ""
        selection = getattr(c, "selection", "") or ""
        key = evidence_pair_key(match, selection)
        idx[key].append(
            {
                "match": match,
                "selection": selection,
                "decimal_odds": float(getattr(c, "decimal_odds", 0) or 0),
                "sport": getattr(c, "sport", "") or "",
                "market_type": getattr(c, "market_type", "") or "",
            }
        )
    return dict(idx), list(raw)


def odds_match_ok(
    scan_odds: float | None, dump_odds: float, *, tol: float = ODDS_TOL_REL
) -> bool:
    if scan_odds is None:
        return True
    try:
        s = float(scan_odds)
        d = float(dump_odds)
    except (TypeError, ValueError):
        return False
    if d <= 0:
        return False
    if abs(s - d) <= 1e-12:
        return True
    # Inclusive relative tol with float slack (e.g. 1.53 vs 1.50 at 2%)
    return abs(s - d) / d <= tol + 1e-12


def find_on_odds_dump(
    match: str,
    selection: str,
    scan_odds: float | None,
    odds_index: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    *,
    tol: float = ODDS_TOL_REL,
) -> dict[str, Any] | None:
    key = evidence_pair_key(match, selection)
    rows = odds_index.get(key) or []
    if not rows:
        return None
    best: dict[str, Any] | None = None
    best_delta = 1e9
    for r in rows:
        o = float(r.get("decimal_odds") or 0)
        if not odds_match_ok(scan_odds, o, tol=tol):
            continue
        if scan_odds is None:
            return dict(r)
        delta = abs(float(scan_odds) - o)
        if delta < best_delta:
            best_delta = delta
            best = dict(r)
    return best


def open_occupancy_from_rows(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    max_per_family: int = MAX_FAMILY_AFTER_MERGE,
    max_per_sport: int = MAX_PER_SPORT_SOFT,
) -> dict[str, Any]:
    """Count open Pending+ConfirmedPlaced family/sport via filter_live_rows."""
    family_counts: Counter[str] = Counter()
    sport_counts: Counter[str] = Counter()
    for r in filter_live_rows(rows):
        if not is_open_risk(str(r.get("result") or "")):
            continue
        sp = normalize_sport(str(r.get("sport") or ""), default="unknown")
        sel = str(r.get("selection") or "")
        mt = str(r.get("market_type") or "")
        fam = market_family(sport=sp, selection=sel, market_type=mt)
        family_counts[fam] += 1
        sport_counts[sp] += 1
    return {
        "family_counts": dict(family_counts),
        "sport_counts": dict(sport_counts),
        "max_per_family": int(max_per_family),
        "max_per_sport": int(max_per_sport),
    }


def load_open_occupancy(
    cfg: Mapping[str, Any] | None,
    *,
    live_rows: Sequence[Mapping[str, Any]] | None = None,
    max_per_family: int = MAX_FAMILY_AFTER_MERGE,
    max_per_sport: int = MAX_PER_SPORT_SOFT,
) -> dict[str, Any]:
    """Read-only open occupancy. Pass live_rows to avoid touching ledger path in tests."""
    if live_rows is not None:
        return open_occupancy_from_rows(
            live_rows, max_per_family=max_per_family, max_per_sport=max_per_sport
        )
    rows: list[dict[str, Any]] = []
    if cfg is not None:
        try:
            from nt.bets_io import load_bets

            bets_path = path_from_config(dict(cfg), "bets")
            rows = list(load_bets(bets_path))
        except Exception:
            rows = []
        try:
            from nt.learning import diversification_limits

            div = diversification_limits(dict(cfg))
            max_per_family = int(
                div.get("max_per_market_family")
                or div.get("max_per_market")
                or max_per_family
            )
            max_per_sport = int(div.get("max_per_sport") or max_per_sport)
        except Exception:
            pass
    return open_occupancy_from_rows(
        rows, max_per_family=max_per_family, max_per_sport=max_per_sport
    )


def load_deep_queue_lines(
    cfg: Mapping[str, Any] | None,
    *,
    deep_queue: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if deep_queue is not None:
        return [dict(x) for x in deep_queue if isinstance(x, Mapping)]
    if cfg is None:
        return []
    try:
        from nt.deep_queue_state import load_deep_queue_state

        state = load_deep_queue_state(dict(cfg))
        if not state:
            return []
        q = state.get("deep_queue") or state.get("queue") or []
        if isinstance(q, list):
            return [dict(x) for x in q if isinstance(x, Mapping)]
    except Exception:
        return []
    return []


def _line_notes_blob(line: Mapping[str, Any]) -> str:
    notes = line.get("notes")
    tags = line.get("tags")
    parts: list[str] = []
    if notes is not None:
        if isinstance(notes, (list, tuple)):
            parts.append(" ".join(str(x) for x in notes))
        else:
            parts.append(str(notes))
    if tags is not None:
        if isinstance(tags, (list, tuple)):
            parts.append(" ".join(str(x) for x in tags))
        else:
            parts.append(str(tags))
    return " ".join(parts).lower()


def is_coverage_critical(line: Mapping[str, Any]) -> bool:
    blob = _line_notes_blob(line)
    for tag in COVERAGE_TAGS:
        if tag in blob:
            return True
    tags = line.get("tags")
    if isinstance(tags, (list, tuple)):
        joined = " ".join(str(t) for t in tags).lower()
        if any(t in joined for t in COVERAGE_TAGS):
            return True
        if "coverage_critical" in joined:
            return True
    if line.get("coverage_critical") or line.get("_scaffold_equiv"):
        return True
    return False


def coverage_floor_enabled(cfg: Mapping[str, Any] | None) -> bool:
    if not cfg:
        return False
    try:
        from nt.light_research import coverage_floor_cfg

        cfc = coverage_floor_cfg(dict(cfg))
        return bool(cfc.get("enabled"))
    except Exception:
        try:
            raw = dict((cfg.get("research") or {}).get("coverage_floor") or {})
            return bool(raw.get("enabled"))
        except Exception:
            return False


def _has_coverage_tag(line: Mapping[str, Any]) -> bool:
    blob = _line_notes_blob(line)
    if any(t in blob for t in COVERAGE_TAGS):
        return True
    if line.get("coverage_critical") or line.get("_scaffold_equiv"):
        return True
    tags = line.get("tags")
    if isinstance(tags, (list, tuple)):
        joined = " ".join(str(t) for t in tags).lower()
        return any(t in joined for t in COVERAGE_TAGS) or "coverage_critical" in joined
    return False


def coverage_critical_lines(
    queue: Sequence[Mapping[str, Any]],
    *,
    coverage_floor_on: bool = False,
    top_promo_pct: float = TOP_PROMO_SCAFFOLD_PCT,
) -> list[dict[str, Any]]:
    """
    Coverage-critical engine lines for primary worklist union (KD15).

    Prefer explicit coverage_floor tags. If none tagged and coverage_floor is on,
    treat top ~20% by promo as scaffold-equivalent.
    """
    tagged: list[dict[str, Any]] = []
    for line in queue:
        if isinstance(line, Mapping) and _has_coverage_tag(line):
            tagged.append(dict(line))
    if tagged:
        return tagged
    if not coverage_floor_on:
        return []
    ranked = sorted(
        [dict(x) for x in queue if isinstance(x, Mapping)],
        key=_promo_of,
        reverse=True,
    )
    n = len(ranked)
    if n <= 0:
        return []
    k = max(1, int(math.floor(n * float(top_promo_pct))))
    out: list[dict[str, Any]] = []
    for r in ranked[:k]:
        rr = dict(r)
        rr["_scaffold_equiv"] = True
        rr["coverage_critical"] = True
        notes = str(rr.get("notes") or "")
        if "coverage_floor:top_promo_scaffold" not in notes.lower():
            rr["notes"] = (
                notes + " coverage_floor:top_promo_scaffold:equiv"
            ).strip()
        out.append(rr)
    return out


def load_light_verdicts_map(
    cfg: Mapping[str, Any] | None,
) -> dict[tuple[str, str], str]:
    """Read-only light LATEST / day batch → evidence_pair_key → verdict (KD16)."""
    if cfg is None:
        return {}
    payload: dict[str, Any] | None = None
    try:
        from nt.reasoning_chain import load_light_payload

        payload = load_light_payload(dict(cfg))
    except Exception:
        payload = None
    if not payload:
        try:
            outbox = path_from_config(dict(cfg), "outbox")
            latest = outbox / "light_research" / "LATEST.json"
            if latest.is_file():
                data = json.loads(latest.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    payload = data
        except Exception:
            payload = None
    if not isinstance(payload, dict):
        return {}
    out: dict[tuple[str, str], str] = {}
    records = payload.get("records") or payload.get("candidates") or []
    if not isinstance(records, list):
        return out
    for r in records:
        if not isinstance(r, Mapping):
            continue
        k = evidence_pair_key(
            str(r.get("match") or "").strip(),
            str(r.get("selection") or "").strip(),
        )
        v = str(r.get("verdict") or r.get("light_verdict") or "").strip().lower()
        if k[0] and k[1] and v:
            out[k] = v
    return out


def _promo_of(row: Mapping[str, Any]) -> float:
    try:
        v = row.get("promo_score")
        if v is None:
            v = row.get("promotion_score")
        return float(v or 0.0)
    except (TypeError, ValueError):
        return 0.0


def truncate_agent_rows(
    rows: Sequence[Mapping[str, Any]], *, max_n: int = AGENT_MAX
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep top max_n by promo (stable), return (kept, dropped_for_agent_max)."""
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda t: (-_promo_of(t[1]), t[0]))
    kept = [dict(indexed[i][1]) for i in range(min(max_n, len(indexed)))]
    dropped = [dict(indexed[i][1]) for i in range(max_n, len(indexed))]
    return kept, dropped


def _queue_line_as_candidate(
    line: Mapping[str, Any],
    *,
    reason: str = "engine_topup",
    open_occ: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert deep_queue line into a shortlist candidate (engine provenance)."""
    sp = normalize_sport(str(line.get("sport") or ""), default="unknown")
    sel = str(line.get("selection") or "").strip()
    mt = str(line.get("market_type") or "")
    fam = str(line.get("market_family") or "").strip() or market_family(
        sport=sp, selection=sel, market_type=mt
    )
    odds = fnum(line.get("decimal_odds") if line.get("decimal_odds") is not None else line.get("odds"))
    match = str(line.get("match") or "").strip()
    key = evidence_pair_key(match, sel)
    occ = open_occ or {}
    fam_counts = dict(occ.get("family_counts") or {})
    sp_counts = dict(occ.get("sport_counts") or {})
    max_f = int(occ.get("max_per_family") or MAX_FAMILY_AFTER_MERGE)
    max_s = int(occ.get("max_per_sport") or MAX_PER_SPORT_SOFT)
    open_fam = int(fam_counts.get(fam) or 0)
    open_sp = int(sp_counts.get(sp) or 0)
    agents = ["ENGINE"]
    if str(reason).startswith("engine_fallback"):
        agents = ["ENGINE"]
    return {
        "match": match,
        "selection": sel,
        "decimal_odds": odds,
        "sport": sp,
        "market_type": mt,
        "market_family": fam,
        "scan_agents": agents,
        "scan_reason": reason if reason.startswith("engine") else f"engine_topup: {reason}",
        "role": "ENGINE",
        "light_verdict": str(line.get("light_verdict") or line.get("verdict") or "").lower(),
        "promo_score": _promo_of(line),
        "in_engine_deep_queue": True,
        "on_odds_dump": True,
        "engine_topup": reason.startswith("engine_topup") or reason == "engine_topup",
        "engine_fallback": "fallback" in reason or reason.startswith("engine_fallback"),
        "_key": key,
        "open_family_count": open_fam,
        "open_sport_count": open_sp,
        "open_family_full": open_fam >= max_f,
        "open_sport_full": open_sp >= max_s,
        "coverage_critical": bool(
            line.get("coverage_critical") or _has_coverage_tag(line)
        ),
        "notes": str(line.get("notes") or ""),
    }


def _has_force_scan(reason: str) -> bool:
    return FORCE_SCAN_TOKEN.lower() in (reason or "").lower()


def _render_scan_agent(agents: Sequence[str]) -> str:
    ordered = sorted(
        agents,
        key=lambda x: (_AGENT_ORDER.index(x) if x in _AGENT_ORDER else 99, x),
    )
    return "+".join(ordered)


def _priority_tuple(
    c: Mapping[str, Any],
    *,
    open_occ: Mapping[str, Any] | None = None,
    prefer_d_longtail: bool = False,
) -> tuple:
    """Higher is better (sort reverse=True)."""
    fam = str(c.get("market_family") or "")
    sp = str(c.get("sport") or "")
    occ = open_occ or {}
    fam_counts = dict(occ.get("family_counts") or {})
    sp_counts = dict(occ.get("sport_counts") or {})
    max_f = int(occ.get("max_per_family") or MAX_FAMILY_AFTER_MERGE)
    max_s = int(occ.get("max_per_sport") or 2)
    open_fam_full = bool(c.get("open_family_full")) or (
        int(fam_counts.get(fam) or 0) >= max_f
    )
    open_sp_full = bool(c.get("open_sport_full")) or (
        int(sp_counts.get(sp) or 0) >= max_s
    )
    promo = float(c.get("promo_score") or 0.0)
    in_q = 1 if c.get("in_engine_deep_queue") else 0
    multi = list(c.get("scan_agents") or [])
    role = str(c.get("role") or (multi[0] if multi else "")).upper()
    fam_l = fam.lower()
    role_score = 0
    if role == "A" and any(x in fam_l for x in ("_ml", "1x2", "moneyline")):
        role_score = 2
    elif role == "B" and any(x in fam_l for x in ("total", "prop", "180")):
        role_score = 2
    elif role == "C" and any(x in fam_l for x in ("handicap", "hc")):
        role_score = 2
    elif role == "D" and is_long_tail(
        str(c.get("selection") or ""),
        str(c.get("market_type") or ""),
        fam,
    ):
        role_score = 2
    elif role in ("A", "B", "C", "D"):
        role_score = 1
    # When D-armed: prefer D over B on long-tail family collisions (soft sort key).
    d_lt_boost = 0
    if prefer_d_longtail and is_long_tail(
        str(c.get("selection") or ""),
        str(c.get("market_type") or ""),
        fam,
    ):
        has_d = "D" in multi or role == "D"
        has_b = "B" in multi or role == "B"
        if has_d and not has_b:
            d_lt_boost = 2
        elif has_d:
            d_lt_boost = 1
        elif has_b:
            d_lt_boost = 0
    agent_tie = min(
        (
            _AGENT_ORDER.index(a) if a in _AGENT_ORDER else 99
            for a in multi
        ),
        default=99,
    )
    reason_len = len(str(c.get("scan_reason") or ""))
    return (
        0 if open_fam_full else 1,
        0 if open_sp_full else 1,
        d_lt_boost,
        promo,
        in_q,
        role_score,
        -agent_tie,
        reason_len,
        str(c.get("match") or ""),
        str(c.get("selection") or ""),
    )


def _enrich_candidate(
    c: dict[str, Any],
    *,
    odds_index: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    queue_keys: set[tuple[str, str]],
    queue_promo: Mapping[tuple[str, str], float],
    light_by_key: Mapping[tuple[str, str], str],
) -> dict[str, Any]:
    out = dict(c)
    dump = find_on_odds_dump(
        str(out.get("match") or ""),
        str(out.get("selection") or ""),
        fnum(out.get("decimal_odds")),
        odds_index,
    )
    out["on_odds_dump"] = dump is not None
    if dump is not None:
        sp = normalize_sport(
            str(out.get("sport") or dump.get("sport") or ""), default="unknown"
        )
        if not out.get("sport"):
            out["sport"] = sp
        if out.get("decimal_odds") is None and dump.get("decimal_odds") is not None:
            out["decimal_odds"] = float(dump["decimal_odds"])
        if not out.get("market_type"):
            out["market_type"] = str(dump.get("market_type") or "")
    else:
        sp = normalize_sport(str(out.get("sport") or ""), default="unknown")
        out["sport"] = sp
    fam = str(out.get("market_family") or "").strip()
    if not fam:
        fam = market_family(
            sport=str(out.get("sport") or ""),
            selection=str(out.get("selection") or ""),
            market_type=str(out.get("market_type") or ""),
        )
    out["market_family"] = fam
    key = evidence_pair_key(str(out.get("match") or ""), str(out.get("selection") or ""))
    out["_key"] = key
    out["in_engine_deep_queue"] = bool(out.get("in_engine_deep_queue")) or key in queue_keys
    if key in queue_promo:
        out["promo_score"] = max(float(out.get("promo_score") or 0.0), float(queue_promo[key]))
    if not out.get("light_verdict") and key in light_by_key:
        out["light_verdict"] = light_by_key[key]
    agents = _agents_list(out.get("scan_agents"), default_agent=str(out.get("role") or "A"))
    out["scan_agents"] = agents
    if not out.get("role") and agents:
        out["role"] = agents[0]
    return out


def _public(c: Mapping[str, Any]) -> dict[str, Any]:
    raw_agents = list(c.get("scan_agents") or [])
    agents: list[str] = []
    for a in raw_agents:
        s = str(a).strip()
        if s.lower() in ("engine", "engine_topup", "engine_fallback", "+engine"):
            na = "ENGINE"
        else:
            na = _normalize_agent_id(s, default="")
        if na and na not in agents:
            agents.append(na)
    render = _render_scan_agent(agents)
    return {
        "match": str(c.get("match") or ""),
        "selection": str(c.get("selection") or ""),
        "decimal_odds": c.get("decimal_odds"),
        "sport": str(c.get("sport") or ""),
        "market_type": str(c.get("market_type") or ""),
        "market_family": str(c.get("market_family") or ""),
        "scan_agents": agents,
        "scan_agent": render,
        "scan_reason": str(c.get("scan_reason") or ""),
        "on_odds_dump": bool(c.get("on_odds_dump", True)),
        "in_engine_deep_queue": bool(c.get("in_engine_deep_queue") or False),
        "light_verdict": str(c.get("light_verdict") or ""),
        "promo_score": float(c.get("promo_score") or 0.0),
        "open_family_count": int(c.get("open_family_count") or 0),
        "open_sport_count": int(c.get("open_sport_count") or 0),
        "open_family_full": bool(c.get("open_family_full") or False),
        "open_sport_full": bool(c.get("open_sport_full") or False),
        "coverage_critical": bool(c.get("coverage_critical") or False),
    }


def _apply_family_cap(
    candidates: Sequence[Mapping[str, Any]],
    *,
    max_family: int = MAX_FAMILY_AFTER_MERGE,
    dropped: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    KD4: each market_family ≤ max_family.
    Prefer spread to 1 first (pass1), then fill second seats (pass2).
    """
    if dropped is None:
        dropped = []
    ordered = list(candidates)
    first_seats: list[dict[str, Any]] = []
    leftovers: list[dict[str, Any]] = []
    seen_fam: set[str] = set()
    for c in ordered:
        fam = str(c.get("market_family") or "other")
        if fam not in seen_fam:
            seen_fam.add(fam)
            first_seats.append(dict(c))
        else:
            leftovers.append(dict(c))
    after = list(first_seats)
    fam_counts: Counter[str] = Counter(
        str(c.get("market_family") or "other") for c in after
    )
    for c in leftovers:
        fam = str(c.get("market_family") or "other")
        if fam_counts[fam] < max_family:
            after.append(c)
            fam_counts[fam] += 1
        else:
            pub = _public(c)
            pub["drop_reason"] = "family_cap"
            dropped.append(pub)
    return after


def _engine_topup(
    final: list[dict[str, Any]],
    *,
    queue: Sequence[Mapping[str, Any]],
    odds_index: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    open_occ: Mapping[str, Any],
    light_by_key: Mapping[tuple[str, str], str],
    max_family: int,
    shortlist_min: int,
    shortlist_max: int,
    multi_sport_board: bool,
    soft_sport_cap: int,
    dropped: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Append unused engine light-pass / never-fail lines until shortlist_min (ISS-1)."""
    have = {
        evidence_pair_key(str(c.get("match") or ""), str(c.get("selection") or ""))
        for c in final
    }
    fam_counts: Counter[str] = Counter(
        str(c.get("market_family") or "other") for c in final
    )
    sp_counts: Counter[str] = Counter(str(c.get("sport") or "unknown") for c in final)
    ranked = sorted(queue, key=_promo_of, reverse=True)
    added = 0
    out = list(final)
    for line in ranked:
        if len(out) >= shortlist_min or len(out) >= shortlist_max:
            break
        match = str(line.get("match") or "")
        sel = str(line.get("selection") or "")
        k = evidence_pair_key(match, sel)
        if k in have:
            continue
        dump = find_on_odds_dump(
            match, sel, fnum(line.get("decimal_odds") or line.get("odds")), odds_index
        )
        if dump is None:
            continue
        light = str(
            line.get("light_verdict")
            or line.get("verdict")
            or light_by_key.get(k)
            or ""
        ).lower()
        if light in ("fail", "hard_fail", "light_fail"):
            continue
        cand = _queue_line_as_candidate(line, reason="engine_topup", open_occ=open_occ)
        fam = str(cand.get("market_family") or "other")
        sp = str(cand.get("sport") or "unknown")
        if fam_counts[fam] >= max_family:
            continue
        if cand.get("open_family_full") or cand.get("open_sport_full"):
            continue
        if multi_sport_board and sp_counts[sp] >= soft_sport_cap:
            continue
        out.append(cand)
        have.add(k)
        fam_counts[fam] += 1
        sp_counts[sp] += 1
        added += 1
    return out, added


def _engine_queue_shortlist(
    queue: Sequence[Mapping[str, Any]],
    *,
    odds_index: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    open_occ: Mapping[str, Any],
    light_by_key: Mapping[tuple[str, str], str],
    max_family: int,
    shortlist_max: int,
    reason: str = "engine_fallback",
) -> list[dict[str, Any]]:
    """Build shortlist from engine deep_queue only (ISS-2 all-fail path)."""
    ranked = sorted(queue, key=_promo_of, reverse=True)
    cands: list[dict[str, Any]] = []
    for line in ranked:
        match = str(line.get("match") or "")
        sel = str(line.get("selection") or "")
        odds = fnum(line.get("decimal_odds") if line.get("decimal_odds") is not None else line.get("odds"))
        dump = find_on_odds_dump(match, sel, odds, odds_index)
        if dump is None:
            continue
        light = str(
            line.get("light_verdict")
            or line.get("verdict")
            or light_by_key.get(evidence_pair_key(match, sel))
            or ""
        ).lower()
        if light in ("fail", "hard_fail", "light_fail"):
            continue
        cands.append(
            _queue_line_as_candidate(line, reason=reason, open_occ=open_occ)
        )
    dummy_dropped: list[dict[str, Any]] = []
    capped = _apply_family_cap(cands, max_family=max_family, dropped=dummy_dropped)
    return capped[:shortlist_max]


def merge_candidates(
    agent_candidates: Mapping[str, Sequence[Mapping[str, Any]]]
    | Sequence[Mapping[str, Any]],
    odds_path: Path | str,
    *,
    open_occ: Mapping[str, Any] | None = None,
    deep_queue: Sequence[Mapping[str, Any]] | None = None,
    light_verdicts: Mapping[tuple[str, str], str] | None = None,
    max_family: int = MAX_FAMILY_AFTER_MERGE,
    shortlist_max: int = SHORTLIST_MAX,
    shortlist_min: int = SHORTLIST_MIN,
    soft_sport_cap: int = MAX_PER_SPORT_SOFT,
    odds_tol: float = ODDS_TOL_REL,
    coverage_floor_on: bool = False,
    agent_max: int = AGENT_MAX,
    agent_d_armed: bool | None = None,
    agent_d_min_lines: int = DEFAULT_AGENT_D_MIN_LINES,
) -> dict[str, Any]:
    """
    Deterministic merge of multi-agent scan candidates (A/B/C + optional D).

    Returns payload with candidates, dropped, primary_worklist, counts.
    """
    dropped: list[dict[str, Any]] = []
    notes: list[str] = []
    agent_raw_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
    by_ag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    d_in_input = False

    if isinstance(agent_candidates, Mapping):
        for ag, rows in agent_candidates.items():
            ag_n = _normalize_agent_id(str(ag), default="")
            rows_list = [dict(r) for r in (rows or []) if isinstance(r, Mapping)]
            if ag_n == "D":
                d_in_input = True
            if ag_n in ("A", "B", "C", "D"):
                agent_raw_counts[ag_n] = len(rows_list)
            kept_rows, over = truncate_agent_rows(rows_list, max_n=agent_max)
            for r in over:
                c = dict(r)
                if not c.get("scan_agents"):
                    c["scan_agents"] = _agents_list(None, default_agent=ag_n)
                pub = _public(c)
                pub["drop_reason"] = "agent_max_5"
                dropped.append(pub)
            for r in kept_rows:
                c = dict(r)
                if not c.get("scan_agents"):
                    c["scan_agents"] = _agents_list(None, default_agent=ag_n)
                if not c.get("role"):
                    c["role"] = ag_n
                by_ag[ag_n].append(c)
    else:
        ungrouped = [dict(r) for r in agent_candidates if isinstance(r, Mapping)]
        for r in ungrouped:
            c = dict(r)
            agents = _agents_list(
                c.get("scan_agents") or c.get("role") or "",
                default_agent="",
            )
            if not agents:
                agents = ["A"]
            c["scan_agents"] = agents
            for a in agents:
                if a in ("A", "B", "C", "D"):
                    by_ag[a].append(dict(c))
                    if a == "D":
                        d_in_input = True
        for ag_n in ("A", "B", "C", "D"):
            rows_list = by_ag.get(ag_n) or []
            agent_raw_counts[ag_n] = len(rows_list)
            kept_rows, over = truncate_agent_rows(rows_list, max_n=agent_max)
            by_ag[ag_n] = kept_rows
            for r in over:
                pub = _public(r)
                pub["drop_reason"] = "agent_max_5"
                dropped.append(pub)

    if agent_d_armed is None:
        d_armed = bool(d_in_input) or agent_raw_counts.get("D", 0) > 0
    else:
        d_armed = bool(agent_d_armed)

    raw_list: list[dict[str, Any]] = []
    for ag_n in ("A", "B", "C", "D"):
        raw_list.extend(by_ag.get(ag_n) or [])
    raw_n = sum(agent_raw_counts.values())

    odds_index, odds_raw = build_odds_index(odds_path)
    sports_on_dump = {
        normalize_sport(str(getattr(c, "sport", "") or ""), default="unknown")
        for c in odds_raw
    }
    sports_on_dump.discard("unknown")
    multi_sport_board = len(sports_on_dump) >= 3

    # Depth header context (does not gate merge; spawn decision is scan-depth CLI).
    try:
        depth = match_line_counts(odds_path)
        max_lines = int(depth.get("max_lines_per_match") or 0)
    except Exception:
        depth = {"per_match": {}, "max_lines_per_match": 0, "total_lines": 0}
        max_lines = 0
    min_lines = int(agent_d_min_lines)
    spawn_from_depth = should_spawn_agent_d(depth, min_lines=min_lines)
    if d_armed:
        agent_d_header = (
            f"spawned (max_lines_per_match={max_lines}, min_lines={min_lines})"
        )
    else:
        agent_d_header = (
            f"skipped (max_lines_per_match={max_lines}, min_lines={min_lines})"
        )

    queue = list(deep_queue or [])
    queue_keys: set[tuple[str, str]] = set()
    queue_promo: dict[tuple[str, str], float] = {}
    for line in queue:
        if not isinstance(line, Mapping):
            continue
        k = evidence_pair_key(
            str(line.get("match") or ""),
            str(line.get("selection") or ""),
        )
        queue_keys.add(k)
        ps = fnum(line.get("promo_score") if line.get("promo_score") is not None else line.get("promotion_score"))
        if ps is not None:
            queue_promo[k] = max(float(queue_promo.get(k, 0.0)), float(ps))

    if open_occ is None:
        open_occ = open_occupancy_from_rows([])
    light_by_key: dict[tuple[str, str], str] = dict(light_verdicts or {})

    expected_agents = ["A", "B", "C"]
    if d_armed or d_in_input:
        expected_agents.append("D")

    # ISS-2: all agents empty → engine deep_queue fallback
    if raw_n == 0:
        fb = _engine_queue_shortlist(
            queue,
            odds_index=odds_index,
            open_occ=open_occ,
            light_by_key=light_by_key,
            max_family=max_family,
            shortlist_max=shortlist_max,
            reason="engine_fallback",
        )
        notes.append("fallback: engine_deep_queue")
        missing = [a for a in expected_agents if agent_raw_counts.get(a, 0) == 0]
        if missing:
            notes.append("scan_agent_missing: " + ",".join(missing))
        public_final = [_public(c) for c in fb]
        primary = list(public_final)
        cov = coverage_critical_lines(
            queue, coverage_floor_on=coverage_floor_on
        )
        seen = {
            evidence_pair_key(str(c.get("match") or ""), str(c.get("selection") or ""))
            for c in primary
        }
        for line in cov:
            k = evidence_pair_key(
                str(line.get("match") or ""), str(line.get("selection") or "")
            )
            if k in seen:
                continue
            if len(primary) >= PRIMARY_CAP:
                pub = {
                    "match": str(line.get("match") or ""),
                    "selection": str(line.get("selection") or ""),
                    "decimal_odds": fnum(line.get("decimal_odds") or line.get("odds")),
                    "drop_reason": "primary_cap_drop",
                    "notes": "coverage_critical overflow",
                }
                dropped.append(pub)
                continue
            cand = _queue_line_as_candidate(
                line, reason="coverage_critical", open_occ=open_occ
            )
            cand["coverage_critical"] = True
            pub = _public(cand)
            pub["coverage_critical"] = True
            primary.append(pub)
            seen.add(k)
        return {
            "schema_version": 1,
            "odds_file": str(odds_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "agents": agent_raw_counts,
            "agent_raw_counts": agent_raw_counts,
            "raw_n": 0,
            "final_n": len(public_final),
            "max_per_family_after_merge": max_family,
            "primary_worklist_n": len(primary),
            "multi_sport_board": multi_sport_board,
            "sports_on_dump": sorted(sports_on_dump),
            "open_occupancy": {
                "family_counts": dict(open_occ.get("family_counts") or {}),
                "sport_counts": dict(open_occ.get("sport_counts") or {}),
                "max_per_family": int(open_occ.get("max_per_family") or max_family),
                "max_per_sport": int(open_occ.get("max_per_sport") or soft_sport_cap),
            },
            "candidates": public_final,
            "primary_worklist": primary,
            "dropped": dropped,
            "notes": notes,
            "fallback": "engine_deep_queue",
            "scan_agent_missing": missing,
            "agent_d": agent_d_header,
            "agent_d_armed": d_armed,
            "spawn_agent_d_depth": spawn_from_depth,
            "max_lines_per_match": max_lines,
            "agent_d_min_lines": min_lines,
        }

    # Enrich + hard filters
    enriched: list[dict[str, Any]] = []
    for raw in raw_list:
        c = _enrich_candidate(
            dict(raw),
            odds_index=odds_index,
            queue_keys=queue_keys,
            queue_promo=queue_promo,
            light_by_key=light_by_key,
        )
        dump = find_on_odds_dump(
            str(c.get("match") or ""),
            str(c.get("selection") or ""),
            fnum(c.get("decimal_odds")),
            odds_index,
            tol=odds_tol,
        )
        if dump is None:
            pub = _public(c)
            pub["drop_reason"] = "off_odds_dump"
            dropped.append(pub)
            continue
        c["on_odds_dump"] = True
        reason = str(c.get("scan_reason") or "").strip()
        if not reason:
            pub = _public(c)
            pub["drop_reason"] = "empty_scan_reason"
            dropped.append(pub)
            continue
        agents = list(c.get("scan_agents") or [])
        role = str(c.get("role") or (agents[0] if agents else "")).upper()
        is_a_only = agents == ["A"] or (len(agents) == 1 and agents[0] == "A")
        o = fnum(c.get("decimal_odds"))
        if is_a_only and o is not None:
            if o + 1e-9 < AGENT_A_ODDS_LO or o - 1e-9 > AGENT_A_ODDS_HI:
                pub = _public(c)
                pub["drop_reason"] = "agent_a_odds_band"
                dropped.append(pub)
                continue
        light = str(c.get("light_verdict") or "").lower()
        if light in ("fail", "hard_fail", "light_fail"):
            if not _has_force_scan(reason) and not c.get("in_engine_deep_queue"):
                pub = _public(c)
                pub["drop_reason"] = "light_fail"
                dropped.append(pub)
                continue
        fam = str(c.get("market_family") or "")
        sp = str(c.get("sport") or "unknown")
        fam_counts = dict(open_occ.get("family_counts") or {})
        sp_counts = dict(open_occ.get("sport_counts") or {})
        max_f = int(open_occ.get("max_per_family") or max_family)
        max_s = int(open_occ.get("max_per_sport") or soft_sport_cap)
        c["open_family_count"] = int(fam_counts.get(fam) or 0)
        c["open_sport_count"] = int(sp_counts.get(sp) or 0)
        c["open_family_full"] = c["open_family_count"] >= max_f
        c["open_sport_full"] = c["open_sport_count"] >= max_s
        if not c.get("role"):
            c["role"] = role or "A"
        enriched.append(c)

    # Dedupe by key; union scan_agents
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for c in enriched:
        key = c.get("_key") or evidence_pair_key(
            str(c.get("match") or ""), str(c.get("selection") or "")
        )
        prev = by_key.get(key)  # type: ignore[arg-type]
        if prev is None:
            by_key[key] = c  # type: ignore[index]
            continue
        agents = list(dict.fromkeys(list(prev.get("scan_agents") or []) + list(c.get("scan_agents") or [])))
        agents = _agents_list(agents)
        r1 = str(prev.get("scan_reason") or "")
        r2 = str(c.get("scan_reason") or "")
        reason = r1 if len(r1) >= len(r2) else r2
        if r1 and r2 and r1 != r2:
            # keep longer primary; note secondary lightly
            keep = prev if len(r1) >= len(r2) else c
            other = c if keep is prev else prev
            reason = str(keep.get("scan_reason") or "")
            if other.get("scan_reason") and other.get("scan_reason") != reason:
                reason = reason  # keep primary; secondary agents already unioned
        keep = (
            prev
            if _priority_tuple(prev, open_occ=open_occ, prefer_d_longtail=d_armed)
            >= _priority_tuple(c, open_occ=open_occ, prefer_d_longtail=d_armed)
            else c
        )
        other = c if keep is prev else prev
        keep = dict(keep)
        keep["scan_agents"] = agents
        keep["scan_reason"] = str(keep.get("scan_reason") or reason)
        if other.get("scan_reason") and other.get("scan_reason") != keep.get("scan_reason"):
            keep["scan_reason"] = (
                f"{keep.get('scan_reason')} also: {other.get('scan_reason')}"
            )[:400]
        keep["promo_score"] = max(
            float(keep.get("promo_score") or 0.0), float(other.get("promo_score") or 0.0)
        )
        keep["in_engine_deep_queue"] = bool(
            keep.get("in_engine_deep_queue") or other.get("in_engine_deep_queue")
        )
        by_key[key] = keep  # type: ignore[index]

    deduped = list(by_key.values())
    deduped.sort(
        key=lambda c: _priority_tuple(
            c, open_occ=open_occ, prefer_d_longtail=d_armed
        ),
        reverse=True,
    )

    drops_before_family = len(dropped)
    after_family = _apply_family_cap(
        deduped, max_family=max_family, dropped=dropped
    )
    # When D-armed: note B long-tail seats yielded to D on family collision.
    if d_armed:
        kept_d_lt_fams: set[str] = set()
        for c in after_family:
            agents_c = list(c.get("scan_agents") or [])
            if "D" not in agents_c:
                continue
            if is_long_tail(
                str(c.get("selection") or ""),
                str(c.get("market_type") or ""),
                str(c.get("market_family") or ""),
            ):
                kept_d_lt_fams.add(str(c.get("market_family") or "other"))
        for drow in dropped[drops_before_family:]:
            if drow.get("drop_reason") != "family_cap":
                continue
            agents_d = list(drow.get("scan_agents") or [])
            if "B" not in agents_d:
                continue
            fam_d = str(drow.get("market_family") or "other")
            if fam_d not in kept_d_lt_fams:
                continue
            if not is_long_tail(
                str(drow.get("selection") or ""),
                str(drow.get("market_type") or ""),
                fam_d,
            ):
                continue
            note = "b_yielded_longtail_to_d"
            prev_notes = str(drow.get("notes") or "").strip()
            drow["notes"] = f"{prev_notes}; {note}".strip("; ") if prev_notes else note
            if note not in notes:
                notes.append(note)

    # Soft open occupancy: defer open_family_full, readd up to OPEN_FULL_READD_MAX if thin
    after_open: list[dict[str, Any]] = []
    pending_open: list[dict[str, Any]] = []
    for c in after_family:
        if c.get("open_family_full"):
            pending_open.append(c)
        else:
            after_open.append(c)
    readded = 0
    for cc in pending_open:
        if len(after_open) < shortlist_min and readded < OPEN_FULL_READD_MAX:
            note = f"research_despite_open_full: {cc.get('market_family')}"
            notes.append(note)
            after_open.append(cc)
            readded += 1
        else:
            pub = _public(cc)
            pub["drop_reason"] = "open_family_full"
            dropped.append(pub)

    # Soft sport cap on multi-sport boards
    after_sport: list[dict[str, Any]] = []
    sp_counts_sel: Counter[str] = Counter()
    deferred_sport: list[dict[str, Any]] = []
    if multi_sport_board:
        for c in after_open:
            sp = str(c.get("sport") or "unknown")
            if sp_counts_sel[sp] >= soft_sport_cap:
                deferred_sport.append(c)
            else:
                after_sport.append(c)
                sp_counts_sel[sp] += 1
        # fill if below min
        for c in deferred_sport:
            if len(after_sport) < shortlist_min:
                after_sport.append(c)
            else:
                pub = _public(c)
                pub["drop_reason"] = "sport_soft_cap"
                dropped.append(pub)
    else:
        after_sport = list(after_open)

    # Clamp to shortlist_max
    final = after_sport[:shortlist_max]
    for c in after_sport[shortlist_max:]:
        pub = _public(c)
        pub["drop_reason"] = "shortlist_max"
        dropped.append(pub)

    topup_n = 0
    if len(final) < shortlist_min:
        final, topup_n = _engine_topup(
            final,
            queue=queue,
            odds_index=odds_index,
            open_occ=open_occ,
            light_by_key=light_by_key,
            max_family=max_family,
            shortlist_min=shortlist_min,
            shortlist_max=shortlist_max,
            multi_sport_board=multi_sport_board,
            soft_sport_cap=soft_sport_cap,
            dropped=dropped,
        )
        if topup_n:
            notes.append(f"engine_topup: +{topup_n}")

    missing = [a for a in expected_agents if agent_raw_counts.get(a, 0) == 0]
    if missing:
        notes.append("scan_agent_missing: " + ",".join(missing))

    # Soft D role-drift: never hard-drop; annotate if ≥3 of D's kept rows are main_board.
    d_kept_main: list[dict[str, Any]] = []
    for c in final:
        agents_c = list(c.get("scan_agents") or [])
        if "D" not in agents_c:
            continue
        if is_main_board(
            str(c.get("selection") or ""),
            str(c.get("market_type") or ""),
            str(c.get("market_family") or ""),
        ):
            d_kept_main.append(c)
    if len(d_kept_main) >= 3:
        main_desc = "; ".join(
            f"{x.get('match')}|{x.get('selection')}" for x in d_kept_main[:5]
        )
        notes.append(f"process_miss: agent_d_role_drift ({main_desc})")

    public_final = [_public(c) for c in final]

    # Primary worklist = shortlist ∪ coverage_critical (cap PRIMARY_CAP)
    primary: list[dict[str, Any]] = list(public_final)
    shortlist_keys = {
        evidence_pair_key(str(c.get("match") or ""), str(c.get("selection") or ""))
        for c in primary
    }
    cov = coverage_critical_lines(queue, coverage_floor_on=coverage_floor_on)
    for line in cov:
        k = evidence_pair_key(
            str(line.get("match") or ""), str(line.get("selection") or "")
        )
        if k in shortlist_keys:
            # mark coverage_critical on existing shortlist row if present
            for p in primary:
                pk = evidence_pair_key(
                    str(p.get("match") or ""), str(p.get("selection") or "")
                )
                if pk == k:
                    p["coverage_critical"] = True
            continue
        if len(primary) >= PRIMARY_CAP:
            dropped.append(
                {
                    "match": str(line.get("match") or ""),
                    "selection": str(line.get("selection") or ""),
                    "decimal_odds": fnum(line.get("decimal_odds") or line.get("odds")),
                    "drop_reason": "primary_cap_drop",
                    "notes": "coverage_critical overflow",
                }
            )
            continue
        cand = _queue_line_as_candidate(
            line, reason="coverage_critical", open_occ=open_occ
        )
        cand["coverage_critical"] = True
        # must be on odds dump
        dump = find_on_odds_dump(
            str(cand.get("match") or ""),
            str(cand.get("selection") or ""),
            fnum(cand.get("decimal_odds")),
            odds_index,
        )
        if dump is None:
            continue
        pub = _public(cand)
        pub["coverage_critical"] = True
        primary.append(pub)
        shortlist_keys.add(k)

    out = {
        "schema_version": 1,
        "odds_file": str(odds_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agents": agent_raw_counts,
        "agent_raw_counts": agent_raw_counts,
        "raw_n": raw_n,
        "final_n": len(public_final),
        "max_per_family_after_merge": max_family,
        "primary_worklist_n": len(primary),
        "multi_sport_board": multi_sport_board,
        "sports_on_dump": sorted(sports_on_dump),
        "open_occupancy": {
            "family_counts": dict(open_occ.get("family_counts") or {}),
            "sport_counts": dict(open_occ.get("sport_counts") or {}),
            "max_per_family": int(open_occ.get("max_per_family") or max_family),
            "max_per_sport": int(open_occ.get("max_per_sport") or soft_sport_cap),
        },
        "candidates": public_final,
        "primary_worklist": primary,
        "dropped": dropped,
        "notes": notes,
        "fallback": "",
        "scan_agent_missing": missing,
        "agent_d": agent_d_header,
        "agent_d_armed": d_armed,
        "spawn_agent_d_depth": spawn_from_depth,
        "max_lines_per_match": max_lines,
        "agent_d_min_lines": min_lines,
    }
    return out


def render_shortlist_markdown(payload: Mapping[str, Any]) -> str:
    agents = payload.get("agents") or {}
    a = int(agents.get("A") or 0)
    b = int(agents.get("B") or 0)
    c = int(agents.get("C") or 0)
    d = int(agents.get("D") or 0)
    final_n = int(payload.get("final_n") or 0)
    created = str(payload.get("created_at") or "")
    day = created[:10] if created else "run"
    if d > 0 or payload.get("agent_d_armed"):
        source = f"A({a})+B({b})+C({c})+D({d}) → merge → {final_n} candidates"
    else:
        source = f"A({a})+B({b})+C({c}) → merge → {final_n} candidates"
    lines: list[str] = [
        f"# MULTI_AGENT_SHORTLIST — {day}",
        f"# Source: {source}",
        f"# Family rule: each market_family ≤{int(payload.get('max_per_family_after_merge') or 2)} after merge (drop at ≥3)",
    ]
    agent_d_line = str(payload.get("agent_d") or "").strip()
    if agent_d_line:
        lines.append(f"# agent_d: {agent_d_line}")
    else:
        max_lines = payload.get("max_lines_per_match")
        min_lines = payload.get("agent_d_min_lines") or DEFAULT_AGENT_D_MIN_LINES
        if d > 0 or payload.get("agent_d_armed"):
            lines.append(
                f"# agent_d: spawned (max_lines_per_match={max_lines}, min_lines={min_lines})"
            )
        else:
            lines.append(
                f"# agent_d: skipped (max_lines_per_match={max_lines}, min_lines={min_lines})"
            )
    occ = payload.get("open_occupancy") or {}
    lines.append(
        f"# Open occupancy: family={occ.get('family_counts') or {}} sport={occ.get('sport_counts') or {}}"
    )
    lines.append(f"# Soft sport multi-board: {payload.get('multi_sport_board')}")
    lines.append("# Deep research primary: ## Primary worklist below (cap 15)")
    for note in payload.get("notes") or []:
        lines.append(f"# Note: {note}")
    fb = payload.get("fallback") or ""
    if fb:
        lines.append(f"# fallback: {fb}")
    lines.extend(
        [
            "",
            "| # | Match | Selection @ odds | Family | scan_agent | Why (scan) |",
            "|---|-------|------------------|--------|------------|------------|",
        ]
    )
    for i, row in enumerate(payload.get("candidates") or [], start=1):
        try:
            odds = float(row.get("decimal_odds")) if row.get("decimal_odds") is not None else None
            odds_s = f"{odds:.2f}" if odds is not None else "?"
        except (TypeError, ValueError):
            odds_s = "?"
        why = str(row.get("scan_reason") or "").replace("|", "/")
        if len(why) > 80:
            why = why[:77] + "..."
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    str(row.get("match") or ""),
                    f"{row.get('selection') or ''} @ {odds_s}",
                    str(row.get("market_family") or ""),
                    str(row.get("scan_agent") or ""),
                    why,
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Primary worklist (Stage 2 — deep these only on primary pass)")
    pw = payload.get("primary_worklist") or []
    short_n = int(payload.get("final_n") or 0)
    lines.append(f"- All {short_n} multi-agent shortlist rows above")
    extra = [r for r in pw if r.get("coverage_critical") and r not in (payload.get("candidates") or [])]
    # also show coverage_critical not already in shortlist by key
    short_keys = {
        evidence_pair_key(str(r.get("match") or ""), str(r.get("selection") or ""))
        for r in (payload.get("candidates") or [])
    }
    cov_extra = [
        r
        for r in pw
        if evidence_pair_key(str(r.get("match") or ""), str(r.get("selection") or ""))
        not in short_keys
    ]
    if cov_extra:
        lines.append("- Plus coverage_critical from engine queue not already listed:")
        for r in cov_extra:
            lines.append(
                f"  - {r.get('match')} | {r.get('selection')} | coverage_critical"
            )
    lines.append(
        f"- Total primary_n = {len(pw)} (cap {PRIMARY_CAP})"
    )
    lines.append("")
    lines.append("## Dropped at merge")
    drops = payload.get("dropped") or []
    if not drops:
        lines.append("- _(none)_")
    else:
        for d in drops[:40]:
            lines.append(
                f"- {d.get('match')} | {d.get('selection')} — **{d.get('drop_reason') or '?'}**"
                + (f" ({d.get('notes')})" if d.get("notes") else "")
            )
    lines.append("")
    lines.append("## Notes")
    lines.append("- Keys: evidence_pair_key; odds validated on full dump (2% relative tol)")
    lines.append("- Engine deep_queue.json NOT rewritten")
    lines.append(
        "- Stage 3 portfolio still hard-caps max 2 per family and max 2 per sport at place"
    )
    return "\n".join(lines) + "\n"


def run_scan_merge(
    cfg: Mapping[str, Any] | None,
    odds: Path | str,
    *,
    agent_a: Path | str | None = None,
    agent_b: Path | str | None = None,
    agent_c: Path | str | None = None,
    agent_d: Path | str | None = None,
    agents_dir: Path | str | None = None,
    out: Path | str | None = None,
    out_json: Path | str | None = None,
    live_rows: Sequence[Mapping[str, Any]] | None = None,
    deep_queue: Sequence[Mapping[str, Any]] | None = None,
    light_verdicts: Mapping[tuple[str, str], str] | None = None,
    use_live_open: bool = True,
    write: bool = True,
    agent_d_armed: bool | None = None,
) -> dict[str, Any]:
    """
    Load agents + odds, merge, optionally write outbox artifacts.
    """
    odds_path = Path(odds)
    paths: dict[str, Path] = {}
    if agents_dir is not None:
        found = discover_agent_files(agents_dir)
        paths.update(found)
    if agent_a is not None:
        paths["A"] = Path(agent_a)
    if agent_b is not None:
        paths["B"] = Path(agent_b)
    if agent_c is not None:
        paths["C"] = Path(agent_c)
    if agent_d is not None:
        paths["D"] = Path(agent_d)

    agent_map: dict[str, list[dict[str, Any]]] = {
        "A": parse_agent_file(paths.get("A"), default_agent="A"),
        "B": parse_agent_file(paths.get("B"), default_agent="B"),
        "C": parse_agent_file(paths.get("C"), default_agent="C"),
    }
    d_expected = "D" in paths
    if d_expected:
        agent_map["D"] = parse_agent_file(paths.get("D"), default_agent="D")

    if use_live_open:
        open_occ = load_open_occupancy(cfg, live_rows=live_rows)
    else:
        open_occ = open_occupancy_from_rows(live_rows or [])

    queue = load_deep_queue_lines(cfg, deep_queue=deep_queue)
    resolved_light = (
        dict(light_verdicts)
        if light_verdicts is not None
        else load_light_verdicts_map(cfg)
    )
    min_lines = agent_d_min_lines_from_cfg(cfg)
    d_armed_flag = agent_d_armed
    if d_armed_flag is None and d_expected:
        d_armed_flag = True

    payload = merge_candidates(
        agent_map,
        odds_path,
        open_occ=open_occ,
        deep_queue=queue,
        light_verdicts=resolved_light,
        coverage_floor_on=coverage_floor_enabled(cfg),
        agent_d_armed=d_armed_flag,
        agent_d_min_lines=min_lines,
    )
    payload["agent_files"] = {k: str(v) for k, v in paths.items()}
    payload["markdown"] = render_shortlist_markdown(payload)

    if write:
        out_path: Path | None
        if out is not None:
            out_path = Path(out)
        else:
            try:
                outbox = path_from_config(dict(cfg or {}), "outbox")
            except Exception:
                outbox = Path("outbox")
            out_path = outbox / "MULTI_AGENT_SHORTLIST.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload["markdown"], encoding="utf-8")
        payload["md_path"] = str(out_path)

        if out_json is not None:
            json_path = Path(out_json)
        else:
            json_path = out_path.with_suffix(".json")
            if "MULTI_AGENT" not in json_path.name.upper():
                json_path = out_path.parent / "multi_agent_shortlist.json"
        slim = {
            k: v
            for k, v in payload.items()
            if k not in ("markdown",)
        }
        json_path.write_text(
            json.dumps(slim, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        payload["json_path"] = str(json_path)

    return payload
