"""Backfill bets.csv `date` from match kickoff (CEST calendar day), not place time.

Sources (first hit wins):
  1) kickoff= in notes
  2) data/odds/collections + latest.json + live_latest.json
  3) Kick-off: lines in inbox odds dumps (match vs name fuzzy)

Does not invent kickoffs for unknown matches.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import load_bets, write_bets
from nt.config import load_config, path_from_config

KO_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?")


def _norm_match(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace(" - ", " vs ").replace("–", "vs").replace("´", "'").replace("'", "'")
    s = re.sub(r"\s+", " ", s)
    return s


def _date_from_ko(ko: str) -> str:
    m = KO_RE.search(ko or "")
    return m.group(1) if m else ""


def build_kickoff_index() -> dict[str, str]:
    """match_key -> 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'."""
    idx: dict[str, str] = {}

    def add(name: str, ko: str) -> None:
        d = _date_from_ko(ko)
        if not name or not d:
            return
        full = ko.strip().replace("T", " ")[:16]
        key = _norm_match(name)
        # Prefer more specific kickoff times if already present as date-only
        if key not in idx or (len(full) > len(idx[key]) and ":" in full):
            idx[key] = full if ":" in full else d

    # Structured JSON odds
    paths = list((ROOT / "data" / "odds" / "collections").glob("*.json"))
    for extra in ("latest.json", "live_latest.json"):
        p = ROOT / "data" / "odds" / extra
        if p.exists():
            paths.append(p)
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        events = data if isinstance(data, list) else data.get("events") or []
        if not isinstance(events, list):
            continue
        for e in events:
            if not isinstance(e, dict):
                continue
            ko = str(e.get("kickoff") or e.get("kickoff_iso") or "")
            home = str(e.get("home") or "").strip()
            away = str(e.get("away") or "").strip()
            ev = str(e.get("event") or e.get("name") or "").strip()
            if home and away:
                add(f"{home} vs {away}", ko)
                add(f"{home} - {away}", ko)
            if ev:
                add(ev, ko)

    # Odds text dumps
    for p in sorted((ROOT / "inbox").glob("*.txt")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Split loosely on HUB / Vinner blocks
        parts = re.split(r"\n(?=HUB\n|Vinner(?:\s|\n))", text)
        for part in parts:
            lines = [ln.strip() for ln in part.splitlines() if ln.strip()]
            if not lines:
                continue
            ko_line = next((ln for ln in lines if ln.lower().startswith("kick-off")), "")
            if not ko_line:
                continue
            ko = ko_line.split(":", 1)[1].strip() if ":" in ko_line else ""
            # Event: Name or HUB home/away
            ev = ""
            for ln in lines:
                if ln.lower().startswith("event:"):
                    ev = ln.split(":", 1)[1].strip()
                    break
            if not ev and lines[0] == "HUB" and len(lines) >= 6:
                home, away = lines[1], lines[5]
                ev = f"{home} vs {away}"
            if not ev and lines[0].startswith("Vinner") and len(lines) >= 5:
                ev = f"{lines[1]} vs {lines[3]}"
            if ev:
                add(ev, ko)

    return idx


def lookup_kickoff(match: str, idx: dict[str, str]) -> str:
    key = _norm_match(match)
    if key in idx:
        return idx[key]
    # substring soft match
    for k, v in idx.items():
        if key in k or k in key:
            return v
    # token overlap
    toks = set(re.findall(r"[a-z0-9]+", key))
    best = ""
    best_n = 0
    for k, v in idx.items():
        kt = set(re.findall(r"[a-z0-9]+", k))
        n = len(toks & kt)
        if n >= 2 and n > best_n and n >= min(3, len(toks)):
            best_n = n
            best = v
    return best


def main() -> None:
    cfg = load_config()
    path = path_from_config(cfg, "bets")
    rows = load_bets(path)
    idx = build_kickoff_index()
    print(f"kickoff index size: {len(idx)}")

    changed = 0
    for r in rows:
        match = r.get("match") or ""
        old = (r.get("date") or "").strip()
        # Prefer kickoff already stored in notes
        notes = r.get("notes") or ""
        m_note = re.search(r"kickoff=([0-9T: +\-]+)", notes)
        ko = m_note.group(1).strip() if m_note else lookup_kickoff(match, idx)
        new_date = _date_from_ko(ko)
        if not new_date:
            print(f"SKIP (no kickoff): {match[:50]}")
            continue
        if ko and "kickoff=" not in notes:
            r["notes"] = ((notes + f"; kickoff={ko[:16]}").strip("; "))[:500]
        if old != new_date:
            print(f"UPDATE {old} -> {new_date} | {match[:50]} | ko={ko[:16]}")
            r["date"] = new_date
            changed += 1
        else:
            print(f"OK     {old} | {match[:50]} | ko={ko[:16]}")

    write_bets(path, rows)
    print(f"done; date changes: {changed}")


if __name__ == "__main__":
    main()
