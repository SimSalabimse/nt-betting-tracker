from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from nt.bets_io import fnum
from nt.portfolio import Candidate
from nt.sport_taxonomy import normalize_sport


def _safe_odds(x: object) -> float | None:
    try:
        v = fnum(x)
    except (TypeError, ValueError):
        return None
    if v is None:
        return None
    if v < 1.01 or v > 1000:
        return None
    return v


def parse_odds_file(path: Path) -> list[Candidate]:
    """
    Supported formats:
    1) CSV with headers: date,match,selection,decimal_odds[,sport,market_type,p_model,notes]
    2) Norsk Tipping Oddsen dump (match blocks separated by blank lines)
    3) Simple markdown/text lines:
       Match | Selection | Odds
       or: Match - Selection @ 1.85
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv" or _looks_like_csv(text):
        return _parse_csv(path)
    if _looks_like_nt_dump(text):
        return _parse_nt_dump(text)
    return _parse_text(text)


def _looks_like_nt_dump(text: str) -> bool:
    """NT Oddsen paste: HUB / Vinner headers, alternating selection+odds lines."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    hub_count = sum(1 for ln in lines if ln == "HUB" or ln.startswith("HUB "))
    vinner_count = sum(1 for ln in lines if ln == "Vinner" or ln.startswith("Vinner "))
    odds_like = sum(1 for ln in lines if _safe_odds(ln) is not None)
    return (hub_count + vinner_count) >= 1 and odds_like >= 6 and "|" not in lines[0]


def _split_match_blocks(text: str) -> list[list[str]]:
    """
    Split dump into match blocks using blank-line gaps.

    NT pastes put several empty lines between events. We split on 2+ consecutive
    blank lines so markets inside one event stay together, while the next HUB /
    Vinner event starts a new block.
    """
    # Normalize newlines; split on 2+ blank lines (allow whitespace-only lines)
    parts = re.split(r"(?:\r?\n[ \t]*){3,}", text.strip())
    blocks: list[list[str]] = []
    for part in parts:
        lines = [ln.rstrip() for ln in part.splitlines()]
        # drop leading/trailing empties
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            blocks.append(lines)
    return blocks


def _parse_nt_dump(text: str) -> list[Candidate]:
    """
    Parse Norsk Tipping Oddsen multi-match paste.

    Blocks (separated by blank lines):
      Football/snooker:
        HUB / Home / odds / Uavgjort / odds / Away / odds / markets...
      NBA / basketball:
        Vinner (inkludert overtid/straffer) / A / odds / B / odds / markets...
        (may also include a HUB 3-way later in the same block)
      Esports / tennis / 2-way:
        Vinner / A / odds / B / odds / markets...
    """
    rows: list[Candidate] = []
    for chunk in _split_match_blocks(text):
        rows.extend(_parse_nt_block(chunk))

    # de-dupe identical match/selection/odds
    seen: set[str] = set()
    out: list[Candidate] = []
    for c in rows:
        key = f"{c.match}|{c.selection}|{c.decimal_odds}"
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _parse_nt_block(chunk: list[str]) -> list[Candidate]:
    if not chunk:
        return []
    first = chunk[0].strip()
    if first == "HUB":
        return _parse_hub_block(chunk)
    if first.startswith("Vinner (inkludert overtid"):
        return _parse_two_way_block(chunk, kind="nba", market0=first)
    if first == "Vinner" or first.startswith("Vinner "):
        # Esports / tennis / generic 2-way moneyline
        return _parse_two_way_block(chunk, kind="vinner", market0=first)
    # Orphan market chunk without a clear event header — skip
    return []


def _parse_hub_block(chunk: list[str]) -> list[Candidate]:
    """Football-style 1X2 HUB opener."""
    if len(chunk) < 7:
        return []
    home = chunk[1].strip()
    away = chunk[5].strip()
    if not home or not away or _safe_odds(chunk[2]) is None:
        return []
    # Basic shape: home, odds, draw label, odds, away, odds
    if _safe_odds(chunk[4]) is None and chunk[3].strip().lower() not in ("uavgjort", "draw", "x"):
        # still try if slightly different
        pass
    match = f"{home} vs {away}"
    sport = normalize_sport(_infer_sport(home, away, chunk, default="football"))
    return _walk_markets(chunk, match=match, sport=sport, market="HUB", start_i=1)


