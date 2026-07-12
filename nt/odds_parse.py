from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from nt.bets_io import fnum
from nt.portfolio import Candidate


def parse_odds_file(path: Path) -> list[Candidate]:
    """
    Supported formats:
    1) CSV with headers: date,match,selection,decimal_odds[,sport,market_type,p_model,notes]
    2) Simple markdown/text lines:
       Match | Selection | Odds
       or: Match - Selection @ 1.85
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv" or _looks_like_csv(text):
        return _parse_csv(path)
    return _parse_text(text)


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
            date = (norm.get("date") or "").strip()
            p_model = fnum(norm.get("p_model") or norm.get("prob"))
            rows.append(
                Candidate(
                    date=date,
                    match=match,
                    selection=selection,
                    decimal_odds=odds,
                    sport=(norm.get("sport") or "").strip(),
                    market_type=(norm.get("market_type") or norm.get("market") or "").strip(),
                    p_model=p_model,
                    notes=(norm.get("notes") or "").strip(),
                    evidence_key=f"{match}_{selection}_{odds}",
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
    from nt.evidence import evidence_path, load_evidence

    for c in candidates:
        path = evidence_path(evidence_dir, c.evidence_key or f"{c.match}_{c.selection}")
        # also try simpler keys
        alts = [
            path,
            evidence_dir / f"{c.match.replace(' ', '_')}.json",
        ]
        ev = None
        for p in alts:
            ev = load_evidence(p)
            if ev:
                break
        # glob partial
        if not ev and evidence_dir.exists():
            for p in evidence_dir.glob("*.json"):
                try:
                    data = load_evidence(p)
                except Exception:
                    continue
                if not data:
                    continue
                if data.get("match") == c.match and data.get("selection") == c.selection:
                    ev = data
                    break
        c.evidence = ev
        if ev and c.p_model is None and ev.get("p_model") is not None:
            c.p_model = float(ev["p_model"])
