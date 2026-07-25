"""
Thin multi-agent scan merge helper (Stage 1b).

Parse agent JSONL/JSON (+ best-effort MD), validate against full odds dump,
dedupe by evidence_pair_key, soft family/sport diversity, light-fail drop,
emit MULTI_AGENT_SHORTLIST.md (+ optional JSON) with primary worklist hints.

No place / p_model / capital. Never rewrites data/state/deep_queue.json or ledger.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from nt.bets_io import is_open_risk
from nt.config import path_from_config
from nt.live_ledger import filter_live_rows
from nt.market_family import market_family
from nt.odds_common import evidence_pair_key, fnum
from nt.odds_parse import parse_odds_file
from nt.sport_taxonomy import normalize_sport

ODDS_TOL_REL = 0.02  # 2% relative
MAX_FAMILY_AFTER_MERGE = 2
MAX_PER_SPORT_SOFT = 3
SHORTLIST_MAX = 15
SHORTLIST_MIN = 8
PRIMARY_CAP = 15
AGENT_MAX = 5  # KD2: truncate each agent to ≤5
AGENT_A_ODDS_LO = 1.40
AGENT_A_ODDS_HI = 1.90
FORCE_SCAN_TOKEN = "force_scan:"
OPEN_FULL_READD_MAX = 1  # design: may keep 1 research seat despite open full
COVERAGE_TAGS = (
    "coverage_floor:top_promo_scaffold",
    "coverage_floor:sport_rotation",
)
TOP_PROMO_SCAFFOLD_PCT = 0.20  # KD15 tag-missing scaffold-equivalent

_AGENT_ORDER = {"A": 0, "B": 1, "C": 2, "ENGINE": 50}


# ---------------------------------------------------------------------------
# Parse agent outputs
# ---------------------------------------------------------------------------


def _normalize_agent_id(raw: object, default: str = "") -> str:
    s = str(raw or default or "").strip().upper()
    if not s:
        return default
    # "scan_agent: A" / "A+C" / "agent_a" → first letter A/B/C when possible
    m = re.search(r"\b([ABC])\b", s)
    if m:
        return m.group(1)
    if s in _AGENT_ORDER:
        return s
    if s.startswith("AGENT_"):
        tail = s.split("_", 1)[-1][:1]
        if tail in _AGENT_ORDER:
            return tail
    return s[:1] if s[:1] in _AGENT_ORDER else (default or s)


def _agents_list(raw: object, default_agent: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(raw, (list, tuple)):
        for x in raw:
            a = _normalize_agent_id(x, default_agent)
            if a and a not in out:
                out.append(a)
    elif raw is not None and str(raw).strip():
        s = str(raw).strip()
        # A+C / A,C / A B
        parts = re.split(r"[+,/|\s]+", s)
        for p in parts:
            a = _normalize_agent_id(p, default_agent)
            if a and a not in out:
                out.append(a)
    if not out and default_agent:
        out = [_normalize_agent_id(default_agent)]
    # Sort A→B→C then other
    out.sort(key=lambda a: (_AGENT_ORDER.get(a, 99), a))
    return out


def _cand_from_dict(d: Mapping[str, Any], *, default_agent: str = "") -> dict[str, Any] | None:
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
    reason = str(d.get("scan_reason") or d.get("reason") or d.get("why") or "").strip()
    sport = str(d.get("sport") or "").strip()
    market_type = str(d.get("market_type") or "").strip()
    light = d.get("light_verdict") or d.get("light") or ""
    if light is not None:
        light = str(light).strip().lower()
    else:
        light = ""
    promo = fnum(d.get("promo_score") or d.get("promotion_score"))
    fam = str(d.get("market_family") or "").strip()
    role = str(d.get("role") or (agents[0] if agents else default_agent) or "").strip()
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
        "promo_score": promo,
        "in_engine_deep_queue": bool(d.get("in_engine_deep_queue", False)),
        "notes": str(d.get("notes") or ""),
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
        if "candidates" in data and isinstance(data["candidates"], list):
            rows = data["candidates"]
        elif "match" in data and "selection" in data:
            rows = [data]
        else:
            rows = []
    else:
        rows = []
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


def _parse_md_best_effort(text: str, *, default_agent: str = "") -> list[dict[str, Any]]:
    """Best-effort MD template parser (JSONL remains primary)."""
    out: list[dict[str, Any]] = []
    # Split on numbered items
    chunks = re.split(r"(?m)(?=^\d+\.\s)", text.strip())
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk or not re.match(r"^\d+\.", chunk):
            continue
        m_match = re.search(r"\*\*Match:\*\*\s*(.+)", chunk, re.I)
        if not m_match:
            continue
        match = m_match.group(1).strip().splitlines()[0].strip()
        sel = ""
        odds: float | None = None
        m_sel = re.search(
            r"\*\*Selection\s*\+?\s*odds:\*\*\s*(.+)", chunk, re.I
        )
        if m_sel:
            line = m_sel.group(1).strip().splitlines()[0].strip()
            mo = _SEL_ODDS_RE.match(line)
            if mo:
                sel = mo.group("sel").strip()
                odds = fnum(mo.group("odds"))
            else:
                sel = line
        m_why = re.search(r"\*\*Why promising:\*\*\s*(.+)", chunk, re.I)
        reason = m_why.group(1).strip().splitlines()[0].strip() if m_why else ""
        m_ag = re.search(r"\*\*scan_agent:\*\*\s*(\S+)", chunk, re.I)
        agent_raw = m_ag.group(1) if m_ag else default_agent
        if not match or not sel:
            continue
        c = _cand_from_dict(
            {
                "match": match,
                "selection": sel,
                "decimal_odds": odds,
                "scan_reason": reason,
                "scan_agents": _agents_list(agent_raw, default_agent),
            },
            default_agent=default_agent,
        )
        if c:
            out.append(c)
    return out


def parse_agent_file(
    path: Path | str | None,
    *,
    default_agent: str = "",
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
    # JSON array / object
    if suffix == ".json":
        rows = _parse_json_payload(text, default_agent=default_agent)
        if rows:
            return rows
        # fall through to MD if mislabeled
    if suffix == ".jsonl" or suffix == ".ndjson":
        rows = _parse_jsonl(text, default_agent=default_agent)
        if rows:
            return rows
        # maybe single JSON blob
        rows = _parse_json_payload(text, default_agent=default_agent)
        if rows:
            return rows

    # Auto-detect: try JSONL lines first, then full JSON, then MD
    if text.lstrip().startswith("{") or text.lstrip().startswith("["):
        # Prefer line-oriented JSONL when multiple lines of objects
        lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if len(lines) > 1 and all(ln.strip().startswith("{") for ln in lines[:5]):
            rows = _parse_jsonl(text, default_agent=default_agent)
            if rows:
                return rows
        rows = _parse_json_payload(text, default_agent=default_agent)
        if rows:
            return rows
        rows = _parse_jsonl(text, default_agent=default_agent)
        if rows:
            return rows

    if suffix in (".md", ".markdown", ".txt") or "**Match:**" in text or "**match:**" in text.lower():
        return _parse_md_best_effort(text, default_agent=default_agent)

    # Last resort
    rows = _parse_jsonl(text, default_agent=default_agent)
    if rows:
        return rows
    rows = _parse_json_payload(text, default_agent=default_agent)
    if rows:
        return rows
    return _parse_md_best_effort(text, default_agent=default_agent)


def discover_agent_files(agents_dir: Path | str) -> dict[str, Path]:
    """Find scan_agent_a/b/c* files under a directory (prefer jsonl > json > md)."""
    d = Path(agents_dir)
    found: dict[str, Path] = {}
    if not d.is_dir():
        return found
    for letter in ("a", "b", "c"):
        pats = [
            f"scan_agent_{letter}*.jsonl",
            f"scan_agent_{letter}*.json",
            f"scan_agent_{letter}*.md",
            f"scan_{letter}*.jsonl",
            f"scan_{letter}*.json",
        ]
        hits: list[Path] = []
        for pat in pats:
            hits.extend(sorted(d.glob(pat)))
        if hits:
            # Prefer jsonl
            hits.sort(
                key=lambda p: (
                    {".jsonl": 0, ".ndjson": 0, ".json": 1, ".md": 2}.get(p.suffix.lower(), 9),
                    p.name,
                )
            )
            found[letter.upper()] = hits[0]
    return found


# ---------------------------------------------------------------------------
# Odds dump index + validation
# ---------------------------------------------------------------------------


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
        key = evidence_pair_key(c.match, c.selection)
        idx[key].append(
            {
                "match": c.match,
                "selection": c.selection,
                "decimal_odds": float(c.decimal_odds),
                "sport": c.sport or "",
                "market_type": getattr(c, "market_type", "") or "",
            }
        )
    return dict(idx), raw


def odds_match_ok(
    scan_odds: float | None,
    dump_odds: float,
    *,
    tol: float = ODDS_TOL_REL,
) -> bool:
    if dump_odds <= 0:
        return False
    if scan_odds is None:
        # Allow missing scan odds if key matches (operator may omit exact price)
        return True
    return abs(float(scan_odds) - float(dump_odds)) / float(dump_odds) <= tol + 1e-12


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
    # Prefer exact odds, else within tol
    best: dict[str, Any] | None = None
    best_delta = 1e9
    for r in rows:
        o = float(r["decimal_odds"])
        if scan_odds is None:
            return dict(r)
        if odds_match_ok(scan_odds, o, tol=tol):
            delta = abs(float(scan_odds) - o)
            if delta < best_delta:
                best_delta = delta
                best = dict(r)
    return best


# ---------------------------------------------------------------------------
# Open occupancy (live ledger read-only)
# ---------------------------------------------------------------------------


def open_occupancy_from_rows(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    max_per_family: int = MAX_FAMILY_AFTER_MERGE,
    max_per_sport: int = 2,
) -> dict[str, Any]:
    """Count open Pending+ConfirmedPlaced family/sport via filter_live_rows."""
    family_counts: Counter[str] = Counter()
    sport_counts: Counter[str] = Counter()
    for r in filter_live_rows(rows or []):
        if not is_open_risk(r.get("result")):
            continue
        sp = normalize_sport(str(r.get("sport") or ""), default="unknown")
        sel = str(r.get("selection") or "")
        mt = str(r.get("market_type") or "")
        fam = market_family(sport=sp, selection=sel, market_type=mt)
        if fam:
            family_counts[fam] += 1
        if sp:
            sport_counts[sp] += 1
    return {
        "family_counts": dict(family_counts),
        "sport_counts": dict(sport_counts),
        "max_per_family": int(max_per_family),
        "max_per_sport": int(max_per_sport),
    }


def load_open_occupancy(
    cfg: Mapping[str, Any] | None = None,
    *,
    live_rows: Sequence[Mapping[str, Any]] | None = None,
    max_per_family: int = MAX_FAMILY_AFTER_MERGE,
    max_per_sport: int = 2,
) -> dict[str, Any]:
    """Read-only open occupancy. Pass live_rows to avoid touching ledger path in tests."""
    if live_rows is not None:
        return open_occupancy_from_rows(
            live_rows, max_per_family=max_per_family, max_per_sport=max_per_sport
        )
    if cfg is None:
        return open_occupancy_from_rows(
            [], max_per_family=max_per_family, max_per_sport=max_per_sport
        )
    try:
        from nt.bets_io import load_bets

        bets_path = path_from_config(dict(cfg), "bets")
        rows = load_bets(bets_path)
    except Exception:
        rows = []
    # Diversify caps from learning if present
    try:
        from nt.learning import diversification_limits

        div = diversification_limits(dict(cfg))
        max_per_family = int(div.get("max_per_market_family", max_per_family))
        max_per_sport = int(div.get("max_per_sport", max_per_sport))
    except Exception:
        pass
    return open_occupancy_from_rows(
        rows, max_per_family=max_per_family, max_per_sport=max_per_sport
    )


# ---------------------------------------------------------------------------
# Deep queue (read-only) → coverage_critical + promo hints
# ---------------------------------------------------------------------------


def load_deep_queue_lines(
    cfg: Mapping[str, Any] | None = None,
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
        q = state.get("deep_queue") or []
        return [dict(x) for x in q if isinstance(x, Mapping)]
    except Exception:
        return []


def _line_notes_blob(line: Mapping[str, Any]) -> str:
    parts = [
        str(line.get("notes") or ""),
        str(line.get("reason") or ""),
        str(line.get("tags") or ""),
        " ".join(str(t) for t in (line.get("tag_list") or []) if t),
    ]
    return " ".join(parts).lower()


def is_coverage_critical(line: Mapping[str, Any]) -> bool:
    blob = _line_notes_blob(line)
    for tag in COVERAGE_TAGS:
        if tag in blob:
            return True
    # Also check explicit tags list
    tags = line.get("tags")
    if isinstance(tags, (list, tuple)):
        joined = " ".join(str(t) for t in tags).lower()
        for tag in COVERAGE_TAGS:
            if tag in joined:
                return True
    if line.get("coverage_critical") or line.get("_scaffold_equiv"):
        return True
    return False


def coverage_floor_enabled(cfg: Mapping[str, Any] | None) -> bool:
    if not cfg:
        return False
    try:
        from nt.light_research import coverage_floor_cfg

        return bool(coverage_floor_cfg(dict(cfg)).get("enabled", False))
    except Exception:
        cfc = (dict(cfg).get("research") or {}).get("coverage_floor") or {}
        return bool(cfc.get("enabled", False))


def _has_coverage_tag(line: Mapping[str, Any]) -> bool:
    blob = _line_notes_blob(line)
    if any(tag in blob for tag in COVERAGE_TAGS):
        return True
    tags = line.get("tags")
    if isinstance(tags, (list, tuple)):
        joined = " ".join(str(t) for t in tags).lower()
        if any(tag in joined for tag in COVERAGE_TAGS):
            return True
    return bool(line.get("coverage_critical")) and not line.get("_scaffold_equiv")


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
    import math

    tagged: list[dict[str, Any]] = []
    for line in queue:
        if not isinstance(line, Mapping):
            continue
        if _has_coverage_tag(line):
            tagged.append(dict(line))
    if tagged:
        tagged.sort(key=_promo_of, reverse=True)
        return tagged
    # KD15: tags missing → top ~20% by promo when coverage_floor enabled
    if coverage_floor_on and queue:
        ranked = sorted(
            (dict(x) for x in queue if isinstance(x, Mapping)),
            key=_promo_of,
            reverse=True,
        )
        n = len(ranked)
        k = max(1, math.floor(n * float(top_promo_pct))) if n else 0
        out: list[dict[str, Any]] = []
        for r in ranked[:k]:
            rr = dict(r)
            rr["_scaffold_equiv"] = True
            rr["coverage_critical"] = True
            notes = str(rr.get("notes") or "")
            if "coverage_floor:top_promo_scaffold" not in notes.lower():
                rr["notes"] = (notes + " coverage_floor:top_promo_scaffold:equiv").strip()
            out.append(rr)
        return out
    return []


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
    if payload is None:
        try:
            outbox = path_from_config(dict(cfg), "outbox")
            latest = outbox / "light_research" / "LATEST.json"
            if latest.is_file():
                data = json.loads(latest.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    payload = data
                elif isinstance(data, list):
                    payload = {"records": data}
        except Exception:
            payload = None
    if not payload:
        return {}
    out: dict[tuple[str, str], str] = {}
    for r in payload.get("records") or []:
        if not isinstance(r, Mapping):
            continue
        k = evidence_pair_key(str(r.get("match") or ""), str(r.get("selection") or ""))
        v = str(r.get("verdict") or r.get("light_verdict") or "").strip().lower()
        if v:
            out[k] = v
    return out


def _promo_of(row: Mapping[str, Any]) -> float:
    return float(row.get("promo_score") or row.get("promotion_score") or 0.0)


def truncate_agent_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    max_n: int = AGENT_MAX,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep top max_n by promo (stable), return (kept, dropped_for_agent_max)."""
    indexed = list(enumerate(rows or []))
    if len(indexed) <= max_n:
        return [dict(r) for r in (rows or [])], []
    indexed.sort(key=lambda iv: (-_promo_of(iv[1]), iv[0]))
    keep_idx = {iv[0] for iv in indexed[:max_n]}
    kept = [dict(rows[i]) for i in range(len(rows)) if i in keep_idx]
    # Order kept by promo desc for merge priority
    kept.sort(key=lambda r: (-_promo_of(r),))
    dropped = [dict(rows[i]) for i in range(len(rows)) if i not in keep_idx]
    return kept, dropped


