#!/usr/bin/env python3
"""
Migrate pack signal ids via sport card signal_id_aliases (alias → stable).

Dry-run by default. Rewrites signals{} keys in evidence/*.json when --apply.
Does not delete packs. Safe for PR1 migration window.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence_hierarchy.cards import load_sport_card
from nt.evidence_hierarchy.normalize import normalize_sport_for_research


def _migrate_pack(data: dict[str, Any], *, apply: bool) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    sport = normalize_sport_for_research(str(data.get("sport") or "default"))
    card = load_sport_card(sport)
    if card is None:
        return data, [f"no card for sport={sport}"]
    aliases = dict(card.signal_id_aliases or {})
    if not aliases:
        return data, ["no aliases on card"]
    signals = data.get("signals")
    if not isinstance(signals, dict) or not signals:
        return data, ["no signals"]
    new_signals: dict[str, Any] = {}
    changed = False
    for sid, payload in signals.items():
        stable = aliases.get(sid, sid)
        if stable != sid:
            notes.append(f"{sid} -> {stable}")
            changed = True
            if stable in new_signals and isinstance(new_signals[stable], dict):
                # keep existing stable if already filled
                if not (isinstance(payload, dict) and payload.get("filled")):
                    continue
            new_signals[stable] = payload
        else:
            if sid not in new_signals:
                new_signals[sid] = payload
    if changed and apply:
        data = dict(data)
        data["signals"] = new_signals
        data.setdefault("migration_notes", [])
        if isinstance(data["migration_notes"], list):
            data["migration_notes"].append(
                {"tool": "migrate_signal_ids", "changes": list(notes)}
            )
    return data, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate evidence pack signal ids")
    ap.add_argument(
        "--dir",
        type=Path,
        default=ROOT / "evidence",
        help="Evidence directory",
    )
    ap.add_argument("--apply", action="store_true", help="Write changes (default dry-run)")
    ap.add_argument("--limit", type=int, default=0, help="Max files (0=all)")
    args = ap.parse_args()
    paths = sorted(args.dir.glob("*.json"))
    if args.limit:
        paths = paths[: args.limit]
    n_changed = 0
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"skip {path.name}: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        new_data, notes = _migrate_pack(data, apply=args.apply)
        if notes and any("->" in n for n in notes):
            n_changed += 1
            print(f"{path.name}: {', '.join(notes)}")
            if args.apply:
                path.write_text(
                    json.dumps(new_data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"{mode}: {n_changed} packs with alias rewrites (of {len(paths)} scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