def _parse_two_way_block(chunk: list[str], *, kind: str, market0: str) -> list[Candidate]:
    """
    Two-way opener:
      Vinner ...
      SideA
      odds
      SideB
      odds
      <markets...>
    """
    if len(chunk) < 5:
        return []
    home = chunk[1].strip()
    away = chunk[3].strip()
    if not home or not away or _safe_odds(chunk[2]) is None or _safe_odds(chunk[4]) is None:
        return []
    match = f"{home} vs {away}"
    if kind == "nba":
        # OT two-way opener → basketball taxonomy (not separate nba/wnba keys)
        sport = normalize_sport(_infer_sport(home, away, chunk, default="basketball"))
    else:
        sport = normalize_sport(_infer_sport(home, away, chunk, default="esports"))
    return _walk_markets(chunk, match=match, sport=sport, market=market0, start_i=1)


def _extract_kickoff(chunk: list[str]) -> str:
    """Parse ``Kick-off: YYYY-MM-DD HH:MM`` (CEST) from a match block."""
    for ln in chunk:
        s = (ln or "").strip()
        if not s.lower().startswith("kick-off"):
            continue
        # "Kick-off: 2026-07-19 21:00" or "Kick-off:2026-07-19T21:00:00+02:00"
        rest = s.split(":", 1)[1].strip() if ":" in s else ""
        rest = rest.replace("T", " ").strip()
        # keep YYYY-MM-DD HH:MM when present
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?", rest)
        if not m:
            continue
        if m.group(2):
            return f"{m.group(1)} {m.group(2)}"
        return m.group(1)
    return ""


def _match_date_from_kickoff(kickoff: str) -> str:
    """Calendar date of the match from kickoff (not place time)."""
    ko = (kickoff or "").strip()
    if len(ko) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", ko[:10]):
        return ko[:10]
    return ""


def _walk_markets(
    chunk: list[str],
    *,
    match: str,
    sport: str,
    market: str,
    start_i: int,
) -> list[Candidate]:
    """Walk selection/odds pairs; non-odds lines without following odds become market headers."""
    rows: list[Candidate] = []
    kickoff = _extract_kickoff(chunk)
    match_date = _match_date_from_kickoff(kickoff)
    i = start_i
    cur_market = market
    while i < len(chunk):
        line = chunk[i].strip()
        if not line:
            i += 1
            continue
        # Skip metadata tags already consumed (do not treat as markets)
        low = line.lower()
        if low.startswith("sport:") or low.startswith("kick-off") or low.startswith("event:") or low.startswith("idfoevent:") or low == "live":
            i += 1
            continue
        nxt = chunk[i + 1].strip() if i + 1 < len(chunk) else ""
        if _safe_odds(line) is not None:
            # stray odds line
            i += 1
            continue
        # selection + odds pair
        if nxt and _safe_odds(nxt) is not None:
            odds = _safe_odds(nxt)
            assert odds is not None
            sel = _format_selection(cur_market, line)
            rows.append(
                Candidate(
                    date=match_date,
                    match=match,
                    selection=sel,
                    decimal_odds=odds,
                    sport=normalize_sport(sport),
                    market_type=cur_market,
                    evidence_key=f"{match}_{sel}_{odds}",
                    notes=f"nt_dump market={cur_market}",
                    kickoff=kickoff,
                )
            )
            i += 2
            continue
        # new market header (e.g. Totalt 179.5, HUB mid-block, Kart handikap, …)
        cur_market = line
        i += 1
    return rows


def _format_selection(market: str, selection: str) -> str:
    m = (market or "").strip()
    s = (selection or "").strip()
    if not m or m == "HUB":
        # HUB selections are team names / Uavgjort
        if s.lower() in ("uavgjort", "draw", "x"):
            return "Uavgjort"
        low = s.lower()
        if any(k in low for k in ("holder", "over", "under", "ja", "nei", "btts")):
            return s
        if "to win" in low or "vinner" in low:
            return s
        return f"{s} to Win"
    if m == "Vinner" or m.startswith("Vinner "):
        # 2-way moneyline: keep readable winner label
        if "inkludert overtid" in m.lower():
            return f"{m}: {s}"
        return f"Vinner: {s}"
    # Avoid double-prefix if selection already contains market cue
    if s.lower().startswith(m.lower()[:12]):
        return s
    # Compact common markets
    if m.lower().startswith("totalt antall mål") or m.lower().startswith("totalt "):
        # Over/Under lines often complete; prefix totals market when helpful
        if s.lower().startswith("over") or s.lower().startswith("under"):
            if "inkludert overtid" in m.lower() or re.search(r"\d+\.5", m):
                return f"{m}: {s}"
            return s
        return f"{m}: {s}"
    if m.lower() == "begge lag scorer":
        return f"BTTS {s}"
    if "handikap" in m.lower():
        return f"{m}: {s}"
    if m.startswith("1. omgang") or m.startswith("HUB") or m.startswith("1. Kart") or m.startswith("2. Kart"):
        return f"{m} — {s}"
    if m.startswith("1. Sett") or m.startswith("2. Sett"):
        return f"{m} — {s}"
    return f"{m}: {s}" if s not in m else s