def _queue_line_as_candidate(
    line: Mapping[str, Any],
    *,
    reason: str = "engine_topup",
    open_occ: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert deep_queue line into a shortlist candidate (engine provenance)."""
    sp = normalize_sport(str(line.get("sport") or ""), default="unknown")
    sel = str(line.get("selection") or "")
    fam = str(line.get("market_family") or "").strip() or market_family(
        sport=sp, selection=sel, market_type=str(line.get("market_type") or "")
    )
    odds = fnum(line.get("decimal_odds") or line.get("odds"))
    match = str(line.get("match") or "")
    key = evidence_pair_key(match, sel)
    occ = open_occ or {}
    fam_counts = occ.get("family_counts") or {}
    sp_counts = occ.get("sport_counts") or {}
    max_f = int(occ.get("max_per_family") or MAX_FAMILY_AFTER_MERGE)
    max_s = int(occ.get("max_per_sport") or 2)
    open_fam = int(fam_counts.get(fam, 0))
    open_sp = int(sp_counts.get(sp, 0))
    return {
        "match": match,
        "selection": sel,
        "decimal_odds": odds,
        "sport": sp,
        "market_type": str(line.get("market_type") or ""),
        "market_family": fam,
        "scan_agents": ["engine"],
        "scan_reason": reason,
        "role": "engine",
        "light_verdict": str(line.get("light_verdict") or line.get("verdict") or ""),
        "promo_score": _promo_of(line),
        "in_engine_deep_queue": True,
        "on_odds_dump": True,
        "engine_topup": reason.startswith("engine_topup"),
        "engine_fallback": reason.startswith("engine_fallback"),
        "_key": key,
        "open_family_count": open_fam,
        "open_sport_count": open_sp,
        "open_family_full": open_fam >= max_f if fam else False,
        "open_sport_full": open_sp >= max_s if sp else False,
    }


# ---------------------------------------------------------------------------
# Merge core
# ---------------------------------------------------------------------------


def _has_force_scan(reason: str) -> bool:
    return FORCE_SCAN_TOKEN in (reason or "").lower()


def _render_scan_agent(agents: Sequence[str]) -> str:
    ordered = sorted(
        {a for a in agents if a},
        key=lambda a: (_AGENT_ORDER.get(a, 99), a),
    )
    return "+".join(ordered)


def _priority_tuple(
    c: Mapping[str, Any],
    *,
    open_occ: Mapping[str, Any],
) -> tuple:
    """Higher is better (sort reverse=True)."""
    fam = str(c.get("market_family") or "")
    sp = str(c.get("sport") or "")
    fam_counts = open_occ.get("family_counts") or {}
    sp_counts = open_occ.get("sport_counts") or {}
    max_f = int(open_occ.get("max_per_family") or MAX_FAMILY_AFTER_MERGE)
    max_s = int(open_occ.get("max_per_sport") or 2)
    open_fam_full = int(fam_counts.get(fam, 0)) >= max_f if fam else False
    open_sp_full = int(sp_counts.get(sp, 0)) >= max_s if sp else False
    promo = float(c.get("promo_score") or 0.0)
    in_q = 1 if c.get("in_engine_deep_queue") else 0
    multi = len(c.get("scan_agents") or [])
    # Role specificity: prefer A for ML-ish, B for totals, C for HC when role matches family
    role = str(c.get("role") or ((c.get("scan_agents") or [""])[0])).upper()
    fam_l = fam.lower()
    role_score = 0
    if role == "A" and ("_ml" in fam_l or fam_l.endswith("1x2") or "moneyline" in fam_l):
        role_score = 2
    elif role == "B" and ("total" in fam_l or "prop" in fam_l or "180" in fam_l):
        role_score = 2
    elif role == "C" and ("handicap" in fam_l or "hc" in fam_l):
        role_score = 2
    elif role in ("A", "B", "C"):
        role_score = 1
    agent_tie = -min((_AGENT_ORDER.get(a, 99) for a in (c.get("scan_agents") or ["Z"])), default=99)
    reason_len = len(str(c.get("scan_reason") or ""))
    return (
        in_q,
        promo,
        multi,
        role_score,
        0 if open_fam_full else 1,
        0 if open_sp_full else 1,
        agent_tie,
        reason_len,
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
        out["match"], out["selection"], out.get("decimal_odds"), odds_index
    )
    out["on_odds_dump"] = dump is not None
    if dump:
        # Prefer dump sport/odds/selection identity
        if not out.get("sport") and dump.get("sport"):
            out["sport"] = dump["sport"]
        if out.get("decimal_odds") is None and dump.get("decimal_odds") is not None:
            out["decimal_odds"] = dump["decimal_odds"]
        if not out.get("market_type") and dump.get("market_type"):
            out["market_type"] = dump["market_type"]
    sp = normalize_sport(str(out.get("sport") or ""), default="unknown")
    out["sport"] = sp if sp != "unknown" or out.get("sport") else str(out.get("sport") or "")
    if not out.get("sport"):
        out["sport"] = sp
    fam = str(out.get("market_family") or "").strip()
    if not fam:
        fam = market_family(
            sport=out.get("sport") or "",
            selection=out.get("selection") or "",
            market_type=out.get("market_type") or "",
        )
    out["market_family"] = fam
    key = evidence_pair_key(out["match"], out["selection"])
    out["_key"] = key
    if key in queue_keys:
        out["in_engine_deep_queue"] = True
    if out.get("promo_score") is None and key in queue_promo:
        out["promo_score"] = queue_promo[key]
    elif out.get("promo_score") is None:
        out["promo_score"] = 0.0
    if not out.get("light_verdict") and key in light_by_key:
        out["light_verdict"] = light_by_key[key]
    if not out.get("scan_agents"):
        out["scan_agents"] = _agents_list(out.get("role") or "A")
    return out


def merge_candidates(
    agent_candidates: Mapping[str, Sequence[Mapping[str, Any]]] | Sequence[Mapping[str, Any]],
    *,
    odds_path: Path | str,
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
) -> dict[str, Any]:
    """
    Deterministic merge of multi-agent scan candidates.

    Returns payload with candidates, dropped, primary_worklist, counts.
    """
    # Flatten agent map with per-agent max-5 truncate (KD2)
    raw_list: list[dict[str, Any]] = []
    agent_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    agent_raw_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    dropped: list[dict[str, Any]] = []
    notes: list[str] = []

    if isinstance(agent_candidates, Mapping):
        for ag, rows in agent_candidates.items():
            ag_n = _normalize_agent_id(ag, str(ag))
            rows_list = [dict(r) for r in (rows or [])]
            if ag_n in agent_raw_counts:
                agent_raw_counts[ag_n] = len(rows_list)
            kept_rows, over = truncate_agent_rows(rows_list, max_n=agent_max)
            for r in over:
                c = dict(r)
                if not c.get("scan_agents"):
                    c["scan_agents"] = _agents_list(ag_n)
                dropped.append({**_public(c), "drop_reason": "agent_max_5"})
            n = 0
            for r in kept_rows:
                c = dict(r)
                if not c.get("scan_agents"):
                    c["scan_agents"] = _agents_list(ag_n)
                if not c.get("role"):
                    c["role"] = ag_n
                raw_list.append(c)
                n += 1
            if ag_n in agent_counts:
                agent_counts[ag_n] = n
    else:
        # Sequence: group by first scan_agent then truncate per letter
        by_ag: dict[str, list[dict[str, Any]]] = defaultdict(list)
        ungrouped: list[dict[str, Any]] = []
        for r in agent_candidates:
            c = dict(r)
            agents = _agents_list(c.get("scan_agents") or c.get("role") or "")
            if agents and agents[0] in ("A", "B", "C"):
                by_ag[agents[0]].append(c)
            else:
                ungrouped.append(c)
        for ag_n in ("A", "B", "C"):
            rows_list = by_ag.get(ag_n) or []
            agent_raw_counts[ag_n] = len(rows_list)
            kept_rows, over = truncate_agent_rows(rows_list, max_n=agent_max)
            for r in over:
                dropped.append({**_public(r), "drop_reason": "agent_max_5"})
            agent_counts[ag_n] = len(kept_rows)
            raw_list.extend(kept_rows)
        raw_list.extend(ungrouped)

    odds_index, odds_raw = build_odds_index(odds_path)
    sports_on_dump = {
        normalize_sport(getattr(c, "sport", "") or "", default="unknown")
        for c in odds_raw
    }
    sports_on_dump.discard("unknown")
    multi_sport_board = len(sports_on_dump) >= 3

    queue = list(deep_queue or [])
    queue_keys: set[tuple[str, str]] = set()
    queue_promo: dict[tuple[str, str], float] = {}
    for line in queue:
        k = evidence_pair_key(str(line.get("match") or ""), str(line.get("selection") or ""))
        queue_keys.add(k)
        ps = fnum(line.get("promo_score") or line.get("promotion_score"))
        if ps is not None:
            queue_promo[k] = max(queue_promo.get(k, 0.0), float(ps))

    light_by_key: dict[tuple[str, str], str] = dict(light_verdicts or {})
    occ = dict(open_occ or open_occupancy_from_rows([]))

    # ISS-2 early: all agents empty → engine deep_queue fallback
    if not raw_list and queue:
        fb = _engine_queue_shortlist(
            queue,
            odds_index=odds_index,
            open_occ=occ,
            light_by_key=light_by_key,
            max_family=max_family,
            shortlist_max=shortlist_max,
            reason="engine_fallback",
        )
        missing = [a for a in ("A", "B", "C") if agent_raw_counts.get(a, 0) == 0]
        notes.append("fallback: engine_deep_queue")
        notes.append(f"scan_agent_missing: {','.join(missing) if missing else 'A,B,C'}")
        primary = [_public(c) for c in fb]
        # Still union any remaining coverage_critical not already present
        cov = coverage_critical_lines(queue, coverage_floor_on=coverage_floor_on)
        seen = {c["_key"] for c in fb}
        for line in cov:
            k = evidence_pair_key(str(line.get("match") or ""), str(line.get("selection") or ""))
            if k in seen:
                continue
            if len(primary) >= PRIMARY_CAP:
                dropped.append(
                    {
                        "match": line.get("match"),
                        "selection": line.get("selection"),
                        "decimal_odds": line.get("decimal_odds"),
                        "drop_reason": "primary_cap_drop",
                        "notes": "coverage_critical overflow",
                    }
                )
                continue
            primary.append(
                {
                    "match": line.get("match"),
                    "selection": line.get("selection"),
                    "decimal_odds": line.get("decimal_odds"),
                    "sport": line.get("sport") or "",
                    "market_family": line.get("market_family")
                    or market_family(
                        sport=str(line.get("sport") or ""),
                        selection=str(line.get("selection") or ""),
                    ),
                    "scan_agents": [],
                    "scan_agent": "",
                    "scan_reason": "coverage_critical",
                    "coverage_critical": True,
                    "in_engine_deep_queue": True,
                    "promo_score": _promo_of(line),
                }
            )
            seen.add(k)
        public_final = [_public(c) for c in fb]
        return {
            "schema_version": 1,
            "odds_file": str(odds_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "agents": agent_counts,
            "agent_raw_counts": agent_raw_counts,
            "raw_n": 0,
            "final_n": len(public_final),
            "max_per_family_after_merge": max_family,
            "primary_worklist_n": len(primary),
            "multi_sport_board": multi_sport_board,
            "sports_on_dump": sorted(sports_on_dump),
            "open_occupancy": {
                "family_counts": dict(occ.get("family_counts") or {}),
                "sport_counts": dict(occ.get("sport_counts") or {}),
                "max_per_family": occ.get("max_per_family"),
                "max_per_sport": occ.get("max_per_sport"),
            },
            "candidates": public_final,
            "primary_worklist": primary,
            "dropped": dropped,
            "notes": notes,
            "fallback": "engine_deep_queue",
            "scan_agent_missing": missing if missing else ["A", "B", "C"],
        }

    enriched: list[dict[str, Any]] = []

    for raw in raw_list:
        c = _enrich_candidate(
            dict(raw),
            odds_index=odds_index,
            queue_keys=queue_keys,
            queue_promo=queue_promo,
            light_by_key=light_by_key,
        )
        # Hard drops
        if not c.get("on_odds_dump"):
            # Also try with tol explicitly (find_on_odds already applied)
            dropped.append({**_public(c), "drop_reason": "off_odds_dump"})
            continue
        # Re-check odds tol against chosen dump row
        dump = find_on_odds_dump(
            c["match"], c["selection"], c.get("decimal_odds"), odds_index, tol=odds_tol
        )
        if dump is None:
            dropped.append({**_public(c), "drop_reason": "off_odds_dump"})
            continue
        if not str(c.get("scan_reason") or "").strip():
            dropped.append({**_public(c), "drop_reason": "empty_scan_reason"})
            continue
        # Agent A odds band
        agents = c.get("scan_agents") or []
        role = str(c.get("role") or "").upper()
        is_a_only = agents == ["A"] or (role == "A" and set(agents) <= {"A"})
        if is_a_only or (agents == ["A"]):
            o = c.get("decimal_odds")
            if o is not None and not (AGENT_A_ODDS_LO - 1e-9 <= float(o) <= AGENT_A_ODDS_HI + 1e-9):
                dropped.append({**_public(c), "drop_reason": "agent_a_odds_band"})
                continue
        # Light-fail soft drop (KD16) for multi-agent-only lines
        light = str(c.get("light_verdict") or "").lower()
        if light in ("fail", "hard_fail", "light_fail"):
            if not c.get("in_engine_deep_queue") and not _has_force_scan(
                str(c.get("scan_reason") or "")
            ):
                dropped.append({**_public(c), "drop_reason": "light_fail"})
                continue
        # Open occupancy counts on candidate
        fam = c.get("market_family") or ""
        sp = c.get("sport") or ""
        fam_counts = occ.get("family_counts") or {}
        sp_counts = occ.get("sport_counts") or {}
        max_f = int(occ.get("max_per_family") or max_family)
        max_s = int(occ.get("max_per_sport") or 2)
        c["open_family_count"] = int(fam_counts.get(fam, 0))
        c["open_sport_count"] = int(sp_counts.get(sp, 0))
        c["open_family_full"] = c["open_family_count"] >= max_f if fam else False
        c["open_sport_full"] = c["open_sport_count"] >= max_s if sp else False
        enriched.append(c)

    # Dedupe by evidence_pair_key
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for c in enriched:
        key = c["_key"]
        if key not in by_key:
            by_key[key] = c
            continue
        prev = by_key[key]
        # Union scan_agents
        agents = list(prev.get("scan_agents") or [])
        for a in c.get("scan_agents") or []:
            if a not in agents:
                agents.append(a)
        agents = _agents_list(agents)
        # Prefer longer/clearer reason
        r1 = str(prev.get("scan_reason") or "")
        r2 = str(c.get("scan_reason") or "")
        if len(r2) > len(r1):
            reason = r2
            if r1 and r1 not in r2:
                reason = f"{r2}; also: {r1}"
            keep = dict(c)
        else:
            reason = r1
            if r2 and r2 not in r1 and len(r2) > 0:
                reason = f"{r1}; also: {r2}" if r1 else r2
            keep = dict(prev)
        keep["scan_agents"] = agents
        keep["scan_reason"] = reason
        # Merge flags
        keep["in_engine_deep_queue"] = bool(
            prev.get("in_engine_deep_queue") or c.get("in_engine_deep_queue")
        )
        keep["promo_score"] = max(
            float(prev.get("promo_score") or 0), float(c.get("promo_score") or 0)
        )
        # Prefer non-empty light pass over missing
        if not keep.get("light_verdict") and c.get("light_verdict"):
            keep["light_verdict"] = c["light_verdict"]
        by_key[key] = keep

    deduped = list(by_key.values())
    # Sort by priority
    deduped.sort(key=lambda c: _priority_tuple(c, open_occ=occ), reverse=True)

    # Soft drop open_full when alternatives exist (deprioritize already sorted lower)
    kept: list[dict[str, Any]] = []
    for c in deduped:
        if c.get("open_family_full"):
            # Prefer drop; keep only if we would fall under shortlist_min later
            # Mark and handle after first pass family/sport caps
            c = dict(c)
            c["_soft_open_family"] = True
        if c.get("open_sport_full"):
            c = dict(c)
            c["_soft_open_sport"] = True
        kept.append(c)

    # Family cap ≤2 (KD4): prefer spread to 1 first, then second seats
    after_family = _apply_family_cap(kept, max_family=max_family, dropped=dropped)

    # Soft open_full drops (prefer drop; may re-add at most OPEN_FULL_READD_MAX)
    after_open: list[dict[str, Any]] = []
    pending_open: list[tuple[str, dict[str, Any]]] = []
    for c in after_family:
        if c.get("_soft_open_family"):
            pending_open.append(("open_family_full", c))
        elif c.get("_soft_open_sport"):
            pending_open.append(("open_sport_full", c))
        else:
            after_open.append(c)
    # Highest promo first; re-add at most 1 seat if under shortlist_min
    pending_open.sort(key=lambda rc: _promo_of(rc[1]), reverse=True)
    readded = 0
    for reason, c in pending_open:
        if len(after_open) < shortlist_min and readded < OPEN_FULL_READD_MAX:
            cc = dict(c)
            note = f"research_despite_open_full: {reason}"
            cc["scan_reason"] = f"{cc.get('scan_reason') or ''} [{note}]".strip()
            after_open.append(cc)
            readded += 1
        else:
            dropped.append({**_public(c), "drop_reason": reason})

    # Soft sport spread ≤3 when multi-sport board
    after_sport: list[dict[str, Any]] = []
    if multi_sport_board and soft_sport_cap > 0:
        sp_counts_sel: Counter[str] = Counter()
        deferred_sport: list[dict[str, Any]] = []
        for c in after_open:
            sp = str(c.get("sport") or "unknown")
            if sp_counts_sel[sp] >= soft_sport_cap:
                deferred_sport.append(c)
                continue
            sp_counts_sel[sp] += 1
            after_sport.append(c)
        for c in deferred_sport:
            if len(after_sport) > shortlist_min:
                dropped.append({**_public(c), "drop_reason": "sport_soft_cap"})
            else:
                after_sport.append(c)
    else:
        after_sport = after_open

    # Size clamp max
    final = after_sport
    if len(final) > shortlist_max:
        for c in final[shortlist_max:]:
            dropped.append({**_public(c), "drop_reason": "shortlist_max"})
        final = final[:shortlist_max]

    # ISS-1: engine top-up when final < shortlist_min
    if len(final) < shortlist_min and queue:
        final, topup_n = _engine_topup(
            final,
            queue=queue,
            odds_index=odds_index,
            open_occ=occ,
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

    # ISS-2 late: all candidates dropped but queue healthy → full engine fallback
    if not final and queue:
        final = _engine_queue_shortlist(
            queue,
            odds_index=odds_index,
            open_occ=occ,
            light_by_key=light_by_key,
            max_family=max_family,
            shortlist_max=shortlist_max,
            reason="engine_fallback",
        )
        notes.append("fallback: engine_deep_queue")
        missing = [a for a in ("A", "B", "C") if agent_counts.get(a, 0) == 0]
        if sum(agent_counts.values()) == 0:
            missing = ["A", "B", "C"]
        notes.append(f"scan_agent_missing: {','.join(missing) if missing else 'A,B,C'}")

    # Primary worklist = shortlist ∪ coverage_critical (cap 15)
    shortlist_keys = {c["_key"] for c in final}
    primary: list[dict[str, Any]] = [_public(c) for c in final]
    cov = coverage_critical_lines(queue, coverage_floor_on=coverage_floor_on)
    for line in cov:
        k = evidence_pair_key(str(line.get("match") or ""), str(line.get("selection") or ""))
        if k in shortlist_keys:
            continue
        if len(primary) >= PRIMARY_CAP:
            dropped.append(
                {
                    "match": line.get("match"),
                    "selection": line.get("selection"),
                    "decimal_odds": line.get("decimal_odds"),
                    "drop_reason": "primary_cap_drop",
                    "notes": "coverage_critical overflow",
                }
            )
            continue
        primary.append(
            {
                "match": line.get("match"),
                "selection": line.get("selection"),
                "decimal_odds": line.get("decimal_odds"),
                "sport": line.get("sport") or "",
                "market_family": line.get("market_family")
                or market_family(
                    sport=str(line.get("sport") or ""),
                    selection=str(line.get("selection") or ""),
                ),
                "scan_agents": [],
                "scan_agent": "",
                "scan_reason": "coverage_critical",
                "coverage_critical": True,
                "in_engine_deep_queue": True,
                "promo_score": _promo_of(line),
            }
        )
        shortlist_keys.add(k)

    public_final = [_public(c) for c in final]
    out: dict[str, Any] = {
        "schema_version": 1,
        "odds_file": str(odds_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agents": agent_counts,
        "agent_raw_counts": agent_raw_counts,
        "raw_n": len(raw_list),
        "final_n": len(public_final),
        "max_per_family_after_merge": max_family,
        "primary_worklist_n": len(primary),
        "multi_sport_board": multi_sport_board,
        "sports_on_dump": sorted(sports_on_dump),
        "open_occupancy": {
            "family_counts": dict(occ.get("family_counts") or {}),
            "sport_counts": dict(occ.get("sport_counts") or {}),
            "max_per_family": occ.get("max_per_family"),
            "max_per_sport": occ.get("max_per_sport"),
        },
        "candidates": public_final,
        "primary_worklist": primary,
        "dropped": dropped,
        "notes": notes,
    }
    if any(n.startswith("fallback:") for n in notes):
        out["fallback"] = "engine_deep_queue"
    return out


def _apply_family_cap(
    candidates: Sequence[Mapping[str, Any]],
    *,
    max_family: int,
    dropped: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    KD4: each market_family ≤ max_family.
    Prefer spread to 1 first (pass1), then fill second seats (pass2).
    """
    ordered = list(candidates)
    # Pass 1: at most 1 per family
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
    # Pass 2: second seats up to max_family, by original priority order
    fam_counts: Counter[str] = Counter(
        str(c.get("market_family") or "other") for c in first_seats
    )
    after: list[dict[str, Any]] = list(first_seats)
    for c in leftovers:
        fam = str(c.get("market_family") or "other")
        if fam_counts[fam] >= max_family:
            dropped.append({**_public(c), "drop_reason": "family_cap"})
            continue
        fam_counts[fam] += 1
        after.append(c)
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
    have = {c["_key"] for c in final}
    fam_counts: Counter[str] = Counter(
        str(c.get("market_family") or "other") for c in final
    )
    sp_counts: Counter[str] = Counter(str(c.get("sport") or "unknown") for c in final)
    # Rank queue by promo desc
    ranked = sorted(
        (dict(x) for x in queue if isinstance(x, Mapping)),
        key=_promo_of,
        reverse=True,
    )
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
        # Must be on odds dump
        dump = find_on_odds_dump(
            match, sel, fnum(line.get("decimal_odds") or line.get("odds")), odds_index
        )
        if dump is None:
            continue
        # Light: skip hard fail
        light = str(
            light_by_key.get(k)
            or line.get("light_verdict")
            or line.get("verdict")
            or ""
        ).lower()
        if light in ("fail", "hard_fail", "light_fail"):
            continue
        cand = _queue_line_as_candidate(line, reason="engine_topup", open_occ=open_occ)
        if dump.get("sport") and not cand.get("sport"):
            cand["sport"] = dump["sport"]
        fam = str(cand.get("market_family") or "other")
        if fam_counts[fam] >= max_family:
            continue
        # Prefer not open-full
        if cand.get("open_family_full") or cand.get("open_sport_full"):
            continue
        sp = str(cand.get("sport") or "unknown")
        if multi_sport_board and soft_sport_cap > 0 and sp_counts[sp] >= soft_sport_cap:
            continue
        fam_counts[fam] += 1
        sp_counts[sp] += 1
        have.add(k)
        out.append(cand)
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
    ranked = sorted(
        (dict(x) for x in queue if isinstance(x, Mapping)),
        key=_promo_of,
        reverse=True,
    )
    cands: list[dict[str, Any]] = []
    for line in ranked:
        match = str(line.get("match") or "")
        sel = str(line.get("selection") or "")
        if not match or not sel:
            continue
        odds = fnum(line.get("decimal_odds") or line.get("odds"))
        # Prefer on-dump; still allow if odds index empty in unit tests with synthetic queue
        dump = find_on_odds_dump(match, sel, odds, odds_index)
        if odds_index and dump is None:
            continue
        light = str(
            light_by_key.get(evidence_pair_key(match, sel))
            or line.get("light_verdict")
            or line.get("verdict")
            or ""
        ).lower()
        if light in ("fail", "hard_fail", "light_fail"):
            continue
        cands.append(
            _queue_line_as_candidate(line, reason=reason, open_occ=open_occ)
        )
    # Family cap via two-pass spread
    dummy_dropped: list[dict[str, Any]] = []
    capped = _apply_family_cap(cands, max_family=max_family, dropped=dummy_dropped)
    return capped[:shortlist_max]


def _public(c: Mapping[str, Any]) -> dict[str, Any]:
    raw_agents = list(c.get("scan_agents") or [])
    # Preserve engine token for top-up / fallback provenance
    agents: list[str] = []
    for a in raw_agents:
        s = str(a).strip()
        if not s:
            continue
        if s.lower() == "engine":
            if "engine" not in agents:
                agents.append("engine")
            continue
        na = _normalize_agent_id(s)
        if na and na not in agents:
            agents.append(na)
    if not agents and (c.get("engine_topup") or c.get("engine_fallback")):
        agents = ["engine"]
    render = _render_scan_agent([a for a in agents if a != "engine"])
    if "engine" in agents:
        render = "engine" if not render else f"{render}+engine"
    out = {
        "match": c.get("match"),
        "selection": c.get("selection"),
        "decimal_odds": c.get("decimal_odds"),
        "sport": c.get("sport") or "",
        "market_type": c.get("market_type") or "",
        "market_family": c.get("market_family") or "",
        "scan_agents": agents,
        "scan_agent": render,
        "scan_reason": c.get("scan_reason") or "",
        "on_odds_dump": bool(c.get("on_odds_dump", True)),
        "in_engine_deep_queue": bool(c.get("in_engine_deep_queue", False)),
        "light_verdict": c.get("light_verdict") or "",
        "promo_score": c.get("promo_score"),
        "open_family_count": c.get("open_family_count", 0),
        "open_sport_count": c.get("open_sport_count", 0),
        "open_family_full": bool(c.get("open_family_full", False)),
        "open_sport_full": bool(c.get("open_sport_full", False)),
    }
    if c.get("coverage_critical"):
        out["coverage_critical"] = True
    if c.get("engine_topup"):
        out["engine_topup"] = True
    if c.get("engine_fallback"):
        out["engine_fallback"] = True
    return out


# ---------------------------------------------------------------------------
# Render + run
# ---------------------------------------------------------------------------


def render_shortlist_markdown(payload: Mapping[str, Any]) -> str:
    agents = payload.get("agents") or {}
    a = int(agents.get("A") or 0)
    b = int(agents.get("B") or 0)
    c = int(agents.get("C") or 0)
    final_n = int(payload.get("final_n") or 0)
    day = ""
    created = str(payload.get("created_at") or "")
    if created:
        day = created[:10]
    lines: list[str] = [
        f"# MULTI_AGENT_SHORTLIST — {day or 'run'}",
        f"# Source: A({a})+B({b})+C({c}) → merge → {final_n} candidates",
        f"# Family rule: each market_family ≤{payload.get('max_per_family_after_merge', 2)} after merge (drop at ≥3)",
        f"# Open occupancy: family={payload.get('open_occupancy', {}).get('family_counts', {})} "
        f"sport={payload.get('open_occupancy', {}).get('sport_counts', {})}",
        f"# Soft sport multi-board: {payload.get('multi_sport_board')}",
        "# Deep research primary: ## Primary worklist below (cap 15)",
    ]
    for note in payload.get("notes") or []:
        lines.append(f"# Note: {note}")
    if payload.get("fallback"):
        lines.append(f"# fallback: {payload.get('fallback')}")
    lines.extend(
        [
            "",
            "| # | Match | Selection @ odds | Family | scan_agent | Why (scan) |",
            "|---|-------|------------------|--------|------------|------------|",
        ]
    )
    for i, row in enumerate(payload.get("candidates") or [], 1):
        odds = row.get("decimal_odds")
        odds_s = f"{float(odds):.2f}" if odds is not None else "?"
        why = str(row.get("scan_reason") or "").replace("|", "/")
        if len(why) > 80:
            why = why[:77] + "..."
        lines.append(
            f"| {i} | {row.get('match')} | {row.get('selection')} @ {odds_s} | "
            f"{row.get('market_family')} | {row.get('scan_agent')} | {why} |"
        )
    lines.append("")
    lines.append("## Primary worklist (Stage 2 — deep these only on primary pass)")
    pw = payload.get("primary_worklist") or []
    short_n = len(payload.get("candidates") or [])
    lines.append(f"- All {short_n} multi-agent shortlist rows above")
    extra = [r for r in pw if r.get("coverage_critical")]
    if extra:
        lines.append("- Plus coverage_critical from engine queue not already listed:")
        for r in extra:
            lines.append(
                f"  - {r.get('match')} | {r.get('selection')} @ {r.get('decimal_odds')} | coverage_critical"
            )
    lines.append(f"- Total primary_n = {len(pw)} (cap {PRIMARY_CAP})")
    lines.append("")
    lines.append("## Dropped at merge")
    drops = payload.get("dropped") or []
    if not drops:
        lines.append("- _(none)_")
    else:
        for d in drops:
            lines.append(
                f"- {d.get('match')} | {d.get('selection')} — **{d.get('drop_reason')}**"
                + (f" ({d.get('scan_reason')})" if d.get("scan_reason") else "")
            )
    lines.append("")
    lines.append("## Notes")
    lines.append("- Keys: evidence_pair_key; odds validated on full dump (2% relative tol)")
    lines.append("- Engine deep_queue.json NOT rewritten")
    lines.append("- Stage 3 portfolio still hard-caps max 2 per family and max 2 per sport at place")
    lines.append("")
    return "\n".join(lines)


def run_scan_merge(
    cfg: Mapping[str, Any] | None,
    *,
    odds: Path | str,
    agent_a: Path | str | None = None,
    agent_b: Path | str | None = None,
    agent_c: Path | str | None = None,
    agents_dir: Path | str | None = None,
    out: Path | str | None = None,
    out_json: Path | str | None = None,
    live_rows: Sequence[Mapping[str, Any]] | None = None,
    deep_queue: Sequence[Mapping[str, Any]] | None = None,
    light_verdicts: Mapping[tuple[str, str], str] | None = None,
    use_live_open: bool = True,
    write: bool = True,
) -> dict[str, Any]:
    """
    Load agents + odds, merge, optionally write outbox artifacts.
    """
    odds_path = Path(odds)
    paths: dict[str, Path | None] = {"A": None, "B": None, "C": None}
    if agents_dir:
        found = discover_agent_files(agents_dir)
        paths.update(found)
    if agent_a:
        paths["A"] = Path(agent_a)
    if agent_b:
        paths["B"] = Path(agent_b)
    if agent_c:
        paths["C"] = Path(agent_c)

    agent_map = {
        "A": parse_agent_file(paths["A"], default_agent="A"),
        "B": parse_agent_file(paths["B"], default_agent="B"),
        "C": parse_agent_file(paths["C"], default_agent="C"),
    }

    if use_live_open:
        open_occ = load_open_occupancy(cfg, live_rows=live_rows)
    else:
        open_occ = open_occupancy_from_rows(live_rows or [])

    queue = load_deep_queue_lines(cfg, deep_queue=deep_queue)

    # ISS-3: auto-load light LATEST for KD16 when caller did not inject map
    resolved_light = light_verdicts
    if resolved_light is None and cfg is not None:
        resolved_light = load_light_verdicts_map(cfg)

    payload = merge_candidates(
        agent_map,
        odds_path=odds_path,
        open_occ=open_occ,
        deep_queue=queue,
        light_verdicts=resolved_light,
        coverage_floor_on=coverage_floor_enabled(cfg),
    )
    payload["agent_files"] = {k: str(v) if v else None for k, v in paths.items()}
    payload["markdown"] = render_shortlist_markdown(payload)

    if write:
        out_path = Path(out) if out else None
        if out_path is None and cfg is not None:
            try:
                outbox = path_from_config(dict(cfg), "outbox")
                out_path = outbox / "MULTI_AGENT_SHORTLIST.md"
            except Exception:
                out_path = Path("outbox") / "MULTI_AGENT_SHORTLIST.md"
        if out_path is None:
            out_path = Path("outbox") / "MULTI_AGENT_SHORTLIST.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload["markdown"], encoding="utf-8")
        payload["md_path"] = str(out_path)

        json_path = Path(out_json) if out_json else out_path.with_suffix(".json")
        # Prefer multi_agent_shortlist.json name when default md name
        if out_json is None and out_path.name.upper().startswith("MULTI_AGENT"):
            json_path = out_path.parent / "multi_agent_shortlist.json"
        slim = {k: v for k, v in payload.items() if k != "markdown"}
        json_path.write_text(
            json.dumps(slim, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        payload["json_path"] = str(json_path)

    return payload