def _infer_sport(home: str, away: str, chunk: list[str], *, default: str = "football") -> str:
    """
    Infer sport from NT dump block text → **canonical** taxonomy key.

    Priority:
      1) Explicit collector tag ``Sport: …`` (**authoritative** when present)
      2) Strong market keywords (darts before snooker; tennis; baseball; basketball; …)
      3) Weak cues — never force snooker from comma names alone
    """
    blob = " ".join(chunk[:80]).lower()
    homes = f"{home} {away}".lower()
    default_c = normalize_sport(default, default="football")

    # 1) Authoritative tag from multi-sport collector dumps
    for ln in chunk[:40]:
        s = (ln or "").strip()
        if s.lower().startswith("sport:"):
            tag = s.split(":", 1)[1].strip()
            # Ignore Sport-Source lines (handled by startswith sport: only exact)
            if s.lower().startswith("sport-source"):
                continue
            return normalize_sport(tag, default=default_c)

    # 2) Strong market / keyword cues (order matters)
    # Darts BEFORE snooker — both use "Last, First" names
    if any(
        k in blob
        for k in (
            "180s",
            " 180",
            "totalt antall 180",
            "flest 180s",
            "utsjekk",
            "checkout",
            "legs handikap",
            "leg handikap",
            "totalt antall runder",
            "runde handikap",
            "matchplay",
            "world matchplay",
            "premier league darts",
        )
    ):
        return "darts"
    if any(
        k in blob
        for k in (
            "century",
            "centuries",
            "frame handikap",
            "parti handikap",  # NT snooker frame HC wording
            "totalt antall frames",
            "totalt antall parti",
            "høyeste break",
            "highest break",
            "snooker",
        )
    ):
        return "snooker"
    # Basketball OT markets only — never bare "straffer" (football ET/penalties)
    if "inkludert overtid" in blob and "innings" not in blob:
        return "basketball"
    if "ekstra innings" in blob or "1. inning" in blob or re.search(r"\binning", blob):
        return "baseball"
    # Tennis — do NOT match bare "game" (too broad)
    if any(
        k in blob
        for k in (
            "game handikap",
            "totalt antall games",
            "1. sett",
            "2. sett",
            "sett -",
            "set handikap",
            "korrekt resultat (best av 3)",
            "korrekt resultat (best av 5)",
        )
    ):
        return "tennis"
    if "kart" in blob or ("best av 3" in blob and "kart" in blob):
        return "esports"
    if any(k in blob for k in ("mål", "begge lag", "handikap 3-veis", "uavgjort", "hjørnespark")):
        return "football"
    # Team tokens — require "X city" club form, never bare "city" alone (B7)
    if re.search(
        r"\b(fc|united|athletic|rovers|rangers|bk|if)\b",
        homes,
    ) or re.search(r"\b\w+\s+city\b", homes):
        return "football"

    # 3) Comma "Last, First" boards without market cues → unknown (NOT snooker)
    # Caller / Sport: tag / next collector run should supply identity.
    if "," in (home or "") or "," in (away or ""):
        return "unknown"

    return default_c

def _looks_like_csv(text: str) -> bool:
    first = text.strip().splitlines()[0] if text.strip() else ""
    return "match" in first.lower() and ("," in first or ";" in first)


def _parse_csv(path: Path) -> list[Candidate]:
    rows: list[Candidate] = []
    with open(path, newline="", encoding="utf-8") as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        for r in reader:
            # normalize keys
            norm = {re.sub(r"[^a-z0-9]+", "_", k.strip().lower()): v for k, v in r.items() if k}
            match = (norm.get("match") or norm.get("event") or "").strip()
            selection = (norm.get("selection") or norm.get("bet") or "").strip()
            odds = fnum(norm.get("decimal_odds") or norm.get("odds"))
            if not match or not selection or odds is None:
                continue
            kickoff = (norm.get("kickoff") or norm.get("kick_off") or "").strip()
            date = (norm.get("date") or "").strip() or _match_date_from_kickoff(kickoff)
            p_model = fnum(norm.get("p_model") or norm.get("prob"))
            raw_sport = (norm.get("sport") or "").strip()
            rows.append(
                Candidate(
                    date=date,
                    match=match,
                    selection=selection,
                    decimal_odds=odds,
                    sport=normalize_sport(raw_sport) if raw_sport else "",
                    market_type=(norm.get("market_type") or norm.get("market") or "").strip(),
                    p_model=p_model,
                    notes=(norm.get("notes") or "").strip(),
                    evidence_key=f"{match}_{selection}_{odds}",
                    kickoff=kickoff.replace("T", " ")[:16],
                )
            )
    return rows


def _parse_text(text: str) -> list[Candidate]:
    rows: list[Candidate] = []
    # pipe table
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or set(line) <= set("|-: "):
            continue
        if "|" in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 3:
                continue
            if parts[0].lower() in ("match", "event") and "odd" in parts[2].lower():
                continue
            odds = fnum(parts[2])
            if odds is None and len(parts) > 3:
                odds = fnum(parts[3])
            if odds is None:
                continue
            rows.append(
                Candidate(
                    date="",
                    match=parts[0],
                    selection=parts[1],
                    decimal_odds=odds,
                    evidence_key=f"{parts[0]}_{parts[1]}_{odds}",
                )
            )
            continue
        # Match - Selection @ 1.85
        m = re.match(r"(.+?)\s+[-–]\s+(.+?)\s*@\s*([0-9]+(?:[.,][0-9]+)?)", line)
        if m:
            odds = fnum(m.group(3))
            if odds is None:
                continue
            rows.append(
                Candidate(
                    date="",
                    match=m.group(1).strip(),
                    selection=m.group(2).strip(),
                    decimal_odds=odds,
                    evidence_key=f"{m.group(1).strip()}_{m.group(2).strip()}_{odds}",
                )
            )
    return rows


def attach_evidence(candidates: list[Candidate], evidence_dir: Path) -> None:
    """
    Attach evidence packs. Index match+selection once (O(files + candidates)).

    Phase 4: exact key first, then soft keys via ``normalize_*_key`` so
    ``Vinner: X`` packs still attach to ``X to Win`` candidates.

    HV v3: soft-key collisions prefer newest researched_at / mtime (not first-wins).
    Annotates board_odds_at_attach / odds_snapshot_missing for diagnostics only —
    never stamps board odds into odds_at_research for place eligibility.
    """
    from nt.evidence import evidence_path, load_evidence
    from nt.odds_common import evidence_pair_key
    from nt.pack_freshness import annotate_attach_diagnostics, pack_recency_ts

    by_key: dict[tuple[str, str], dict] = {}
    path_by_key: dict[tuple[str, str], Path] = {}
    by_soft: dict[tuple[str, str], dict] = {}
    path_by_soft: dict[tuple[str, str], Path] = {}
    if evidence_dir.exists():
        for p in evidence_dir.glob("*.json"):
            # skip templates subdirectory files only at top level
            if p.parent != evidence_dir:
                continue
            try:
                data = load_evidence(p)
            except Exception:
                continue
            if not data:
                continue
            m = str(data.get("match") or "").strip()
            s = str(data.get("selection") or "").strip()
            if m and s:
                prev_exact = by_key.get((m, s))
                prev_exact_path = path_by_key.get((m, s))
                if prev_exact is None or pack_recency_ts(data, p) >= pack_recency_ts(
                    prev_exact, prev_exact_path
                ):
                    by_key[(m, s)] = data
                    path_by_key[(m, s)] = p
                soft = evidence_pair_key(m, s)
                # Newest pack wins on soft collision (researched_at / mtime)
                prev = by_soft.get(soft)
                prev_path = path_by_soft.get(soft)
                if prev is None or pack_recency_ts(data, p) >= pack_recency_ts(prev, prev_path):
                    by_soft[soft] = data
                    path_by_soft[soft] = p

    for c in candidates:
        exact = (c.match or "", c.selection or "")
        ev = by_key.get(exact)
        used_path: Path | None = path_by_key.get(exact)
        if not ev:
            soft = evidence_pair_key(c.match, c.selection)
            ev = by_soft.get(soft)
            used_path = path_by_soft.get(soft)
        if not ev:
            path = evidence_path(evidence_dir, c.evidence_key or f"{c.match}_{c.selection}")
            ev = load_evidence(path)
            if ev:
                used_path = path
        if not ev:
            alt = evidence_dir / f"{(c.match or '').replace(' ', '_')}.json"
            ev = load_evidence(alt)
            if ev:
                used_path = alt
        if ev is not None:
            # Diagnostics only — never invent odds_at_research from board
            try:
                board = float(c.decimal_odds)
            except (TypeError, ValueError):
                board = 0.0
            ev = annotate_attach_diagnostics(ev, board)
        c.evidence = ev
        if used_path is not None and used_path.is_file():
            try:
                # Prefer project-relative path for portability
                c.evidence_path = str(used_path.as_posix())
            except Exception:
                c.evidence_path = str(used_path)
        if ev and c.p_model is None and ev.get("p_model") is not None:
            c.p_model = float(ev["p_model"])
